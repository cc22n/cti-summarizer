"""Tests for the normalization service."""

from decimal import Decimal

import pytest

from app.models.alert import NormalizedAlert, RawAlert
from app.models.category import AlertCategory
from app.models.source import Source
from app.services.normalization import NormalizationService, cvss_to_severity


class TestCvssToSeverity:
    """Test CVSS score to severity mapping."""

    def test_critical(self):
        assert cvss_to_severity(9.8) == "critical"
        assert cvss_to_severity(10.0) == "critical"
        assert cvss_to_severity(9.0) == "critical"

    def test_high(self):
        assert cvss_to_severity(8.9) == "high"
        assert cvss_to_severity(7.0) == "high"

    def test_medium(self):
        assert cvss_to_severity(6.9) == "medium"
        assert cvss_to_severity(4.0) == "medium"

    def test_low(self):
        assert cvss_to_severity(3.9) == "low"
        assert cvss_to_severity(0.1) == "low"

    def test_info(self):
        assert cvss_to_severity(0.0) == "info"
        assert cvss_to_severity(None) == "info"

    def test_decimal_input(self):
        assert cvss_to_severity(Decimal("7.5")) == "high"


class TestNormalizeNVD:
    """Test NVD alert normalization."""

    def test_full_nvd_alert(self, db, sample_source, sample_raw_alert):
        """Test normalization of a complete NVD CVE."""
        svc = NormalizationService()
        result = svc.normalize_raw_alert(sample_raw_alert, db)

        assert result is not None
        assert result.title == "CVE-2026-12345"
        assert result.description == "Test vulnerability description"
        assert result.severity == "high"
        assert result.cvss_score == Decimal("8.5")
        assert result.source_name == "NVD"
        assert result.attack_vectors == {"vector": "NETWORK"}
        assert result.mitre_techniques == {"cwes": ["CWE-79"]}
        assert result.published_date is not None

    def test_nvd_no_cvss(self, db, sample_source):
        """Test NVD alert with no CVSS score."""
        raw = RawAlert(
            source_id=sample_source.id,
            external_id="CVE-2026-99999",
            raw_data={
                "cve": {
                    "id": "CVE-2026-99999",
                    "descriptions": [
                        {"lang": "en", "value": "No score vulnerability"}
                    ],
                    "metrics": {},
                    "references": [],
                    "weaknesses": [],
                    "configurations": [],
                }
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        svc = NormalizationService()
        result = svc.normalize_raw_alert(raw, db)

        assert result is not None
        assert result.severity == "info"
        assert result.cvss_score is None

    def test_nvd_cpe_extraction(self, db, sample_source):
        """Test CPE product extraction from configurations."""
        raw = RawAlert(
            source_id=sample_source.id,
            external_id="CVE-2026-CPE",
            raw_data={
                "cve": {
                    "id": "CVE-2026-CPE",
                    "descriptions": [
                        {"lang": "en", "value": "CPE test"}
                    ],
                    "metrics": {},
                    "references": [],
                    "weaknesses": [],
                    "configurations": [
                        {
                            "nodes": [
                                {
                                    "cpeMatch": [
                                        {
                                            "criteria": "cpe:2.3:a:apache:tomcat:10.0.0:*:*:*:*:*:*:*"
                                        }
                                    ]
                                }
                            ]
                        }
                    ],
                }
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        svc = NormalizationService()
        result = svc.normalize_raw_alert(raw, db)

        assert result is not None
        assert result.affected_products is not None
        products = result.affected_products["products"]
        assert len(products) == 1
        assert products[0]["vendor"] == "apache"
        assert products[0]["product"] == "tomcat"


class TestNormalizeCISA:
    """Test CISA KEV alert normalization."""

    def test_cisa_ransomware_known(self, db):
        """Test CISA entry with known ransomware campaign."""
        source = Source(
            name="CISA_KEV",
            source_type="api",
            base_url="https://www.cisa.gov/...",
        )
        db.add(source)
        db.commit()

        raw = RawAlert(
            source_id=source.id,
            external_id="CVE-2026-CISA1",
            raw_data={
                "cveID": "CVE-2026-CISA1",
                "vendorProject": "Microsoft",
                "product": "Exchange Server",
                "vulnerabilityName": "Exchange RCE",
                "shortDescription": "Remote code execution",
                "dateAdded": "2026-03-29",
                "dueDate": "2026-04-19",
                "knownRansomwareCampaignUse": "Known",
                "requiredAction": "Apply updates.",
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        svc = NormalizationService()
        result = svc.normalize_raw_alert(raw, db)

        assert result is not None
        assert result.severity == "critical"  # ransomware = critical
        assert result.source_name == "CISA_KEV"
        assert "Exchange RCE" in result.title
        assert result.affected_products["vendor"] == "Microsoft"
        assert result.iocs == {"ransomware_campaign": True}
        assert result.attack_vectors["actively_exploited"] is True

    def test_cisa_no_ransomware(self, db):
        """Test CISA entry without ransomware campaign."""
        source = Source(
            name="CISA_KEV",
            source_type="api",
            base_url="https://www.cisa.gov/...",
        )
        db.add(source)
        db.commit()

        raw = RawAlert(
            source_id=source.id,
            external_id="CVE-2026-CISA2",
            raw_data={
                "cveID": "CVE-2026-CISA2",
                "vendorProject": "Apache",
                "product": "HTTP Server",
                "vulnerabilityName": "Apache SSRF",
                "shortDescription": "Server side request forgery",
                "dateAdded": "2026-03-28",
                "dueDate": "2026-04-18",
                "knownRansomwareCampaignUse": "Unknown",
                "requiredAction": "Upgrade.",
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        svc = NormalizationService()
        result = svc.normalize_raw_alert(raw, db)

        assert result is not None
        assert result.severity == "high"  # no ransomware = high
        assert result.iocs is None


# ── 11.8 assign_categories ────────────────────────────────────────────────────

class TestAssignCategories:
    """Tests for NormalizationService.assign_categories keyword matching."""

    def _make_alert(self, db, title: str, description: str = "") -> NormalizedAlert:
        from app.models.source import Source
        src = Source(
            name="TEST_CAT",
            source_type="api",
            base_url="https://example.com",
            polling_interval_minutes=60,
            is_active=True,
        )
        db.add(src)
        db.flush()
        raw = RawAlert(source_id=src.id, external_id=f"CAT-{title[:8]}", raw_data={})
        db.add(raw)
        db.flush()
        alert = NormalizedAlert(
            raw_alert_id=raw.id,
            title=title,
            description=description,
            severity="info",
            source_name="TEST_CAT",
        )
        db.add(alert)
        db.flush()
        return alert

    def _make_category(self, db, name: str, keywords: list) -> AlertCategory:
        cat = AlertCategory(name=name, keywords=keywords)
        db.add(cat)
        db.flush()
        return cat

    def test_matching_keyword_assigns_category(self, db):
        alert = self._make_alert(db, "New ransomware campaign detected")
        cat = self._make_category(db, "ransomware", ["ransomware", "ransom"])

        NormalizationService.assign_categories(alert, [cat])

        assert cat in alert.categories

    def test_non_matching_keyword_does_not_assign(self, db):
        alert = self._make_alert(db, "Apache server update")
        cat = self._make_category(db, "ransomware", ["ransomware", "ransom"])

        NormalizationService.assign_categories(alert, [cat])

        assert cat not in alert.categories

    def test_keyword_match_is_case_insensitive(self, db):
        alert = self._make_alert(db, "RANSOMWARE variant detected")
        cat = self._make_category(db, "ransomware", ["ransomware"])

        NormalizationService.assign_categories(alert, [cat])

        assert cat in alert.categories

    def test_keyword_found_in_description(self, db):
        alert = self._make_alert(
            db, "CVE-2026-0001", description="exploits a remote code execution flaw"
        )
        cat = self._make_category(db, "rce", ["remote code execution", "rce"])

        NormalizationService.assign_categories(alert, [cat])

        assert cat in alert.categories

    def test_multiple_categories_assigned(self, db):
        alert = self._make_alert(db, "Ransomware using phishing to spread")
        ransom_cat = self._make_category(db, "ransomware", ["ransomware"])
        phish_cat = self._make_category(db, "phishing", ["phishing", "phish"])

        NormalizationService.assign_categories(alert, [ransom_cat, phish_cat])

        assert ransom_cat in alert.categories
        assert phish_cat in alert.categories

    def test_empty_keywords_list_never_matches(self, db):
        alert = self._make_alert(db, "Critical vulnerability")
        cat = self._make_category(db, "empty_cat", [])

        NormalizationService.assign_categories(alert, [cat])

        assert cat not in alert.categories

    def test_no_duplicate_assignment(self, db):
        alert = self._make_alert(db, "ransomware attack uses phishing")
        cat = self._make_category(db, "ransomware", ["ransomware"])

        NormalizationService.assign_categories(alert, [cat])
        NormalizationService.assign_categories(alert, [cat])

        assert alert.categories.count(cat) == 1


# ── 14.1 OTX normalization ────────────────────────────────────────────────────

class TestNormalizeOTX:
    def _make_source(self, db):
        from app.models.source import Source
        src = Source(name="OTX", source_type="api", base_url="https://otx.alienvault.com")
        db.add(src)
        db.commit()
        return src

    def test_basic_fields_populated(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="pulse-basic",
            raw_data={
                "name": "APT Campaign",
                "description": "Finance sector threat",
                "tags": [],
                "indicators": [{"type": "domain"} for _ in range(5)],
                "attack_ids": [],
                "created": "2026-06-01T10:00:00.000000",
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)

        assert result is not None
        assert result.title == "APT Campaign"
        assert result.source_name == "OTX"
        assert result.severity == "low"  # 5 indicators < threshold 10

    def test_high_indicator_count_yields_high_severity(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="pulse-high",
            raw_data={
                "name": "High indicator pulse",
                "description": "",
                "tags": [],
                "indicators": [{"type": "ip"} for _ in range(60)],
                "attack_ids": [],
                "created": "",
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result.severity == "high"

    def test_ransomware_tag_overrides_to_critical(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="pulse-ransom",
            raw_data={
                "name": "Ransomware campaign",
                "description": "",
                "tags": ["Ransomware", "malware"],
                "indicators": [],
                "attack_ids": [],
                "created": "",
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result.severity == "critical"

    def test_attack_ids_stored_in_mitre_techniques(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="pulse-mitre",
            raw_data={
                "name": "Pulse with MITRE",
                "description": "",
                "tags": [],
                "indicators": [],
                "attack_ids": [{"id": "T1059", "name": "Cmd"}, {"id": "T1190", "name": "Exploit"}],
                "created": "",
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result.mitre_techniques is not None
        assert "T1059" in result.mitre_techniques["attack_ids"]
        assert "T1190" in result.mitre_techniques["attack_ids"]


# ── 14.2 MITRE ATT&CK normalization ──────────────────────────────────────────

class TestNormalizeMITRE:
    def _make_source(self, db):
        from app.models.source import Source
        src = Source(name="MITRE_ATTACK", source_type="api", base_url="https://attack.mitre.org")
        db.add(src)
        db.commit()
        return src

    def test_severity_is_always_info(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="T1059",
            raw_data={
                "type": "attack-pattern",
                "name": "Command and Scripting Interpreter",
                "description": "Adversaries may abuse scripting.",
                "kill_chain_phases": [{"phase_name": "execution"}],
                "x_mitre_platforms": ["Windows", "Linux"],
                "x_mitre_data_sources": [],
                "modified": "2026-01-10T00:00:00.000Z",
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)

        assert result is not None
        assert result.severity == "info"
        assert result.source_name == "MITRE_ATTACK"

    def test_technique_id_in_mitre_techniques(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="T1190",
            raw_data={
                "name": "Exploit Public-Facing Application",
                "description": "...",
                "kill_chain_phases": [],
                "x_mitre_platforms": ["Linux", "Windows"],
                "x_mitre_data_sources": ["Application Log"],
                "modified": "2026-03-01T00:00:00Z",
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result.mitre_techniques["technique_id"] == "T1190"
        assert "Linux" in result.mitre_techniques["platforms"]

    def test_title_combines_id_and_name(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="T1078",
            raw_data={
                "name": "Valid Accounts",
                "description": "",
                "kill_chain_phases": [],
                "x_mitre_platforms": [],
                "x_mitre_data_sources": [],
                "modified": "",
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert "T1078" in result.title
        assert "Valid Accounts" in result.title


# ── 14.3 RSS normalization ────────────────────────────────────────────────────

class TestNormalizeRSS:
    def _make_source(self, db):
        from app.models.source import Source
        src = Source(name="RSS", source_type="rss", base_url="rss://multiple")
        db.add(src)
        db.commit()
        return src

    def test_severity_is_always_info(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="https://example.com/article-1",
            raw_data={
                "feed_url": "https://example.com/feed",
                "feed_title": "Security Blog",
                "title": "Ransomware targets hospitals",
                "link": "https://example.com/article-1",
                "summary": "Hospitals hit by ransomware.",
                "published": "Mon, 01 Jun 2026 10:00:00 +0000",
                "tags": ["ransomware"],
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)

        assert result is not None
        assert result.severity == "info"
        assert result.source_name == "RSS"
        assert result.title == "Ransomware targets hospitals"

    def test_iocs_contains_link_and_feed(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="https://example.com/article-2",
            raw_data={
                "feed_url": "https://feeds.example.com/rss",
                "feed_title": "CTI Feed",
                "title": "Article",
                "link": "https://example.com/article-2",
                "summary": "",
                "published": "",
                "tags": [],
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result.iocs["link"] == "https://example.com/article-2"
        assert result.iocs["feed_url"] == "https://feeds.example.com/rss"

    def test_published_date_parsed(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="https://example.com/article-3",
            raw_data={
                "feed_url": "",
                "feed_title": "",
                "title": "Article",
                "link": "",
                "summary": "",
                "published": "Mon, 01 Jun 2026 00:00:00 +0000",
                "tags": [],
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result.published_date is not None
        assert result.published_date.year == 2026


# ── 14.4 URLhaus normalization ────────────────────────────────────────────────

class TestNormalizeURLhaus:
    def _make_source(self, db):
        from app.models.source import Source
        src = Source(name="URLhaus", source_type="api", base_url="https://urlhaus-api.abuse.ch")
        db.add(src)
        db.commit()
        return src

    def test_online_url_yields_high_severity(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="urlhaus-111",
            raw_data={
                "url": "http://evil.com/payload.exe",
                "url_status": "online",
                "threat": "malware_download",
                "tags": None,
                "date_added": "2026-06-01 10:00:00 UTC",
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result is not None
        assert result.severity == "high"
        assert result.source_name == "URLhaus"

    def test_offline_url_yields_medium_severity(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="urlhaus-222",
            raw_data={
                "url": "http://old-evil.com/dropper.exe",
                "url_status": "offline",
                "threat": "malware_download",
                "tags": None,
                "date_added": "",
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result.severity == "medium"

    def test_botnet_cc_threat_yields_critical(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="urlhaus-333",
            raw_data={
                "url": "http://c2.evil.com/gate",
                "url_status": "online",
                "threat": "botnet_cc",
                "tags": None,
                "date_added": "2026-06-01 10:00:00 UTC",
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result.severity == "critical"

    def test_iocs_contains_url_and_threat(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="urlhaus-444",
            raw_data={
                "url": "http://test.com/mal.bin",
                "url_status": "unknown",
                "threat": "malware_download",
                "tags": ["Emotet"],
                "date_added": "",
                "urlhaus_reference": "https://urlhaus.abuse.ch/url/444/",
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result.iocs["url"] == "http://test.com/mal.bin"
        assert result.iocs["threat"] == "malware_download"


# ── 14.5 VirusTotal normalization ─────────────────────────────────────────────

class TestNormalizeVirusTotal:
    def _make_source(self, db):
        from app.models.source import Source
        src = Source(name="VirusTotal", source_type="api", base_url="https://www.virustotal.com")
        db.add(src)
        db.commit()
        return src

    def test_high_malicious_count_yields_critical(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="vt-sha256aaa",
            raw_data={
                "id": "sha256aaa",
                "attributes": {
                    "sha256": "sha256aaa",
                    "meaningful_name": "ransomware.exe",
                    "last_submission_date": 1748745600,
                    "last_analysis_stats": {"malicious": 45, "suspicious": 2},
                    "tags": ["trojan"],
                },
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result is not None
        assert result.severity == "critical"  # malicious >= 30
        assert result.source_name == "VirusTotal"

    def test_moderate_malicious_count_yields_high(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="vt-sha256bbb",
            raw_data={
                "id": "sha256bbb",
                "attributes": {
                    "sha256": "sha256bbb",
                    "meaningful_name": "dropper.dll",
                    "last_submission_date": 1748745600,
                    "last_analysis_stats": {"malicious": 20, "suspicious": 3},
                    "tags": [],
                },
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result.severity == "high"  # 15 <= malicious < 30

    def test_ransomware_tag_overrides_to_critical(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="vt-sha256ccc",
            raw_data={
                "id": "sha256ccc",
                "attributes": {
                    "sha256": "sha256ccc",
                    "meaningful_name": "locker.exe",
                    "last_submission_date": 1748745600,
                    "last_analysis_stats": {"malicious": 8, "suspicious": 1},
                    "tags": ["ransomware"],
                },
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result.severity == "critical"

    def test_iocs_contains_sha256_and_counts(self, db):
        src = self._make_source(db)
        raw = RawAlert(
            source_id=src.id,
            external_id="vt-sha256ddd",
            raw_data={
                "id": "sha256ddd",
                "attributes": {
                    "sha256": "sha256ddd",
                    "meaningful_name": "sample.bin",
                    "last_submission_date": None,
                    "last_analysis_stats": {"malicious": 10, "suspicious": 0},
                    "tags": [],
                },
            },
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result.iocs["sha256"] == "sha256ddd"
        assert result.iocs["malicious_count"] == 10


# ── 14.6 Normalizer dispatch for unknown source ───────────────────────────────

class TestNormalizeDispatch:
    def test_unknown_source_returns_none(self, db):
        from app.models.source import Source
        src = Source(
            name="UNKNOWN_SRC",
            source_type="api",
            base_url="https://example.com",
        )
        db.add(src)
        db.flush()
        raw = RawAlert(source_id=src.id, external_id="x", raw_data={})
        db.add(raw)
        db.commit()
        db.refresh(raw)

        result = NormalizationService().normalize_raw_alert(raw, db)
        assert result is None
