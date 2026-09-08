# algobox 1.1.1 HarmonyOS PC pre-adaptation notes

## Status

- Worktree: `D:\harmonyos\worktrees\algobox`
- Branch: `feat/algobox-1.1.1`
- Current status: CI #40723 passed Conan build, `test_package`, L0, and L1 on OpenHarmonyPCDeveloper-CI-031; Windows-local validation remains limited to patch-chain/static checks because `qmake6` is an OHOS-target binary.
- Issue tracking: skipped per user instruction; no issue number required for this round.

## 适配路径

- 路径 A：完成 qmake 配方、补丁、`test_package` 和前置依赖检查。
- 路径 B：已补充 `knowledge/drafts/DRAFT-algobox-ohos-target-qmake-windows-host.{kv,md}`，记录 OHOS-target `qmake6` 不能作为 Windows host build tool 的边界，可作为本包的 B 类知识材料。

## W0 Dependency Check

Required dependencies from upstream `algobox.pro` and source includes:

- `qtbase/6.11.1`: present in archives; provides Qt Core, Gui, Widgets, Network and Xml.
- Qt PrintSupport: not available in current `qtbase/6.11.1`/`qtbase-gui/6.11.1`; patched out for this package.

Per the one-library-one-PR rule, this PR does not need separate `qtwebengine`, `qtwebchannel`, or `qtcore5compat` packages.

## Source And Build System

- Upstream source: `https://www.xm1math.net/algobox/algobox-1.1.1.tar.bz2`
- SHA256: `b5db2479360d5efa00c1856466e98481571d22064ed63272706ff0d5098f0e5e`
- Build system: qmake, top-level `algobox.pro`
- Upstream tests: no `make check`, `ctest`, or dedicated test directory found in the 1.1.1 source archive.

## Recipe Strategy

- Use qmake from the `qtbase` dependency (`bin/qmake6` or `bin/qmake`).
- Expose Qt dependency roots through `QMAKEPATH` so qmake can locate separate Qt module `.pri` files.
- Remove the WebChannel hooks and move the browser/help pane to a QWidget/TextBrowser fallback instead of the WebEngine page stack.
- Keep the QTextCodec compatibility layer fully local; do not probe QtCore5Compat on OHOS if the package does not ship a usable shared library.
- Drop `core5compat` from `algobox.pro`; the OHOS qmake package does not expose that module, and the local shim now covers all needed text conversions.
- Patch in `--version` and `--help` before `QApplication` construction so L2/test_package can run without display startup.
- Disable the direct system-printer action because Qt PrintSupport is absent; keep a PDF export fallback built on QtGui.

## Local Verification

- Downloaded official source archive and verified SHA256 locally.
- Inspected source tree and confirmed qmake-only Qt application.
- Confirmed no existing `algobox` archive/worktree/branch before creating this worktree.
- Current Windows shell has no `conan` executable on `PATH`, so local validation is limited to Python syntax checks, patch-chain application, and static source inspection.
- CI #40700 passed the previous WebChannel compile point, then exposed a malformed patch literal in `algowebpage.cpp`; `0005-ohos-fix-algowebpage-newline-split.patch` restores `msg.split("\\n")` as a single C++ source line.
- CI #40716 then reached qmake and reported `Project ERROR: Unknown module(s) in QT: core5compat`; `0007-ohos-drop-core5compat-module.patch` removes the stale qmake module.
- CI #40723 (OpenHarmonyPCDeveloper-CI-031, 2026-09-05 22:08:57) passed Conan build, `test_package/test.sh`, L0, and L1 for `feat/algobox-1.1.1`.
- Windows-local full build remains runner-bound because the OHOS-target `qtbase/6.11.1` package exports `qmake6` as an OHOS binary, which Windows cannot execute if the recipe reaches qmake locally.

## Expected Next Commands

Dependency check on a Conan-enabled host:

```sh
conan download "qtbase/6.11.1" -r=ohpcd --only-recipe
```

Full validation command used by CI:

```sh
CI_PACKAGES="archives/a/algobox/1.1.1" zsh ci/conan/build_and_test.sh
```

Shadow CI queue command:

```sh
/path/to/run-ohos-shadow-ci.sh archives/a/algobox/1.1.1
```

## Follow-up Items

- If the CI classifies this GUI package as a command-line tool because it installs `bin/algobox`, add software-level `archives/a/algobox/commands.json`; this round intentionally stayed inside the version directory.

## Knowledge Draft

- 已补充 algobox 相关知识草稿 `knowledge/drafts/DRAFT-algobox-ohos-target-qmake-windows-host.kv` / `.md`，记录 `qtbase/6.11.1` 导出的 `qmake6` 是 OHOS-target 二进制，Windows host 只能做 graph/metadata 检查，不能把它当成本机可执行 build tool。
- 这条经验适用于其它 qmake/Qt 包：dependency graph 解析成功，不代表 build tool 可在当前宿主机直接运行；浏览器/帮助页 fallback 后要继续清理不再使用的 Qt 模块，并保留真正本地的 compatibility shim。
