# Rate limiting & retries

Both rate limiting and retries are on by default and configurable per client:

```python
from pygazelle import OrpheusClient

OrpheusClient(api_key="...", rate=3.0, max_retries=3)
```

- `rate` — requests per second (token bucket).
- `max_retries` — retries with exponential backoff on `429` and `5xx` responses.

## How it works

The [transport layer](../reference/transport.md) uses a `TokenBucket` to smooth
out request bursts, then retries transient failures (`429 Too Many Requests` and
`5xx` server errors) with exponential backoff. Once `max_retries` is exhausted on
a `429`, a [`GazelleRateLimitError`](error-handling.md) is raised.

!!! tip
    For probing a live tracker (e.g. validating credentials), set `max_retries=0`
    and make a single read-only request to avoid hammering the API.
