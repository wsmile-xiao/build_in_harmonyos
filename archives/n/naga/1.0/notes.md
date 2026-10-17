# naga 1.0 适配笔记

> 创建时间: 2026-09-07
> 状态: 工作树待 HMBS 真机预检（未提交）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | naga（终端贪吃蛇游戏） |
| 包版本 | 1.0（任务指定；上游无版本标签） |
| 上游 | https://github.com/anayjoshi/naga |
| 许可证 | BSD-3-Clause |
| 构建系统 | makefile-custom（直接 clang 编译，未调用上游 Makefile） |
| 源码 | 官方 GitHub 归档，master HEAD commit 924af37（2014-11-24），commit 锁定 |
| 源码 sha256 | 0ff91d435b2e30746aadbb944d3920390a546c82d22e406d848ef2232100feaa |

## 二、版本说明

上游仓库共 13 个 commit，无 tag、无 release。按任务要求以 1.0 作为包版本，
源码取 master HEAD（924af372be681ac737c6a62c3cf009062b2e9472）的官方归档，
commit 锁定保证不可变、可复现（itk/aws-crt-cpp/dr_flac 等配方先例）。

## 三、依赖

- ncurses（系统运行时库，无 Conan 依赖，R27）：CI worker 自带 ncurses 运行时但缺 dev 头文件（bitwise 配方印证），故打包 ncurses 头文件到 res/headers（与 nudoku/5.0.4、bitwise/0.50 的 res/ 内容一致），build() 以 -I res/headers 编译、链接时 -lncurses 解析到系统库（nudoku 先例）。
- 上游 curses_wrapper.c 直接 #include <curses.h>，捆绑头文件即满足，无需改源码。
- 依赖图不再含 ncurses/6.4 Conan 边：远端该包无 OHOS 预制二进制，--build=missing 从源码构建会把 ninja（C++ cmake 构建）在未知 HarmonyOS 平台上拉入闭包并失败；纯 C 包不经过 cmake，移除该边即绕开此后端工具链故障域。

## 四、为何不调用上游 Makefile

1. 硬编码 CC=gcc，无法注入 Conan 工具链（R33）。
2. install 目标直接 mv naga 到 /usr/local/bin，无 DESTDIR/前缀支持。
3. 无 check/test 可执行目标（见第五节审计）。
4. 工程仅 7 个翻译单元，直接用 Conan clang 编译确定性更高（nudoku 先例）。

## 五、上游测试审计（结论：上游确无测试）

审计方法：下载官方归档并列出全部 25 个条目。

1. Makefile 仅有 clean/uninstall/install 目标（test 仅 .PHONY 声明，无规则体）。
2. TEST_SOURCES 引用的 src/tests/run_tests.c 在源码包中不存在
   （src/ 下仅 14 个 .c/.h 文件，无 tests/ 目录）。
3. SConstruct 仅定义构建与安装，无测试定义。

因此 build() 不调用上游测试，如实输出 HMBS_UPSTREAM_TEST_RESULT
status:"no_tests" 标记；test_package/MANIFEST.yml 已写入
upstream_tests_exist: false 与本审计摘要。

## 六、配方设计

- requirements(): 空（R27，ncurses 为系统运行时库）；res/headers 捆绑头文件经 export_sources/source 流转，build() 守卫缺失即报错。
- validate(): os in ("Linux", "OHOS")（R32）。
- build(): R33 从 tools.build:compiler_executables 取 cc/ar
  （ar 缺失时由编译器同目录推导 llvm-ar，nudoku 先例）；
  7 个单元逐个编译后链接 naga（库名取自依赖 cpp_info.libs，加 -lpthread）；
  curses-free 的 4 个单元（engine/naga/utils/keypress）归档为 libnaga.a。
- 三处 self.run 均显式 env="conanbuild"，复用 HMBS 注入的 buildenv
  （PATH 与 TMPDIR/TMP/TEMP）；配方不硬编码系统临时目录、不写
  CONAN_HOME/settings.yml。
