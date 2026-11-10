"""Conservative session-local identity checks; no remote profile lookup or fuzzy guessing."""

import re
import unicodedata
from urllib.parse import unquote, urlsplit


def normalized_name(value):
    value = unicodedata.normalize("NFKC", value or "").casefold()
    value = re.sub(r"\s*\|\s*(linkedin|x|twitter)\s*$", "", value)
    return " ".join(value.split()).strip()


def profile_identity(url):
    parsed = urlsplit(str(url))
    host = (parsed.hostname or "").lower()
    path = unquote(parsed.path).rstrip("/").casefold()
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        match = re.match(r"^/in/([^/]+)(?:/|$)", path)
        return "linkedin:" + match[1] if match else None
    if host in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
        parts = path.strip("/").split("/")
        if len(parts) == 1 and parts[0] not in {"", "home", "explore", "messages", "i", "search"}:
            return "x:" + parts[0]
    return None


def same_subject(left, right):
    a, b = profile_identity(left["source_url"]), profile_identity(right["source_url"])
    if a and b:
        return a == b  # Distinct profile URLs beat coincidentally identical names.
    name_a, name_b = normalized_name(left.get("person")), normalized_name(right.get("person"))
    if name_a and name_b and name_a == name_b:
        company_a = normalized_name(left.get("company"))
        company_b = normalized_name(right.get("company"))
        return not company_a or not company_b or company_a == company_b
    # Never identify a person merely because both captures came from the same inbox/article.
    if name_a or name_b:
        return False
    x, y = urlsplit(left["source_url"]), urlsplit(right["source_url"])
    return (x.hostname, x.path.rstrip("/"), x.query) == (y.hostname, y.path.rstrip("/"), y.query)


def duplicate_of(db, session_id, details, exclude_id=None, approved_only=False):
    from sqlalchemy import select

    from resumatch.models import Capture

    query = select(Capture).where(Capture.session_id == session_id, Capture.decision != "discarded")
    if exclude_id:
        query = query.where(Capture.id != exclude_id)
    if approved_only:
        query = query.where(Capture.decision == "approved")
    return next((c for c in db.scalars(query) if same_subject(c.details, details)), None)
