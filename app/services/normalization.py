"""Normalization service - transforms raw alerts into unified format.

Each source has its own raw data structure. This service maps them
to the NormalizedAlert schema with consistent severity, fields, etc.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime

from sqlalchemy.orm import Session

from app.models.alert import NormalizedAlert, RawAlert

logger = logging.getLogger(__name__)


def cvss_to_severity(score: float | Decimal | None) -> str:
    """Map CVSS 3.x score to severity string.

    CVSS 3.x ranges:
        0.0       -> info
        0.1-3.9   -> low
        4.0-6.9   -> medium
        7.0-8.9   -> high
        9.0-10.0  -> critical
    """
    if score is None:
        return "info"
    s = float(score)
    if s >= 9.0:
        return "critical"
    if s >= 7.0:
        return "high"
    if s >= 4.0:
        return "medium"
    if s > 0.0:
        return "low"
    return "info"


class NormalizationService:
    """Transforms raw alerts into normalized alerts."""

    def normalize_raw_alert(
        self, raw_alert: RawAlert, db: Session
    ) -> NormalizedAlert | None:
        """Normalize a single raw alert based on its source.

        Returns None if normalization fails (logged, not raised).
        """
        source_name = raw_alert.source.name if raw_alert.source else "UNKNOWN"

        try:
            if source_name == "NVD":
                return self._normalize_nvd(raw_alert)
            elif source_name == "CISA_KEV":
                return self._normalize_cisa_kev(raw_alert)
            elif source_name == "OTX":
                return self._normalize_otx(raw_alert)
            elif source_name == "MITRE_ATTACK":
                return self._normalize_mitre(raw_alert)
            elif source_name == "RSS":
                return self._normalize_rss(raw_alert)
            elif source_name == "URLhaus":
                return self._normalize_urlhaus(raw_alert)
            elif source_name == "VirusTotal":
                return self._normalize_virustotal(raw_alert)
            else:
                logger.warning(
                    "No normalizer for source: %s", source_name
                )
                return None
        except Exception as exc:
            logger.error(
                "Normalization failed for raw_alert %d: %s",
                raw_alert.id,
                exc,
            )
            return None

    def _normalize_nvd(self, raw_alert: RawAlert) -> NormalizedAlert:
        """Normalize NVD CVE data.

        NVD structure:
        {
          "cve": {
            "id": "CVE-2024-XXXX",
            "descriptions": [{"lang": "en", "value": "..."}],
            "metrics": {
              "cvssMetricV31": [{"cvssData": {"baseScore": 7.5, ...}}]
            },
            "weaknesses": [...],
            "configurations": [...],
            "references": [...]
          }
        }
        """
        cve = raw_alert.raw_data.get("cve", {})

        # Title
        cve_id = cve.get("id", raw_alert.external_id)
        title = cve_id

        # Description (English)
        description = ""
        for desc in cve.get("descriptions", []):
            if desc.get("lang") == "en":
                description = desc.get("value", "")
                break

        # CVSS score - try v3.1, then v3.0, then v2.0
        cvss_score = None
        metrics = cve.get("metrics", {})

        for metric_key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            metric_list = metrics.get(metric_key, [])
            if metric_list:
                cvss_data = metric_list[0].get("cvssData", {})
                raw_score = cvss_data.get("baseScore")
                if raw_score is not None:
                    try:
                        cvss_score = Decimal(str(raw_score))
                    except (InvalidOperation, ValueError):
                        pass
                break

        severity = cvss_to_severity(cvss_score)

        # Attack vector from CVSS
        attack_vectors = None
        for metric_key in ("cvssMetricV31", "cvssMetricV30"):
            metric_list = metrics.get(metric_key, [])
            if metric_list:
                cvss_data = metric_list[0].get("cvssData", {})
                av = cvss_data.get("attackVector")
                if av:
                    attack_vectors = {"vector": av}
                break

        # Affected products from configurations (CPE)
        affected_products = self._extract_cpe_products(cve)

        # Published date
        published_date = None
        pub_str = cve.get("published")
        if pub_str:
            try:
                published_date = datetime.fromisoformat(
                    pub_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # Weaknesses as MITRE-adjacent info
        mitre_techniques = None
        weaknesses = cve.get("weaknesses", [])
        if weaknesses:
            cwe_ids = []
            for w in weaknesses:
                for desc in w.get("description", []):
                    cwe_id = desc.get("value", "")
                    if cwe_id.startswith("CWE-"):
                        cwe_ids.append(cwe_id)
            if cwe_ids:
                mitre_techniques = {"cwes": cwe_ids}

        # References as IOCs
        iocs = None
        refs = cve.get("references", [])
        if refs:
            iocs = {
                "references": [
                    {"url": r.get("url", ""), "source": r.get("source", "")}
                    for r in refs[:10]  # cap at 10
                ]
            }

        return NormalizedAlert(
            raw_alert_id=raw_alert.id,
            title=title,
            description=description,
            severity=severity,
            cvss_score=cvss_score,
            affected_products=affected_products,
            attack_vectors=attack_vectors,
            mitre_techniques=mitre_techniques,
            iocs=iocs,
            source_name="NVD",
            published_date=published_date,
        )

    def _normalize_cisa_kev(self, raw_alert: RawAlert) -> NormalizedAlert:
        """Normalize CISA KEV entry.

        CISA KEV structure:
        {
          "cveID": "CVE-2024-XXXX",
          "vendorProject": "Microsoft",
          "product": "Windows",
          "vulnerabilityName": "...",
          "shortDescription": "...",
          "dateAdded": "2024-01-15",
          "dueDate": "2024-02-05",
          "knownRansomwareCampaignUse": "Known",
          "requiredAction": "Apply updates..."
        }
        """
        data = raw_alert.raw_data

        cve_id = data.get("cveID", raw_alert.external_id)
        vuln_name = data.get("vulnerabilityName", "")
        title = f"{cve_id}: {vuln_name}" if vuln_name else cve_id

        description = data.get("shortDescription", "")
        required_action = data.get("requiredAction", "")
        if required_action:
            description = f"{description}\n\nRequired Action: {required_action}"

        # CISA KEV = actively exploited, always high/critical
        ransomware_use = data.get("knownRansomwareCampaignUse", "Unknown")
        severity = "critical" if ransomware_use == "Known" else "high"

        # Affected products
        vendor = data.get("vendorProject", "")
        product = data.get("product", "")
        affected_products = None
        if vendor or product:
            affected_products = {"vendor": vendor, "product": product}

        # Published date
        published_date = None
        date_added = data.get("dateAdded")
        if date_added:
            try:
                published_date = datetime.strptime(
                    date_added, "%Y-%m-%d"
                ).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass

        # IOC: ransomware campaign use
        iocs = None
        if ransomware_use == "Known":
            iocs = {"ransomware_campaign": True}

        # Due date as attack vector urgency context
        attack_vectors = None
        due_date = data.get("dueDate")
        if due_date:
            attack_vectors = {
                "remediation_due": due_date,
                "actively_exploited": True,
            }

        return NormalizedAlert(
            raw_alert_id=raw_alert.id,
            title=title,
            description=description,
            severity=severity,
            cvss_score=None,  # CISA KEV doesn't include CVSS
            affected_products=affected_products,
            attack_vectors=attack_vectors,
            mitre_techniques=None,
            iocs=iocs,
            source_name="CISA_KEV",
            published_date=published_date,
        )

    def _normalize_otx(self, raw_alert: RawAlert) -> NormalizedAlert:
        """Normalize AlienVault OTX pulse.

        OTX pulse structure:
        {
          "id": "...",
          "name": "Threat Actor X campaign",
          "description": "...",
          "tags": ["ransomware", "apt"],
          "indicators": [{"type": "domain", "indicator": "evil.com"}, ...],
          "attack_ids": [{"id": "T1059", "name": "Command and Scripting"}, ...],
          "industries": ["Finance"],
          "targeted_countries": ["US"],
          "created": "2024-01-15T10:00:00.000000",
          "modified": "2024-01-16T08:00:00.000000",
          "tlp": "white"
        }
        """
        data = raw_alert.raw_data

        title = data.get("name", raw_alert.external_id)[:500]
        description = data.get("description", "")[:2000]

        # Severity heuristic: based on indicator count (no CVSS available)
        indicators = data.get("indicators", [])
        indicator_count = len(indicators)
        if indicator_count >= 50:
            severity = "high"
        elif indicator_count >= 10:
            severity = "medium"
        else:
            severity = "low"

        # Override to critical if ransomware tag present
        tags = [t.lower() for t in data.get("tags", [])]
        if "ransomware" in tags:
            severity = "critical"

        # MITRE ATT&CK IDs from OTX
        mitre_techniques = None
        attack_ids = data.get("attack_ids", [])
        if attack_ids:
            mitre_techniques = {
                "attack_ids": [
                    a.get("id", "") for a in attack_ids if a.get("id")
                ]
            }

        # IOC summary (not raw indicators - could be thousands)
        ioc_types = list({i.get("type", "") for i in indicators[:100] if i.get("type")})
        iocs = {
            "count": indicator_count,
            "types": ioc_types,
        }

        # Affected scope
        industries = data.get("industries", [])
        countries = data.get("targeted_countries", [])
        affected_products = None
        if industries or countries:
            affected_products = {
                "industries": industries,
                "targeted_countries": countries,
            }

        # Published date
        published_date = None
        created_str = data.get("created", "")
        if created_str:
            try:
                published_date = datetime.fromisoformat(
                    created_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        return NormalizedAlert(
            raw_alert_id=raw_alert.id,
            title=title,
            description=description,
            severity=severity,
            cvss_score=None,
            affected_products=affected_products,
            attack_vectors=None,
            mitre_techniques=mitre_techniques,
            iocs=iocs,
            source_name="OTX",
            published_date=published_date,
        )

    def _normalize_mitre(self, raw_alert: RawAlert) -> NormalizedAlert:
        """Normalize MITRE ATT&CK technique (STIX attack-pattern object).

        STIX attack-pattern structure:
        {
          "type": "attack-pattern",
          "id": "attack-pattern--...",
          "name": "PowerShell",
          "description": "...",
          "kill_chain_phases": [{"kill_chain_name": "mitre-attack", "phase_name": "execution"}],
          "x_mitre_platforms": ["Windows", "Linux"],
          "x_mitre_data_sources": ["Process: Process Creation", ...],
          "external_references": [{"source_name": "mitre-attack", "external_id": "T1059.001"}],
          "modified": "2024-01-10T00:00:00.000Z"
        }
        """
        obj = raw_alert.raw_data

        # Extract ATT&CK ID
        technique_id = raw_alert.external_id
        title = f"{technique_id}: {obj.get('name', 'Unknown Technique')}"[:500]
        description = obj.get("description", "")[:3000]

        # MITRE techniques are TTPs, not severity-rated
        severity = "info"

        # Kill chain phases and platforms
        kill_chain_phases = [
            p.get("phase_name", "")
            for p in obj.get("kill_chain_phases", [])
            if p.get("phase_name")
        ]
        platforms = obj.get("x_mitre_platforms", [])
        mitre_techniques = {
            "technique_id": technique_id,
            "kill_chain_phases": kill_chain_phases,
            "platforms": platforms,
        }

        attack_vectors = {"platforms": platforms} if platforms else None

        # Data sources as IOC-adjacent info
        data_sources = obj.get("x_mitre_data_sources", [])
        iocs = {"data_sources": data_sources} if data_sources else None

        # Modified date as published_date
        published_date = None
        modified_str = obj.get("modified", "")
        if modified_str:
            try:
                published_date = datetime.fromisoformat(
                    modified_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        return NormalizedAlert(
            raw_alert_id=raw_alert.id,
            title=title,
            description=description,
            severity=severity,
            cvss_score=None,
            affected_products=None,
            attack_vectors=attack_vectors,
            mitre_techniques=mitre_techniques,
            iocs=iocs,
            source_name="MITRE_ATTACK",
            published_date=published_date,
        )

    def _normalize_rss(self, raw_alert: RawAlert) -> NormalizedAlert:
        """Normalize RSS feed entry.

        RSS raw_data structure (from RSSAdapter):
        {
          "feed_url": "https://...",
          "feed_title": "Bleeping Computer",
          "title": "Article title",
          "link": "https://...",
          "summary": "Article excerpt...",
          "published": "Mon, 15 Jan 2024 10:00:00 +0000",
          "tags": ["ransomware", "malware"]
        }
        """
        data = raw_alert.raw_data

        title = data.get("title", "RSS Alert")[:500]
        description = data.get("summary", "")[:2000]

        # No CVSS for RSS - default to info
        severity = "info"

        # Published date (already normalized by feedparser in the adapter)
        published_date = None
        published_str = data.get("published", "")
        if published_str:
            try:
                # parsedate_to_datetime returns tz-aware; astimezone converts
                # without discarding the original offset the way replace() would.
                published_date = parsedate_to_datetime(published_str).astimezone(
                    timezone.utc
                )
            except Exception:
                pass

        iocs = {
            "link": data.get("link", ""),
            "feed_url": data.get("feed_url", ""),
            "feed_title": data.get("feed_title", ""),
        }

        return NormalizedAlert(
            raw_alert_id=raw_alert.id,
            title=title,
            description=description,
            severity=severity,
            cvss_score=None,
            affected_products=None,
            attack_vectors=None,
            mitre_techniques=None,
            iocs=iocs,
            source_name="RSS",
            published_date=published_date,
        )

    def _normalize_urlhaus(self, raw_alert: RawAlert) -> NormalizedAlert:
        """Normalize URLhaus malicious URL entry.

        URLhaus raw_data structure:
        {
          "id": "2134567",
          "url": "http://evil.com/malware.exe",
          "url_status": "online",   # online | offline | unknown
          "date_added": "2024-01-15 10:30:00 UTC",
          "threat": "malware_download",  # or "botnet_cc"
          "tags": ["Emotet", "botnet"],
          "urlhaus_reference": "https://urlhaus.abuse.ch/url/2134567/"
        }
        """
        data = raw_alert.raw_data

        url = data.get("url", raw_alert.external_id)
        threat = data.get("threat", "")
        url_status = data.get("url_status", "unknown")
        tags = [str(t).lower() for t in (data.get("tags") or [])]

        title = f"Malicious URL: {url[:200]}"
        description = (
            f"URLhaus reported malicious URL. "
            f"Threat type: {threat or 'unknown'}. "
            f"Status: {url_status}."
        )
        if tags:
            description += f" Tags: {', '.join(tags[:10])}."

        # Severity heuristic
        if url_status == "online":
            severity = "high"
        elif url_status == "offline":
            severity = "medium"
        else:
            severity = "low"

        # Escalate to critical for known high-risk threat types
        if threat in ("botnet_cc",):
            severity = "critical"

        # Published date
        published_date = None
        date_str = data.get("date_added", "")
        if date_str:
            try:
                published_date = datetime.strptime(
                    date_str, "%Y-%m-%d %H:%M:%S UTC"
                ).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass

        iocs = {
            "url": url,
            "url_status": url_status,
            "threat": threat,
            "urlhaus_reference": data.get("urlhaus_reference", ""),
        }

        return NormalizedAlert(
            raw_alert_id=raw_alert.id,
            title=title,
            description=description,
            severity=severity,
            cvss_score=None,
            affected_products=None,
            attack_vectors={"threat_type": threat} if threat else None,
            mitre_techniques=None,
            iocs=iocs,
            source_name="URLhaus",
            published_date=published_date,
        )

    def _normalize_virustotal(self, raw_alert: RawAlert) -> NormalizedAlert:
        """Normalize a VirusTotal Intelligence search result.

        VT item structure:
        {
          "id": "<sha256>",
          "attributes": {
            "sha256": "...",
            "meaningful_name": "malware.exe",
            "last_submission_date": 1234567890,
            "last_analysis_stats": {"malicious": 42, "suspicious": 5, ...},
            "tags": ["trojan", "ransomware"]
          }
        }
        """
        item = raw_alert.raw_data or {}
        attrs = item.get("attributes", {})

        sha256 = attrs.get("sha256") or item.get("id", raw_alert.external_id)
        name = attrs.get("meaningful_name") or sha256[:16]
        tags = [str(t).lower() for t in (attrs.get("tags") or [])]
        stats = attrs.get("last_analysis_stats", {})
        malicious = int(stats.get("malicious", 0))
        suspicious = int(stats.get("suspicious", 0))

        title = f"Malware sample: {name}"
        description = (
            f"VirusTotal detection: {malicious} malicious, {suspicious} suspicious."
        )
        if tags:
            description += f" Tags: {', '.join(tags[:10])}."

        if malicious >= 30:
            severity = "critical"
        elif malicious >= 15:
            severity = "high"
        elif malicious >= 5:
            severity = "medium"
        else:
            severity = "low"

        for ransomware_tag in ("ransomware", "ransom"):
            if ransomware_tag in tags:
                severity = "critical"
                break

        published_date = None
        last_sub = attrs.get("last_submission_date")
        if last_sub:
            try:
                published_date = datetime.fromtimestamp(
                    int(last_sub), tz=timezone.utc
                )
            except (OSError, OverflowError, ValueError):
                pass

        iocs = {
            "sha256": sha256,
            "malicious_count": malicious,
            "suspicious_count": suspicious,
            "tags": tags,
        }

        return NormalizedAlert(
            raw_alert_id=raw_alert.id,
            title=title,
            description=description,
            severity=severity,
            cvss_score=None,
            affected_products=None,
            attack_vectors=None,
            mitre_techniques=None,
            iocs=iocs,
            source_name="VirusTotal",
            published_date=published_date,
        )

    @staticmethod
    def assign_categories(alert: "NormalizedAlert", categories: list) -> None:
        """Assign threat categories via keyword matching in title and description.

        categories is a list of AlertCategory ORM objects whose .keywords field
        holds a JSON list of keyword strings (set by setup_db seed).
        """
        text_blob = f"{alert.title} {alert.description or ''}".lower()
        for cat in categories:
            kw_list = cat.keywords if isinstance(cat.keywords, list) else []
            if any(kw.lower() in text_blob for kw in kw_list):
                if cat not in alert.categories:
                    alert.categories.append(cat)

    @staticmethod
    def _extract_cpe_products(cve: dict) -> dict | None:
        """Extract affected product names from CPE configurations."""
        products = []
        configurations = cve.get("configurations", [])

        for config in configurations:
            for node in config.get("nodes", []):
                for cpe_match in node.get("cpeMatch", []):
                    criteria = cpe_match.get("criteria", "")
                    # CPE format: cpe:2.3:a:vendor:product:version:...
                    parts = criteria.split(":")
                    if len(parts) >= 5:
                        vendor = parts[3]
                        product = parts[4]
                        if vendor != "*" and product != "*":
                            products.append(
                                {"vendor": vendor, "product": product}
                            )

        if products:
            # Deduplicate
            seen = set()
            unique = []
            for p in products:
                key = f"{p['vendor']}:{p['product']}"
                if key not in seen:
                    seen.add(key)
                    unique.append(p)
            return {"products": unique[:20]}  # cap at 20
        return None
