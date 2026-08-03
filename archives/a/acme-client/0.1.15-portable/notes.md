# acme-client 0.1.15-portable adaptation notes

## Scope

- Package: acme-client/0.1.15-portable
- Upstream: kristapsdz/acme-client-portable commit `ba153daacb62d8a24fef6d6a5a737d2eff607509`
- Issue: #804
- Source: https://github.com/kristapsdz/acme-client-portable/archive/ba153daacb62d8a24fef6d6a5a737d2eff607509.tar.gz

## Adaptation

- Added a Conan application recipe.
- Builds the upstream `GNUmakefile` target with OHOS clang.
- Uses the Conan `libressl/3.9.1` dependency for the libtls API, crypto headers, and libraries.
- Installs the `acme-client` binary, man page, and ISC license.
- Signs the binary only for OHOS builds.

## Functional Validation Scope

- Upstream `acme-client-portable` depends on LibreSSL `libtls` for the core ACME HTTPS workflow.
- The package links the real LibreSSL `libtls`, `libssl`, and `libcrypto` libraries; no compatibility stub is used.
- The deterministic local test validates `tls_init`, configuration allocation, client allocation, and `tls_configure`.
- Live certificate issuance is not claimed by the local test because it requires an external ACME service, account material, DNS/domain control, and network access.

## Tests

- Added a `test_package` CLI smoke test and a compiled libtls API consumer.
- The CLI test runs the packaged binary with no arguments and verifies the expected usage error path.
- The C consumer compiles, links, and executes against the packaged LibreSSL dependency.
- Both tests are deterministic and avoid external ACME network calls.

## Local Validation

- `python -m py_compile` was run for recipe/test files.
- `git diff --check` passed.
- Linux x86_64 Conan 2.30.0 completed build, packaging, and `test_package`; the smoke test reported `PASS: acme-client binary reports usage without network access`.
- Full OHOS `conan create` requires the remote CI environment.
