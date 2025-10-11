import re

from PyQt6.QtCore import QObject, pyqtSignal


class Backend(QObject):
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def log(self, msg):
        """Log a message with timestamp."""
        self.log_signal.emit(msg)

    def get_env_type_value(self, env):
        """Get the environment type value based on environment."""
        return {
            "QA": "integration",
            "PROD": "production",
            "DEV": "development"
        }.get(env, "")

    def replace_domain(self, content, env):
        """Replace domain in content with the target domain for the given environment."""
        suffix = self.get_target_domain_suffix(env)
        return re.sub(
            r'(https://[a-zA-Z0-9\-]+?)\.menusifu(cloud)?(qa|dev)?\.com',
            rf'\1.{suffix}',
            content
        )

    def get_target_domain_suffix(self, env):
        """Get the target domain suffix based on environment."""
        return {
            "QA": "menusifucloudqa.com",
            "PROD": "menusifucloud.com",
            "DEV": "menusifudev.com"
        }.get(env, "")
