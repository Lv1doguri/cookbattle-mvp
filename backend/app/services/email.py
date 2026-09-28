"""Sends the signup verification email. If SMTP isn't configured (local dev/demo), the link is
logged instead of emailed, so the flow still works end-to-end without real mail credentials."""
import logging
import smtplib
from email.mime.text import MIMEText

from ..config import settings

log = logging.getLogger("cookbattle")


def verification_link(token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/verify-email?token={token}"


def send_verification_email(to_email: str, nickname: str, token: str) -> None:
    link = verification_link(token)
    if not settings.smtp_host:
        log.warning("SMTP_HOST not set — logging the verification link instead of emailing it.\n%s -> %s", to_email, link)
        return

    body = (
        f"{nickname}님, 요리왕 가입을 완료하려면 아래 링크를 눌러주세요.\n\n"
        f"{link}\n\n"
        "이 링크는 30분 동안만 유효해요. 본인이 요청한 게 아니라면 이 메일을 무시하셔도 됩니다."
    )
    msg = MIMEText(body)
    msg["Subject"] = "[요리왕] 이메일을 인증해주세요"
    msg["From"] = settings.smtp_from
    msg["To"] = to_email

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
