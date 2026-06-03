## 1. gazelle-client deltas

- [x] 1.1 Document the new resource namespaces (`bookmarks`, `subscriptions`, `site`)
- [x] 1.2 Document expanded torrent methods (`get_group`, `add_tag`, `add_log`)
- [x] 1.3 Document `artists.similar` and user `get`/`search`/`torrents`
- [x] 1.4 Document the `requests` resource (`get`/`search`/`fill`)

## 2. gazelle-transport deltas

- [x] 2.1 Document the write request path (POST + multipart + authkey injection)
- [x] 2.2 Document non-idempotent write safety (no 429/5xx retry; cookie-401 re-auth; no 403 resend)

## 3. response-models deltas

- [x] 3.1 Replace the tracker-subclasses requirement with tolerant base models
- [x] 3.2 Document endpoint model coverage

## 4. Reconcile

- [x] 4.1 Validate the change (`openspec change validate api-surface-expansion`)
- [x] 4.2 Archive to fold deltas into the main specs (`openspec archive`)
