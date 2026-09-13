# DRAFT-E568 — OHOS musl ncurses 找不到 terminfo，TERM 齐备仍 cannot initialize terminal
# Timestamp: 2026-09-10
# Software: mdp 1.0.18(所有链接 ncursesw/ncurses 的 TUI 程序)
# Gate: conan create test_package / 真实终端运行
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-E568-mdp-ohos-musl-terminfo-path
severity: 2
category: platform|runtime|ncurses
trigger_tool: ncurses / musl
phase: test
approach: musl 链接的 ncurses 程序在 TERM 已正确设置(如 xterm-256color)时仍报
  "ncurses: cannot initialize terminal type" 退出,先检查系统 terminfo 数据库位置:
  OHOS 基础环境装在 /usr/share/terminfo,而 musl ncurses 默认编译期搜索路径
  (TERMINFO_DIRS 缺省)不含该目录;运行时显式 export TERMINFO=/usr/share/terminfo
  (或 TERMINFO_DIRS)即可让 setupterm 找到条目;测试脚本应在探测目录存在后再进 pty 运行

keywords: TERMINFO, terminfo, musl, ncurses, cannot initialize terminal, TERM,
  xterm-256color, setupterm, OHOS, pty, TUI

error_signature: ncurses: cannot initialize terminal type \(\$TERM="[^"]*"\); exiting|Error opening terminal: [a-z0-9-]+|could not find terminal
match_keywords: ncurses,terminfo,cannot initialize terminal,TERM,musl

root_cause: musl 版 ncurses 的 terminfo 搜索路径由编译期 TERMINFO_DIRS/默认值决定,
  OHOS 系统镜像把 terminfo 数据库放在 /usr/share/terminfo,但 musl ncurses 构建时
  默认路径集合未收录该位置;环境变量 TERMINFO/TERMINFO_DIRS 也未在 CI 与 conanrun
  环境中导出。结果:程序对 TERM=xterm-256color 报 cannot initialize terminal,
  与"terminfo 文件明明存在"的直观观察冲突,极易误判为二进制/架构问题。
  本机验证:同一二进制在 TERMINFO=/usr/share/terminfo 下进入 ncurses 交替屏
  (ESC[?1049h)渲染成功,未设置时 76 字节即退出。
affected_scope: 所有在 OHOS(musl)上运行、依赖 ncurses terminfo 的 TUI 程序的
  test_package/CI 测试;典型如 mdp、htop、dialog 类工具;交叉编译自 Linux 开发机
  的场景不受影响(glibc ncurses 默认路径含 /usr/share/terminfo)

rec_priority: 1
