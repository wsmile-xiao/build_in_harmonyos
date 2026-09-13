# DRAFT-E569 — TUI 程序 stdin 管道喂入与 /dev/tty freopen 冲突,测试须 pty 双通道
# Timestamp: 2026-09-10
# Software: mdp 1.0.18(所有 FILE=- 从 stdin 读输入、按键另开 /dev/tty 的 TUI 程序)
# Gate: conan create test_package
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-E569-mdp-stdin-tty-freopen-pty-dual-channel
severity: 2
category: runtime|testing|ncurses
trigger_tool: pty / TUI viewer
phase: test
approach: TUI 程序支持 FILE=-(stdin 读 Markdown)时,上游常在解析后 freopen("/dev/tty")
  作为按键输入源:无控制终端则 exit(1),debug 输出也被吞掉。测试须用 python pty.fork()
  双通道:pty 提供控制终端(子进程 dup2 管道到 stdin 喂内容),读到目标输出后向 pty
  写 'q' 退出;注意 pty 为终端模式输出 \r\n,断言前 tr -d '\r'。直接管道
  `printf ... | mdp -d -` 会因无 /dev/tty 失败,不代表解析缺陷。

keywords: /dev/tty, freopen, pty, pty.fork, stdin, FILE=-, TUI, ncurses, viewer,
  控制终端, controlling terminal, exit 1, \r\n, tr -d

error_signature: freope?n\("/dev/tty".*\) == NULL|Bad file descriptor|.*: cannot open /dev/tty|exit\(1\).*tty
match_keywords: /dev/tty,stdin,pty,freopen,tty
root_cause: 上游 mdp main() 在 FILE=-(或无参数)时置 noreload=1,解析完成后无条件
  freopen("/dev/tty","r",stdin) 作为按键输入源,失败即 exit(1);此时 -d 的解析
  统计尚未 flush 到 stderr 之外或已写但进程退出码非 0。管道 stdin 场景(典型 CI
  `printf ... | prog -`)没有控制终端,freopen 必失败。这是 TUI 程序的普遍模式
  (按键不能与内容输入共用 stdin),不是鸿蒙/构建缺陷。
affected_scope: 所有支持 stdin 输入且按键走 /dev/tty 的 TUI 程序的 test_package 测试
  (mdp 及同构 viewer);影响 CI 用例设计,不影响运行功能

rec_priority: 1
