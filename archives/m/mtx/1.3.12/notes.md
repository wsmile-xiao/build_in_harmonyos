# mtx 1.3.12 适配笔记

## 结论摘要

- 构建系统：autotools（2008 年 autoconf 2.13 时代产物，`configure` 已随 tarball 发布）。
- 依赖：**零外部依赖**（W0 无依赖检查项），只链接 libc。
- 产物形态：5 个命令行工具，`package_type = "application"` → 需要软件级 `commands.json`（R38）。
- 平台后端：上游 `scsi_linux.c` 走 Linux SCSI generic（`SG_IO`）；**真机 sysroot 已确认**
  自带 `scsi/scsi.h`、`scsi/scsi_ioctl.h`、`scsi/sg.h`、`sys/mtio.h`，因此**不需要 stub、
  不需要 `#ifdef __OHOS__` 功能裁剪**。
- 补丁 4 个，全部是构建系统可移植性修补，没有改一行 SCSI 业务逻辑。
- **真机（HarmonyOS PC aarch64）已验证**：4 补丁干净应用 → configure → make → make install
  DESTDIR → test_package/test.sh 全绿。

## 编译环境

- 构建系统：autotools（GNU make 必需，上游 `Makefile.in` 开头明确写了不支持非 GNU make）
- 编译日期：2026-09-29
- 编译器：clang 15.0.4（`Target: aarch64-unknown-linux-ohos`，OHOS 适配版 conan 的
  `ci/conan/profiles/ohos-aarch64`；真机为 `ohos-aarch64-localdevice` 变体）
- 状态：built（真机构建+测试通过；官方 `ci/conan/build_and_test.sh` 因设备缺 conan 未跑，见下）

## 源码与校验

| 项 | 值 |
|----|----|
| 官方源 | `https://downloads.sourceforge.net/project/mtx/mtx-stable/1.3.12/mtx-1.3.12.tar.gz` |
| sha256 | `0261c5e90b98b6138cd23dadecbc7bc6e2830235145ed2740290e1f35672d843` |
| 大小 | 235214 字节 |
| 镜像 | `https://deb.debian.org/debian/pool/main/m/mtx/mtx_1.3.12.orig.tar.gz` |
| 镜像等价证据 | 两个 URL 下载后 **sha256 完全相同**，`tar -tzf` 均为 96 个条目；Debian 的 `.orig.tar.gz` 校验值可在 `mtx_1.3.12-18.dsc` 的 `Checksums-Sha256` 中查到（同为 `0261c5e9…d843`）。tarball 内的 `debian/` 目录是上游 `makedist` 自己打包进去的，不是 Debian 重打包 |
| 解包结构 | `mtx-1.3.12/` 单层，`strip_root=True` 即可 |
| 许可 | GPL-2.0-or-later |

## 构建系统分析

1. `configure.in` 用 `AC_CANONICAL_SYSTEM` + `AC_PROG_CC` + `AC_CHECK_HEADERS(...)`，
   用 `case "$host_os"` 决定 `TARGET` 与 `AC_DEFINE`：
   - 分支模式是 `*linux*` → `linux-ohos` **能匹配**，`TARGET=linux`、`AC_DEFINE(LINUX)`，
     与上游 Linux 路径完全一致；
   - 因此**不需要**给 `configure.in`/`configure` 增加 `ohos` 分支，也不需要 `__OHOS__` 宏。
2. `Makefile.in` 用 GNU make 的 `ifeq ($(TARGET),linux)` 追加
   `-Wall -DLONG_PRINT_REQUEST_SENSE=1`；`TARGET=linux` 时才生效。
3. `configure` 生成 `config.h`（`AC_CONFIG_HEADER`）+ `Makefile`（`AC_OUTPUT`）；
   `config.h.in` 里 `HAVE_SCSI_SG_H` 等宏默认 0，由 configure 检测后写成 1。
4. `mtxl.c` 依据 `HAVE_*_H` 宏 `#include "scsi_linux.c"`；`scsi_linux.c` 在
   `#ifdef SG_IO` 下用 `sg_io_hdr_t` + `ioctl(fd, SG_IO, ...)`，否则退回
   `struct sg_header` 老接口 —— 两条路径都依赖 `<scsi/sg.h>`。
5. 零外部依赖：源码 include 列表里没有第三方库头文件，`configure.in` 无 `AC_CHECK_LIB`；
   `mtxl.c` 只用 libc（`open`/`ioctl`/`read`/`write`/`malloc`）。

