# DRAFT-E429 — 无 --version/--help 的纯 termios TUI 程序消费者验证须 pty 渲染断言
# Timestamp: 2026-09-20
# Software: cfm 0.6.6（纯 termios TUI 文件管理器，无 ncurses、无 FILE=-、无 /dev/tty freopen）
# Gate: conan-verify L2 + test_package 消费者用例
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-E429-cfm-termios-tui-pty-consumer-test
severity: 2
category: runtime|testing|termios
trigger_tool: pty / TUI / conan_test / L2
phase: test|smoke_test
approach: 纯 termios TUI 程序（无 ncurses、无 FILE=-、无 /dev/tty freopen）通常没有
  --version/--help 参数（argv[1] 即目录/文件参数），L2 冒烟对 --version 返回非 0 属上游
  行为（warn 非阻塞）。普通非 TTY 运行（stdin 关闭）常快速退出 0——只证明 ELF 加载与
  目录扫描，不能证明 TUI 渲染。消费者验证必须用 python pty.fork() 提供控制终端：断言
  输出含 \x1b[ 转义序列（备屏/光标控制=真实渲染），随后发送退出键（如 'q'）并断言
  exit 0。C 消费者可 fork+execvp 传临时目录 + 关闭 stdin 作冒烟（注意勿用根目录 "/"，
  某些 TUI 在非交互模式下对 "/" 扫描会挂起；用 mkdtemp 工作目录）。

keywords: termios, TUI, pty, pty.fork, isatty, 控制终端, --version, --help, L2 冒烟, 转义序列, \x1b[, 退出键, 消费者用例, 非 TTY 快速退出

error_signature: --version.*rc=1|--help.*rc=1|TUI.*not render|pty.*no escape|interactive.*not verified
match_keywords: termios, TUI, pty, pty.fork, isatty, --version, --help, L2, smoke, escape, \x1b[, q quit, consumer test
root_cause: TUI 渲染依赖控制终端（termios/ioctl TIOCGWINSZ）；上游无版本/帮助参数时
  L2 冒烟无 --version 可测；无控制终端时渲染通道不可验证，仅加载/退出可测。
affected_scope: 所有纯 termios 直控、无 ncurses、无 FILE=-、无 /dev/tty freopen 的
  TUI 程序的 test_package 消费者验证（cfm 及同构 TUI 工具）；影响 CI 用例设计，不影响运行功能

rec_priority: 1
rec_approach: pty-render-assert-quit
rec_description: python pty.fork() 起 pty，子进程 execvp(TUI, [prog, <mkdtemp 目录>])，
  父进程收集输出断言含 \x1b[（备屏渲染），写入 'q' 退出键，断言 exit 0；另加 C 消费者
  fork+execvp 关闭 stdin 冒烟（rc=0）
rec_command: 见 archives/c/cfm/0.6.6/test_package/conanfile.py test() 与 test.c（实测通过）
rec_auto_fix: false

fallback_priority: 2
fallback_approach: tty-less-smoke
fallback_description: 仅断言非 TTY 运行 exit 0（加载+扫描），放弃渲染验证；覆盖度低，仅在无 python3 pty 环境时退用
fallback_command: cfm <dir> </dev/null >/dev/null 2>&1; echo $?
fallback_auto_fix: true

principles: TUI 渲染必须真实终端通道验证；L2 的 --version/--help 对无参数 TUI 属上游设计
  而非缺陷；消费者用例须区分"能加载"与"真实渲染"
caused_by: 上游 TUI 程序无 --version/--help 且渲染依赖控制终端
similar_to: DRAFT-E569-mdp-stdin-tty-freopen-pty-dual-channel（同 pty.fork 技术，异根因/异边界：E569 是 FILE=-/dev/tty freopen 双通道，本候选是纯 termios 单通道渲染断言）
similar_to: E503（同 L2 --version/--help 场景，异方案：E503 改程序补长选项，本候选改测试通道）
conflicts_with:
prerequisite_of:
doc_file: knowledge/drafts/DRAFT-E429-cfm-termios-tui-pty-consumer-test.md
last_updated: 2026-09-20
source_event: cfm 0.6.6 适配：--version/--help 返回 1（argv[1] 作目录），非 TTY 运行快速退出 0，
  pty 驱动后断言 \x1b[ 渲染 + 'q' 退出 rc=0 通过（consumer pty 226 bytes）
authors: AtomCode
source_pr: (本 PR)
source_commit: (本 PR)
metrics_success_count: 1
metrics_fail_count: 0
metrics_confidence: 0.9
metrics_last_used: 2026-09-20
