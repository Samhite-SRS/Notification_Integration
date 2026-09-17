"""
Email adapter over plain SMTP - the same host/port/STARTTLS/login/sendmail
sequence validated standalone earlier in this project (SMTP_Test.docx /
test_smtp.py), now wrapped behind the common NotificationProvider
interface. `destination` is the recipient's email address.
"""
import smtplib
import uuid
from email.mime.text import MIMEText

from app.providers.base import NotificationProvider, ProviderResult


class EmailProvider(NotificationProvider):
    name = "email"

    def __init__(self, host: str, port: int, username: str, password: str, sender_email: str, timeout_seconds: float = 10.0):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender_email = sender_email
        self._timeout_seconds = timeout_seconds

    def send(self, *, destination: str, title: str, message: str, subject: str | None = None) -> ProviderResult:
        msg = MIMEText(message)
        msg["Subject"] = subject or title or "Notification"
        msg["From"] = self._sender_email
        msg["To"] = destination

        message_id = f"email-{uuid.uuid4()}"
        msg["Message-ID"] = f"<{message_id}>"

        try:
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout_seconds) as smtp:
                smtp.starttls()
                smtp.login(self._username, self._password)
                smtp.sendmail(self._sender_email, [destination], msg.as_string())
        except smtplib.SMTPAuthenticationError:
            return ProviderResult(
                success=False, status="FAILED", error_message="SMTP authentication failed", retryable=False
            )
        except smtplib.SMTPRecipientsRefused:
            return ProviderResult(
                success=False, status="FAILED", error_message="Recipient address rejected", retryable=False
            )
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, OSError) as exc:
            return ProviderResult(
                success=False, status="FAILED", error_message=f"SMTP connection error: {exc}", retryable=True
            )
        except smtplib.SMTPException as exc:
            return ProviderResult(success=False, status="FAILED", error_message=f"SMTP error: {exc}", retryable=True)

        return ProviderResult(success=True, status="SENT", provider_message_id=message_id)