### 真机 SCSI 头文件核查（已确认）

HarmonyOS PC 的 clang sysroot（`$HOME/usr/local/sysroot/usr/include`）内实测存在：

```text
scsi/scsi.h          4055 B
scsi/scsi_ioctl.h     333 B
scsi/sg.h            3214 B
sys/mtio.h           5379 B
```

真机 `configure` 输出：`checking for scsi/scsi.h... yes`、`scsi/scsi_ioctl.h... yes`、
`scsi/sg.h... yes`、`sys/mtio.h... yes`；生成的 `config.h` 中
`HAVE_SCSI_SCSI_H/HAVE_SCSI_SCSI_IOCTL_H/HAVE_SCSI_SG_H/HAVE_SYS_MTIO_H` 全为 1。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `--host=aarch64-linux-ohos` 时 configure 报 `Invalid configuration 'aarch64-linux-ohos': machine 'aarch64-linux' not recognized`，随后 `config.sub $host_alias failed` 并 exit 1 | tarball 内置的 2004 年版 `config.sub` 的 `maybe_os` 白名单只列到 `linux-uclibc*`，不认识 `linux-ohos` | 补丁 0002：`maybe_os` 白名单 + 合法 OS 列表补 `linux-ohos*` |
| 2 | 补了 `linux-ohos` 后仍报 `Invalid configuration 'aarch64-linux-ohos': machine 'aarch64' not recognized` | 同一份 `config.sub` 的 basic_machine 白名单里**根本没有 `aarch64`**（当年只有 `arm`/`armv[2345]` 等）；而 OHOS conan 的 `_get_gnu_triplet("OHOS","armv8")` 正好产出 `aarch64-linux-ohos` | 补丁 0002 追加 `aarch64 | aarch64_be`。**只补 `linux-ohos` 不够，这是本库最关键的坑。** |
| 3 | 真机 configure 在 `checking build system type...` 阶段失败：`config.guess: line 1307: .../tmp/cgXXXXXX/dummy.c: Permission denied` → `unable to guess system type` | 真机 `uname -s` 是 `HarmonyOS`，2004 年版 `config.guess` 无该分支，走到末尾 fallback 去编译 `dummy.c`；而它能写文件的唯一途径是 `umask 077 && mktemp -d "$TMPDIR/cgXXXXXX"` 建的目录 —— **umask 077 在 HMDFS 上建出的临时目录对后续写入不可用**（E011/E167 同类坑）。另外真机 `/tmp` 只读，必须显式给 `TMPDIR` | 补丁 0001 两件事一起做：① 在 `*:NetBSD:*:*` 之前插入 `*:HarmonyOS:*:*` 分支，输出 `aarch64-unknown-linux-ohos`（命中该分支后不再走 fallback）；② 把该处 `umask 077` 改为 `umask 022` |
| 4 | `configure` 走到 `config.status` 段时还会用 `umask 077 && mktemp -d "./confXXXXXX"` 建临时目录 | autoconf 2.13 生成的 configure 里同一处 HMDFS umask 问题 | 补丁 0004：两处 `umask 077` → `umask 022` |
| 5 | `make install` 报 `install: cannot stat 'mtx.1'`，退出码非 0；5 个二进制已装好但 man 页失败 | 上游 install 目标 man 页写裸 `"$$file"`；Conan 用 `basic_layout` 做**源外构建**，build 目录里没有 `*.1`（VPATH 只影响 make 的查找，不影响 recipe 里的 shell） | 补丁 0003：`$(INSTALL_DOC) "$(srcdir)/$$file"` |
| 6 | 上游 install 目标不支持 `DESTDIR`，`Autotools.install()` 传的 `DESTDIR=<package_folder>` 被忽略，会直写 `$(sbindir)` | 上游 `Makefile.in` 未定义 `DESTDIR` | 补丁 0003：补 `DESTDIR =` 变量并把 install 目标全部路径改为 `$(DESTDIR)$(dir)` |
| 7 | `conan create` 报 `KeyError: '1.3.12'`（`source()` 里 `self.conan_data["sources"][self.version]`） | 本仓库 `conandata.yml` 用模板的**扁平**结构（`sources: {url, sha256}`），没有按版本分层；但配方写成了按版本取 | 配方改为 `get(self, **self.conan_data["sources"], strip_root=True)` |
| 8 | 配方 `get()` 报 `TypeError: get() got an unexpected keyword argument 'mirror_url'` | `sources:` 里多写了一个自定义键 `mirror_url`，而 `get()` 只接受固定参数 | 删掉该键，镜像信息只保留在 `conandata.yml` 注释中 |
| 9 | `conan create` 下载源码失败：`ConnectTimeoutError(master.dl.sourceforge.net:443)`，重试后 `ConanException: Error downloading file …` | 真机网络到 SourceForge CDN 节点不可达（R39 的镜像 fallback 机制为此存在，但 `conan create` 本身不读镜像键） | 不做吞错式绕过：把**已校验 sha256 的同一份 tarball**预置进隔离 CONAN_HOME 的下载缓存（`core.sources:download_cache=<CH>/dl_cache/<sha256(url)>`）后再跑 create —— 既没改源，也没跳过校验 |
| 10 | 独立执行 `test.sh` 时报 `mktemp: failed to create directory via template '/tmp/tmp.XXXXXXXXXX': Read-only file system`（在 `conan create` 内部跑却正常） | `test.sh` 原先裸用 `mktemp -d`，默认落 `/tmp`；真机 `/tmp` 只读。conan 内部跑能过是因为 conan 自己注入了可写的 `TMPDIR`，属于「被环境掩盖的脚本缺陷」 | `test.sh` 改为按 `$TMPDIR` → `$HOME/tmp` → `$PWD/.mtx-test-tmp` 依次挑选可写目录，找不到就明确报错 |

