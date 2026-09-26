# DRAFT — 原始 Makefile ncurses CLI 的链接/运行验证三重适配
# Timestamp: 2026-09-24
# Software: 3d-ascii-viewer-c 1.4.0
# Gate: conan-verify G2 / test_ohos / consumer / W3
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-3d-ascii-viewer-c-1.4.0-raw-makefile-ncursesw-cli-test-pattern
severity: 2
category: ohos|make|conan|ncurses|cli
trigger_tool: make / conan / ncurses
phase: compilation|linking|testing
approach: 三处适配：①上游 Makefile 内部 `CC := gcc`（:= 覆盖环境变量）时，
  conanfile build() 必须以 make 命令行变量覆盖 `make CC=<conan conf c>
  CFLAGS=... LDFLAGS=...`（R33：编译器取自 tools.build:compiler_executables）；
  ②ohpcd ncurses/6.4 仅打包 libncursesw.a（宽字符版），上游 `-lncurses` 改
  `-lncursesw`（头文件仍 ncurses.h，无需改源码）；③headless/conan test 环境
  initscr 报 Error opening terminal 时，test_package 将 ncurses 声明为直接
  requires，使 ncurses runenv_info 的 TERMINFO 聚合进 conanrun 环境，测试命令加
  TERM=xterm；对交互 TUI 用 --snap 单帧渲染作非交互可观察验证入口；④CI 门禁
  L0c 要求 test_package/ 内除 conanfile.py 外必须存在真实测试源文件
  （.c/.cpp/.cc/.cxx/.sh/.py，maxdepth 2），L0d 要求 test() 经 self.run 实际
  执行该测试源——CLI 包应把 --snap/--help 断言写成独立 shell 脚本由 test()
  `self.run(f'sh ...')` 调用，不能只内联命令（R01 曾因无测试源文件被远端 L0c
  no_test_sources 拦截，R02 补齐后复验通过）。

keywords: CC :=, make 变量覆盖, libncursesw, TERMINFO, conanrun, runenv,
  test_package, requires, headless, --snap, TUI, initscr

error_signature: make: gcc: No such file or directory|-lncurses.*cannot find|-lncurses.*No such file|Error opening terminal: [a-z0-9-]+|failed to load file
match_keywords: make, gcc, CC :=, -lncurses, -lncursesw, ncursesw, terminfo, TERMINFO, Error opening terminal, test_package, runenv_info, conanrun, raw makefile, cli

root_cause: ①原始 POSIX Makefile 常用 `CC := gcc` 与 `LDFLAGS := -lm -lncurses`，
  := 使命令行/环境 CC 被覆盖，交叉编译时调用系统 gcc 失败；②制品仓 ncurses 包为
  宽字符构建（libncursesw.a），上游链接名 -lncurses 找不到库；③ncurses 程序
  initscr() 需要 TERM + TERMINFO，headless 验证环境缺 terminfo 数据库路径导致
  "Error opening terminal"（与 DRAFT-E568 系统 terminfo 路径问题同面异因）。

affected_scope: 所有使用原始 POSIX Makefile（无 configure）构建、链接 ncurses、
  产出 CLI 可执行文件的 Conan 配方（OHOS aarch64 + ohpcd ncurses/6.4）。CMake/
  autotools 项目由 toolchain 管理编译链接，不受影响；纯库型（无 CLI 运行验证）
  只涉及前两项。

verification_cmd: python3 scripts/ohc-run.py conan-verify 3d-ascii-viewer-c 1.4.0 2>&1 | grep -E "G2: PASS|Error opening terminal"

rec_approach: raw-makefile-ncursesw-cli-triple-adapt
prescan_pattern: make: gcc: No such file|Error opening terminal: [a-z0-9-]+|failed to load file

# 真实证据: 3d-ascii-viewer-c 1.4.0 (2026-09-24)
# - conan-verify G2: 首轮 make 找不到 gcc → build() 加 make 变量覆盖；第二轮
#   test_package Error opening terminal → ncurses 直接 requires + TERMINFO 聚合；
#   第三轮 PASS（报告 reports/conan-verify-report.md，日志 reports/conan-create.log）
# - 本机运行: --help rc=0；12 个样例模型 --snap 渲染全部 rc=0
#   （tmp/oh-runner-logs/3d-ascii-viewer-c-1.4.0/run-models.log）
# - 鸿蒙专项 test_ohos T1-T5 全过；消费者用例 C1-C3 全过
# 知识候选台账 + 七轴查重: reports/knowledge-candidate-ledger.md