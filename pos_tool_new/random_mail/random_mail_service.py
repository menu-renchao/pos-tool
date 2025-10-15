# random_mail_service.py
from pos_tool_new.backend import Backend
import json
import os
import requests
import random
import string
import re

class RandomMailService(Backend):
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.mail.tm"
        self.session = requests.Session()
        self.current_account = None
        self.accounts = []
        self.data_file = "email_accounts.json"
        self._load_accounts()
        self.counter = 0
        self._init_counter()

    def _load_accounts(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.accounts = json.load(f)
                    if self.accounts:
                        self.current_account = self.accounts[-1]
            except Exception:
                self._save_accounts()

    def _save_accounts(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, ensure_ascii=False, indent=2)

    def _init_counter(self):
        # 计数器用于生成唯一用户名
        if self.accounts:
            self.counter = len(self.accounts)
        else:
            self.counter = 0

    def _generate_username(self):
        # 生成唯一用户名
        self.counter += 1
        rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"user{self.counter}_{rand_str}"

    def create_account(self):
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
        for acc in self.accounts:
            if acc["email"] == email:
                self.current_account = acc
                return
        raise ValueError("邮箱不存在")

    def get_emails(self):
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
        """获取邮件HTML内容，复杂或过大内容则提示无法展示"""
        headers = {"Authorization": f"Bearer {self.current_account['token']}"}
        response = self.session.get(
            f"{self.base_url}/messages/{mail_id}",
            headers=headers
        )
        html_list = response.json().get("html", [""])
        if not html_list or not html_list[0]:
            return "<html><body><b>无内容</b></body></html>"
        html = html_list[0]
        # 判断复杂富文本标签或内容超长
        complex_tags = r'<(img|iframe|script|style|object|embed|link|video|audio|form|svg|canvas)[\s>]'
        max_len = 10*1024  # 进一步收紧最大长度为10KB
        if re.search(complex_tags, html, re.I) or len(html) > max_len:
            return "<html><body><b>内容过大或过于复杂，无法展示</b></body></html>"
        return html

    def _get_available_domain(self):
        response = self.session.get(f"{self.base_url}/domains")
        return response.json()["hydra:member"][0]["domain"]

    def delete_account(self, email):
        self.accounts = [acc for acc in self.accounts if acc['email'] != email]
        self._save_accounts()
        if self.current_account and self.current_account["email"] == email:
            self.current_account = self.accounts[-1] if self.accounts else None
