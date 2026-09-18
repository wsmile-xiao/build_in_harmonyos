# libpskc 2.6.14 适配笔记

## 概述

libpskc 是 **OATH Toolkit** 发行版中的 PSKC（Portable Symmetric Key Container，
RFC 6030）库，用于解析/构建/校验 PSKC 格式的对称密钥容器。

- 上游：https://oath-toolkit.codeberg.page/
- 版本：2.6.14
- 构建系统：**autotools**（发行版自带预生成 `configure`，Autoconf 2.72）
- 许可：LGPL-2.1-or-later
- 编译日期：2026-09-16
- 状态：built

## 工程形态：oath-toolkit 的**子目录**工程

libpskc **不是**独立 tarball，而是 `oath-toolkit-2.6.14.tar.gz` 内的
`libpskc/` 子目录。实测其**自带预生成**的构件：

| 文件 | 状态 |
|---|---|
| `libpskc/configure` | ✓ 存在（`libpskc configure 2.6.14`，Autoconf 2.72）|
| `libpskc/Makefile.in` | ✓ |
| `libpskc/aclocal.m4` | ✓ |
| `libpskc/gl/` | ✓ 自带 gnulib（51 项）|

→ 故**无需 autoreconf**，可按独立 autotools 项目**就地构建**。

> 附注：`libpskc/configure.ac` 引用了上级路径（`../.tarball-version`、
> `AC_CONFIG_MACRO_DIRS([m4 gl/m4 ../m4])`），但因 `configure` 与 `Makefile.in`
> 均已预生成，构建期不触发这些引用；实测就地 `./configure` 可正常运行。

### 与同项目其它组件的关系

`oath-toolkit` 含 5 个组件（顶层 `AC_CONFIG_SUBDIRS`）：

```
liboath  libpskc  pam_oath  oathtool  pskctool
```

实测 **libpskc 不依赖 liboath**（`Makefile.am` 只 `LIBADD = gl/libgnu.la`，
源码中无 `include <liboath/*>`）→ 可独立交付，不必先构建 liboath。

## 交付物

| 类型 | 文件 |
|---|---|
| 库 | `lib/libpskc.so*` |
| pkg-config | `lib/pkgconfig/libpskc.pc` |
| 头 | `include/pskc/{pskc,exports,version,global,errors,enums,container,keypackage}.h` |
| 数据 | `share/xml/pskc/*.xsd` + `catalog-pskc.xml`（schemas）|

## 依赖：**必需 vs 可选**（本包关键判别点）

### libxml2 —— **默认必需**

`libpskc/configure.ac`：

```sh
PKG_CHECK_MODULES(XML2, libxml-2.0,, [AC_MSG_ERROR([Cannot find libxml2])])
```

**找不到 libxml2 直接 configure 失败**。好在该依赖在 ohpcd **已发布**
（2.15.3 / 2.15.3.1），且其 `pkg_config_name="libxml-2.0"`（实测
`archives/l/libxml2/2.15.3.1/conanfile.py:108`）**正是 configure 查找的模块名**
——无需别名适配。

### xmlsec1 —— **可选，缺失即降级**

```sh
PKG_CHECK_MODULES(XMLSEC, xmlsec1$xmlsecengine, [xmlsec=yes], [xmlsec=no])
```

实测语义：xmlsec1 找不到 → `xmlsec=no` → **不定义** `USE_XMLSEC`
（`AC_DEFINE(USE_XMLSEC, 1, ...)` 被跳过）。这是**上游受支持的配置**
（`--with-xmlsec-crypto-engine` 亦有专档）。

**本适配走这条降级路径**，因为 xmlsec1 **未发布到 ohpcd**。后果必须讲清：

- 签名相关入口 `pskc_sign_x509` / `pskc_verify_x509crt` 编译为**返回错误的桩**；
- 容器解析、访问器、序列化、校验等**其余功能不受影响**（消费者测试覆盖这些）；
- 消费者测试**刻意不覆盖**这两个入口，并在代码注释与 MANIFEST 中显式标注该边界
  ——**不静默跳过**（R51）。

> `xmlcatalog` 仅在 xmlsec 路径上被检查（`AC_PATH_PROG(XMLCATALOG, ...)`，
> 缺失则 `xmlsec=no`），故本路径无需它。

### openssl

**非直接依赖**——只会在 xmlsec1 存在时经其间接引入。

## OHOS 适配（3 处）

### ① `config.guess` / `config.sub` 补 OHOS 识别（R15）

