# weggli/0.2.4 for HarmonyOS PC

weggli is a fast and robust semantic search tool for C and C++ codebases
(originally Google Project Zero, now maintained at
[weggli-rs/weggli](https://github.com/weggli-rs/weggli)). It matches patterns
against Abstract Syntax Trees, so queries look like C/C++ code instead of
regular expressions.

This recipe builds the official `v0.2.4` tag for HarmonyOS PC
(`aarch64-unknown-linux-ohos`, clang 15, libc++, Release) and packages the
`weggli` CLI binary together with its license and README.

## OHOS adaptation

* **Toolchain** — `rust-toolchain/1.97.1` from the ohpcd repository
  (`tool_requires`) provides cargo/rustc plus the `aarch64-unknown-linux-ohos`
  standard library. Conan unpacks that payload with mode 0770 and HMDFS rejects
  `chmod`, so cargo/rustc (and the `librustc_driver` rustc dlopens) are copied
  into the private build folder and — only if the loader still refuses them —
  self-signed with the OHOS `binary-sign-tool` (`below/0.11.0` precedent).
* **Cargo runtime** — cargo 1.97 dynamic-links `libssl.so`/`libcrypto.so`/`libz.so`
  and needs `SSL_get0_group_name` (OpenSSL 3.5+), which the system OpenSSL 3.0
  does not export; the sha256-pinned Harmonybrew OHOS bottles are unpacked into
  the build folder and put on `LD_LIBRARY_PATH` (`below`/`argc`/`alass`
  precedent). No shared system prefix is written (R49).
* **C++ standard library** — `build.rs` compiles one C++ grammar file with the
  `cc` crate, which emits `-lstdc++` by default; the OHOS SDK ships `libc++`
  only, so the build sets `CXXSTDLIB=c++`.
* **Lock graph (knowledge E358)** — `aarch64-unknown-linux-ohos` is
  `target_os=linux` + `target_env=ohos`, which the locked libc 0.2.112 and
  nix 0.17.0 predate. Two auditable patches migrate the lock graph inside the
  upstream semver constraints (`libc 0.2.155`, `nix 0.28.0` with the `signal`
  feature) and keep the build `--locked`. **No weggli source line is changed.**

## Tests

* Upstream Rust suite (executed in `build()`):
  `cargo test --release --locked --target aarch64-unknown-linux-ohos --lib --bins --tests`
  → **56 passed / 0 failed / 0 ignored** (2 lib unit tests, 9 `tests/cli.rs`,
  45 `tests/query.rs`); counts are the framework's own `test result:` lines and
  are persisted to `res/upstream_test_result.json` so that conan's cache-hit
  path still publishes them from `test_package`.
* Upstream Python bindings (`tests/__init__.py`, `--features python`) →
  **4 passed / 0 failed** (the OHOS loader needs `LD_PRELOAD=libpython3.12.so.1.0`
  for pyo3 extension modules; command and log in `reports/upstream-tests.md`).
* `test_package/test.sh` → **8 passed / 0 failed**: 5 consumer CLI cases plus
  3 HarmonyOS-specific cases (AArch64/OHOS artifact, the SIGPIPE-reset path
  added by the nix dependency, and a semantic query over an OHOS sample fixture).

## Consumer usage

```bash
conan install --requires=weggli/0.2.4 -pr:h=ci/conan/profiles/ohos-aarch64
weggli --version                 # weggli 0.2.4
weggli '{_ $buf[_]; memcpy($buf,_,_);}' src/
```

The package installs only the CLI binary (`bin/weggli`); weggli's Rust library
and the optional pyo3 extension module are not part of the distributed package.
