# ═══ Draft knowledge entry — 终端类应用 terminfo 数据库随包分发(OHOS /usr/share/terminfo 不完整) ═══
# Timestamp: 2026-09-11
# Software: ne 3.3.4(任何 terminfo 模式终端应用,构建链接 ncurses 成功但运行时报 unknown terminal)
# Gate: conan create test_package 运行期 / 设备实机运行
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-E5xx-terminfo-database-bundle
severity: 2
category: portability
trigger_tool: terminfo runtime lookup
phase: runtime

error_signature: Error opening terminal|tgetent failure|setupterm returns ERR|unknown terminal type
match_keywords: terminfo,TERMINFO,TERMINFO_DIRS,setupterm,tigetstr,tgetent,Error opening terminal,unknown terminal type,TERM environment variable

root_cause: OHOS/musl 环境不带完整 ncurses terminfo 数据库(glibc 发行版通常
  /usr/share/terminfo 有数千条目;OHOS 实测仅极少量 hex 目录 s/ x/ 等,常见终端
  类型无法全部解析)。终端类应用(terminfo 模式)运行时按 TERM 环境变量查 terminfo:
  TERMINFO → TERMINFO_DIRS → /usr/share/terminfo → ~/.terminfo 都找不到即失败
  退出。构建期链接 ncurses 成功 ≠ 运行期有 terminfo 数据——纯运行时数据依赖,
  编译器/链接器无法发现。

rec_approach: 1. 配方 package() 从 conan ncurses 依赖包复制 share/terminfo 到
  自己的 package share/terminfo(copy(self, "*", src, dst))。2. package_info()
  定义运行时环境:self.runenv_info.define_path("TERMINFO", <pkg>/share/terminfo)
  + define_path("TERMINFO_DIRS", ...)(ncurses/6.4 配方同款做法)。
  3. test_package 的测试进程若不经 conanrun env(python 直跑),须自行构造
  TERMINFO 环境传给被测二进制。4. TERM 默认值:CI 无 TERM 或 TERM=dumb 时
  tigetstr 全空——测试里显式 TERM=ansi(最通用条目)。

fallback: 用户 conan install 时用 ncurses 的 runenv(等效);或应用改用
  NE_ANSI/termcap 内置模式(ne 特有,功能受限不通用)。

verification_cmd: TERMINFO=$(conan cache path ne/3.3.4)/share/terminfo TERM=ansi ne --help
  # 期望: 版本横幅正常输出;不设 TERMINFO 时依赖系统库(不完整)
  conan create archives/n/ne/3.3.4 --build=missing  # test_package 全绿

affected_scope: 所有 terminfo/termcap 模式终端应用(源码 include <term.h> /
  setupterm/tigetstr/tgetent 调用即高概率命中)

prescan_pattern: include\s*<term\.h>|setupterm\(|tigetstr\(|tgetent\(
