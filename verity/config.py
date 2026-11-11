"""Tiny .env loader (no dependencies). Real keys live in .env, which is git-ignored."""
import os

def load_env(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def data_dir():
    return os.environ.get("VERITY_DATA", "data/receipts")

def site_dir():
    return os.environ.get("VERITY_SITE", "docs")

def grade_hours():
    return float(os.environ.get("VERITY_GRADE_HOURS", "24"))
