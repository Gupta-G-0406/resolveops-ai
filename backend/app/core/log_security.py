
import logging
import re


SECRET_NAMES = (
    r"api[_-]?key|access[_-]?token|"
    r"refresh[_-]?token|password|"
    r"client[_-]?secret|secret"
)

SENSITIVE_PATTERNS = [
    (
        re.compile(
            r"(?i)(authorization\s*[:=]\s*"
            r"bearer\s+)[^\s,;\"']+"
        ),
        r"\1[REDACTED]",
    ),
    (
        re.compile(
            rf'(?i)((?:["\'])?(?:{SECRET_NAMES})'
            rf'(?:["\'])?\s*[:=]\s*["\']?)'
            rf'[^"\'\s,;}}]+'
        ),
        r"\1[REDACTED]",
    ),
]


def redact_sensitive_data(value: str) -> str:
    for pattern, replacement in SENSITIVE_PATTERNS:
        value = pattern.sub(replacement, value)

    return value


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()

        record.msg = redact_sensitive_data(message)
        record.args = ()

        return True
