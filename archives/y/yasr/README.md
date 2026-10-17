# yasr

`yasr`（Yet Another Screen Reader）是一个轻量的**控制台屏幕阅读器**：它在一个 pty 里拉起用户的 shell，截获这条 I/O 流，在内存里维护"屏幕上应该显示什么"的窗口模型，再把内容通过 TTS 设备朗读出来。它面向的是能访问文本转语音（TTS）设备的用户，最初为 SpeakOut 硬件合成器设计，也尝试支持 DEC-Talk、DoubleTalk、Apollo、ViaVoice Outloud，以及 Emacspeak 服务器。

上游为 SourceForge 项目 [yasr](https://yasr.sourceforge.net/)（作者 Michael P. Gorse，`AC_INIT` 中的联系方式为 mgorse@alum.wpi.edu，源码头注明维护者 mgorse@users.sourceforge.net），许可证 LGPL-2.0-or-later（COPYING 为 1991 年 FSF Library General Public License 文本，含"or (at your option) any later version"授权）。

> 注意区分：GitHub 上的 `mgorse/yasr` 与 `tbsaunde/yasr` 两个同名仓库都不是本包上游（二者的 `/tags` 均无 0.6.9）；`download.savannah.nongnu.org/releases/yasr/` 与 `github.com/yasr/yasr` 均为 404。发布归档只托管在 SourceForge。

## 功能概述

- `yasr` — 主程序。用法（取自 `yasr.1` 的 SYNOPSIS）：`yasr [-C config file] [-c] [-s synthesizer] [-p synthesizer port] [program arg1 ... argN]`。程序与参数被送进 pty 内的 shell 执行，其屏幕输出由 yasr 解读并朗读
- 配置文件三级搜索：命令行 `-C` 指定者 → `~/.yasr.conf` → `$(pkgdatadir)/yasr.conf`（随包安装的默认配置，安装到 `share/yasr/yasr.conf`）
- 键位向导（keyboard wizard）：由 `yasr.h` 的 `USE_KBWIZ` 宏编入，用于交互式绑定按键说明
- 手册页 `yasr.1`

未随包安装的构建产物：`yasr/keytest`（`noinst_PROGRAMS`，交互式按键诊断工具，用于查看终端实际送出的键码）；`acclogin`（顶层 `Makefile.am` 仅在 `YASR_SUN`，即 Solaris 条件分支下才加入 SUBDIRS）。

## 依赖关系

- 编译依赖：无第三方 Conan 包。`configure.in` 只探测 libc/libutil/gettext 三件：`AC_CHECK_LIB(util, openpty)`、`AC_REPLACE_FUNCS(openpty forkpty login_tty cfmakeraw)`、`AM_GNU_GETTEXT(external)`
- 运行依赖：需要可访问的 TTS 设备（`/dev/tts` 等串口合成器）或 Emacspeak 服务器；HarmonyOS PC 上无此类设备，故运行期仅能验证"程序可加载、配置可解析、pty 会话可建立并干净收尾"这一层（见 test_package）
- ⚠ **已知限制**：Conan 的 autotools 打包约定用 `--prefix=/`，而 `yasr/Makefile.am` 把 `PACKAGE_DATA_DIR` 作**编译期宏**烙进二进制 ⇒ 实际值是 `//share/yasr`。因此**不带 `-C` 且没有 `~/.yasr.conf` 时，yasr 找不到随包的 `share/yasr/yasr.conf`**（`config.c` 的三级搜索是 `-C → $HOME/.yasr.conf → PACKAGE_DATA_DIR/yasr.conf`）。配置文件本身确实随包安装且非空，前两级路径不受影响，故按上游文档使用 `~/.yasr.conf` 或显式 `-C` 即功能完整；test_package 的 5 个用例走的正是这两条可用路径，"仅靠随包默认配置"一路未覆盖且确证不可用（证据与处置选项见版本级 notes.md「已知限制」）

## OHOS 适配要点

1. **门槛是平台三元组，不是依赖**。tarball 自带预生成的 `configure`（GNU Autoconf 2.61，2006）与 `config.guess`（2007-07-22）/`config.sub`（2007-06-28），三个脚本都不认 aarch64、更不认 `ohos`。构建机缺 `automake`，因此不能走 `autoreconf` 自举，只能按 build-systems.md §3.6 的优先级②直接改这些 autoconf 生成件（并记明"该改动在 autoreconf 后会丢失"）。
2. **仓内官方处方脚本对本包失效**。`scripts/patch-autotools-ohos.pl`（E007/E072 的推荐方案）在 config.sub 上的三处锚点（`android-linux` 块、`gnu* | android*` OS 列表、`linux-uclibc* )` 收尾）全部落空——2007-06-28 版 config.sub 里 `android` 出现 0 次；实测该脚本对 config.sub 改动数为 0、总评分 `Score 1/5`、退出码 1。故按 E072 的三处白名单语义手工落点：KERNEL-OS 拆分列表补 `linux-ohos*`、OS 白名单补 `-linux-ohos*`，且**顺序敏感**——必须排在通用分支 `-linux*)` 之前，否则该分支会 `sed 's|linux|linux-gnu|'` 把三元组改写成 `-linux-gnu-ohos`。同理 config.guess 那一版**没有 `GUESS=` 累积机制**，脚本插入的赋值块形同无效并掉进 "unable to guess system type" 尾部，须改成打印三元组后 `exit 0`。
3. **`configure` 退 0 不等于构建件已生成**（本包最阴的一处）。autoconf 的 `AS_TMPDIR` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 在当前目录建私有临时目录；本机 euid 与构建树 owner 不同 uid，写权限只能来自 group 位，而 toybox `mktemp -d` 跟随 umask（022 → `drwxr-s--x` 可写；077 → `drwx--S---` 不可写，且 `chmod` 改不动模式），普通 `mkdir` 则被归一成 `drwxrws--x` 因而没事。结果 `config.status` 静默产不出任何 `Makefile`/`config.h`，`configure` 仍然返回 0，直到 `make` 才暴露为 "No targets specified"。解法采用 E011 的 `umask 077 → umask 022`（同型先例：aide 0.19.3、xz 5.6.2、tar 1.35、wget 1.19.1、ivykis 0.43.2，以及已合入的 `archives/a/a52dec/0.7.4/patches/0002-configure-umask-022.patch`）。
4. **E060 的 `use-tmpfs-workaround` 在本包未被执行 ⇒ 既未证实也未否证（证据不足；第 1 棒「在本包被否证」的说法已撤回）**。E060 把该现象归因于「HMDFS 临时目录限制」并建议「复制源码到 tmpfs（如 `$HOME/tmp`）再 configure」；实测 `$HOME`（`/storage/Users/currentUser`）自身的 fs 类型就是 **hmdfs**（`/proc/mounts:71`，父级 `tmpfs on /storage/Users` 被子挂载按最长前缀覆盖），三条构建树实算全为 hmdfs ⇒ 处方从未被现场满足，谈不上「被满足而无效」；而本机非特权 uid 下又找不到一个可写的真 tmpfs（`/dev/shm` 是真 tmpfs 但 `mkdir` 报 EACCES）⇒ 成对对照做不出来。本包实际生效的是 E011/E206 的 `umask 077→022`（补丁 0003）；逐条读数见 `0.6.9/notes.md`「已试过的失败方案」第 1 条。
5. **`yasr.h` 的陈旧原型与 musl `<pty.h>` 冲突**：上游自己声明了非 const 的 `openpty()`/`forkpty()`，与 sysroot `<pty.h>` 的 const 原型不一致而报 conflicting types。由于 `config.h` 报 `HAVE_OPENPTY/HAVE_FORKPTY/HAVE_PTY_H=1` 且生成的 `yasr/Makefile` 里 `LIBOBJS` 为空（自带的替代实现根本没参与编译），这两条原型纯属死重量 ⇒ 用 `HAVE_*` 守卫即可，**不引入平台宏**（PF5/R8 干净）。
6. **禁用 `--build/--host/--target` 绕过**（E007/E122 的 forbid 项，会让 AC_RUN_IFELSE 类运行时探测全部跳过、config.h 与实际平台不符），本包一律靠补丁解决。
7. 并行构建不可用：GNU make 4.4.1 的 jobserver FIFO 在本机 `mkfifo ...: Operation not permitted` ⇒ `make -j1`。
8. 实测未签名的 `bin/yasr` 在本机可直接 exec（无 rc=126 签名墙）。

## 参考资料

- 项目主页与下载：<https://yasr.sourceforge.net/> ／ <https://sourceforge.net/projects/yasr/>
- 官方发布归档：<https://downloads.sourceforge.net/yasr/yasr-0.6.9.tar.gz>（302 → `master.dl.sourceforge.net/project/yasr/yasr/0.6.9/`，与 Debian `yasr_0.6.9.orig.tar.gz` 逐字节相同）
- 许可证文本：tarball 内 `COPYING`（FSF Library General Public License, Version 2, June 1991）