libpskc 的 `build-aux` 是 **2024 世代**（`timestamp='2024-01-01'`）。实测仓内
`scripts/patch-autotools-ohos.pl` 对该世代**命中 5/5**：

```
  [ok] Added ohos-linux triplet
  [ok] Added ohos* to OS list
  [skip] linux-ohos already present
Score: 5/5   ✅ Patching successful.
```

> 与 pwquality 1.4.5 恰成对比：那边是 **2018 世代**，同脚本**只打中 1/5**
> （需按旧版格式手工补）。**先验世代、再决定用手工补丁还是脚本。**

补丁由该脚本生成后固化为
`patches/0001-libpskc-build-aux-config-guess-sub-ohos.patch`（20 增行），
**未使用 `--build`/`--host` 硬编码**（本仓铁律）。

### ② `umask 077` → `022`（HMDFS 陷阱）

`libpskc/configure` 内有 **2 处** `umask 077`。`config.status` 会在**构建目录**
（非 `TMPDIR`）创建 `confXXXXXX` 临时目录并写入 `subs*.awk`，HMDFS 拒绝写入
700 目录 → `Permission denied`。**cracklib / pwquality 踩过同一个坑**，故同样
把 two 处放宽为 `022`。

### ③ 构建裁剪与单 job

- `make SUBDIRS="gl schemas include ." -j1`：裁掉
  `examples/tests/gtk-doc/man`（**但保留 `schemas`**——上游 `tests/Makefile.am`
  需要 `$(top_builddir)/schemas/catalog-pskc.xml`）；
- `--disable-gtk-doc --disable-gtk-doc-html --disable-gcc-warnings`；
- **`make -j1`**（R9：并行 make 触发 HMDFS jobserver fifo EPERM，见 E074）；
- `CONFIG_SHELL` / `SHELL` 指向真实 bash（本机 `/bin/sh` 是 toybox）。

## 上游测试

`libpskc/tests/` 提供 **6 个 C 测试程序**（由 `tests/Makefile.am` 的
`TESTS = $(ctests)` 驱动）：

```
tst_accessors  tst_basic  tst_errors  tst_invalidread  tst_setters  tst_validate
```

`build()` 内以 `make check SUBDIRS=tests -j1` 执行，输出捕获到
`make-check.log` 并回填真实结果（R51）。

> 实现细节：`ConanFile.run` **只返回退出码**（实测签名为 `run(...) -> int`），
> 故用 `stdout=`/`stderr=` 传入文件对象来捕获套件输出，而不是访问不存在的
> `res.stdout`。

## 消费者测试（test_package）

`test_package/test_libpskc.py`：用 C 编译器链接**打包的** `pskc/pskc.h` 与
`libpskc.so` 编译并运行真实 C 程序（与 cracklib / pwquality 同思路）。
PSKC XML 夹具的形状取自上游 `tests/tst_accessors.c`，**不靠猜 XML**。

| 组 | 断言 |
|---|---|
| 打包物 | `include/pskc/pskc.h`、`lib/libpskc.so*`、`lib/pkgconfig/libpskc.pc` 均存在 |
| **pkg-config 契约** | `--modversion` = **2.6.14**；`--libs` 含 `-lpskc` |
| 版本 API | `pskc_check_version` 三支：`PSKC_VERSION` / `NULL` 非空；`"999.999"` / `"0"` / `"UNKNOWN"` 返回 NULL |
| 初始化 | `pskc_global_init` → `PSKC_OK`；`pskc_init` 得非空句柄 |
| **真实解析** | `pskc_parse_from_memory` 解析 KeyContainer → `pskc_get_version == "1.0"`、`pskc_get_id == "KCID-1"`、`pskc_get_keypackage(0)` 非空 |
| **序列化往返** | `pskc_output(XML)` 回写并校验含 `KeyContainer`（真实经 libxml2 往返）|
| 错误路径 | 畸形 XML → `rc != PSKC_OK` |
| 资源释放 | `pskc_done` / `pskc_global_done` |

## 验证结果

```
conan create archives/l/libpskc/2.6.14 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
→ exit=0
```

