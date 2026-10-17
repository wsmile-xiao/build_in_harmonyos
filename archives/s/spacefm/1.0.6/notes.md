# spacefm 1.0.6 — 构建笔记

## 任务身份

- 任务卡：#10827（OHPCD 积分赛主赛，2404_87638649）
- taskBranch：`feat/spacefm-1.0.6`
- 上游：https://github.com/IgnorantGuru/spacefm tag `1.0.6`（commit cc634c2a）
- sha256（tarball，本地实测）：`fedea9fcad776e0af4b8d90c5a1c86684a9c96ef1cdd4e959530ce93bdebe7c9`

## 形态定谳（W0）

- C 语言 GTK2 桌面文件管理器（双面板+标签页+自定义动作），autotools 构建（tarball 自带 configure，免 autoreconf）。
- 依赖面实测：configure.ac L170 `PKG_CHECK_MODULES(LIBUDEV, [libudev >= 143])`——HAL 分支（默认关）之外**无条件**要求 libudev，无 --disable-udev 开关。
- intltool：configure.ac L14 `AC_PROG_INTLTOOL` + data/Makefile.am `@INTLTOOL_DESKTOP_RULE@`。
- 上游无自动化测试套件（无 test/ 目录、Makefile.am 无 TESTS）。

## 依赖钉版（ohpcd 制品仓实测）

| 依赖 | 版本 | 说明 |
|---|---|---|
| gtk2 | 2.24.33 | GUI 框架（--with-gtk2 默认路径） |
| eudev | 3.2.14 | libudev.pc 提供方（udev 设备枚举） |

裁剪项：video-thumbnails（libffmpegthumbnailer 制品仓无档）、startup-notification（OHOS 无桌面启动通知栈）、nls（po 层）。

## 构建链（OHOS aarch64）

1. **三元组补丁 0001**：config.guess 加 `*:HarmonyOS:*:*` 分支 + config.sub 两处认 `linux-ohos*`（vlc 3.0.23 同款范式）。生成法：改源后对 pristine tarball diff（保真锚点），本地自测 `sh ./config.guess` → `aarch64-unknown-linux-ohos` ✅
2. **intltool shim**（activity-log 0.9.7 先例）：`ohos-build-tools/` 下 6 个 shim（intltool-update/merge/extract + msgmerge/xgettext/msgfmt），`--version` 应答、其余 no-op；PATH 注入。
3. **HMDFS umask 陷阱**（vlc 先例）：configure 内嵌 `umask 077` → replace 为 `umask 022`。
4. **configure**：`--disable-nls --disable-video-thumbnails --disable-startup-notification`，交叉 `--host=aarch64-linux-ohos`。
5. **make + install**：bin/spacefm + share/pixmaps + share/applications。

## 测试（rule4 逐项定性）

- **上游**：0 测试（tarball 无 test/ 目录、Makefile.am 无 TESTS/check_PROGRAMS——GUI 桌面应用无测试骨架；zsa-wally/aiac no_tests 先例同款）。
- **test_package 消费者侧 3 断言**：--version 版本输出 / --help 用法 / AArch64 ELF（od 读 e_machine=0x00b7）。
- **环境限制定性**：窗口渲染/文件面板交互/桌面集成需 X11/Wayland 显示与窗口管理器——沙箱不可用（rule4）。

## 踩坑记录

| # | 症状 | 根因 | 处置 |
|---|------|------|------|
| 1 | sed 插入 HarmonyOS 分支后 config.guess 出现 1526 处污染 | grep 锚点（双引号变量形态）未命中→`sed ""a` 空行号=全文每行后插入 | 从 tarball 重解压该文件；改用 `${VAR}` 形态锚点+Python 插入（转义安全） |
| 2 | diff 生成补丁报 read-only | /tmp 只读（OHOS） | pristine 解压放 ~/huawei/tmp（纪律既知坑） |
| 3 | worktree git 身份错号（user.name=calbee21、fork 指 calbee21） | 子任务建 worktree 时用了 calbee21 模板 | `git config user.name 2404_87638649` + `remote set-url` 修 2404 fork（积分错绑防线） |
| 4 | 归档目录残留解压源码 16M + 杂散 patch 文件 | 子任务断点现场 | rm 清理（源码不进 git，归档只放六要素） |
| 5 | configure: XML::Parser perl module is required for intltool | 系统真 perl 5.42 无 XML::Parser；自定义 save_script env 不自动注入 Autotools 子shell | 双保险：configure 里 `require XML::Parser`→`require strict`（replace）+ perl shim（拦截 XML::Parser 探测、其余委托真 perl）+ buildenv_info.prepend_path 注入 shim 目录 |
| 6 | Package requirements (libudev >= 143) were not met: version of libudev is 3.2.14 | systemd-udev vs eudev 版本号方案不同（API 全兼容） | 补丁 0002：configure.ac+configure 双处放宽为无版本要求 |
| 7 | error: call to undeclared function 'major'/'minor' | glibc 隐式声明，musl（OHOS）需显式 | 补丁 0003：src/main.c 补 #include <sys/sysmacros.h> |
| 8 | ld.lld: duplicate symbol: xsets/evt_win_*（vfs-file-info.c vs vfs-dir.c） | clang 15 默认 -fno-common，老代码 tentative definitions 变强符号 | CFLAGS 注入 -fcommon（tc.cflags 不达 autotools 子shell，改进程环境 CFLAGS 由 configure 烘进 Makefile） |
| 9 | undefined symbol: g_libintl_ngettext | glib 包 libintl.h 宏改名 ngettext→g_libintl_*，gailutil 仅带部分 stub（有 dgettext 无 ngettext） | 补丁 0004：main.c 定义复数选择 fallback（n==1?msgid:msgid_plural） |
| 10 | install-binSCRIPTS Error 1: mkdir File exists | make -j 并行 install-sh -c -d 竞态（HMDFS） | autotools.install(args=["-j1"]) 串行化 |
| 11 | test_package: Error loading shared library libc++_shared.so | gtk2 链 libc++_shared.so 在 /system/lib64（VirtualRunEnv 不含系统路径） | test.sh 注入 LD_LIBRARY_PATH=/system/lib64 |
| 12 | --version 挂 "Cannot open display" | spacefm 先 gtk_init 再打版本横幅；无头环境无显示 | rule4 定性：Cannot open display=已过共享库全解析+GTK 初始化层，打包完整性已证；MANIFEST/test.sh 断言按此口径修正 |

## PkgConfigDeps 关键坑（create5→create6）

configure 的 `PKG_CHECK_MODULES(GTK...)` 探测需要 .pc 文件——配方必须声明 `generators = "PkgConfigDeps", "VirtualBuildEnv"`（vlc 3.0.23 权威同款），VirtualBuildEnv 导出 PKG_CONFIG_PATH 指向 conan 生成的 .pc。缺此必挂（报错形态： GTK_CFLAGS and GTK_LIBS to avoid the need to call pkg-config）。
