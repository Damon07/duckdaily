"""Dependency-free checks for the daily publishing contract."""
from pathlib import Path
import re
from datetime import date

root = Path(__file__).resolve().parents[1]
errors = []
for path in sorted((root / "_posts").glob("*.md")):
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-duckdb-daily\.md", path.name)
    if not match:
        errors.append(f"{path.name}: invalid filename")
        continue
    day = match[1]
    try:
        date.fromisoformat(day)
    except ValueError:
        errors.append(f"{path.name}: invalid date")
    content = path.read_text(encoding="utf-8")
    sections = content.split("---", 2)
    if len(sections) != 3 or sections[0].strip():
        errors.append(f"{path.name}: missing front matter")
        continue
    metadata, body = sections[1], sections[2]
    for field in ("title", "date", "description", "coverage_date"):
        if not re.search(rf"^{field}:\s*\S", metadata, re.M):
            errors.append(f"{path.name}: missing {field}")
    if not re.search(rf'^coverage_date:\s*[\"\']?{day}[\"\']?\s*$', metadata, re.M):
        errors.append(f"{path.name}: coverage date differs from filename")
    if not re.search(rf'^date:\s*[\"\']?{day}\b', metadata, re.M):
        errors.append(f"{path.name}: date differs from filename")
    if not re.search(r'https://(?:github\.com/duckdb/|duckdb\.org/)', body):
        errors.append(f"{path.name}: missing official source")
if errors:
    raise SystemExit("\n".join(errors))
print("Publishing contract checks passed")
