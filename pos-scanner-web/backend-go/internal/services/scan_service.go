package services

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

// ScanStatus represents the current scan status
type ScanStatus struct {
	mu         sync.RWMutex
	IsScanning bool                      `json:"is_scanning"`
	Progress   int                       `json:"progress"`
	CurrentIP  string                    `json:"current_ip"`
	Results    []map[string]interface{}  `json:"results"`
	Error      string                    `json:"error"`
}

// ScanService handles network scanning operations
type ScanService struct {
	status *ScanStatus
	cancel context.CancelFunc
	mu     sync.Mutex
}

// NewScanService creates a new scan service
func NewScanService() *ScanService {
	return &ScanService{
		status: &ScanStatus{
			IsScanning: false,
			Progress:   0,
			Results:    make([]map[string]interface{}, 0),
		},
	}
}

// GetStatus returns the current scan status
func (s *ScanService) GetStatus() *ScanStatus {
	s.status.mu.RLock()
	defer s.status.mu.RUnlock()
	return &ScanStatus{
		IsScanning: s.status.IsScanning,
		Progress:   s.status.Progress,
		CurrentIP:  s.status.CurrentIP,
		Results:    s.status.Results,
		Error:      s.status.Error,
	}
}

// GetLocalIPs returns all local IPv4 addresses
func (s *ScanService) GetLocalIPs() ([]string, error) {
	ips := make([]string, 0)

	// Try hostname lookup first
	hostname, err := os.Hostname()
	if err == nil {
		hostnameIPs, err := net.LookupHost(hostname)
		if err == nil {
			for _, ip := range hostnameIPs {
				if net.ParseIP(ip).To4() != nil && !strings.HasPrefix(ip, "127.") {
					ips = append(ips, ip)
				}
			}
		}
	}

	// Fallback: get all network interfaces
	if len(ips) == 0 {
		ifaces, err := net.Interfaces()
		if err != nil {
			return nil, err
		}
		for _, iface := range ifaces {
			addrs, err := iface.Addrs()
			if err != nil {
				continue
			}
			for _, addr := range addrs {
				if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() && ipnet.IP.To4() != nil {
					ips = append(ips, ipnet.IP.String())
				}
			}
		}
	}

	// If still empty, try another approach
	if len(ips) == 0 {
		conn, err := net.Dial("udp", "8.8.8.8:80")
		if err == nil {
			localAddr := conn.LocalAddr().(*net.UDPAddr)
			ips = append(ips, localAddr.IP.String())
			conn.Close()
		}
	}

	return ips, nil
}

// StartScan initiates a network scan
func (s *ScanService) StartScan(localIP string, onResult func(result map[string]interface{})) error {
	s.mu.Lock()
	if s.status.IsScanning {
		s.mu.Unlock()
		return fmt.Errorf("scan already in progress")
	}

	// Reset status
	s.status.mu.Lock()
	s.status.IsScanning = true
	s.status.Progress = 0
	s.status.CurrentIP = ""
	s.status.Results = make([]map[string]interface{}, 0)
	s.status.Error = ""
	s.status.mu.Unlock()

	ctx, cancel := context.WithCancel(context.Background())
	s.cancel = cancel
	s.mu.Unlock()

	go s.performScan(ctx, localIP, onResult)

	return nil
}

// StopScan stops the current scan
func (s *ScanService) StopScan() {
	s.mu.Lock()
	if s.cancel != nil {
		s.cancel()
	}
	s.status.mu.Lock()
	s.status.IsScanning = false
	s.status.mu.Unlock()
	s.mu.Unlock()
}

