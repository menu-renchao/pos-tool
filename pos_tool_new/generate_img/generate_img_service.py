import math
import os
import time

import numpy as np
from PIL import Image

from pos_tool_new.backend import Backend


class GenerateImgService(Backend):
    def __init__(self):
        super().__init__()

    def generate_image(self, mode, width, height, mb, fmt):
        try:
            if mode == "dim":
                if not width or not height:
                    self.log("参数错误：未填写宽度和高度", "error")
                    return None, "请填写宽度和高度"
                width = int(width)
                height = int(height)
            else:
                if not mb:
                    self.log("参数错误：未填写图片大小", "error")
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
            self.log(f"生成图片成功: {output_path} 尺寸: {width}x{height} 格式: {fmt}", "success")
            return output_path, None
        except Exception as e:
            self.log(f"生成图片失败: {e}", "error")
            return None, str(e)

    def _sky_gradient(self, width, height):
        # 向量化实现，极大提升大图生成速度
        y = np.linspace(0, 1, height)[:, None]
        x = np.linspace(0, 1, width)[None, :]
        r = 200 + 55 * y
        g = 220 + 35 * y
        b = 255 - 35 * y
        horizontal_variation = 0.98 + 0.04 * np.sin(x * 4 * np.pi)
        r = np.clip(r * horizontal_variation, 0, 255)
        g = np.clip(g * horizontal_variation, 0, 255)
        b = np.clip(b * horizontal_variation, 0, 255)
        arr = np.stack([r, g, b], axis=-1).astype(np.uint8)
        return arr
