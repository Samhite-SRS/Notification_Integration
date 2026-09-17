"""
Common interface every channel adapter implements. The Notification
Service (app/services/notification_service.py) only ever talks to this
interface - it never contains Teams/Slack/SMTP-specific code, so a new
channel is just a new class that implements `send()` (spec section 9/21).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResult:
    """What every adapter hands back, regardless of channel."""

    success: bool
    status: str  # "SENT" or "FAILED"
    provider_message_id: str | None = None
    error_message: str | None = None
    # Only meaningful when success is False: should the caller retry?
    retryable: bool = False


class NotificationProvider(ABC):
    """NotificationProvider.send(...) -> provider_message_id/status (spec section 9)."""

    #: short machine name stored in notification_deliveries.provider
    name: str = "base"

    @abstractmethod
    def send(self, *, destination: str, title: str, message: str, subject: str | None = None) -> ProviderResult:
        """Attempt one delivery. Must never raise - catch provider-specific
        exceptions internally and translate them into a ProviderResult so the
        service layer has one consistent failure shape to work with."""
        raise NotImplementedError
