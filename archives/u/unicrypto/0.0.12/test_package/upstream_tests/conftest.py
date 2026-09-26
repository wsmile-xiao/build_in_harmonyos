# Test-harness conftest for the packaged self-contained unicrypto.
# unicrypto.symmetric performs module-level `AES = get_preferred_cipher('AES')`
# etc. at import time.  On a pure-only host (no C-accelerated backend), the
# preferred backend is `pure`; importing unicrypto.backends.pure.AES triggers a
# circular re-import of the in-progress pure.AES module while symmetric is still
# initialising, unless symmetric is fully imported first.  Pre-importing
# unicrypto.symmetric (and the pure hashlib/pbkdf2 the tests use) lets the
# upstream pure-backend tests run without the circular-import failure.
import unicrypto.symmetric  # noqa: F401  (fully loads preferred-backend bindings)
import unicrypto.hashlib  # noqa: F401
