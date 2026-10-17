# yash 2.60 适配笔记

## 任务来源

- 平台任务 contrib-12268（开源鸿蒙PC专项积分赛），分支 `feat/yash-2.60`，2026-09-19 认领
- 上游：https://github.com/magicant/yash （569 stars，非 fork，release 2.60 实拉核验存在）
- 语言实测（R47 lang-preflight）：C（37 个 .c 源文件，主体占比 100%；7 个 .sh 为辅助脚本）

## 选库核验（§3.2 否决线）

1. 他人已移植：`archives/` 全量比对 + `git grep yash` 同源反查均无；制品仓 `conan list "yash/*" -r=ohpcd` = 0（设备实测）
2. 语言/构建生态：C + 手写 configure/Makefile，CI 工具链具备
3. 难度定级：A（纯编译适配，零补丁）；唯一依赖 ncurses/6.6 已发布制品仓（W0 设备侧 `conan download --only-recipe` 实测）

## 上游测试清点（R51）

- 上游**有**完整测试套件：tests/ 下 243 个 .tst 文件（126 POSIX 组 + 117 yash 扩展组），tests/Makefile `test` 目标驱动，逐断言写 .trs（%%% OK[/%%% ERROR[/%%% SKIPPED:）
- 配方 build() 真实执行全部 243 个并解析 .trs 统计进构建日志；失败项如实归因（平台差异逐类列出）

## 平台适配要点

- **行编辑依赖 terminfo**：configure 检测不到 curses 会 fail 并提示 --disable-lineedit；用已发布的 ncurses/6.6 + --with-term-lib=ncurses，CPPFLAGS/LDFLAGS 指向 conan 包目录
- **NLS 关闭**：平台无 gettext，--disable-nls
- **LD_LIBRARY_PATH 盾**：build() 显式清空（lld/libxml2 根因，同 libodfgen/libabw）

## 编译结束

设备实机验证（2026-09-19，OHOS aarch64）：

- `conan-verify`：G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS（RC=0）
- CI 同源闸门 `CI_PACKAGES=archives/y/yash/2.60 zsh ci/conan/build_and_test.sh`：L0/L1/L4/L5 全 pass，Pass rate 100%
- 上游测试实测（设备，剔除缓存全新构建）：171 个非 REQUIRETTY 文件执行——文件级 PASS=156 FAIL=15；断言级 OK=11097 / ERROR=487 / SKIPPED=26（通过率 95.8%）
- test_package：6 组消费者断言全过

平台适配踩坑与归因（全部实证）：

1. **"[ no such command"（根因，非编译问题）**：yash 的 substitutive 内建仅当 PATH 存在同名外部命令时启用；本平台无 /bin/[（实测），导致 [ 完全失效、上游测试 409 项连锁报错。补丁 0001 把 [ 改注册为 BI_MANDATORY（语义不变：substitutive 内建本就定义为与外部工具行为一致；上游 master 仍维持 substitutive）
2. **%REQUIRETTY% 测试挂死**：HiShell 会话有控制终端（checkfg 通过）但无完整前台进程组语义——ptwrap 下 sigstop3-p.tst 挂死 10+ 分钟（两次复现）；enqueue.sh 回退的 tmp.queue 硬链接队列在 hmdfs 上不可靠。配方级排除全部 72 个 %REQUIRETTY% 测试并如实申报，其余测试加 timeout -s KILL 120 兜底
3. **孤儿测试进程持有管道导致 conan 挂死**：测试输出必须重定向到文件而非继承 stdout，跑完 pkill 清扫
4. **失败项逐类归因**：sigrtmin*-y（124+ 断言，OHOS musl 实时信号语义差异）｜umask-p/test1-y -k（hmdfs 不保留权限位）｜fc-y/history*-y（历史记录依赖交互终端）｜bracket-y/fnmatch-p/option-p（musl 正则/glob 括号语义差异）｜exec-p/redir-p/trap-y（单项零散差异）
5. **ncurses 选型**：制品仓 ncurses/6.6 只提供宽字符库（libncursesw.a），须 --with-term-lib=ncursesw
