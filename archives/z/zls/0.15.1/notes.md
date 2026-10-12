# zls 0.15.1 HarmonyOS adaptation notes

## Upstream

- Project: `zigtools/zls` (Zig Language Server)
- Tag: `0.15.1`
- Source URL: `https://codeload.github.com/zigtools/zls/tar.gz/refs/tags/0.15.1`
- Source sha256: `40a4559c3007ed9333769fc3e111ed466403b53f31ad9242874a62ab385b331b`
- License: MIT
- Product: single static aarch64 ELF `zig-out/bin/zls` (pure Zig, no libc, no C sources)

## Toolchain pinning

- `build.zig`: `minimum_build_zig_version = "0.15.1"`; Zig 0.16.x / 0.14.x hit an
  `@compileError`. Must build with the in-repo `zig/0.15.2` tool package
  (its wrapper auto-signs compiler-spawned ELFs and carries the
  copy_file_range OVERFLOW + test-runner terminal-mode patches). `zig/0.16.x`
  is forbidden for this recipe.
- `0.15.1` is a tagged release, so `getVersion()` returns immediately without
  `git describe` — no git needed at build time.

## Dependency vendoring (minizign 0.1.13 paradigm)

Upstream `build.zig.zon` declares 4 dependencies: `known-folders`,
`diffz`, `lsp_kit` (hard) and `tracy` (lazy, only fetched with
`-Denable-tracy`; not enabled here, so never fetched).

Hard dependencies are downloaded in `source()` from pinned tarballs
(conandata.yml `zig_dependencies`, each with SHA256 and a gh-proxy fallback
URL) and extracted to `<source>/deps/<name>`; a patch rewrites the three
hard dependency entries to local `.path` refs so neither `zig build` nor
`zig build test` touches the network on OHOS runners:

- known-folders `92defaee76b07487769ca352fd0ba95bc8b42a2f`
  sha256 `b2248ce99958d17023fcd60c606fa20c69f089ff6877aa23aecda57824be7844`
- diffz `a20dd1f11b10819a6f570f98b42e1c91e3704357`
  sha256 `c4fe9d0624ca5a9499fc4592e404eedb94934491ef214e5199be61c441d7c074`
- lsp-kit `576e9405b1ab22c17c0f9318feed3278aa66b0ea`
  sha256 `dd20a2951144f9c755c282853542e4f417e60c6673817d044067192444bfdabe`

All three are leaf packages (no nested Zig dependencies; verified from their
build.zig.zon).

## OHOS build adaptations

1. Zig host libc probing bypass (flow-control 0.7.2 precedent): clear
   `CC/CXX/CFLAGS/CPPFLAGS/LDFLAGS/CPATH/*_INCLUDE_PATH` in `build()`. zls is
   pure Zig, but the build runner / test runner host executables and zig's
   target probing still consult the environment, so the env is cleared
   defensively.
2. Zig caches are pinned into the conan build folder
   (`ZIG_GLOBAL_CACHE_DIR` / `ZIG_LOCAL_CACHE_DIR`) and
   `ZIG_OHOS_SIGN_ROOTS` covers both caches plus `zig-out/`, so every
   compiler-emitted ELF (zls_gen, build runner, test binaries) is
   auto-signed by the zig/0.15.2 wrapper before being spawned.
3. The final `zig-out/bin/zls` is signed again in `package()` via
   `binary-sign-tool` (`.codesign` section stripped with `llvm-objcopy`
   first), then packaged.
4. `zig build test` on a host (native) build also runs the build-runner
   cases which spawn `zig build` subprocesses (using `b.graph.zig_exe`, i.e.
   the wrapper path — signature propagation stays inside the covered cache
   roots).

## Upstream tests

`zig build test -Doptimize=ReleaseSafe` (run in `build()`, i.e. inside the
authoritative conan create). Measured on the OHOS device runner:

- `tests/tests.zig` main unit suite: **409 passed; 8 skipped; 0 failed**
  (417 test blocks). The 8 skips are upstream-authored unconditional
  `if (true) return error.SkipZigTest` TODO skips — 7 in
  `tests/lsp_features/completion.zig` (lines 67, 151, 3366, 3683, 3948,
  4161, 4234) and 1 in `tests/lsp_features/definition.zig` (line 146).
  They fire on every platform (upstream keeps them in-tree) and none is
  OHOS-related.
- `src/` module test binary: **All 92 tests passed** (includes analyser
  InternPool/StringPool/completions/degibberish, Uri posix/windows,
  offsets, DiagnosticsCollection, build_runner.check; the InternPool
  thread-safety test ran and passed — build is multi-threaded).
- `tests/analysis`: **23/23 case files success** (analysis_check per case).
- `tests/build_runner_cases`: **10/10 cases success** (each spawns
  `zig build` via the wrapper).
- Step summary: **Build Summary: 49/49 steps succeeded**.

Note (sign-and-retry): the first attempt of each `zig build` invocation
reports `failed to spawn ... AccessDenied` for freshly compiled host
executables (build runner, zls_gen, lsp-codegen, test binaries); the
zig/0.15.2 wrapper then signs the cache roots and re-runs the same command,
which succeeds. This doubled the effective build wall time but completed
correctly; final package ELF gets a second self-sign in `package()`.

Local device conan create wall time: ~420s (well under the 3600s CI
default; no build_timeouts entry required).

## test_package (consumer side, OHOS-specific)

`test.sh` asserts OHOS adaptation points, not just upstream behavior:

1. `zls --version` == `0.15.1` — the ELF executes at all, which on OHOS
   proves the self-sign step is accepted by the kernel (unsigned ELFs are
   refused at exec).
2. `zls env` resolves config/log paths through known-folders under the OHOS
   HOME layout.
3. The packaged zls is a static aarch64 ELF with zero `DT_NEEDED` entries —
   no host `.so` closure introduced by the adaptation.
4. A real LSP stdio session (`initialize` -> `initialized` -> `shutdown` ->
   `exit`, JSON-RPC Content-Length framing) gets a capabilities response for
   id:1 and a null-result shutdown response for id:2, and exits cleanly —
   proving the threaded stdio transport and server loop work on OHOS.
