# pipexec — OpenHarmony 编译档案

## 软件简介

pipexec 让你把**一棵进程树**写成单条命令：每个进程用 `[ NAME /path/to/prog args… ]`
描述，进程之间的 fd 连线用 `{NAME1:fd1>NAME2:fd2}` 描述，pipexec 负责 fork/exec、
建管道、dup fd、等待所有子进程退出并汇总退出码。它是 shell 管道与重定向的超集
（支持任意拓扑、非 0/1 的 fd、一对多/多对一在 2.6.2 中不合法，见下）。

典型用法：

```sh
pipexec -- [ ECHO /bin/echo Hello World ] [ CAT /bin/cat ] '{ECHO:1>CAT:0}' '{CAT:1>GREP:0}'
```

许可证 GPL-2.0-or-later。本次适配上游发布版 **2.6.2**。

## 上游信息

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/flonatel/pipexec （原 `florath/pipexec`，同名项目已迁移） |
| 目标版本 | 2.6.2（2024-10-16 发布） |
| 源码 URL | https://github.com/flonatel/pipexec/releases/download/2.6.2/pipexec-2.6.2.tar.xz |
| SHA256 | `d3ba6802a9dc4e5f336e840958c4ddaf3de427fa70a62430688c91e4d46e3d1d` |
| 许可证 | GPL-2.0-or-later（`LICENSE`） |
| 构建系统 | GNU autotools（`configure.ac` + automake `Makefile.am`/`Makefile.inc` + libtool） |

**为什么用 release asset 而不是 tag archive**：只有 release tarball（由上游
`build/create_tar.sh` 在发布时跑过 autotools）内含生成好的 `configure`、`Makefile.in`、
`aclocal.m4`、`config.h.in`。CI 镜像没有 autoconf/automake，用 tag archive 会触发
无法执行的 autoreconf。两者顶层目录都是 `pipexec-2.6.2/`，`strip_root=True` 均可处理。

## OHOS 适配要点

上游源码是**严格 POSIX**（只用 `fork`/`execv`/`pipe`/`dup2`/`wait`/`poll`/`fcntl`，
不碰 glibc 专属接口），因此适配集中在**构建系统**，共 4 个 portability 补丁，前三个
只在 OHOS 有实际影响、Linux 行为不变，第 4 个是 HMDFS 专属修复，全部不含任何
`__OHOS__` 平台宏（R8）：

1. **`0001-config-guess-sub-ohos.patch`（E007）**
   上游 `config.guess`（2018-02-24）/`config.sub` 不认识 HarmonyOS；`uname -s` 返回
   `HarmonyOS` 时 `configure` 在 "checking host system type" 处直接
   `unable to guess system type` 中断。补丁给 `config.guess` 加
   `*:HarmonyOS:*:*)` 分支（→ `aarch64-unknown-linux-ohos`），并让 `config.sub`
   认识 `linux-ohos` / `ohos-linux` 三元组。**不用 `--build/--host` 绕行**（E007：
   那会把 `cross_compiling` 置真，跳过 `AC_RUN_IFELSE` 探测）。
   注意该版本 `config.guess` 的分支必须以 `echo <triplet>; exit` 收尾。

2. **`0002-configure-respect-user-cflags.patch`**
   `configure.ac` 在末尾**无条件赋值** `CFLAGS="-std=c99 ${COMMON_FLAGS}"`、
   `CXXFLAGS="-std=c++11 ${COMMON_FLAGS}"`，把 Conan `AutotoolsToolchain` 注入的
   `--target=aarch64-linux-ohos`、`--sysroot=…`、`-fPIC` 全部丢掉（实测：生成的
   Makefile 里外部 CFLAGS 标记消失）。补丁把两处赋值改成追加
   （`CFLAGS="$CFLAGS …"`），与 `archives/l/libnova/0.16` 的
   `respect-user-cflags` 同型。

