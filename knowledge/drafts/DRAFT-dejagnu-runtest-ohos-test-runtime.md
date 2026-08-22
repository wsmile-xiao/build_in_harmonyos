# DRAFT-dejagnu-runtest-ohos-test-runtime — DejaGNU/runtest 测试运行时注入（OHOS）

> **Contributor**: GoliWie | **Status**: DRAFT | **Updated**: 2026-08-21
> **Severity**: medium | **Category**: ohos / toolchain / dejagnu-testing
> **Audience**: binutils / gcc / gdb 等所有用 DejaGNU testsuite 的库

## Scope
在 OHOS 上用 DejaGNU 测试框架（runtest / make check）的库，需要在 build() 集成 make check 时把 expect/tcl 运行时环境注入执行环境，并用动态三元组绕开 runtest **运行时**的 config.guess 探测，避免 0 个 .exp 空跑 / 全部跳过造成的"测试假象"。

## 背景
- runtest 是 Tcl 脚本，需要 expect 解释器；expect 又需要 `TCL_LIBRARY` 指向 tcl 的 `lib/tcl8.6/init.tcl`。
- 若 PATH/TCL_LIBRARY 不全，`runtest --version` 判假，生成式 Makefile 的 `check-DEJAGNU` target 落入 else 分支 → 0 个 .exp 空跑且 exit 0（假象）。
- runtest.exp（Tcl 驱动）在未提供 `--build/--host` 时会调用 config.guess；OHOS HMDFS tmpdir 下 config.guess 编译 dummy.c 被内核拒绝（`Permission denied`，与 E011 同类 UID 映射/权限问题），13 个 .exp 全部跳过。
- OHOS expect 5.45.4 spawn/PTY 限制使个别 report-card 测试 unresolved（`spawn id expX not open`），属跨库系统能力缺口，须在 PR 报告如实声明。

## 模式（步骤）
1. `generate()`：`Environment` 注入 `expect/bin`→PATH、`tcl/lib`→LD_LIBRARY_PATH、`tcl/lib/tcl8.6`→TCL_LIBRARY，`save_script("dejagnu_check_env")`（自定义名，避免 clobber conanbuild.sh）。
2. `build()`：`_get_gnu_triplet(settings.os, settings.arch)` 动态计算三元组（`aarch64-ohos`，非硬编码平台名），`RUNTESTFLAGS="--build=.. --host=.."` 传给 `make check`。
3. `self.run(make_check_cmd, env=["conanbuild","dejagnu_check_env"])`；make check 非零退出用 `try/except ConanException` 容忍并如实记录日志，PR 报告统计口径以日志为准（禁写全量通过）。

## E011 边界（重要）
- **configure 层禁止绕过**：不得用 `--build/--host` 传 configure（E011 forbid_1），否则 AC_RUN_IFELSE 全跳过、config.h 检测结果失真。
- **runtest 运行时允许**：RUNTESTFLAGS 三元组只传给 make check 的 runtest.exp（运行时三元组探测），configure 阶段走正常 AC_RUN_IFELSE。二者语义不同，不冲突——后人不得把本模式的 RUNTESTFLAGS 误用到 configure 层。

## 验证
- `grep -cE "config\.guess.*Permission denied" <log>` = 0（修复后）。
- `grep -cE "Running .*\.exp" <log>` = 13（真实执行，非空跑）。
- 统计：`# of expected passes` 359 / `# of unresolved testcases` 2（report-card，OHOS expect spawn/PTY 跨库缺口，用户已接受 ACCEPTED_WITH_DECLARED_GAP）/ `# of unexpected failures` 0。

## Source
- Package: `archives/d/dejagnu/1.6.3`（`conanfile.py` generate()/build()）
- 证据日志（设备 run 目录）：`worktree/.ci_logs/conan_build_dejagnu_1.6.3.log`（13 Running .exp、359/2/0/361）、`ci-round-4.log`（config.guess 4 处 Permission denied）、`conan-create-round-4b.log`（RUNTESTFLAGS 修复后 13 .exp 真实执行）
- Similar: E272（expect spawn/stty 家族）、E011（configure 层 umask）、E253（OCaml config.guess/tmpdir）
