# algernon

Algernon is a small self-contained pure-Go web server with built-in support for Lua, Markdown, Pongo2, JSX and more. It supports HTTP/2, QUIC, Redis, PostgreSQL and automatic TLS via CertMagic.

- Homepage: <https://github.com/xyproto/algernon>
- License: BSD-3-Clause
- Package type: command-line application (web server)
- CI note: the recipe uses a Go 1.26.x toolchain (worker-provided when available, otherwise a sha256-verified go1.26.3 from the Aliyun mirror) and runs the full upstream `go test -mod=vendor ./...` suite before `go build`. On OHOS, test binaries and the final executable are self-signed with binary-sign-tool.
