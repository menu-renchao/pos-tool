import re
import subprocess


def get_ttl(ip):
    try:
        output = subprocess.check_output(f'ping -n 1 {ip}', shell=True, encoding='gbk')
        match = re.search(r'TTL=(\d+)', output, re.IGNORECASE)
        if not match:
            match = re.search(r'TTL=(\d+)', output, re.IGNORECASE)
        if match:
            return int(match.group(1))
    except Exception as e:
        print(f'Error: {e}')
    return None


def guess_os_by_ttl(ttl):
    if ttl == 128:
        return "Windows"
    elif ttl == 64:
        return "Ubuntu"
    elif ttl == 255:
        return "Router/Cisco Device"
    else:
        return "Unknown OS"


if __name__ == "__main__":
    target_ip = input("Enter target IP (e.g., 192.168.1.1): ")
    ttl = get_ttl(target_ip)
    if ttl:
        print(f"Detected TTL: {ttl}")
        os_guess = guess_os_by_ttl(ttl)
        print(f"Possible OS: {os_guess}")
    else:
        print("Failed to detect TTL.")
