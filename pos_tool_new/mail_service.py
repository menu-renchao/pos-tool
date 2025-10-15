import json
import os
import random
import re
import string
import requests


class MailTM:
    def __init__(self):
        self.base_url = "https://api.mail.tm"
        self.session = requests.Session()
        self.current_account = None
        self.accounts = []
        self.data_file = "email_accounts.json"
        self._load_accounts()  # 加载已有账户
        self.counter = 0
        self._init_counter()  # 初始化计数器

    def _load_accounts(self):
        """从JSON文件加载账户数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.accounts = json.load(f)
                    if self.accounts:
                        self.current_account = self.accounts[-1]
            except Exception:
                # 文件损坏时创建新文件
                self._save_accounts()

    def _save_accounts(self):
        """保存账户数据到JSON文件"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, ensure_ascii=False, indent=2)

    def create_account(self):
        """创建新邮箱账户"""
        domain = self._get_available_domain()
        email = f"{self._generate_username()}@{domain}"
        password = "Temp@1234"

        # 注册账户
        self.session.post(
            f"{self.base_url}/accounts",
            json={"address": email, "password": password}
        )

        # 获取Token
        token = self.session.post(
            f"{self.base_url}/token",
            json={"address": email, "password": password}
        ).json()["token"]

        account = {"email": email, "token": token}
        self.current_account = account
        self.accounts.append(account)
        self._save_accounts()
        return email

    def switch_account(self, email):
        """切换到历史邮箱"""
        for acc in self.accounts:
            if acc["email"] == email:
                self.current_account = acc
                return
        raise ValueError("邮箱不存在")

    def get_emails(self):
        """获取邮件列表（按时间倒序）"""
        if not self.current_account:
            return []

        headers = {"Authorization": f"Bearer {self.current_account['token']}"}
        response = self.session.get(
            f"{self.base_url}/messages?page=1",
            headers=headers
        )

        emails = response.json().get("hydra:member", [])
        return sorted(emails, key=lambda x: x["createdAt"], reverse=True)

    def get_email_content(self, mail_id):
        """获取邮件HTML内容"""
        headers = {"Authorization": f"Bearer {self.current_account['token']}"}
        response = self.session.get(
            f"{self.base_url}/messages/{mail_id}",
            headers=headers
        )
        return response.json().get("html", [""])[0]

    def _get_available_domain(self):
        """获取可用域名"""
        response = self.session.get(f"{self.base_url}/domains")
        return response.json()["hydra:member"][0]["domain"]

    def delete_account(self, email):
        """删除指定邮箱账户"""
        # 从内存中移除
        self.accounts = [acc for acc in self.accounts if acc['email'] != email]

        # 如果删除的是当前账户，切换到其他账户或设为None
        if self.current_account and self.current_account['email'] == email:
            self.current_account = self.accounts[-1] if self.accounts else None

        # 保存更改
        self._save_accounts()

    def _generate_username(self):
        """生成递增前缀+随机字母的用户名"""
        prefix = f"{self.counter:04d}"
        suffix = ''.join(random.choices(string.ascii_lowercase, k=6))
        self.counter += 1
        return prefix + suffix

    def _init_counter(self):
        """从已有账户初始化计数器"""
        if self.accounts:
            last_email = self.accounts[-1]['email']
            match = re.match(r'^(\d{4})[a-z]{6}@', last_email.split('@')[0])
            if match:
                self.counter = int(match.group(1)) + 1