# fluent-bit - OpenHarmony OHOS adaptation

Fluent Bit is a fast and lightweight log processor and forwarder for
collecting, transforming, and forwarding observability data.

## Versions

- 5.0.9: real-dependency HarmonyOS adaptation passed on device

## Build strategy

This version intentionally does not use the historical zero-dependency stub
strategy.  The first validation target keeps core features real:

- TLS through `openssl/3.5.6.1`
- SQLDB through `sqlite3/3.49.1`
- YAML config through `libyaml/0.2.5`
- BSD fts APIs through `musl-fts/1.2.7`

Large optional surfaces such as Kafka, LuaJIT, WASM, Arrow, Avro, and the full
AWS plugin set stay disabled until the core build and upstream test audit are
stable.

## Package layout

- `5.0.9/conanfile.py` - Conan 2.x application recipe
- `5.0.9/patches/` - source patches for generated include paths and OHOS C build fixes
- `5.0.9/test_package/` - package smoke test for the installed binary
- `5.0.9/manifest.yaml` - version manifest
- `5.0.9/notes.md` - current status and next validation steps
