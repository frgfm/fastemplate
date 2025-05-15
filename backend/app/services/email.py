# Copyright (C) 2025, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from typing import Dict, List

import requests

from app.core.config import settings

__all__ = ["email_client"]


class ResendClient:
    BASE_URL = "https://api.resend.com"

    def __init__(self, api_key: str, email_from: str, verify_api_key: bool = True) -> None:
        self.api_key = api_key
        if verify_api_key:
            # Verify API key
            response = requests.get(f"{self.BASE_URL}/domains", headers=self.headers, timeout=5)
            if response.status_code != 200:
                raise ValueError("Invalid Resend API key")

        self.email_from = email_from

    @property
    def headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def send(self, recipients: List[str], subject: str, html: str) -> requests.Response:
        return requests.post(
            f"{self.BASE_URL}/emails",
            headers=self.headers,
            json={
                "from": self.email_from,
                "to": recipients,
                "subject": subject,
                "html": html,
            },
            timeout=5,
        )

    def send_email_with_button(
        self, email: str, subject: str, hint: str, button_text: str, button_link: str, ignore_text: str
    ) -> requests.Response:
        return self.send(
            recipients=[email],
            subject=subject,
            html=(
                f'<h2 style="font-family: Arial, sans-serif;">{subject}</h2>'
                f'<p style="font-family: Arial, sans-serif;">{hint}</p>'
                "<p>"
                f'<a href="{button_link}" '
                'style="display: inline-block; padding: 10px 20px; font-family: Arial, sans-serif; '
                "font-size: 16px; color: #ffffff; background-color: #52528C; text-decoration: none; "
                'border-radius: 5px;">'
                f"{button_text}"
                "</a>"
                "</p>"
                f'<p style="font-family: Arial, sans-serif; font-size: 12px; color: #6c757d;"><i>{ignore_text}</i></p>'
            ),
        )

    def confirm_user(self, email: str, confirm_link: str) -> requests.Response:
        return self.send_email_with_button(
            email,
            "Confirm your signup",
            "Please confirm your email address by clicking the button below:",
            "Confirm your email",
            confirm_link,
            "If you did not sign up for this account, you can ignore this email.",
        )

    def send_link(self, email: str, link: str) -> requests.Response:
        return self.send_email_with_button(
            email,
            "Your magic link",
            "Click the button below to login:",
            "Login",
            link,
            "This link will expire in 5 minutes.",
        )


email_client = ResendClient(settings.RESEND_KEY, settings.EMAIL_FROM, verify_api_key=settings.RESEND_VERIFY_API_KEY)
