# Transport

The transport layer is the HTTP plumbing beneath the clients: auth, rate
limiting, retries, and response parsing. You normally don't construct it
directly — the client subclasses wire it up — but it's documented here for
reference and advanced configuration.

::: pygazelle.transport.GazelleTransport

::: pygazelle.transport.TokenBucket
