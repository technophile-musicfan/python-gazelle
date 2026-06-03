# Authentication

Pass either an API key or a username/password (cookie/login auth):

```python
from pygazelle import OrpheusClient

OrpheusClient(api_key="...")                       # API-key auth
OrpheusClient(username="user", password="pass")    # cookie/login auth
```

Generate an API key in your tracker's user settings.

## Per-tracker differences

Orpheus and RED expect different `Authorization` header formats — the client
handles this for you:

- **Orpheus** uses `Authorization: token <key>`.
- **RED** uses a bare `Authorization: <key>` header and requires a `User-Agent`.

This is wired up in the client subclasses and the
[transport layer](../reference/transport.md), so you only ever pass your
credentials.

!!! warning "Live API care"
    Never loop requests against a tracker after an auth error — repeated failed
    auth can get you banned. Verify credentials with a single request.