> 第 1、2、3、5、6、7、8、10 条都真实复现过；第 3、4、10 条只能在真机上暴露
> （本机 Alpine 的 `/tmp` 可写、`uname -s` 是 `Linux`，所以本机跑通了而真机失败）。
> 第 9 条是环境网络限制，非配方问题。

## 源码修改（补丁清单）

**一个文件一个补丁**，保证每个补丁都能独立应用到 pristine 源码（同一文件写两个补丁会因
上下文重叠而互相依赖，已按此重构）。

| 补丁 | 目的 | 是否改业务逻辑 |
|------|------|----------------|
| `0001-config.guess-harmonyos-and-hmdfs-umask.patch` | build 三元组识别 HarmonyOS → `aarch64-unknown-linux-ohos`；mktemp 目录 umask 077 → 022（HMDFS） | 否 |
| `0002-config.sub-aarch64-linux-ohos.patch` | config.sub 接受 `aarch64` 机器名与 `linux-ohos` 三元组 | 否 |
| `0003-Makefile.in-destdir-and-srcdir-man.patch` | install 目标支持 `DESTDIR`，man 页从 `$(srcdir)` 取（源外构建） | 否 |
| `0004-configure-hmdfs-umask.patch` | config.status 的 mktemp 目录 umask 077 → 022（HMDFS） | 否 |

**有意不写的补丁**：

- `configure.in` 增加 `*ohos*` 分支：不必要。现有 `*linux*` 分支已覆盖 `linux-ohos`，
  加了反而造成“改模板不改生成文件”的不一致（tarball 内的 `configure` 已生成）。
- `config.sub` 的 umask：该文件里没有 `mktemp`/`umask`，无需处理。
- Debian 的 `011-gdd15_c23_bool.patch`（`typedef enum { false, true } boolean` 与 C23 冲突）：
  本仓库 profile 为 `compiler.cppstd=17`，C 侧默认 gnu17，不会触发；
  若未来 CI 切 `-std=c23` 需要补上。

## 依赖版本

无。`conanfile.py` 没有 `requirements()`，`conandata.yml` 只有一个源码。
W0（依赖发布检查）结论：**无需等待任何依赖**，不存在拆库问题。

## 验证结果

### 真机验证（HarmonyOS PC aarch64，HongMeng Kernel 1.12.0）✅

真机上已有 conan **2.31.1**（`$HOME/.local/lib/python3.12/site-packages/conan`，CLI 入口
`$HOME/.local/bin/conan`，其 `.conan2/settings.yml` 认识 `OHOS`）。
为避免污染共享 `~/.conan2`，验证使用**隔离 CONAN_HOME**：

```sh
CH="$HOME/mtx-run/conan-home"
cp ~/.conan2/settings.yml              "$CH/settings.yml"
cp ~/.conan2/profiles/ohos-aarch64-localdevice "$CH/profiles/"
# 该 profile 的 compiler_executables 指向带 -Wl,--code-sign 的 wrapper clang
CONAN_HOME="$CH" conan create . \
    -pr:h=ohos-aarch64-localdevice -pr:b=ohos-aarch64-localdevice
```

