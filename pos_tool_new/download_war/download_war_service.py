import re
from urllib.parse import urlparse, unquote
import requests
from pos_tool_new.backend import Backend


class DownloadWarService(Backend):
    def transform_url(self, original_url):
        parsed_url = urlparse(original_url)
        path_parts = parsed_url.path.strip('/').split('/')
        if 'buildConfiguration' in path_parts:
            idx = path_parts.index('buildConfiguration')
            if len(path_parts) > idx + 2:
                project_build = f"{path_parts[idx + 1]}/{path_parts[idx + 2]}"
                return f"https://{parsed_url.netloc}/repository/downloadAll/{project_build}:id/artifacts.zip"
        elif 'kpos.war' in path_parts:
            idx = path_parts.index('repository')
            if 'download' in path_parts[idx:]:
                download_idx = idx + path_parts[idx:].index('download')
                if len(path_parts) > download_idx + 2:
                    project_build = f"{path_parts[download_idx + 1]}/{path_parts[download_idx + 2]}"
                    return f"https://{parsed_url.netloc}/repository/downloadAll/{project_build}/artifacts.zip"
        return None

    def download_war(self, url, progress_callback=None, expected_size_mb=None):
        try:
            headers = {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "cookie": "TCSESSIONID=2507ED4FAACCF3B89F28EFB2AF5E8F1F"
            }
            headers_2 = headers.copy()
            headers_2["cookie"] = "TCSESSIONID=765BD3E3AD0BF5B9185394176B0AAEC5"

            if 'buildConfiguration' in url or 'kpos.war' in url:
                transformed_url = self.transform_url(url)
                if transformed_url:
                    url = transformed_url

            self.log("正在解析下载地址...")
            response = requests.get(url, headers=headers, allow_redirects=False)
            if response.status_code != 302:
                return False, f"错误：期望状态码302，但收到{response.status_code}"

            redirect_url = response.headers.get('location')
            if not redirect_url:
                return False, "错误：未找到重定向URL"

            self.log("解析成功！即将开始下载...", "success")
            file_response = requests.get(redirect_url, headers=headers_2, stream=True)
            if file_response.status_code != 200:
                return False, f"错误：下载请求失败，状态码{file_response.status_code}"

            content_disposition = file_response.headers.get('content-disposition', '')
            filename = re.search(r"filename\*=UTF-8''(.+)", content_disposition)
            filename = unquote(filename.group(1)).strip(';') if filename else "artifacts.zip"
            self.log(f"保存文件为: {filename}", level="info")

            total = int(file_response.headers.get('content-length', 0)) or int(expected_size_mb * 1024 * 1024) if expected_size_mb else 0
            downloaded, chunk_size = 0, 8192

            with open(filename, 'wb') as f:
                for chunk in file_response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            percent = int(downloaded * 100 / total) if total else 0
                            speed = f"{downloaded / 1024:.2f} KB/s"
                            progress_callback(percent, speed, downloaded, total)

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