// performScan executes the actual network scan
func (s *ScanService) performScan(ctx context.Context, localIP string, onResult func(result map[string]interface{})) {
	defer func() {
		s.status.mu.Lock()
		s.status.IsScanning = false
		s.status.mu.Unlock()
	}()

	// Get network range
	_, ipNet, err := net.ParseCIDR(localIP + "/23")
	if err != nil {
		s.status.mu.Lock()
		s.status.Error = err.Error()
		s.status.mu.Unlock()
		return
	}

	// Generate all hosts in the network
	hosts := generateHosts(ipNet)
	totalHosts := len(hosts)

	// Scan ports concurrently
	openIPs := make([]string, 0)
	var mu sync.Mutex
	var scannedCount int

	// Use worker pool pattern
	workerCount := 200
	ipChan := make(chan string, workerCount)
	resultChan := make(chan string, workerCount)

	var wg sync.WaitGroup

	// Start workers
	for i := 0; i < workerCount; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for ip := range ipChan {
				select {
				case <-ctx.Done():
					return
				default:
					if s.scanPort(ip, 22080, 2) {
						resultChan <- ip
					}
					// Update progress more smoothly
					mu.Lock()
					scannedCount++
					progress := scannedCount * 40 / totalHosts
					if progress > 40 {
						progress = 40
					}
					s.status.mu.Lock()
					s.status.Progress = progress
					s.status.CurrentIP = ip
					s.status.mu.Unlock()
					mu.Unlock()
				}
			}
		}()
	}

	// Collect results
	go func() {
		wg.Wait()
		close(resultChan)
	}()

	// Send IPs to workers
	go func() {
		for _, ip := range hosts {
			select {
			case <-ctx.Done():
				break
			default:
				ipChan <- ip
			}
		}
		close(ipChan)
	}()

	// Collect open IPs with progress updates
	s.status.mu.Lock()
	s.status.Progress = 5
	s.status.mu.Unlock()

	for ip := range resultChan {
		mu.Lock()
		openIPs = append(openIPs, ip)
		scannedCount++
		progress := 5 + scannedCount*40/totalHosts
		if progress > 45 {
			progress = 45
		}
		s.status.mu.Lock()
		s.status.Progress = progress
		s.status.mu.Unlock()
		mu.Unlock()
	}

	// Port scanning complete
	s.status.mu.Lock()
	s.status.Progress = 45
	s.status.mu.Unlock()

	// Fetch device info concurrently
	totalOpen := len(openIPs)
	if totalOpen == 0 {
		totalOpen = 1
	}

	// Use worker pool for fetching device info
	fetchWorkerCount := 100 // 并发数
	if fetchWorkerCount > totalOpen {
		fetchWorkerCount = totalOpen
	}

	fetchChan := make(chan string, fetchWorkerCount)
	fetchResultChan := make(chan map[string]interface{}, fetchWorkerCount)
	var fetchWg sync.WaitGroup
	var completedCount int

	// Start fetch workers
	for i := 0; i < fetchWorkerCount; i++ {
		fetchWg.Add(1)
		go func() {
			defer fetchWg.Done()
			for ip := range fetchChan {
				select {
				case <-ctx.Done():
					return
				default:
					result := s.fetchAndProcess(ip, 22080)
					fetchResultChan <- result
				}
			}
		}()
	}

	// Collect results
	go func() {
		fetchWg.Wait()
		close(fetchResultChan)
	}()

	// Send IPs to fetch workers
	go func() {
		for _, ip := range openIPs {
			select {
			case <-ctx.Done():
				return
			default:
				fetchChan <- ip
			}
		}
		close(fetchChan)
	}()

	// Collect fetch results
	for result := range fetchResultChan {
		s.status.mu.Lock()
		s.status.Results = append(s.status.Results, result)
		completedCount++
		// Update progress (45-95%)
		s.status.Progress = 45 + completedCount*50/totalOpen
		if s.status.Progress > 95 {
			s.status.Progress = 95
		}
		if ip, ok := result["ip"].(string); ok {
			s.status.CurrentIP = ip
		}
		s.status.mu.Unlock()

		if onResult != nil {
			onResult(result)
		}
	}

	// Complete
	s.status.mu.Lock()
	s.status.Progress = 100
	s.status.CurrentIP = ""
	s.status.mu.Unlock()
}

// scanPort checks if a port is open on the given IP
func (s *ScanService) scanPort(ip string, port, timeout int) bool {
	address := net.JoinHostPort(ip, strconv.Itoa(port))
	conn, err := net.DialTimeout("tcp", address, time.Duration(timeout)*time.Second)
	if err != nil {
		return false
	}
	conn.Close()
	return true
}

