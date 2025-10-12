import re
from urllib.parse import urlparse, unquote

import requests

from pos_tool_new.backend import Backend


class DownloadWarService(Backend):
    def transform_url(self, original_url):
        parsed_url = urlparse(original_url)
        path_parts = parsed_url.path.strip('/').split('/')
        if 'buildConfiguration' in path_parts:
            build_config_index = path_parts.index('buildConfiguration')
            if len(path_parts) > build_config_index + 2:
                project_build = f"{path_parts[build_config_index + 1]}/{path_parts[build_config_index + 2]}"
                new_url = f"https://{parsed_url.netloc}/repository/downloadAll/{project_build}:id/artifacts.zip"
                return new_url
        elif 'kpos.war' in path_parts:
            repo_index = path_parts.index('repository')
            if 'download' in path_parts[repo_index:]:
                download_index = repo_index + path_parts[repo_index:].index('download')
                if len(path_parts) > download_index + 2:
                    project_build = f"{path_parts[download_index + 1]}/{path_parts[download_index + 2]}"
                    new_url = f"https://{parsed_url.netloc}/repository/downloadAll/{project_build}/artifacts.zip"
                    return new_url
        return None

    def download_war(self, url, progress_callback=None, expected_size_mb=None):
        try:
            import time
            initial_url = url
            headers = {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "zh-CN,zh;q=0.9",
                "priority": "u=0, i",
                "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "none",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "cookie": "RememberMe=2055198417^266#-4234407954504083926; TCSESSIONID=2507ED4FAACCF3B89F28EFB2AF5E8F1F"
            }
            headers_2 = headers.copy()
            headers_2["cookie"] = "TCSESSIONID=765BD3E3AD0BF5B9185394176B0AAEC5"
            if 'buildConfiguration' in initial_url or 'kpos.war' in initial_url:
                transformed_url = self.transform_url(initial_url)
                if transformed_url:
                    initial_url = transformed_url
                    self.log(f"转换后的URL: {initial_url}", level="info")
            self.log("正在获取下载地址...")
            response = requests.get(initial_url, headers=headers, allow_redirects=False)
            if response.status_code != 302:
                return False, f"错误：期望状态码302，但收到{response.status_code}"
            redirect_url = response.headers.get('location')
            if not redirect_url:
                return False, "错误：未找到重定向URL"
            self.log(f"获取到最终下载地址: {redirect_url}")
            file_response = requests.get(redirect_url, headers=headers_2, stream=True)
            if file_response.status_code != 200:
                return False, f"错误：下载请求失败，状态码{file_response.status_code}"
            content_disposition = file_response.headers.get('content-disposition', '')
            filename_match = re.search(r"filename\*=UTF-8''(.+)", content_disposition)
            if filename_match:
                filename = unquote(filename_match.group(1)).strip(';')
            else:
                filename = "artifacts.zip"
            self.log(f"保存文件为: {filename}", level="info")
            total = int(file_response.headers.get('content-length', 0))
            if total == 0 and expected_size_mb:
                total = int(expected_size_mb * 1024 * 1024)
            downloaded = 0
            chunk_size = 8192
            start_time = time.time()
            last_time = start_time
            last_downloaded = 0
            with open(filename, 'wb') as f:
                for chunk in file_response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        # 只通过回调显示进度条，不再频繁记录日志
                        if now - last_time > 0.5 or (total and downloaded == total):
                            percent = 0
                            if total > 0:
                                percent = int(downloaded * 100 / total)
                                if percent > 100:
                                    percent = 100
                                if downloaded > total:
                                    downloaded = total
                            elapsed = now - last_time
                            if elapsed > 0:
                                speed = (downloaded - last_downloaded) / elapsed
                                if speed > 1024 * 1024:
                                    speed_str = f"{speed / (1024 * 1024):.2f} MB/s"
                                else:
                                    speed_str = f"{speed / 1024:.2f} KB/s"
                            else:
                                speed_str = None
                            if progress_callback:
                                progress_callback(percent, speed_str, downloaded, total)
                            last_time = now
                            last_downloaded = downloaded
            self.log("文件下载完成!", level="success")
            return True, filename
        except requests.exceptions.RequestException as e:
            self.log(f"网络请求错误: {e}", level="error")
            if progress_callback:
                progress_callback(-1, None, None, None)
            return False, f"网络请求错误: {e}"
        except Exception as e:
            self.log(f"发生未知错误: {e}", level="error")
            if progress_callback:
                progress_callback(-1, None, None, None)
            return False, f"发生未知错误: {e}"
