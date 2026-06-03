# Error handling

All exceptions derive from [`GazelleError`](../reference/errors.md):

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

## Exception hierarchy

| Exception | Raised when |
|---|---|
| `GazelleError` | Base class for everything below. |
| `GazelleAuthError` | Bad credentials, `401`, or `403`. |
| `GazelleRateLimitError` | `429` after `max_retries` is exhausted. |
| `GazelleNotFoundError` | `404` / unknown id. |
| `GazelleAPIError` | Any other API failure. Carries `status_code`. |

See the [Errors reference](../reference/errors.md) for full details.
