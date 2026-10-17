# synergy-core 1.20.4 adaptation notes

## Source closure

- Main release: `v1.20.4`
- Main commit: `702933225ded0f86d977dbfb18683447ae4ec5fb`
- Required source submodule: `synergy-extra@706bdf4d815643c0db722389b67a273a365d2225`
- Build-only upstream-test source: GoogleTest `v1.17.0`

GoogleTest is used only to compile and execute Synergy's upstream tests. It is
not exported, packaged, or exposed as a Conan dependency.

## OpenHarmony backend

The upstream non-GUI build still selects Qt, X11, DBus, and the X11 screen
factory. The adaptation therefore provides a native OpenHarmony platform
backend rather than a headless stub. It covers:

- InputKit key, mouse, wheel, hotkey, monitor, interceptor, and injection APIs.
- Native multi-display geometry and pointer positioning.
- Pasteboard and UDMF clipboard exchange.
- Command-line taskbar/status receivers for server and client operation.
- Capability-selected native architecture, application, and source sets.

Input authorization is coordinated fail-closed across concurrent requests.
Capture-server and injection-client roles are enforced independently, and
InputKit `actionTime` values are not treated as trusted injection provenance.
Clipboard write tracking, deferred hotkey cleanup, and callback shutdown use
explicit state machines so native callbacks cannot outlive backend resources.

## Build and dependency decisions

- `BUILD_GUI=OFF`, `BUILD_UNIFIED=ON`, and `BUILD_TESTS=ON` produce one
  `synergy-core` executable plus the two upstream GTest executables.
- `SYSTEM_GTEST=OFF` selects the build-only, source-fetched GoogleTest tree.
- `SYNERGY_VERSION_RELEASE=ON` makes release-tarball versioning deterministic.
- `CMAKE_SKIP_RPATH=ON` prevents build-machine paths from entering ELF files.
- `aws-lc/5.5.0` preserves the OpenSSL API and TLS behavior used by Synergy.

## Upstream test adjustments

- Qt GUI and non-OpenHarmony platform-only test sources are excluded on OHOS.
- One `std::ranges::copy` use is expressed as equivalent `std::copy` for the
  target standard library.
- GoogleTest stream capture honors `TEST_TMPDIR` on OHOS instead of using the
  read-only `/tmp` path.

No test is disabled, skipped, or converted into a passing result.

## Validation

- Historical r32 official-source replay: GNU patch 2.7.6 applied all 43 patches with
  fuzz disabled and no residue; 48 unique targets matched 48/48 expected
  postimages. Git apply and patch-ng also replayed all 43 patches. The three
  formerly full-preimage patches are now boundary-aware reviewable diffs.
- Historical r32 full source replay: 1213/1213 files matched the product source tree
  in both raw and line-ending-normalized manifests.
- Historical r32 native state tests: 8/8 passed from a newly compiled test executable after
  adding finite/range and `INT32_MIN`/`INT32_MAX` pointer-coordinate cases.
- Independent W4 r31 reported no P0/P1 and two P2 findings. The successor
  destroys a non-null UDMF object returned with pasteboard failure status and
  performs pointer-coordinate rounding and relative addition through checked
  wide arithmetic before narrowing. The current 43-patch replay produced all
  48 postimages and the targeted production-path assertions passed 6/6.
- Historical r32 CMake backend capability matrix: 5/5 passed, including a regression check
  that the POSIX compile/link probe result is not pre-seeded.
- Historical r32 single-threaded OHOS cross build against the local `aws-lc/5.5.0`
  C++20 package produced `synergy-core`, `unittests`, `integtests`, and
  `ohos-screen-state-tests`; a final build re-entry reported no work to do.
- Formal finish r32 first ran a fresh single-threaded unqualified Conan create,
  then forced a second single-threaded local-CI rebuild from the current
  48-file input (`5ebc1573f853678472865bb77b6d09e8d56490f5aa0e13eb46b576b054555aac`).
  Both builds produced the same root identity:
  `RREV=b1185e75cf4f9f370391ae5f538edb57`,
  `PID=4ef55ed2994fdc34d981f5bf698651acdcf1de60`, and
  `PREV=6ad65919ab655a005165bb97fb3d663e`. Ninja completed `171/171`; G0/G1/G3/G4,
  L0, L1, L4, and L5 passed. L1e removed the packaged `bin/` directory and the
  consumer test failed for the missing `synergy-core` executable, proving that
  the cross-build skip no longer bypasses the package-artifact dependency.
