# python-gazelle

A typed, async-first Python client library for [Gazelle](https://github.com/WhatCD/Gazelle)-based
music trackers, with built-in support for **Orpheus** and **Redacted (RED)**.

📖 **[Full documentation](https://technophile-musicfan.github.io/python-gazelle/)** — guides + auto-generated API reference.

- **Async-first**, built on [httpx](https://www.python-httpx.org/) — with synchronous wrappers if you prefer blocking calls.
- **Typed responses** via [pydantic v2](https://docs.pydantic.dev/) models.
- **API-key or cookie/login** authentication.
- **Built-in rate limiting** (token bucket) and **automatic retries** on transient errors.
- **Per-tracker handling** of the quirks that differ between Orpheus and RED (auth header, base URL, required headers).

> Status: Beta. The core API client is implemented (torrents, artists, user, notifications, requests, collages, inbox). Cross-seed, upload monitoring, and cross-upload are planned.

## Installation

```bash
uv add python-gazelle        # or: pip install python-gazelle
```

Requires Python 3.11+.

## Quick start (async)

```python
import asyncio
from pygazelle import OrpheusClient

async def main():
    async with OrpheusClient(api_key="YOUR_API_KEY") as client:
        me = await client.user.me()
        print(me.username, me.id)

        # Search returns group-level results
        results = await client.torrents.search("Daft Punk", format="FLAC")
        for r in results:
            print(f"{r.artist} - {r.group_name} ({r.group_year})")

        # Fetch a specific torrent by id, then download its .torrent bytes
        for n in await client.notifications.list():
            print(n.notification_type, n.group_name)
            torrent = await client.torrents.get(n.torrent_id)
            print(torrent.format, torrent.size)
            data = await client.torrents.download(torrent.id)
            break

asyncio.run(main())
```

`RedactedClient` has the same interface — just swap the class:

```python
from pygazelle import RedactedClient

async with RedactedClient(api_key="YOUR_RED_API_KEY") as client:
    ...
```

## Synchronous usage

If you're not in an async context, use the `*Sync` clients. Every method is the
same, just without `await`:

```python
from pygazelle import OrpheusClientSync

client = OrpheusClientSync(api_key="YOUR_API_KEY")
try:
    me = client.user.me()
    results = client.torrents.search("Daft Punk", format="FLAC")
finally:
    client.close()
```

## Authentication

Pass either an API key or username/password (cookie/login auth):

```python
OrpheusClient(api_key="...")                       # API-key auth
OrpheusClient(username="user", password="pass")    # cookie/login auth
```

Generate an API key in your tracker's user settings. Note that Orpheus and RED
expect different `Authorization` header formats — the client handles this for you.

## Resources

Each client exposes resource namespaces:

| Namespace | Methods |
|---|---|
| `client.torrents` | `get(id)`, `get_group(id)`, `search(query, **params)`, `download(id)` |
| `client.artists` | `get(id)`, `search(name)`, `similar(id, limit=None)` |
| `client.user` | `me()`, `get(id)`, `search(query, **params)`, `torrents(id, type, ...)` |
| `client.notifications` | `list(**params)` |
| `client.bookmarks` | `torrents()`, `artists()` |
| `client.subscriptions` | `list()` |
| `client.requests`, `client.collages`, `client.inbox` | see source |

`**params` are passed through to the underlying Gazelle `ajax.php` action
(e.g. `format="FLAC"`, `page=1`).

## Rate limiting & retries

Both are on by default and configurable per client:

```python
OrpheusClient(api_key="...", rate=3.0, max_retries=3)
```

- `rate` — requests per second (token bucket).
- `max_retries` — retries with exponential backoff on `429` and `5xx` responses.

## Error handling

All exceptions derive from `GazelleError`:

```python
from pygazelle import (
    GazelleError, GazelleAuthError, GazelleRateLimitError,
    GazelleNotFoundError, GazelleAPIError,
)

try:
    torrent = await client.torrents.get(123)
except GazelleNotFoundError:
    ...        # 404 / unknown id
except GazelleAuthError:
    ...        # bad credentials / 401 / 403
except GazelleRateLimitError:
    ...        # 429 after retries exhausted
except GazelleAPIError as e:
    ...        # other API failure (e.status_code, str(e))
```

## Development

See [CLAUDE.md](CLAUDE.md) for the architecture overview, conventions, and how to
run the test suite (including `.env` setup and capturing API fixtures for the
model tests).

## Project Docs

The full docs site (user guides + auto-generated API reference) is published at
**<https://technophile-musicfan.github.io/python-gazelle/>**. It's built with MkDocs
+ Material + mkdocstrings; build it locally with `make docs` or preview with
`make docs-serve`.

For how to install uv and Python, see [installation.md](docs/installation.md).

For development workflows, see [development.md](docs/development.md).

For instructions on publishing to PyPI, see [publishing.md](docs/publishing.md).

---

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
