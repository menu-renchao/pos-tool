from flask import Flask, jsonify, send_file, abort
import os
import re

app = Flask(__name__)

# 配置：dist目录路径和exe文件前缀
BUILD_DIR = os.path.join(os.path.dirname(__file__), 'dist')
EXE_PREFIX = 'PosTestUtil_v'
EXE_SUFFIX = '.exe'


def get_latest_exe_info():
    """
    查找build目录下最新版本的exe文件和版本号
    返回 (exe_path, version) 或 (None, None)
    """
    if not os.path.exists(BUILD_DIR):
        return None, None
    version_pattern = re.compile(rf'{EXE_PREFIX}(\d+\.\d+\.\d+\.\d+){EXE_SUFFIX}')
    latest_version = None
    latest_exe = None
    for root, dirs, files in os.walk(BUILD_DIR):
        for file in files:
            match = version_pattern.match(file)
            if match:
                version = match.group(1)
                if (latest_version is None) or (tuple(map(int, version.split('.'))) > tuple(map(int, latest_version.split('.')))):
                    latest_version = version
                    latest_exe = os.path.join(root, file)
    return latest_exe, latest_version


@app.route('/api/version', methods=['GET'])
def get_version():
    _, version = get_latest_exe_info()
    if version:
        return jsonify({'version': version})
    else:
        return jsonify({'error': 'No exe found'}), 404


@app.route('/api/download', methods=['GET'])
def download_exe():
    exe_path, version = get_latest_exe_info()
    if exe_path and os.path.exists(exe_path):
        return send_file(exe_path, as_attachment=True, download_name=f'PosTestUtil_v{version}.exe')
    else:
        abort(404, 'No exe found')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