3. **`0003-version-gen-portable-shell.patch`（E165）**
   `src/Makefile.inc` 生成 `src/app_version.c` 时写死了字面 `/bin/sh`，生成的
   `build/version-gen.sh` 又会经 `#!/bin/sh` 去调 `version.sh`。HarmonyOS 没有传统
   `/bin` 目录、`/bin/sh` 也不在 PATH。补丁 (a) 改用 `configure` 填充的 `$(SHELL)`，
   (b) 直接读 `version.txt`（上游 `version.sh` 本来也只是 cat 这个文件），两个脚本
   都保持 POSIX。

4. **`0004-configure-hmdfs-mktemp.patch`（E114，真机实测）**
   autoconf 在 configure 里用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录；
   HMDFS 上该目录权限归一化为 `drwx--S---`（setgid），**属主自己也无法在其中写文件**，
   于是 `config.status` 报 `./confXXXXXX/subs1.awk: Permission denied`。补丁把 mktemp
   引导换成 `tmp=./conf$$-ohc; mkdir -p "$tmp"`。实测只改 `configure` 即可——生成的
   `config.status` 内嵌同一段模板，会自动继承修复。

**真机专属（不改上游源码，配方内处理）**：

- **E232（HMDFS 无法直接 exec configure）**：真机上 `autotools.configure()` 报
  `Error 126`（`/system/bin/sh: .../configure: Permission denied`），因为源码树在
  HMDFS 上不可执行，且 `CONFIG_SHELL` 只影响 Autoconf 后续子 shell、包不住首次启动。
  配方在 `settings_build.os == "OHOS"` 时改为
  `/system/bin/sh <configure> <autotools._configure_args>`（复用 Conan 生成的完整参数，
  不手工重建），并在 `generate()` 里把 `SHELL`/`CONFIG_SHELL` 指到系统 shell——
  与 `archives/o/opusfile/0.12`（E232 来源 PR）同型。

- **autotools 时间戳**：补丁会重写 `configure.ac`、`Makefile.inc`、`config.guess`、
  `configure`，刷新后的 mtime 会让 `make` 认为生成物过期、重跑镜像里不存在的
  autoconf/automake（`Error 127`）。`build()` 沿依赖链把输入、`aclocal.m4`、其余生成物
  赋成三个递增的过去时间戳（思路同 `archives/l/libmodbus/3.2.0`，需注意 `aclocal.m4`
  既是产物又是 `Makefile.in` 的依赖）。
- **`/bin/*` 子进程路径**：上游 `test/basic_tests.sh` 用 `/bin/true` 等绝对路径，
  `build()` 运行前按 `shutil.which()` 重定向到本机真实路径（E165）。

## 依赖关系

- **编译/运行依赖：无**（`configure.ac` 无库检查，源码只用 libc）。因此不存在 R36
  依赖发布阻塞。
- 被依赖：无（独立 CLI 工具）。

## 产物

`package_type = application`，产出三个可执行文件：

- `bin/pipexec` — 主程序
- `bin/ptee` — 管道 tee 辅助程序
- `bin/peet` — 另一个示例辅助程序

`make install` 会额外装 `bin/ptest`（上游的 stdin/stdout 回环示例程序，非运行时
功能），已在 `package()` 中剔除。

## 上游测试

上游无 `tests/` 目录、无 ctest/pytest 注册、automake `TESTS` 为空；唯一测试入口是
`test/basic_tests.sh`（4 项检查），已在 `build()` 中真实执行 4/4 通过。清点与证据见
`2.6.2/test_package/MANIFEST.yml` 与 `2.6.2/notes.md`（R51 三步法）。

## 参考资料

- [pipexec 官方仓库（flonatel/pipexec）](https://github.com/flonatel/pipexec)
- [pipexec 2.6.2 release](https://github.com/flonatel/pipexec/releases/tag/2.6.2)
- [Debian pipexec 2.6.2-1](https://tracker.debian.org/pkg/pipexec)