- package(): bin/naga + lib/libnaga.a + 5 个逻辑头文件。
- package_info(): libs=["naga"] + bindirs=["bin"]（lib+bin 混合，
  与 nudoku 相同，不设 package_type）。
- test_package: test_naga.c 12 个 CHECK（初始状态/移动/穿墙/吃食/
  碰撞/按键），直连已安装 libnaga.a，经 bash 启动
  （zlib 先例：mksh 无法执行 ELF）；二进制另做 magic + e_machine
  字节级校验；compile/run 双相分别经 conanbuild/conanrun
  （ncurses/6.5 先例）。
- L2 说明：naga 无 --version/--help（main() 不解析参数，直接进游戏），
  CI L2 仅为非阻塞警告，不影响门禁。

## 七、验证状态

- 待 HMBS 真机预检：conan create（编译 + no_tests 标记 +
  test_package 12 断言 + 双标记）→ 通过后由 HMBS 提交并建 PR。
- 若预检报 Invalid setting OHOS 或预检脚本自身 /tmp 只读，
  均定序在配方执行前（stdout 仅预检行、零配方输出），属真机环境侧，
  按守则等待恢复，不改配方口径。

## 八、参考

- archives/n/nsnake/3.0.1/：同类 ncurses 蛇游戏模式。
- archives/n/nudoku/5.0.4/：逻辑静态库 + 二进制混合打包模式。
- knowledge/operations/dependencies.md：ncurses 必须静态。

- 2026-09-08 focused round: readonly_tmp hardening (strategy cycle 43, different route from pure hold): build()/test() propagate HMBS-injected TMPDIR/TMP/TEMP at Python level so cc/ar/test children use task tmpdir; no hardcoded /tmp, no new probing, test semantics unchanged. Invalid-OHOS + preflight.sh mktemp errors still sequence before recipe execution (zero recipe output), env-side.

- 2026-09-08 second round same fingerprint: pre-round TMPDIR propagation reverted. Falsification: fingerprint byte-identical after the guard (only PID/tmp suffix differ, still zero recipe output), proving recipe-side changes cannot influence this executor-wrapper failure domain; recipe restored to audited clean state, holding for backend env recovery per守则 (environment faults require no code change).

- 2026-09-08 third round same fingerprint, strategy=static audit plus hold (no recipe code change): __pycache__ removed from sync payload, .hmbs/ exclude re-verified, audit confirms 12 CHECK invocations == assertion_count 12, both HMBS markers present with required fields, no /tmp or mktemp in shipped code, MANIFEST audit fields present. Recipe ready for first-try pass once executor wrapper (preflight.sh mktemp, CONAN_HOME OHOS settings) recovers.

- 2026-09-08 fourth round same fingerprint, strategy=sync-hygiene experiment + marker cross-check (different from guard/revert/audit holds): (a) tried reverting task-external dirty archives/l/libxext README/manifest to keep single-lib PR; proved untouchable on Windows case-insensitive checkout (repo holds both libxext and libXext entries; checkout of either path flips the other side dirty; restored to round-start state lowercase-dirty); (b) cross-checked test_naga.sh gates (executed/passed/discovered/passedCount) against test_naga.c printf format: compatible; recounted 12 CHECK invocations (13th hit is the macro define) == assertion_count 12; scanned shipped code: no /tmp or mktemp writes (only readonly_tmp comment); .git/info/exclude holds .hmbs/; removed py_compile __pycache__ residue. Recipe bytes unchanged; failure still sequences pre-recipe (zero recipe output), holding for backend env recovery.

- 2026-09-08 fifth round same fingerprint, strategy=download-reliability conformance audit (different from prior guard/revert/static-audit/hygiene-cross-check): verified conandata.yml URL list matches ci/conan/build_and_test.sh get_mirrors GitHub mapping exactly (gh-proxy first, official github.com fallback last, sha256 untouched); current failure shows zero recipe output so the download-timeout exception does not trigger, no URL change warranted. Re-verified .git/info/exclude holds .hmbs/, no __pycache__ residue. Recipe bytes unchanged; pre-recipe wrapper failure (preflight.sh mktemp + Invalid OHOS) still env-side, holding for backend recovery.

