# Quick start

## Async usage

The clients are async-first and work as async context managers:

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

## Resources

Each client exposes resource namespaces:

| Namespace | Methods |
|---|---|
| `client.torrents` | `get(id)`, `search(query, **params)`, `download(id)` |
| `client.artists` | `get(id)`, `search(name)` |
| `client.user` | `me()` |
| `client.notifications` | `list(**params)` |
| `client.requests`, `client.collages`, `client.inbox` | see [API reference](../reference/resources.md) |

`**params` are passed through to the underlying Gazelle `ajax.php` action
(e.g. `format="FLAC"`, `page=1`).