// fetchAndProcess retrieves device information
func (s *ScanService) fetchAndProcess(ip string, port int) map[string]interface{} {
	fullData := s.fetchCompanyProfile(ip, port, 5, 2)
	simpleData := s.extractRequiredInfo(fullData)
	deviceType := s.guessOS(ip, port, 3)

	merchantID := ""
	if v, ok := simpleData["merchantId"].(string); ok {
		merchantID = v
	}

	status := "success"
	if _, hasError := simpleData["error"]; hasError {
		status = "error"
	}

	return map[string]interface{}{
		"ip":         ip,
		"merchantId": merchantID,
		"name":       simpleData["name"],
		"version":    simpleData["version"],
		"type":       deviceType,
		"status":     status,
		"error":      simpleData["error"],
		"fullData":   fullData,
	}
}

// fetchCompanyProfile retrieves the company profile from a device
func (s *ScanService) fetchCompanyProfile(ip string, port, timeout, maxRetries int) map[string]interface{} {
	url := fmt.Sprintf("http://%s:%d/kpos/webapp/store/fetchCompanyProfile", ip, port)

	for attempt := 0; attempt < maxRetries; attempt++ {
		client := &http.Client{Timeout: time.Duration(timeout) * time.Second}
		resp, err := client.Get(url)
		if err != nil {
			continue
		}
		defer resp.Body.Close()

		if resp.StatusCode == http.StatusOK {
			body, err := io.ReadAll(resp.Body)
			if err != nil {
				continue
			}

			var result map[string]interface{}
			if err := json.Unmarshal(body, &result); err != nil {
				continue
			}
			return result
		}
	}

	return map[string]interface{}{"error": "Failed after max retries"}
}

// guessOS determines the OS type of a device
func (s *ScanService) guessOS(ip string, port, timeout int) string {
	url := fmt.Sprintf("http://%s:%d/kpos/webapp/os/getOSType", ip, port)

	client := &http.Client{Timeout: time.Duration(timeout) * time.Second}
	resp, err := client.Get(url)
	if err != nil {
		return "Unknown"
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		body, err := io.ReadAll(resp.Body)
		if err != nil {
			return "Unknown"
		}

		var result map[string]interface{}
		if err := json.Unmarshal(body, &result); err != nil {
			return "Unknown"
		}

		if os, ok := result["os"].(string); ok {
			return os
		}
	}

	return "Unknown"
}

// extractRequiredInfo extracts required fields from API response
func (s *ScanService) extractRequiredInfo(apiResponse map[string]interface{}) map[string]interface{} {
	company, ok := apiResponse["company"].(map[string]interface{})
	if !ok {
		return map[string]interface{}{"error": "No company field"}
	}

	result := make(map[string]interface{})
	if merchantID, ok := company["merchantId"].(string); ok {
		result["merchantId"] = merchantID
	}
	if name, ok := company["name"].(string); ok {
		result["name"] = name
	}
	if appInfo, ok := company["appInfo"].(map[string]interface{}); ok {
		if version, ok := appInfo["version"].(string); ok {
			result["version"] = version
		}
	}

	if len(result) == 0 {
		return map[string]interface{}{"error": "No required fields"}
	}

	return result
}

// generateHosts generates all host IPs in a network
func generateHosts(ipNet *net.IPNet) []string {
	hosts := make([]string, 0)

	ip := make(net.IP, len(ipNet.IP))
	copy(ip, ipNet.IP)

	for ip := ip.Mask(ipNet.Mask); ipNet.Contains(ip); inc(ip) {
		// Skip network and broadcast addresses
		if !ip.Equal(ipNet.IP.Mask(ipNet.Mask)) && !ip.Equal(broadcast(ipNet)) {
			hosts = append(hosts, ip.String())
		}
	}

	return hosts
}

// inc increments an IP address
func inc(ip net.IP) {
	for j := len(ip) - 1; j >= 0; j-- {
		ip[j]++
		if ip[j] > 0 {
			break
		}
	}
}

// broadcast returns the broadcast address of a network
func broadcast(ipNet *net.IPNet) net.IP {
	ip := make(net.IP, len(ipNet.IP))
	copy(ip, ipNet.IP)

	for i := 0; i < len(ip); i++ {
		ip[i] |= ^ipNet.Mask[i]
	}

	return ip
}

// FetchDeviceDetails fetches detailed information for a specific device
func (s *ScanService) FetchDeviceDetails(ip string) (map[string]interface{}, error) {
	return s.fetchCompanyProfile(ip, 22080, 5, 2), nil
}