- 2026-09-08 sixth round same fingerprint, strategy=forbidden-workaround refusal audit (different from guard/revert/static-audit/hygiene/download-audit): re-read raw log + shipped code, confirm sequencing pre-recipe (stdout only 4 preflight lines, zero recipe output; stderr PID/tmp suffix differ from last round, fingerprint otherwise byte-identical). Explicitly reject two tempting but illegal fixes: (a) drop os from settings to dodge Invalid OHOS -> violates PF8 four-settings + R32 OHOS validate, masks toolchain need; (b) patch wrapper mktemp or force-export TMPDIR in recipe Python -> cannot reach preflight.sh[306] wrapper process, prior guard falsified. Grep shipped code: no /tmp or mktemp writes (only readonly_tmp comment), no CONAN_HOME/settings.yml writes, R33 conf reads only. Recipe/test bytes unchanged per infra-fault hold rule; .git/info/exclude holds .hmbs/.

- 2026-09-08 seventh round same fingerprint, strategy=sequencing-proof plus L0 local-gate re-verification with fresh script evidence (different from prior refusal-audit which reasoned without new machine output): (a) re-read raw log, stdout has only 4 preflight lines and zero recipe output, stderr pairs preflight.sh[306] mktemp on read-only /tmp with pipx vanilla conan 2.30 rejecting os=OHOS, so fault sequences before any recipe code runs; (b) fresh scripts confirm shipped code has zero /tmp/mktemp and zero CONAN_HOME/settings.yml writes across conanfile/test conanfile/test_naga.sh/test_naga.c/conandata/MANIFEST, settings four-tuple plus OHOS validate intact, 12 CHECK vs assertion_count 12, both HMBS markers with required fields, gh-proxy-first mirror mapping intact; (c) .git/info/exclude holds .hmbs/, libxext dirt left untouched as pre-existing checkout state. Shipped bytes unchanged per infra-fault hold rule; awaiting backend wrapper/conan-home recovery.

- 2026-09-08 eighth round (strategy cycle 50, different route from all prior holds/guards): prior three holds kept recipe bytes identical, so the same pre-recipe fingerprint (preflight.sh[306] read-only /tmp mktemp + ohpcd remote invalid + zero recipe output) recurred unchanged; holding again cannot falsify whether conan-scope env scrubbing contributes. New route = per-command TMPDIR forwarding instead of global guard or hold: (a) conanfile.py adds _tmp_prefix() reading only HMBS-injected TMPDIR/TMP/TEMP from os.environ and prefixes each self.run (7x cc, 1x link, 1x ar) so cc/ar children carry the task tmpdir even if conanbuild scope scrubs OS env; (b) test_package/conanfile.py prefixes both self.run (compile conanbuild + run conanrun) the same way; (c) test_naga.sh chains TMPDIR/TMP/TEMP across names (empty TMPDIR inherits surviving TMP/TEMP and vice versa), still no mkdir, no invented fallback dir, no hardcoded /tmp. No test semantics changed (12 CHECK, both HMBS markers, no_tests audit untouched), no CONAN_HOME/settings.yml writes, R33 conf reads intact, mirror order untouched. Wrapper mktemp + ohpcd remote remain backend-side; this change only removes the recipe/test side as a /tmp-fallback contributor.

- 2026-09-08 ninth round (same fingerprint 3rd fix, different strategy from 8th-round per-command prefix): 8th-round prefix proven ineffective — new preflight keeps zero recipe output and the same preflight.sh[306] read-only /tmp mktemp, while the conan-home fault mutated from ohpcd-invalid-remote to corrupted remotes.json (Expecting property name line 2 col 2), proving executor-side instability independent of recipe bytes. Falsification revert: removed _tmp_prefix() and per-command prefixes from both conanfiles and restored test_naga.sh to simple re-export audited state, returning shipped code to minimal review-friendly form with no /tmp hardcode, no CONAN_HOME writes, 12 CHECK and both HMBS markers intact. Holding for backend wrapper/conan-home recovery per infra-fault rule.

