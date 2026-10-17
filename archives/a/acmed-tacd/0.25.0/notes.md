# acmed-tacd 0.25.0

`acmed-tacd` packages the upstream `tacd` TLS-ALPN Challenge Daemon binary
from the ACMEd 0.25.0 workspace. It is intentionally separate from the
`acmed` daemon package.

The OHOS build uses the upstream `openssl_vendored` feature and the
`aarch64-unknown-linux-ohos` Cargo target. The build runs the upstream
workspace library and binary unit tests; doctests are unavailable on the
OHOS Rust worker because its Rust installation does not provide executable
`rustdoc`.
