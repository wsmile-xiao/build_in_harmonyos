# wreport 3.36 HarmonyOS PC adaptation

Source: Debian's unmodified wreport 3.36 orig tarball, SHA-256 `fd9ba6f58eb92a06acf9e6950723fb7f48b1fe59fe3d99c5cfc71ac59e886ae9`.

Exploration changes verified on native OHOS/aarch64:

- Find Conan Lua 5.4's `lua-5.4.pc` as well as older Lua pkg-config names.
- Replace GNU-only `::stderr` and `exp10` assumptions for OHOS musl/libc++.
- Include `<string>` explicitly in Python binding header.
- Run the table checker with Meson's discovered Python, since `/usr/bin/python3` is absent.
- Link the extension module to libpython on this OHOS Python distribution.
- Raise Python `KeyError` directly for a missing vartable key rather than relying on exception-class identity across shared objects.
- Initialize the full string-pointer union storage, preventing random upper pointer bits on AArch64.

Native exploratory Meson build passed. With a writable `TMPDIR`, `meson test -C build4 --print-errorlogs` passed 2/2 suites on 2026-09-27. Native OHOS `conan create` then passed the 2/2 upstream suites and the real C++ consumer test.

The repository `ci/conan/setup.sh` and targeted `ci/conan/build_and_test.sh` also passed on the OHOS device on 2026-09-27: G0, L0, L1, L4 and L5 passed; L2 passed with `wrep-importtable --help` while `wrep --version/--help` emitted a non-blocking warning. The local runner needed an explicit `AR=/storage/Users/currentUser/usr/local/bin/llvm-ar`; the hosted PR CI did not have that override and failed during Meson configure with `Unknown linker(s): [['llvm-ar']]` (build #63139). The recipe now pins an executable absolute `ar` path in Meson's generated native file, with a fail-closed error if none is available. The 2026-09-28 native OHOS Conan rerun passed the two upstream Meson suites and the installed-package C++ consumer; its one-launch W3 evidence and exact log hash are under `workspace/wreport-w3-20260928T030900Z` on the contributor host. The 2026-09-27 local CI log remains at `/data/storage/el2/base/files/wreport-3.36-20260927/ci-build-ar.log` on the target device. Hosted CI must be rerun for the new recipe commit.