- Finish automatically generated version-level `.ci-result.json` with
  exit code 0 and SHA-256
  `e5a53bfe6291c6e47fe08c01e9be85b82952b3024bb1f9a192cc87ee57d5d7e5`.
  The complete build log SHA-256 is
  `ca4575b5f2d2d2cc5c561ff7d904e73aaf5f87087c201ea76a6d24f0043251b9`.
- The outer finish pipeline returned 1 only after local CI passed because
  legacy readiness still checks deprecated `packaging/` and `.staging-verified`
  paths, and the repository-wide knowledge scan reports pre-existing unrelated
  incomplete entries. This is recorded separately from the generated local-CI
  PASS and is not changed into a false pipeline RC 0.
- W5 reuses the existing artifact-first capability-gate draft
  `knowledge/drafts/E2151-draft-2301.md`; no duplicate Synergy-specific draft
  is created.
- `consumer_loopback_server_client`: r96 signed target execution passed both
  packaged consumer checks (`2/2`).
- The previous 171 unit plus 3 integration target result is historical and was
  invalidated by the current source and patch changes. The current r32 snapshot
  compiled all 174 tests, but its complete target suite remains pending.
- Independent W4 r32 is an immutable FAIL (`P0/P1/P2/P3=0/2/2/0`). Its
  candidate tree, generated `.ci-result.json`, replay manifests, and local
  build are historical after the r33 edits to patches 0004, 0028, and 0030.
- The r33 successor adds checked finite/range axis conversion, wide native
  mouse differences, overflow-free recenter checks, owned display-output
  cleanup, a Windows-scoped POSIX gate, and directed negative tests. A newly
  compiled host executable passed all 10/10 state cases; its compile and run
  stderr logs are empty, and the CMake script matrix passed 6/6. The durable
  directed run stdout SHA-256 is
  `a267bcf1e89c8360a19f48512ec42282f5a92bf6d9036d57ac2db564548dccff8`.
- r33-r1 is retained as a failed local attempt: it selected the w64devkit
  BusyBox `patch` applet, whose unsupported version probe returned RC 1. The
  create-new r33-r2 run resolved GNU patch 2.7.6 at
  `D:\Program Files\Git\usr\bin\patch.exe` and bound its SHA-256
  `d77a8f8499909a711d343fea72235b8de473c4928243b976589073efafa941dd7`.
- r33-r2 replayed all 43 patches with GNU patch and matched all 48/48 target
  postimages with both Git and GNU engines. The complete product tree matched
  1213/1213 files with zero missing, extra, or normalized-content changes.
  A single-threaded OHOS AArch64 build against `aws-lc/5.5.0` produced four
  ELF64 AArch64 outputs, and a final build re-entry was a no-op. This run is
  bound to staged tree `6d9dbaf148d294574950222833d78279912d0998`.
- The durable r33-r2 `RESULT.json`, closure, and patch replay ledger SHA-256
  values are respectively
  `09512b0bcb9573f9a768aae85f011dce0ee33d3f0271a31f72606884f05568b7`,
  `61e0105fc398b5c678cff806236ecf6718af579ce6f9821b2e0ab7b440a1f48d4`,
  and `e61caefe0f375d48d56602f5bf1ce4074966dbf6641842c3be9cd1d9944850de5`.
- Formal r33 current-input Conan verify and local CI completed with
  `local_ci_exit_code=0`. The outer legacy readiness pipeline remains truthfully
  `pipeline_finish_rc=1`; it is not converted into a pipeline PASS.
- The shared L1 shell gate printed an executed-test PASS even though the same
  log contains `tools.build.cross_building:can_run=False`, reports 174 tests as
  compiled for target execution, and says the packaged CLI checks require
  target execution. Its broad case-insensitive `ctest` expression matched the
  `IpcTests.cpp.o` filename. A fail-closed semantic classifier rejects that
  shared claim and records the local result as build/package validation only.
- Current r96 target execution completed upstream `174/174`, native state
  `10/10`, and packaged consumer `2/2` on `10.62.148.108:2222`; the transaction
  recorded zero authorization requests, unchanged inputs, and PASS for release
  and postrelease.

These local checks do not claim packaged-consumer or upstream target execution,
native interaction, remote CI, or submission closure.

The archive retains historical r32 evidence separately; it is not projected
onto the current candidate. All 174 upstream tests, 10 native state cases, and
two consumer assertions were executed in the single r96 signed-device
transaction. Formal finish r4 then regenerated the version-level
`.ci-result.json` from the unchanged 48-file CI input. W5 and the PRE_CREATE /
POST_CREATE contracts passed. Platform AI Review, current PR HEAD CI, and
submission remain separate gates.

---

**编译结束**: 2026-08-19 09:37
**最终状态**: built
