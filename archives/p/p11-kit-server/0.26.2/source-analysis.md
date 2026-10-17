# p11-kit-server 0.26.2 source and build analysis

## Provenance

- Upstream tag/release: `0.26.2`, released 2026-02-06.
- Upstream archive: `p11-kit-0.26.2.tar.xz`.
- Size: 1,069,216 bytes.
- SHA256: `09fd9f44da4813a3141e73d5e7cf7008e5660d0405f13d56c15e1da9dcecf828`.
- The locally inspected Ubuntu `orig.tar.xz` mirror matched the independently published Buildroot SHA256 exactly.

## Build systems

The release contains both generated Autotools files (`configure`, `configure.ac`, `Makefile.am`) and Meson files (`meson.build`, `meson_options.txt`). Meson is selected because it exposes explicit feature switches and focused test selection without editing generated build files.

## Server targets

Upstream defines these installed private commands in `p11-kit/meson.build`:

- `p11-kit-server` from `p11-kit/server.c`.
- `p11-kit-remote` from `p11-kit/remote.c`.

The server resolves its helper from `P11_KIT_PRIVATEDIR`, falling back to the compiled `PRIVATEDIR`. The Conan package defines `P11_KIT_PRIVATEDIR` through `VirtualRunEnv` so the helper remains relocatable in the package cache.

The commands link to upstream `libp11-kit.so.0`; the package deliberately does not duplicate that library and declares `p11-kit/0.26.2` as a runtime requirement.

The recipe runs `meson install` before selecting the two commands, rather than copying build-tree executables. This lets Meson remove or rewrite build-directory RUNPATH entries. All other installed files are then removed from the server subpackage.

The source archive marks Meson helper and test scripts non-executable in the device checkout. The recipe applies the same source-level portability pattern validated by the separate p11-kit 0.26.2 adaptation: Meson invokes `meson_post_install.sh`, `gen-pkcs11-gnu.sh`, and the selected `test-server.sh` explicitly through `sh`. Packaged OHOS commands are re-signed after installation and copying.

## Focused upstream tests

- `test-server`: eight registered C test cases covering provider and all-token modes, environment/config address discovery, initialization, slot enumeration, sessions, and write protection.
  On OHOS, running all eight in one process deterministically leaves the fourth case with stale dynamically loaded client-module state. The upstream runner accepts a case name; the recipe therefore runs each unchanged named case in an isolated process. All original assertions remain active and pass 8/8.
- `test-server.sh`: server start/address/PID/stop contract using the upstream mock module. Its `p11tool` client-access sub-step is optional and skips if the tool is absent.
  The device has an incompatible optional `p11tool`; the probe treats it as unavailable but continues the mandatory server lifecycle assertions, which pass 1/1.

The complete p11-kit source suite also covers the core library, trust module, CLI object operations, and platform compatibility. Those areas belong to the core `p11-kit` package rather than this binary subpackage; this recipe runs the two server-specific tests.

Passing upstream inventory:

- `/server/initialize`
- `/server/initialize-no-address`
- `/server/initialize-address-from-config`
- `/server/open-session`
- `/server/open-session-write-protected`
- `/server/all/initialize`
- `/server/all/initialize-no-address`
- `/server/all/open-session`
- `test_server_access` from `test-server.sh`

## OHOS compile probe

The Unix peer credential helper selects `SO_PEERCRED`, `getpeereid`, or `getpeerucred` at compile time and otherwise raises an unsupported-platform error. The OHOS build completed all 245 Meson targets, confirming that the Linux-compatible compile path is available.

The filesystem behavior is mount-specific, not a device-wide AF_UNIX prohibition. Probes on HMDFS paths under `/storage/Users/currentUser` return `EPERM`, while `/data/storage/el2/base/cache` supports filesystem `AF_UNIX bind()`. The recipe probes the inherited `TMPDIR`, the application cache, and a build-local fallback, then selects the first socket-capable directory or fails explicitly.

The consumer test independently compiles and runs a C bind probe. `EPERM` is not accepted as success; the passing run confirms a real filesystem socket endpoint in `/data/storage/el2/base/cache`.

The HNP compiler path is a relative link into a versioned SDK. The Conan Python runtime does not reliably resolve it with `os.path.realpath()`, so both recipes ask clang for `--print-resource-dir`, derive the sibling LLVM `lib`, and use `realpath` only as a fallback. This ensures lld loads the SDK-matched `libxml2.so.16`.
