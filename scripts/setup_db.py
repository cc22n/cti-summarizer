"""Database setup and seed script.

Usage:
    python -m scripts.setup_db

Creates the database (if needed), runs migrations,
and seeds initial sources and categories.
"""

import sys
import subprocess
from pathlib import Path

from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal, get_engine, Base
from app.models import Source, AlertCategory, User


INITIAL_SOURCES = [
    {
        "name": "NVD",
        "source_type": "api",
        "base_url": "https://services.nvd.nist.gov/rest/json/cves/2.0",
        "polling_interval_minutes": 360,
    },
    {
        "name": "CISA_KEV",
        "source_type": "api",
        "base_url": (
            "https://www.cisa.gov/sites/default/files/feeds/"
            "known_exploited_vulnerabilities.json"
        ),
        "polling_interval_minutes": 1440,
    },
    {
        "name": "OTX",
        "source_type": "api",
        "base_url": "https://otx.alienvault.com/api/v1/pulses/subscribed",
        "polling_interval_minutes": 360,
    },
    {
        "name": "MITRE_ATTACK",
        "source_type": "stix",
        "base_url": (
            "https://raw.githubusercontent.com/mitre/cti/master/"
            "enterprise-attack/enterprise-attack.json"
        ),
        "polling_interval_minutes": 10080,  # weekly
    },
    {
        "name": "RSS",
        "source_type": "rss",
        "base_url": "rss://multiple",
        "polling_interval_minutes": 120,
    },
    {
        "name": "URLhaus",
        "source_type": "api",
        "base_url": "https://urlhaus-api.abuse.ch/v1/urls/recent/",
        "polling_interval_minutes": 240,
    },
]

INITIAL_CATEGORIES = [
    {
        "name": "ransomware",
        "description": "Ransomware threats and campaigns",
        "keywords": ["ransomware", "ransom", "encrypt", "decrypt", "lockbit", "blackcat"],
    },
    {
        "name": "rce",
        "description": "Remote Code Execution vulnerabilities",
        "keywords": ["remote code execution", "rce", "arbitrary code"],
    },
    {
        "name": "phishing",
        "description": "Phishing and social engineering",
        "keywords": ["phishing", "spear-phishing", "social engineering", "credential theft"],
    },
    {
        "name": "supply_chain",
        "description": "Supply chain attacks and compromises",
        "keywords": ["supply chain", "dependency", "package", "npm", "pypi", "backdoor"],
    },
    {
        "name": "zero_day",
        "description": "Zero-day exploits",
        "keywords": ["zero-day", "0-day", "zero day", "unpatched", "actively exploited"],
    },
    {
        "name": "dos",
        "description": "Denial of Service attacks",
        "keywords": ["denial of service", "dos", "ddos", "resource exhaustion"],
    },
    {
        "name": "privilege_escalation",
        "description": "Privilege escalation vulnerabilities",
        "keywords": ["privilege escalation", "elevation of privilege", "local privilege"],
    },
    {
        "name": "data_breach",
        "description": "Data breaches and leaks",
        "keywords": ["data breach", "data leak", "exposed", "stolen data", "exfiltration"],
    },
]


def create_database():
    """Create the cti_summarizer database if it does not exist."""
    # Parse the database URL to connect to the default 'postgres' db
    db_url = settings.database_url
    base_url = db_url.rsplit("/", 1)[0]
    db_name = db_url.rsplit("/", 1)[1]

    from sqlalchemy import create_engine as ce

    admin_engine = ce(f"{base_url}/postgres", isolation_level="AUTOCOMMIT")

    with admin_engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        )
        if not result.fetchone():
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            print(f"Database '{db_name}' created.")
        else:
            print(f"Database '{db_name}' already exists.")

    admin_engine.dispose()


def seed_data():
    """Seed initial sources, categories, and admin user."""
    from app.auth.jwt import hash_password

    db = SessionLocal()
    try:
        # Seed sources
        for src_data in INITIAL_SOURCES:
            existing = (
                db.query(Source)
                .filter(Source.name == src_data["name"])
                .first()
            )
            if not existing:
                db.add(Source(**src_data, is_active=True))
                print(f"  Seeded source: {src_data['name']}")

        # Seed categories
        for cat_data in INITIAL_CATEGORIES:
            existing = (
                db.query(AlertCategory)
                .filter(AlertCategory.name == cat_data["name"])
                .first()
            )
            if not existing:
                db.add(AlertCategory(**cat_data))
                print(f"  Seeded category: {cat_data['name']}")

        # Seed admin user (only if JWT auth is configured and no admin exists)
        from app.config import settings as _settings

        if _settings.jwt_secret_key:
            admin = db.query(User).filter(User.username == "admin").first()
            if not admin:
                db.add(User(
                    username="admin",
                    hashed_password=hash_password("changeme"),
                    role="admin",
                    is_active=True,
                ))
                print("  Seeded admin user (password: changeme) - CHANGE IMMEDIATELY")

        db.commit()
        print("Seed complete.")
    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}")
        raise
    finally:
        db.close()


def main():
    print("=== CTI Summarizer - Database Setup ===")
    print()

    # 1. Create database
    print("[1/3] Creating database...")
    create_database()

    # 2. Create tables via Alembic (includes summaries table migration)
    print("[2/3] Running Alembic migrations...")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Fallback to direct SQLAlchemy create_all if Alembic fails.
        # This typically happens on a fresh DB where migration 001 references
        # normalized_alerts before the base tables are created by any migration.
        print(f"  Alembic warning: {result.stderr.strip()}")
        print("  Falling back to SQLAlchemy create_all...")
        Base.metadata.create_all(bind=get_engine())
        # Stamp alembic_version so future `alembic upgrade head` calls
        # know all migrations have already been applied.  Without this,
        # Alembic would try to re-create every table on the next run and fail.
        stamp = subprocess.run(
            ["alembic", "stamp", "head"],
            capture_output=True,
            text=True,
        )
        if stamp.returncode != 0:
            print(f"  Alembic stamp warning: {stamp.stderr.strip()}")
        else:
            print("  Alembic version stamped at head.")
    print("  Tables created.")

    # 3. Seed data
    print("[3/3] Seeding initial data...")
    seed_data()

    print()
    print("Setup complete! Next steps:")
    print("  1. Copy .env.example to .env and fill in your API keys")
    print("  2. Run: uvicorn app.main:app --reload")
    print("  3. Visit: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
