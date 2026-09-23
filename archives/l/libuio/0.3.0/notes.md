# libuio 0.3.0 适配笔记

- 上游：<https://github.com/missinglinkelectronics/libuio> tag `v0.3.0`（2024-03-07，commit 37b897d）
- 源码 sha256：`420fb12fca714ddcfa75804e6d3feb492b257579643876201af350b0a5d0fffd`
- 许可证：LGPL-2.1-or-later（库）/ GPL-2.0（lsuio/readuio 工具）
- 构建系统：Autotools（configure.ac + Makefile.am + autogen.sh）

## W0 依赖检查（2026-09-19）

- 运行时依赖：**无**。glib-2.0 为可选支持（configure.ac `--without-glib`），
  关闭后库内自带 `g_warning`→`fprintf`、`g_strerror`→`strerror` 回退
  （libuio_internal.h），CLI 侧 `g_print`→`printf` 回退（lsuio.c/readuio.c）。
- 构建期 tool_requires：`automake/1.18`（ohpcd 已发布，revision 65a7ba60030d）、
  `libtool/2.5.4`（ohpcd 已发布，revision fe9f8e735ad4）；autoconf/m4 由 SDK
  `/data/service/hnp/bin` 提供（avahi/accel-config 先例）。

## 源码与构建系统分析

- 库本体 5 个 C 文件（base/helper/irq/mem/attr）只用 POSIX 头
  （dirent/regex/sysmacros/mman/select 等，musl 均有），无平台风险。
- 产物：`libuio.la`（version-info 4:0:2 → libuio.so.2）+ `bin/lsuio` + `bin/readuio`
  → R38 需软件级 `commands.json`（type: tool）。
- GitHub tag 归档**不含 configure**：build() 先 `bash autogen.sh`
  （= mkdir m4 && touch ChangeLog && autoreconf -s -f -i）再 configure。
- configure.ac 老宏（AM_CONFIG_HEADER/AC_PROG_LIBTOOL/AM_PROG_CC_C_O）在
  automake 1.18 下仅 obsolete 警告（libnxml 0.18.5 同款实测），无需补丁。
- `-Werror` 默认开启（LIBUIO_WERROR）：configure 传 `--without-werror` 关闭，
  避免 clang-15 -Wextra 对 2011 年代码的警告升级为错误。

## 补丁（3 个，单一职责）

1. `0001-replace-argp-with-getopt-long-for-musl.patch`
   - 根因：`argp.h` 是 glibc 扩展，OHOS musl 不提供；configure.ac 对其硬性
     AC_MSG_ERROR。
   - lsuio.c：argp 解析改 getopt_long（-a/--access、-v/--verbose，新增
     -h/--help、-V/--version，行为对齐原 argp 自动提供的 help/version）。
   - readuio.c：`#include <argp.h>` 是死代码（实际用裸 argc/argv），直接删除。
   - configure.ac：删除 argp.h 头文件硬检查。
2. `0002-drop-gettext-i18n-infrastructure.patch`
   - 根因：AM_GNU_GETTEXT([external]) 要求 autoreconf 时有 autopoint/gettextize
     （且 gettext 工具包有 baked datadir 路径坑，见 avahi notes R19）；
     OHOS musl 无 libintl 运行时（ENABLE_NLS 静态链接消费方必挂，avahi 实测）。
   - 删 AM_GNU_GETTEXT/AM_GNU_GETTEXT_VERSION/AC_OUTPUT 的 po/Makefile.in/
     Makefile.am 的 SUBDIRS=po；ENABLE_NLS 保持未定义，上游 `_()` 回退为恒等。
3. `0003-drop-texinfo-docs-build.patch`
   - 根因：info_TEXINFOS 规则要求 makeinfo，交叉工具链无；git 归档无预生成
     .info，`make all` 必挂。删除 info_TEXINFOS/lsuio_TEXINFOS，man 页保留。

## 上游测试清点（R51）

上游 0.3.0 **无测试套件**：源码树无 tests/ 目录；Makefile.am 无 TESTS/
check_PROGRAMS/XFAIL_TESTS；无 `make check` 实质目标。消费者级验证由
test_package 承担（见 test_package/MANIFEST.yml）。

## 本机已验证 / 未验证

已验证（Windows 本机）：

- 源码 URL/sha256（GitHub 官方 tag 归档）。
- 3 个补丁在干净解包树上按序 `git apply` 全部通过；打后 argp/gettext/texinfo
  引用清零；conanfile.py / test_package 语法（py_compile + conan inspect）。
- W0：automake/1.18、libtool/2.5.4 制品仓在架（conan download --only-recipe）。

## 真机验证（2026-09-19，10.62.178.77 全绿 ✅）

真机：10.62.178.77（8 核，内存余 2.5G+；frp-tip.com 那台 20 核但负载 28.7、
内存仅剩 207MB，弃用）。conan 2.29.1，profile 用 **ohos-aarch64-fixed**
（os.version=6.0 + SDK clang 路径；裸 ohos-aarch64 缺 os.version 会报
`settings.os.version value not defined`）。

```bash
cd ~/tmp/libuio-build/0.3.0
export PATH=/data/service/hnp/bin:$HOME/.local/bin:$PATH
conan create . --build=missing -pr:h ohos-aarch64-fixed -pr:b ohos-aarch64-fixed \
  -c tools.build:jobs=2
```

结果：**conan create 全绿**——test_package ctest **2/2 PASS**（test_libuio API
枚举/负路径 + consumer_fake_sysfs 消费者级 23 项断言），`lsuio --version` 输出
`libuio 0.3.0`（getopt_long 补丁真机验证通过），包内 lib/libuio.a +
include/libuio.h + bin/{lsuio,readuio} 齐全；裸 `lsuio` 在无 UIO 设备的系统上按
上游约定打印 "No UIO devices found" 退出 1（test_package 因此用 -V 做冒烟）。