#### A. 真实 `conan create` 结果

| 项 | 值 |
|----|----|
| 命令 | `CONAN_HOME=<isolated> conan create . -pr:h=ohos-aarch64-localdevice -pr:b=ohos-aarch64-localdevice` |
| 结果 | **exit 0**（日志末行 `mtx/1.3.12: Already installed!` 之后进入 test 阶段并全绿） |
| recipe revision | `mtx/1.3.12#262839acb4ade40e58af7250e72ff007` |
| package id | `6b129b068851896169fae42d399fa922d239ce8a` |
| 包设置 | `os=OHOS`、`os.version=6.0`、`arch=armv8`、`compiler=clang 15`、`compiler.libcxx=libc++`、`compiler.cppstd=17`、`build_type=Release` |
| 包目录 | 三次独立运行分别为 `p/b/mtxf593fcbb0446c/p`、`p/b/mtxa0a0c59a0b910/p`、`p/b/mtxce62366ba6a73/p`（每次清隔离 CONAN_HOME 后重建都得到同一 package id） |
| bin 内容 | `mtx` 76224 B、`tapeinfo` 68032 B、`scsitape` 68032 B、`loaderinfo` 68032 B、`csieject`→`scsieject` 63936 B（三次构建字节数完全一致） |
| man 内容 | `mtx.1` `tapeinfo.1` `scsitape.1` `scsieject.1` `loaderinfo.1` |
| 产物格式 | `ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped` |
| test_package（conan 内） | `RUN: bash test.sh <package_folder>` → **`OK: mtx 1.3.12 CLI smoke test passed`** |
| test_package（独立执行，`TMPDIR` 显式 unset） | exit 0，同上全绿 —— 验证 `test.sh` 的临时目录兜底逻辑在真机只读 `/tmp` 下可用 |

#### B. 逐步证据（先手工复刻，用于定位）

工具链：`$HOME/usr/local/bin/clang` wrapper（`clang-15 --sysroot=…/sysroot -fuse-ld=lld
-Wl,--code-sign -D__MUSL__`）+ GNU Make 4.4.1 + `/data/service/hnp/bin/git` 2.45.2。

| # | 验证项 | 结果 |
|---|--------|------|
| 1 | 4 个补丁用 `git apply`（Conan 的补丁引擎）应用到 pristine 源码 | 4/4 `Applied patch … cleanly`，exit 0 |
| 2 | `configure --host=aarch64-linux-ohos` | **exit 0**；`checking build system type... aarch64-unknown-linux-ohos`、`checking host system type... aarch64-unknown-linux-ohos` |
| 3 | SCSI 头文件探测 | `scsi/scsi.h` / `scsi/scsi_ioctl.h` / `scsi/sg.h` / `sys/mtio.h` 全部 `yes` |
| 4 | 生成 Makefile | `TARGET = linux`、`CPU = aarch64`（证明 `*linux*` 分支命中） |
| 5 | 生成 config.h | `HAVE_SCSI_SCSI_H/HAVE_SCSI_SCSI_IOCTL_H/HAVE_SCSI_SG_H/HAVE_SYS_MTIO_H = 1`、`WORDS_BIGENDIAN 0` |
| 6 | `make -j1` | exit 0；5 个可执行文件生成 |
| 7 | `make install DESTDIR=<stage>` | exit 0；staging 出 `bin/`（5）+ `share/man/man1/`（5） |
| 8 | `test_package/test.sh <pkg>` | exit 0，`OK: mtx 1.3.12 CLI smoke test passed` |

真机 `test.sh` 实测输出（`conan create` 内与手工执行一致）：

```text
[test] packaged tools present           ok: mtx / tapeinfo / loaderinfo / scsitape / scsieject
[test] mtx --version                    ok: banner reports 1.3.12
[test] mtx noattach                     ok: noattach succeeded without a SCSI device
[test] mtx -f <regular file> status     "<file> is not an sg device, or old sg driver"
                                        ok: probe reached the SCSI generic interface
[test] usage text of the remaining tools ok: tapeinfo / loaderinfo / scsitape / scsieject usage
OK: mtx 1.3.12 CLI smoke test passed
```

其中 `not an sg device, or old sg driver` 是真机内核返回的真实错误（`SG_GET_VERSION_NUM`
ioctl 在普通文件上失败），**证明 `scsi_linux.c` 与 `SG_IO` 后端在真机二进制里确实生效**，
而不是被编译期裁掉。

