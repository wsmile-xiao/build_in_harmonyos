# uwsgi-rpc 2.0.31 adaptation notes

## Scope

- Issue: TBD. Local repository files, branch names, commit messages, and session context did not contain a clear issue number for `uwsgi-rpc`.
- Package path: `archives/u/uwsgi-rpc/2.0.31`.
- This package adapts the upstream uWSGI `plugins/rpc` dynamic plugin, not the full uWSGI server binary.

## Source

- Upstream: https://github.com/unbit/uwsgi
- Stable tag: 2.0.31
- Tag commit: ce518cce893d20e9c79eb2607f3a6c250468ae4d
- Source archive: https://github.com/unbit/uwsgi/archive/refs/tags/2.0.31.tar.gz
- SHA256: d5fb7b058a6e037cad1f0fb8841de56d673d80a3af036bba830143b60c67c3dc
- The legacy `https://projects.unbit.it/downloads/uwsgi-2.0.31.tar.gz` URL returned 404 during local source probing, so the GitHub tag tarball is used.

## Build

- Build system: uWSGI custom build driver, `uwsgiconfig.py`.
- Recipe entry point: `python3 uwsgiconfig.py --plugin plugins/rpc rpc_conan`.
- The recipe writes `buildconf/rpc_conan.ini` in the extracted source tree.
- Profile choices:
  - `inherit = minimal`
  - `plugins = rpc`
  - `xml/yaml/json/ssl/pcre/routing = false`
  - `embedded_plugins = null`
- No source patches are applied.
- Output: `lib/uwsgi/rpc_plugin.so`.

## Dependencies

- Required dependencies: none.
- `plugins/rpc/uwsgiplugin.py` has empty `CFLAGS`, `LDFLAGS`, and `LIBS`.
- Optional features are deliberately outside this PR:
  - XML-RPC wrapper requires libxml2 and `UWSGI_XML_LIBXML2`.
  - JSON-RPC wrapper requires jansson.
  - Router helpers are under `UWSGI_ROUTING`; enabling them would follow the same routing/PCRE pattern as `uwsgi-router_http`.
- W0 checks:
  - `zlib/1.3.1` recipe exists on `ohpcd`.
  - `libxml2/2.12.5` and `gettext/0.22` from old `uwsgi/2.0.24` notes are not current on `ohpcd`; visible versions are `libxml2/2.15.3*` and `gettext/0.22.5`.
  - This recipe avoids those optional dependencies instead of mixing dependency adaptation into this PR.

## Upstream Tests

- uWSGI ships global `make check`, `make tests`, and language-plugin tests.
- `tests/rpc.py` and `tests/testrpc.py` require the Python plugin/runtime path, which is intentionally not enabled for this minimal plugin package.
- There is no standalone upstream test for the dynamic `plugins/rpc` build without language plugins, so plugin-specific upstream tests are recorded as 0/0.

## Added Test Package

- Builds one C probe with CMake.
- The probe validates that the packaged plugin:
  - exists and is larger than 1 KiB,
  - is ELF64 little-endian,
  - is an `ET_DYN` shared object,
  - targets AArch64 on OHOS or x86_64 in local host checks,
  - contains RPC plugin/request strings such as `rpc_plugin`, `uwsgi_rpc`, RPC request error strings, `application/binary`, and `CONTENT_LENGTH`.
- It intentionally does not require standalone `dlopen(..., RTLD_NOW)` because uWSGI plugins are normally loaded by a uWSGI process that provides the core global symbols.

## Local Validation

- Worktree: `D:\harmonyos\worktrees\uwsgi-rpc`
- Branch: `feat/uwsgi-rpc-2.0.31`
- Source hash verified locally from the GitHub tag tarball:
  `d5fb7b058a6e037cad1f0fb8841de56d673d80a3af036bba830143b60c67c3dc`.
- Upstream structure checked:
  - `buildconf/nolang.ini` inherits `base.ini`, where `rpc` is one of the embedded plugins.
  - `plugins/rpc/rpc_plugin.c` defines `struct uwsgi_plugin rpc_plugin` with `.name = "rpc"` and `.modifier1 = 173`.
  - `plugins/rpc/uwsgiplugin.py` declares empty local compile/link dependency lists.
