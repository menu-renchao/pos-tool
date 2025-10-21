# random_mail_service.py
import json
import os
import random
import string

import requests

from pos_tool_new.backend import Backend


class RandomMailService(Backend):
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.mail.tm"
        self.session = requests.Session()
        self.current_account = None
        self.accounts = []
        self.data_file = "email_accounts.json"
        self.counter_file = "email_counter.count"  # 使用更专业的后缀
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
        # 持久化计数器，保证自增
        if os.path.exists(self.counter_file):
            try:
                with open(self.counter_file, 'r', encoding='utf-8') as f:
                    self.counter = int(f.read().strip() or '0')
            except Exception:
                self.counter = 0
        else:
            self.counter = 0

    def _generate_username(self):
        # 生成唯一用户名，持久化自增
        self.counter += 1
        try:
            with open(self.counter_file, 'w', encoding='utf-8') as f:
                f.write(str(self.counter))
        except Exception:
            pass
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
        """获取邮件HTML内容，始终正常展示，无论大小和复杂度"""
        headers = {"Authorization": f"Bearer {self.current_account['token']}"}
        response = self.session.get(
            f"{self.base_url}/messages/{mail_id}",
            headers=headers
        )
        html_list = response.json().get("html", [""])
        if not html_list or not html_list[0]:
            return "<html><body><b>无内容</b></body></html>"
        html = html_list[0]
        return html

    def _get_available_domain(self):
        response = self.session.get(f"{self.base_url}/domains")
        return response.json()["hydra:member"][0]["domain"]

    def delete_account(self, email):
        self.accounts = [acc for acc in self.accounts if acc['email'] != email]
        self._save_accounts()
        if self.current_account and self.current_account["email"] == email:
            self.current_account = self.accounts[-1] if self.accounts else None