### 本机前置验证（Windows + WSL 内 Alpine 3.19 musl chroot）

用于在动真机前先排除基础错误：4 个补丁可应用、`--host=aarch64-linux-ohos` 可配置、
`TARGET=linux`、SCSI 头文件齐备、原生构建 5 个二进制、`make install DESTDIR` 与
`test.sh` 通过。**注意本机盲区**：Alpine 的 `/tmp` 可写且 `uname -s` 为 `Linux`，
所以补丁 0001 的 umask 部分与 0004 在本机不是必需的 —— 这两条只有真机能验证。

### 未执行项

官方 shadow CI 脚本（`CI_PACKAGES="archives/m/mtx/1.3.12" zsh ci/conan/build_and_test.sh`）
未在真机执行：设备上没有部署 shadow runner（`run-ohos-shadow-ci.sh` 不存在），
`ohpc-ci-shadow/` 下只有历史 run 目录。但其核心步骤（L0 结构门禁所需的 4 文件、
`conan create`、test_package）已在真机用隔离 CONAN_HOME 实跑通过，见 A 节；
L4/L5 的 ELF 检查项可用 A 节 `file`/`ls -l` 证据对应。

## 注意事项

1. **真机没有磁带库/机械手**：5 个工具在真机上只能做 CLI 级 smoke（版本、usage、状态类命令、
   设备探测失败路径），无法验证真实 SCSI 数据通路。这是测试客观边界，不写成“功能已验证”。
2. **`mtx --version` 退出码是 1**：上游 `Version()` 打印 banner 后调用 `Usage()`，
   而 `Usage()` 以 `exit(1)` 结束。不是适配缺陷，`test.sh` 按上游行为断言。
3. **真机必须用带 `-Wl,--code-sign` 的 wrapper clang**：实测裸 `clang-15` 编出的二进制在真机上
   直接 `Permission denied`（run_exit=126），而 wrapper 版本可执行。conan profile 的
   `tools.build:compiler_executables` 已指向 wrapper，无需额外处理，但**不要**改成裸 clang-15。
4. **真机 `/tmp` 只读**：任何脚本都要显式 `TMPDIR=$HOME/...`，否则 `mktemp`/heredoc 失败。
5. **真机自带 `patch` 是精简实现**（只支持 `-d/-i/-p/-R/-l/-s/-u/--dry-run`，
   无 `--forward`/`-N`）。要在真机手工验证补丁，用 `/data/service/hnp/bin/git apply`，
   或直接跑 conan（内部用 patch_ng）。
6. **GNU make 必需**：`Makefile.in` 使用 `ifeq`、`$(BINS:...)` 等 GNU 扩展。
7. **真机 SCSI 权限**：即使有设备节点，HarmonyOS 的 SELinux/沙箱策略可能限制裸设备访问；
   这属于运行期问题，不影响本轮构建类交付。

## 风险与后续

**R1（已消除）**：sysroot 是否有 `include/scsi/` —— 真机实测四个头文件齐备，`configure` 全 `yes`。

**R2（低）**：真机内核 `SG_IO` 行为。已证明 ioctl 通路可达（返回真实 SCSI 错误而非
`ENOTTY`/崩溃）；是否能真正驱动机械手需接实际 SCSI 设备才能定论，本轮不阻塞。

**R3（流程）**：`conan create` 未在真机跑过。官方 shadow CI 上一轮即可确认；
配方侧无已知未验证分支。

## 交付物

| 文件 | 说明 |
|------|------|
| `archives/m/mtx/commands.json` | 软件级 CLI 声明（R38） |
| `archives/m/mtx/manifest.yaml` | 软件级元数据 |
| `archives/m/mtx/README.md` | 软件说明与 OHOS 适配要点 |
| `archives/m/mtx/1.3.12/conanfile.py` | autotools 配方，`package_type = "application"` |
| `archives/m/mtx/1.3.12/conandata.yml` | 源码 URL/sha256 + 4 个补丁声明 |
| `archives/m/mtx/1.3.12/patches/000{1..4}-*.patch` | config.guess / config.sub / Makefile.in / configure |
| `archives/m/mtx/1.3.12/test_package/{conanfile.py,test.sh,MANIFEST.yml}` | 非空壳 CLI 测试 |
| `archives/m/mtx/1.3.12/manifest.yaml` | 版本级元数据 |
| `archives/m/mtx/1.3.12/notes.md` | 本文件 |