- Static recipe checks:
  - `python -m py_compile` passed for `conanfile.py` and `test_package/conanfile.py`.
  - `conan inspect archives/u/uwsgi-rpc/2.0.31` parsed recipe metadata successfully.
  - `git diff --check -- archives/u/uwsgi-rpc/2.0.31` reported no whitespace errors.
  - Windows host `conan create` is intentionally rejected by `validate()` with `Unsupported OS: Windows`.
  - The C probe source compiles with local MinGW GCC for syntax checking.
- Not run locally:
  - Full `conan create` for OHOS. This Windows host has no runnable `/data/service/hnp/bin/clang` toolchain path.
  - `zsh ci/conan/build_and_test.sh`. This Windows host has no usable local `zsh`.
  - A repeated `git ls-remote` tag check later failed due to a transient GitHub connection timeout; the tag had already been confirmed earlier in the run.

## OHOS True-device Validation

- Date: 2026-08-14.
- Device: HarmonyOS / HongMeng Kernel 1.12.0 / aarch64.
- SSH entry: `currentUser@frp-tip.com:33332`.
- Isolated job: `/storage/Users/currentUser/ohos-users/codex/uwsgi-rpc-2.0.31-20260814-033645`.
- Passing run: `/storage/Users/currentUser/ohos-test-runs/codex-uwsgi-rpc-uwsgi-rpc-2.0.31-conan-r2-20260814-034916-8743`.
- Command:
  `CONAN_PROFILE=ohos-aarch64-local zsh ci/conan/build_and_test.sh archives/u/uwsgi-rpc/2.0.31`
- Result: exit code 0, `Total: 1`, `Success: 1`, `Failed: 0`.
- Gate results:
  - `L0_RESULT=pass: all checks passed`
  - `L1_RESULT=pass: test_package executed`
  - `L2_RESULT=skip: no bin/ dir`
  - `L4_RESULT=pass: no patches`
  - `L5_RESULT=pass: lib/ has content`
- Package reference:
  `uwsgi-rpc/2.0.31#2ce1cab1e5a1bea444765e2331fe7a10:6b129b068851896169fae42d399fa922d239ce8a#20b42370368e6a4bde635596e70bb10d`.
- Packaged plugin:
  `lib/uwsgi/rpc_plugin.so`, 22848 bytes, SHA256
  `9e2846d9e33213f425f4c8eb078263597f52e99e56ce48a3ff042a75a14e263c`.
- Test output ended with:
  `uwsgi-rpc plugin probe OK: 22848 bytes`.
- Log hashes:
  - stdout: `2476c9dda1ee5cd9c73efa67b49089c097fd695cc87ac073dd00c03c20ef8812`
  - runner: `f93d45612532461b1d5200f4bf280097c36ef5a3119e53a92a17cb44326eeb7d`
  - meta: `04579969122addfed07644343c4d61ea937912cbd107c273b84a9dbb42e239e8`
  - conan build log: `a7f451e6e24cf291d99ed68ce287b7f89c438604d64f39226e77d7d8359d76d5`
- First attempt reached `conan create` and failed before building because the fresh isolated `CONAN_HOME` had a default Conan `settings.yml` without `OHOS`; the retry copied the device's existing OHOS-aware settings into the isolated job. The device also exposes clang under `/storage/Users/currentUser/usr/local/bin`, so the retry used a job-local profile with that toolchain path. These were true-device job setup fixes only; no recipe changes were needed.
- Non-blocking environment warnings observed:
  - CI pre-download tried `curl`, which is not installed; Conan's own download succeeded through the mirror fallback URL.
  - CMake printed `System is unknown to cmake` for `HarmonyOS` during the C probe configure, but generated and built successfully.
  - `make` printed a jobserver `mkfifo` permission warning under the runner temp directory, but the test executable still built and ran successfully.

## Next Validation Commands

Run only when the OHOS device/shadow CI queue is free:

```sh
CI_PACKAGES="archives/u/uwsgi-rpc/2.0.31" zsh ci/conan/build_and_test.sh
```

or the shadow runner equivalent:

```sh
/path/to/run-ohos-shadow-ci.sh archives/u/uwsgi-rpc/2.0.31
```

Expected CI scope: one package, producing `lib/uwsgi/rpc_plugin.so`, with L0/L1 passing via the C probe and L2 either skipped or treated as plugin package smoke rather than CLI `--version`.
