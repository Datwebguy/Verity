"""Append-only receipt store: one JSON file per receipt. Only grade fields may change after write."""
import json
import os

from .config import data_dir
from .receipt import GRADE_FIELDS, body_hash


def _path(rid, root=None):
    return os.path.join(root or data_dir(), rid + ".json")


def save(receipt, root=None):
    root = root or data_dir()
    os.makedirs(root, exist_ok=True)
    p = _path(receipt["id"], root)
    if os.path.exists(p):
        raise FileExistsError("receipt %s already exists (receipts are append-only)" % receipt["id"])
    with open(p, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, sort_keys=True, ensure_ascii=False)
    return p


def load(rid, root=None):
    with open(_path(rid, root), encoding="utf-8") as f:
        return json.load(f)


def all_receipts(root=None):
    root = root or data_dir()
    if not os.path.isdir(root):
        return []
    out = []
    for n in sorted(os.listdir(root)):
        if n.endswith(".json"):
            with open(os.path.join(root, n), encoding="utf-8") as f:
                out.append(json.load(f))
    return sorted(out, key=lambda r: r["timestamp"], reverse=True)


def update_grade(rid, fields, root=None):
    r = load(rid, root)
    if body_hash(r) != r.get("receipt_hash"):
        raise ValueError("receipt %s body does not match its hash; refusing to grade a tampered receipt" % rid)
    bad = set(fields) - set(GRADE_FIELDS)
    if bad:
        raise ValueError("only grade fields may be updated, got %s" % sorted(bad))
    r.update(fields)
    with open(_path(rid, root), "w", encoding="utf-8") as f:
        json.dump(r, f, indent=2, sort_keys=True, ensure_ascii=False)
    return r


def verify(receipt):
    return body_hash(receipt) == receipt.get("receipt_hash")
