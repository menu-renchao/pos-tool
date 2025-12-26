import math
import os
import time

import numpy as np
from PIL import Image

from pos_tool_new.backend import Backend


class GenerateImgService(Backend):
    def __init__(self):
        super().__init__()

    def generate_image(self, mode, width, height, mb, fmt, color_mode="gradient", color=(255,255,255)):
        try:
            if mode == "dim":
                if not width or not height:
                    self.log("参数错误：未填写宽度和高度", "error")
                    return None, "请填写宽度和高度"
                width = int(width)
                height = int(height)
                target_bytes = None
                arr = self._make_colored_img(width, height, color_mode, color)
                img = Image.fromarray(arr, 'RGB')
                # 修复：生成 output_path 并保存图片
                timestamp = int(time.time())
                filename = f"{timestamp}_{width}x{height}.{fmt.lower()}"
                output_path = os.path.abspath(filename)
                if fmt.lower() in ["jpeg", "jpg"]:
                    img.save(output_path, fmt, quality=100)
                elif fmt.lower() == "png":
                    img.save(output_path, fmt, compress_level=0)
                else:
                    img.save(output_path, fmt)
            else:
                if not mb:
                    self.log("参数错误：未填写图片大小", "error")
                    return None, "请填写图片大小"
                mb = float(mb)
                target_bytes = int(mb * 1024 * 1024)
                max_attempts = 10
                base_pixels = target_bytes // 3
                best_diff = float('inf')
                best_path = None
                best_shape = (0, 0)
                temp_files = []
                for attempt in range(max_attempts):
                    scale = 1.0 + attempt * 0.25
                    pixels = int(base_pixels * scale)
                    side = int(math.sqrt(pixels))
                    width = side
                    height = pixels // side
                    arr = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
                    img = Image.fromarray(arr, 'RGB')
                    try:
                        resample = Image.Resampling.LANCZOS
                    except AttributeError:
                        resample = 3
                    img = img.resize((width, height), resample)
                    timestamp = int(time.time())
                    filename = f"{timestamp}_{width}x{height}_attempt{attempt}.{fmt.lower()}"
                    output_path = os.path.abspath(filename)
                    temp_files.append(output_path)
                    if fmt.lower() in ["jpeg", "jpg"]:
                        img.save(output_path, fmt, quality=100)
                    elif fmt.lower() == "png":
                        img.save(output_path, fmt, compress_level=0)
                    else:
                        img.save(output_path, fmt)
                    actual_size = os.path.getsize(output_path)
                    diff = abs(actual_size - target_bytes)
                    if diff < best_diff:
                        best_diff = diff
                        best_path = output_path
                        best_shape = (width, height)
                    if actual_size >= target_bytes * 0.98:
                        break
                # 删除多余的临时图片，只保留best_path
                for f in temp_files:
                    if f != best_path and os.path.exists(f):
                        try:
                            os.remove(f)
                        except Exception:
                            pass
                output_path = best_path
                width, height = best_shape
            self.log(f"生成图片成功: {output_path} 尺寸: {width}x{height} 格式: {fmt}", "success")
            return output_path, None
        except Exception as e:
            self.log(f"生成图片失败: {e}", "error")
            return None, str(e)

    def _make_colored_img(self, width, height, color_mode, color):
        if color_mode == "solid":
            arr = np.ones((height, width, 3), dtype=np.uint8) * np.array(color, dtype=np.uint8)
        elif color_mode == "gradient":
            arr = self._sky_gradient(width, height)
        elif color_mode == "block":
            arr = np.zeros((height, width, 3), dtype=np.uint8)
            arr[:height//2, :, :] = np.array(color, dtype=np.uint8)
            arr[height//2:, :, :] = np.random.randint(0, 256, (height//2, width, 3), dtype=np.uint8)
        elif color_mode == "noise":
            arr = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        else:
            arr = self._sky_gradient(width, height)
        return arr

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
