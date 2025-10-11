from pos_tool_new.backend import Backend
from PyQt6.QtCore import pyqtSignal
from PIL import Image
import os
import numpy as np
import math
import time

class GenerateImgService(Backend):
    def __init__(self):
        super().__init__()

    def generate_image(self, mode, width, height, mb, fmt):
        try:
            if mode == "dim":
                if not width or not height:
                    self.log("参数错误：未填写宽度和高度")
                    return None, "请填写宽度和高度"
                width = int(width)
                height = int(height)
            else:
                if not mb:
                    self.log("参数错误：未填写图片大小")
                    return None, "请填写图片大小"
                mb = float(mb)
                total_bytes = int(mb * 1024 * 1024)
                pixels = total_bytes // 3
                side = int(math.sqrt(pixels))
                width = side
                height = pixels // side
            # 彩虹渐变生成
            arr = self._sky_gradient(width, height)
            img = Image.fromarray(arr, 'RGB')
            # 兼容不同Pillow版本的LANCZOS
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                try:
                    resample = Image.LANCZOS
                except AttributeError:
                    resample = Image.ANTIALIAS
            img = img.resize((width, height), resample)
            timestamp = int(time.time())
            filename = f"{timestamp}_{width}x{height}.{fmt.lower()}"
            output_path = os.path.abspath(filename)
            img.save(output_path, fmt)
            self.log(f"生成图片成功: {output_path} 尺寸: {width}x{height} 格式: {fmt}")
            return output_path, None
        except Exception as e:
            self.log(f"生成图片失败: {e}")
            return None, str(e)

    def _sky_gradient(self, width, height):
        arr = np.zeros((height, width, 3), dtype=np.uint8)
        for y in range(height):
            for x in range(width):

                vertical_ratio = y / height

                r = int(200 + 55 * vertical_ratio)  # 200-255
                g = int(220 + 35 * vertical_ratio)  # 220-255
                b = int(255 - 35 * vertical_ratio)  # 255-220

                horizontal_variation = 0.98 + 0.04 * np.sin(x / width * 4 * np.pi)

                arr[y, x, 0] = min(255, int(r * horizontal_variation))
                arr[y, x, 1] = min(255, int(g * horizontal_variation))
                arr[y, x, 2] = min(255, int(b * horizontal_variation))

        return arr