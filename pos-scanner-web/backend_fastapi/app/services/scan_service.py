import asyncio
import ipaddress
import json
import logging
import socket
from typing import List, Dict, Any, Optional

import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScanPosService:
    def __init__(self, local_ip: Optional[str] = None):
        self.local_ip = local_ip

    @staticmethod
    async def guess_os_by_ip_async(ip: str, port: int = 22080, timeout: int = 3) -> str:
        url = f"http://{ip}:{port}/kpos/webapp/os/getOSType"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("os", "Unknown")
                return "Unknown"
        except Exception:
            return "Unknown"

    async def fetch_company_profile_async(
        self, ip: str, port: int = 22080, timeout: int = 5, max_retries: int = 2
    ) -> Dict[str, Any]:
        url = f"http://{ip}:{port}/kpos/webapp/store/fetchCompanyProfile"
        last_error = None

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        return response.json()
                    last_error = f"HTTP {response.status_code}"
                    logger.warning(
                        f"Failed to get device info {ip}: {last_error} (attempt {attempt + 1}/{max_retries})"
                    )
                except httpx.RequestError as e:
                    last_error = f"Request error: {str(e)}"
                    logger.warning(
                        f"Request error {ip}: {last_error} (attempt {attempt + 1}/{max_retries})"
                    )
                except json.JSONDecodeError as e:
                    last_error = f"JSON decode error: {str(e)}"
                    logger.warning(
                        f"JSON parse failed {ip}: {last_error} (attempt {attempt + 1}/{max_retries})"
                    )

        logger.error(f"Failed to get device info {ip}: {last_error}")
        return {"error": f"Failed after {max_retries} retries: {last_error}"}

    async def _scan_port_async(
        self, ip: str, port: int, timeout: float = 2.0
    ) -> Optional[str]:
        """Scan if port is open on specified IP."""
        try:
            # Use asyncio for async socket connection
            future = asyncio.open_connection(str(ip), port)
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return str(ip)
        except asyncio.TimeoutError:
            logger.debug(f"Port scan timeout: {ip}:{port}")
            return None
        except ConnectionRefusedError:
            logger.debug(f"Connection refused: {ip}:{port}")
            return None
        except Exception as e:
            logger.debug(f"Port scan error {ip}:{port}: {type(e).__name__}")
            return None

    def _get_local_network(self) -> ipaddress.IPv4Network:
        local_ip = (
            self.local_ip
            if self.local_ip
            else socket.gethostbyname(socket.gethostname())
        )
        return ipaddress.IPv4Network(f"{local_ip}/23", strict=False)

    def _extract_required_info(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        try:
            company = api_response.get("company", {})
            result = {
                "merchantId": company.get("merchantId"),
                "name": company.get("name"),
                "version": company.get("appInfo", {}).get("version"),
            }
            return {k: v for k, v in result.items() if v is not None} or {
                "error": "No required fields"
            }
        except Exception as e:
            return {"error": str(e)}

    async def _scan_open_ips_async(
        self,
        hosts: List[ipaddress.IPv4Address],
        port: int,
        scan_status: Dict[str, Any],
        total_hosts: int,
    ) -> List[str]:
        """Scan for open ports asynchronously."""
        open_ips = []
        semaphore = asyncio.Semaphore(200)  # Limit concurrent connections

        async def scan_with_semaphore(ip, index):
            async with semaphore:
                scan_status["progress"] = (index + 1) * 50 // total_hosts
                scan_status["current_ip"] = str(ip)
                result = await self._scan_port_async(ip, port)
                return result

        tasks = [scan_with_semaphore(ip, i) for i, ip in enumerate(hosts)]
        results = await asyncio.gather(*tasks)

        for result in results:
            if result:
                open_ips.append(result)
                logger.debug(f"Found open port: {result}:{port}")

        return open_ips

    async def _fetch_and_process_async(self, ip: str, port: int) -> Dict[str, Any]:
        full_data = await self.fetch_company_profile_async(ip, port)
        simple_data = self._extract_required_info(full_data)
        device_type = await self.guess_os_by_ip_async(ip, port)

        return {
            "ip": ip,
            "merchantId": simple_data.get("merchantId", ""),
            "name": simple_data.get("name", ""),
            "version": simple_data.get("version", ""),
            "type": device_type,
            "status": "success" if "error" not in simple_data else "error",
            "error": simple_data.get("error", ""),
            "fullData": full_data,
        }

    def get_local_ips(self) -> List[str]:
        """Get all local IPv4 addresses."""
        ips = set()
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if "." in ip and not ip.startswith("127."):
                ips.add(ip)
        return list(ips)
