"""Default names for repeat runs within one workflow, using the server's UTC date."""

import re
from datetime import UTC, timedelta

from sqlalchemy import select

from resumatch.models import OutreachSession


def next_run_name(db, workflow_id, at):
    at = at.astimezone(UTC)
    day = at.date().isoformat()
    midnight = at.replace(hour=0, minute=0, second=0, microsecond=0)
    existing = db.execute(select(OutreachSession.run_name, OutreachSession.started_at).where(
        OutreachSession.workflow_id == workflow_id
    )).all()
    # Custom/renamed runs still consume their place in today's sequence.
    number = sum(midnight <= row.started_at < midnight + timedelta(days=1) for row in existing)
    pattern = re.compile(re.escape(day) + r" \((\d+)\)$")
    names = {row.run_name for row in existing}
    for name in names:
        match = pattern.fullmatch(name)
        if match:
            number = max(number, int(match[1]) + 1)
    if day in names:
        number = max(number, 1)
    candidate = day if number == 0 else f"{day} ({number})"
    while candidate in names:
        number += 1
        candidate = f"{day} ({number})"
    return candidate
