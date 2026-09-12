import logging
import re

logger = logging.getLogger(__name__)

# This is purely for logging/alerting (an audit trail), not a real defense.
# It can be trivially evaded by attackers.
INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?previous\s+instructions",
    r"(?i)system\s*:",
    r"(?i)new\s+instructions\s*:",
    r"(?i)you\s+are\s+now",
]

def scan_for_injection(diff: str, file_path: str, repo: str, pull_number: int) -> bool:
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, diff):
            logger.warning("Potential prompt injection detected in %s PR #%s file %s.", repo, pull_number, file_path)
            return True
    return False
