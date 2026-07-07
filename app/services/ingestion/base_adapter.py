"""Abstract base adapter for CTI feed ingestion."""

import abc
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RawAlertData:
    """Standardized container for raw alert data from any source."""

    external_id: str
    raw_data: dict
    source_name: str
    fetched_at: datetime = field(default_factory=_utcnow)


@dataclass
class IngestionResult:
    """Result of an ingestion run."""

    source_name: str
    status: str  # success / error / partial
    alerts_fetched: int = 0
    alerts_new: int = 0
    error_message: str | None = None
    started_at: datetime = field(default_factory=_utcnow)
    completed_at: datetime | None = None


class BaseAdapter(abc.ABC):
    """Abstract base for CTI feed adapters.

    Each adapter must implement `fetch_alerts()` which returns
    a list of RawAlertData objects from the specific feed.
    """

    SOURCE_NAME: str = ""
    SOURCE_TYPE: str = ""  # api, rss, stix
    BASE_URL: str = ""

    @abc.abstractmethod
    async def fetch_alerts(
        self, since: datetime | None = None
    ) -> list[RawAlertData]:
        """Fetch raw alerts from the CTI source.

        Args:
            since: Only fetch alerts published after this datetime.
                   If None, fetch recent alerts (adapter-specific default).

        Returns:
            List of RawAlertData objects.
        """
        ...

    def _log_fetch(self, count: int) -> None:
        logger.info(
            "[%s] Fetched %d alerts", self.SOURCE_NAME, count
        )
