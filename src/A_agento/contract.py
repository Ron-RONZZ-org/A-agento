'''Service contract between A-agento and A-lien.

This module documents the expected interface for A-lien's RetpostoService.
A-agento depends on these methods being available.

## Contract: RetpostoService

### Required Methods

```python
class RetpostoService:
    def get(self, uuid: str) -> dict | None:
        """Get a single email by UUID.
        ...
        """

    def list(self, limit: int = 50, unread_only: bool = False) -> list[dict]:
        """List recent emails.
        ...
        """
```

### Fallback: Direct DB Access

If RetpostoService is not available, A-agento falls back to direct SQL.

### Expected Schema: mesagxoj table

| Column | Type | Description |
|--------|------|-------------|
| uuid | TEXT PRIMARY KEY | Unique identifier |
| de | TEXT | Sender email |
| al | TEXT | Recipients (JSON array) |
| subjekto | TEXT | Subject line |
| korpo | TEXT | Email body |
| ricevita_je | TEXT | ISO timestamp |
| legita | INTEGER | 0=unread, 1=read |

### Version Compatibility

- A-lien >= 1.0.0: Full service API
- A-lien < 1.0.0: Use fallback direct DB access
'''

from __future__ import annotations


# Contract version - update when contract changes
CONTRACT_VERSION = "1.0.0"

# Expected keys in email dict from A-lien
EXPECTED_EMAIL_KEYS = {
    "uuid",
    "de",  # sender
    "al",  # recipients (JSON array)
    "subjekto",  # subject
    "korpo",  # body
    "ricevita_je",  # received timestamp
    "legita",  # read status
}

# Optional keys that may be present
OPTIONAL_EMAIL_KEYS = {
    "kontrakto",
    "foldero",
    "al_konto",
    "from_konto",
}


def validate_email_dict(email: dict) -> tuple[bool, list[str]]:
    """Validate email dict has required keys.

    Args:
        email: Email dict from A-lien

    Returns:
        (is_valid, missing_keys)
    """
    missing = [k for k in EXPECTED_EMAIL_KEYS if k not in email]
    return len(missing) == 0, missing


__all__ = [
    "CONTRACT_VERSION",
    "EXPECTED_EMAIL_KEYS",
    "OPTIONAL_EMAIL_KEYS",
    "validate_email_dict",
]