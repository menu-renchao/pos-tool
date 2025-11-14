import re

from PyQt6.QtCore import QObject, pyqtSignal

from pos_tool_new.utils.log_manager import global_log_manager


class Backend(QObject):
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def log(self, msg, level="info"):
        """Log a message with timestamp and level."""
        global_log_manager.log(msg, level)

    @staticmethod
    def get_env_type_value(env):
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

    @staticmethod
    def get_target_domain_suffix(env):
        """Get the target domain suffix based on environment."""
        return {
            "QA": "menusifucloudqa.com",
            "PROD": "menusifucloud.com",
            "DEV": "menusifudev.com"
        }.get(env, "")

