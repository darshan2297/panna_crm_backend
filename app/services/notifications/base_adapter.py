from abc import ABC, abstractmethod
from typing import Any


class BaseNotificationAdapter(ABC):
    """
    Abstract base adapter for dispatching alerts to external channels (Email, WhatsApp, etc.).
    Follows the Adapter pattern established in Panna CRM.
    """

    @abstractmethod
    def format_message(
        self,
        title: str,
        message: str,
        severity: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Format the message appropriate for the specific channel."""
        pass

    @abstractmethod
    def dispatch(
        self,
        title: str,
        message: str,
        severity: str,
        recipient: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Dispatch or simulate dispatch to the recipient."""
        pass