| 项 | 实测结果 |
|---|---|
| `conan create` | **exit=0**，Package created |
| umask 修复 | `widened umask 077 -> 022 in libpskc/configure (HMDFS)` |
| **上游 make check** | **# TOTAL: 6 / # PASS: 6 / # SKIP: 0 / # XFAIL: 0 / # FAIL: 0 / # XPASS: 0 / # ERROR: 0** |
| 上游测试清单 | `PASS: tst_basic`、`tst_errors`、`tst_accessors`、`tst_setters`、`tst_validate`、`tst_invalidread` |
| pkg-config 契约 | `libpskc 2.6.14 (-lpskc present)` |
| 消费者程序 | 编译并运行通过：`parsed: version=1.0 id=KCID-1`；`round-trip XML length=459`；`malformed input rejected with rc=-3` |
| 消费者测试 | `libpskc 2.6.14 consumer API: PASS` |

### 适配过程中实测订正的三处（均为我的初版错误）

**① 误假设存在 `src/` 子目录 —— 实为扁平布局**

初版 `_REQUIRED` 写了 `src/libpskc.map`，构建即报：

```
ConanException: libpskc/src/libpskc.map missing from the source tree
```

实测 `libpskc/` 是**扁平** autotools 工程：源码（`global.c` `container.c` …）、
`internal.h`、`libpskc.map` **均直接位于 `libpskc/`**，**没有 `src/`**。
已订正为按真实路径断言。

**② 仓内脚本的「5/5」是模式检查，不等于功能可用**

`scripts/patch-autotools-ohos.pl` 对本包（2024 世代）报 `Score: 5/5 ✅`，
但实测 `config.sub` **仍拒绝** triplet：

```
Invalid configuration 'aarch64-unknown-linux-ohos':
  Kernel 'linux' not known to work with OS 'ohos'.
```

根因：脚本在 `config.sub` 中补了 `basic_os=linux-ohos` 分支，**却漏了
kernel-OS 兼容表**（`case $kernel-$os-$obj` 的 `linux-uclibc*-` 行）——
而脚本的判定是"全文 grep 有没有 `linux-ohos`"，**已被自己刚插入的分支满足**，
于是**假阳性通过、跳过**了兼容表这一处。已按既有解法在兼容表补
`| linux-ohos*-`（该机制在知识库中已由 **E268** 收录，本次是复现而非新发现）。

**③ `SUBDIRS=` 不能作为 make 命令行变量**

初版用 `make SUBDIRS="gl schemas include ." -j1` 裁剪子目录，构建失败：

```
/data/service/hnp/bin/bash: line 21: cd: gl: No such file or directory
make[3]: *** [Makefile:1649: all-recursive] Error 1
```

根因：**GNU make 会把命令行变量经 MAKEFLAGS 传给递归子 make**，于是进到
`libpskc/gl/` 后它又试图 `cd gl`。修法：**把裁剪放进补丁**（改 `Makefile.in`
的 `SUBDIRS` 行），命令行只 `make -j1`。

**④ 消费者测试三处 API 误用（按实测订正）**

| 初版写法 | 实测事实 |
|---|---|
| `pskc_output_t` / `pskc_output_init` / `pskc_output_done` | **不存在**。真实签名是 `int pskc_output(pskc_t *, pskc_output_formats_t, char **out, size_t *len)`（`container.h:91`）|
| `pskc_check_version("0") == NULL` | **写反了**。实现（`global.c:143`）是 `strverscmp(req, PSKC_VERSION) <= 0 ? PSKC_VERSION : NULL`，故**更低的要求应成功**（返回非 NULL）；`"999.999"`/`"UNKNOWN"` 才返回 NULL |
| C 源码内直接引用 Python 变量 `PSKC_XML` | 需以 `json.dumps` 生成合法 C 字符串字面量后替换占位符注入 |

## 注意事项

1. **libpskc 是子目录工程**：从 `oath-toolkit-2.6.14` 的 `libpskc/` 就地构建，
   它自带预生成 `configure`，无需 autoreconf；
2. **libxml2 是硬依赖**（configure 直接 error），须 `PkgConfigDeps` + `AutotoolsDeps`
   双管齐下（前者提供 `.pc` 供 `PKG_CHECK_MODULES`，后者提供 CPPFLAGS/LDFLAGS/LIBS）；
3. **xmlsec1 缺失是降级而非失败**，但签名入口变桩——必须在测试与文档中显式标注；
4. **保留 `schemas` 子目录**（`make check` 需要 `catalog-pskc.xml`）；
5. **不要用 `--build`/`--host` 绕过** —— 本包是 2024 世代，仓内脚本可 5/5 命中；
6. `umask 077` 须放宽为 022（HMDFS），`make -j1`（R9）。
