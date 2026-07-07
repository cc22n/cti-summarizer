"""Ingestion adapters package."""

from app.services.ingestion.nvd_adapter import NVDAdapter
from app.services.ingestion.cisa_adapter import CISAKEVAdapter
from app.services.ingestion.otx_adapter import OTXAdapter
from app.services.ingestion.mitre_adapter import MITREAdapter
from app.services.ingestion.rss_adapter import RSSAdapter
from app.services.ingestion.urlhaus_adapter import URLhausAdapter
from app.services.ingestion.virustotal_adapter import VirusTotalAdapter

__all__ = [
    "NVDAdapter",
    "CISAKEVAdapter",
    "OTXAdapter",
    "MITREAdapter",
    "RSSAdapter",
    "URLhausAdapter",
    "VirusTotalAdapter",
]
