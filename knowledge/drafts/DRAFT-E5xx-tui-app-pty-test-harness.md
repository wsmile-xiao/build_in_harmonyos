# ═══ Draft knowledge entry — TUI 终端应用非交互测试:ne abort on non-tty → pty 宏驱动回归 ═══
# Timestamp: 2026-09-11
# Software: ne 3.3.4(任何 stdin 非 tty 即 abort 的 TUI 应用:编辑器/文件管理器/交互工具)
# Gate: conan create test_package / CI build_and_test.sh L1
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-E5xx-tui-app-pty-test-harness
severity: 2
category: testing
trigger_tool: test_package harness / pty
phase: test

error_signature: Cannot reopen input tty|Aborted \(core dumped\)|exit code 134
match_keywords: Cannot reopen input tty,abort,exit 134,SIGABRT,non-tty,stdin isatty,freopen /dev/tty,TUI test,pty,pseudo-terminal

root_cause: 终端类 TUI 应用(编辑器/文件管理器/交互 shell 工具)普遍在 main 早期检测
  stdin 是否 tty;非 tty(CI 的管道 stdin)时尝试 freopen("/dev/tty") 抢占控制终端,
  CI 环境无控制终端 → freopen 失败 → 直接 abort()。表现:conan test / CI test
  阶段 binary 瞬间 exit 134,stderr 只有 "Cannot reopen input tty"(或类似
  Cannot open tty / not a terminal)。另一类同族表现:程序挂起等待键盘输入
  (无 EOF 概念),直到超时被杀。

rec_approach: 1. python pty.fork() 模拟终端:子进程 execve 目标二进制,父进程
  select 读输出 + waitpid 收状态。2. 优先寻找应用的"宏/脚本模式"参数
  (ne: --macro FILE;vim: -es / -c),在 pty 下驱动完整编辑往返后退出。
  3. OHOS 差异:pty master 在子进程退出后 read 返回 EIO (errno 5) 而非
  EOF——读循环必须 except OSError 后走 waitpid 收尸取真实退出码。
  4. harness 抽成独立 test_package/<name>_pty_test.py,conanfile test()
  用 self.run("python3 harness.py <bin> <args>")(CI L0c/PF3 要求)。
  5. TERM=ansi + TERMINFO 指向包内 terminfo(若包分发)。

fallback: 无法 pty 时改用 --help / 静态检查(低于 R34 实质测试要求,不推荐)。

verification_cmd: conan create archives/n/ne/3.3.4 -pr:h ci/conan/profiles/ohos-aarch64
  -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
  # 期望输出含: ne_pty_test: all 4 tests passed
  # 负向验证(无 pty): 管道运行 ne --help -> exit 134 (SIGABRT)

affected_scope: ne/nano/joe/jed/micro 等终端编辑器;mc/ranger/vifm 等文件管理器;
  htop/btop/dialog/whiptail 交互工具;任何 freopen("/dev/tty") 或等价逻辑的程序

prescan_pattern: freopen\(\"/dev/tty\"|isatty\(fileno\(stdin\)\)