- 2026-09-08 tenth round (strategy cycle 51, different route from TMP-guard/revert/hygiene/download-audit holds): re-read raw preflight summary + shipped code. Prior per-command TMPDIR prefix falsified (identical fingerprint, zero recipe output across guard and revert), so wrapper mktemp fault is pre-recipe executor domain. New log progressed past export into dependency build where ninja/1.13.2 cmake configure fails (CMAKE_CXX_COMPILER clang++ + System unknown to cmake) while ncurses/6.4 reports no compatible binary; grep proves naga closure has zero cmake/ninja/tool_requires edges (only self.requires ncurses/6.4 host edge) and zero /tmp or CONAN_HOME writes (only test_naga.sh comment re-export), 12 CHECK and both HMBS markers intact. Per infra-fault rule recipe bytes unchanged; holding for backend profile (-pr:b=host tool rebuild), wrapper /tmp, and ohpcd ncurses binary recovery.

- 2026-09-08 eleventh round (same fingerprint 2nd fix, different strategy from 10th-round isolation-hold): precedent-based differential diagnosis. Verified naga and nsnake/3.0.1 declare the identical edge self.requires(ncurses/6.4) with zero tool_requires on both sides, and nsnake notes record conan-verify PASS plus CI模拟通过 with that edge — so the dep choice is valid and the ninja/1.13.2-from-source cmake failure (CMAKE_CXX_COMPILER clang++ plus System unknown to cmake under vanilla cmake 4.4.3 with no Platform/HarmonyOS module) is a backend toolchain/infra regression outside any shipped file. Correction to 10th round: ninja IS pulled into the create graph despite no declared edge (remote/toolchain domain), isolation claim revised. No recipe/test byte change per infra-fault rule; .git/info/exclude holds .hmbs/, no __pycache__. Holding for backend ninja prebuilt/profile recovery.

- 2026-09-08 twelfth round (same fingerprint 3rd fix, different strategy from 10th isolation-hold and 11th precedent-hold): actual recipe change. Removed self.requires(ncurses/6.4) and vendored ncurses headers under res/headers (byte-identical copies from merged nudoku/5.0.4 res/, same set as bitwise/0.50); build() compiles with -I res/headers and links -lpthread -lncurses (upstream Makefile LIB order) against the system runtime. Verified upstream curses_wrapper.c includes <curses.h> directly so no source adaptation is needed. Test package untouched (links curses-free libnaga.a only); no_tests audit unchanged. This cuts the Conan edge whose missing OHOS binary dragged the broken ninja-from-source cmake build into the closure.

- 2026-09-08 thirteenth round (strategy cycle 52, different route from 10th-12th holds): re-read raw log, fault domain moved INSIDE recipe execution (export OK, compatible-config check OK, then RUN "/data/service/hnp/bin/clang" -> 127 inaccessible). Prior hold assumption (pure pre-recipe wrapper fault) falsified by this progress. New route = toolchain-path resilience: _toolchain() keeps conf primary (R33) but validates absolute cc path, falls back to bare clang via conanbuild PATH with warning; test_package same guard. No /tmp handling change (no hardcoded /tmp), no test-count change, no CONAN_HOME writes.

- 2026-09-08 fourteenth round (same ld.lld -lncurses fingerprint, 2nd fix, different strategy from 12th-round vendor-headers hold): falsified system-lib assumption. Log proves compile reached link step (7 objects built OK) then failed unable to find library -lncurses, so headers were fine but no system runtime exists on the worker. New route = restore Conan edge pinned to ncurses/6.6 (repo-local autotools static wide-char with OHOS _build_ohos, not on ConanCenter so no cmake/ninja closure) via self.requires, build() resolves absolute includedirs/libdirs/libs from cpp_info preserving lib order and links dep libs + -lpthread; removed res/headers vendoring and export/source res copy. Test package untouched (curses-free libnaga.a, 12 CHECK). Awaiting preflight link verification.