### 消费者用例（路径B 要求）与 ⭐uio_find_by_uio_num errno 怪癖

`test_package/consumer_fake_sysfs.c`：伪造完整 sysfs 树
（name/version/dev/maps/mapN/{addr,size,name}），经 `uio_setsysfs_point()`
重定向后走通枚举/name/version/major/minor/fd/maxmap/addr/size/offset
（=addr&(pagesize-1)，库内计算）/map name/按名索引/按名查找/按基址查找
（23 项断言，真机全过）。

真机发现（写进用例与 PR 说明）：**上游 `uio_find_by_uio_num` 以残留 errno 判
失败**——`create_uio_info` 内 `search_major_minor` 递归扫真 /dev，OHOS 部分条目
scandir/lstat EACCES → 即使设备解析成功也返回 NULL（/dev 路径硬编码，消费者
无法规避）。用例对该 API 断言"命中或带 errno 的已文档化失败"两态之一，正查
路径由按名/按基址查找覆盖。

### ⭐ 真机平台发现（对本机 conan 缓存在 HMDFS 上的设备通用）

1. **HMDFS 拒绝一切脚本直接 exec**（仅 ELF 可执行）——automake/libtool conan
   包的 shim（bin/aclocal→.aclocal-real）与 perl 脚本全部无法直接运行。
   解法：autoreconf 尊重 `$ACLOCAL/$AUTOMAKE/$LIBTOOLIZE` 环境变量覆盖，
   配方以内联 env 前缀驱动"解释器+脚本"形态：
   `perl -I<pkg>/share/automake-1.18 <pkg>/bin/.aclocal-real --automake-acdir=… --system-acdir=…`
   （automake 用 `--libdir=`；perl 模块目录用 `-I`，包烤死的 @INC 无环境变量口）。
   SDK /data/service/hnp/bin 的 autoconf/autoheader/m4/perl 在非 HMDFS 上可
   直接 exec。libisal 记忆"autotools 工具包在 HMDFS 不可建"由此全面解锁。
2. **libtool/2.5.4 包损坏**：conanbuild env 导出 `_lt_pkgdatadir` 指向空目录
   share/libtool-conan，而真身在 share/libtool（且缺 libtoolize 期望的 m4/
   子目录，宏在 share/aclocal）。解法：配方在 build 目录拼装合规 ltdata/
   （build-aux + libltdl + m4 从包内拷贝），`_lt_pkgdatadir` 指过去覆盖。
3. **上游 autogen.sh 用 `autoreconf -s`（symlink 模式）**：HMDFS 拒绝 link(2)。
   解法：OHOS 下不经 autogen.sh，直接 `mkdir -p m4 && touch ChangeLog &&
   autoreconf -f -i`（-i 拷贝语义）。
4. **裸 `ld` 探测**：SDK 只有 ld.lld（且是个加 --code-sign 的 sh 包装，本身
   可执行）。解法：预设 `LD=<SDK>/ld.lld` 环境变量（configure/libtool 尊重），
   不需要本地符号链接（HMDFS 反正拒绝 symlink）。
5. **hnp bash 在 HMDFS 上 getcwd 失败**（"working directory cannot be
   determined"）；mksh(/bin/sh) getcwd 正常但其下 config.status 临时文件机制
   又有坑。解法：预设 `PWD=$build_folder` 走 bash 逻辑 pwd（PWD 随环境传播给
   所有子 shell）。
6. **⭐⭐ 最深一坑：HMDFS 的 uid 映射 + umask**：.conan2 挂载点上进程 uid 与
   目录属主（数字 20001006）不匹配，目录写权实际走 file_manager **组**——
   umask 022 的目录（组 rw）可写，config.status 的 `umask 077 && mktemp -d`
   产生的目录（drwx--S---，组位空）EACCES，报
   "could not setup config files machinery"。同模式目录在 home/tmp 挂载点
   （属主名匹配）却可写，极易误判。解法：写 `bash_env.sh` 定义 mktemp 包装
   函数（内部强制 umask 022），`BASH_ENV=<file>` 让每个非交互 bash
   （configure/config.status/make 的 $SHELL）自动 source；同时
   `CONFIG_SHELL=<hnp bash 绝对路径>` 钉住 config.status/Makefile 的 SHELL。
7. 其余：OHOS 无外网证书链（curl 全挂）但 conan（certifi）下载正常；
  `/tmp` 只读 → TMPDIR 指到 build 目录（libtoolize 的 sh 临时文件也依赖它）；
  make jobserver mkfifo 被 HMDFS 拒绝（无害警告，自动降级）。

### 补丁 0001 真机修订

readuio.c 原 `#include <argp.h>` 在 glibc 下传递包含 errno.h，musl 不会——
删除后 `errno` 未声明（readuio.c:75/86 编译错误）。补丁改为
`#include <argp.h>` → `#include <errno.h>`（保持单一职责：都在"去 argp"补丁内）。

## 下一步

- [x] W0 依赖检查、源码分析、配方/补丁/test_package（本机）
- [x] 真机 conan create + test_package + CLI 冒烟（10.62.178.77 全绿）
- [ ] push fork → GitCode 建 PR（标题 `feat(libuio): 0.3.0 编译完成`）→
      评论 /rebuild 触发 CI → 绿后 /ai review
- [ ] issue 待补
- CI 环境注意：若 buildbot 工作机的 conan 缓存也在 HMDFS 上，上述 OHOS
  自举逻辑同样生效；若在普通存储，autogen 走非 OHOS 分支不受影响。
