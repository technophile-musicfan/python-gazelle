# python-gazelle

A typed, async-first Python client library for [Gazelle](https://github.com/WhatCD/Gazelle)-based
music trackers, with built-in support for **Orpheus** and **Redacted (RED)**.

- **Async-first**, built on [httpx](https://www.python-httpx.org/) — with synchronous wrappers if you prefer blocking calls.
- **Typed responses** via [pydantic v2](https://docs.pydantic.dev/) models.
- **API-key or cookie/login** authentication.
- **Built-in rate limiting** (token bucket) and **automatic retries** on transient errors.
- **Per-tracker handling** of the quirks that differ between Orpheus and RED (auth header, base URL, required headers).

!!! info "Status: Beta"
    The core API client is implemented (torrents, artists, user, notifications,
    requests, collages, inbox). Cross-seed, upload monitoring, and cross-upload are
    planned.

## Installation

```bash
uv add python-gazelle        # or: pip install python-gazelle
```

Requires Python 3.11+.

## Quick start

```python
import asyncio
from pygazelle import OrpheusClient

async def main():
    async with OrpheusClient(api_key="YOUR_API_KEY") as client:
        me = await client.user.me()
        print(me.username, me.id)

        results = await client.torrents.search("Daft Punk", format="FLAC")
        for r in results:
            print(f"{r.artist} - {r.group_name} ({r.group_year})")

asyncio.run(main())
```

See the [Quick start guide](guide/quickstart.md) for more, or jump straight to the
[API reference](reference/clients.md).

---

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
