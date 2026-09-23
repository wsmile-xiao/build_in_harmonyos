# libm17n-core 1.8.6 — 鸿蒙 PC 适配笔记

上游：GNU m17n-lib 1.8.6（多语言文本处理库，提供 M-text 对象与 Unicode 字符表），
<https://download.savannah.gnu.org/releases/m17n/m17n-lib-1.8.6.tar.gz>
（sha256 `7129fe3b…f44a7c86`；同一 tarball 的 sha512 为
`4fe3e9d2…5b595a59`，与 Alpine `community/m17n-lib` APKBUILD 公布的参考哈希一致）。

## 定位

- 任务三方库为 **libm17n-core**，交付物即核心共享库 `libm17n-core.so.0.4.2`。
- 上游 `src/Makefile.am` 的 `BASICBUILDS = libm17n-core.la libm17n.la libm17n-flt.la`
  由同一次 configure+make 生成，后两者离开 core 无法使用，因此本配方一并打包
  `libm17n-core` / `libm17n` / `libm17n-flt` 三个库、4 个公开头文件与 3 个 pkg-config 文件。
- GUI 层（`libm17n-gui` + `libm17n-X` / `libm17n-gd` / `libmimx-anthy` / `libmimx-ispell`
  模块）需要 X11/Xft/Xaw、freetype、fontconfig、libotf、anthy、ispell，OHOS 均不具备，
  其产物在 `package()` 中剔除；上游示例程序（`example/`，会安装到 `bin/`）同理剔除。
- 运行时数据（m17n 数据库，如编码/语言/输入法定义）由独立的 `m17n-db` 数据包提供，
  不在本包范围内；核心 API（MSymbol/MPlist/MCharTable/MText）不依赖该数据即可工作。

## 编译环境

| 项 | 值 |
|---|---|
| 构建系统 | autotools（发布包内置 configure，无需 autoreconf） |
| profile | `os=OHOS os.version=6.0 arch=armv8 compiler=clang/15 build_type=Release`（CI 为设备原生构建，`-pr:h` 与 `-pr:b` 同为 `ohos-aarch64`） |
| 依赖 | `libxml2/2.15.3.1`（制品仓已发布，R36 满足） |
| 关键 configure 参数 | `--disable-nls --disable-dependency-tracking --disable-static` + `ac_cv_func_malloc_0_nonnull=yes`、`ac_cv_func_realloc_0_nonnull=yes`、`ac_cv_func_alloca_works=yes`、`ac_cv_func_memcmp_working=yes`、`ac_cv_func_strcoll_works=yes`、`HAVE_XML2_CONFIG=no` |
| 补丁 | `patches/0001-config.guess-harmonyos.patch`（config.guess 的 HarmonyOS 分支，§5）、`patches/0002-configure-umask-hmdfs.patch`（configure 辅助目录 umask 077→022，§5.2）；两个补丁都只做平台可移植性修复，不触碰任何 C 源码 |

## 上游测试用例情况

上游 1.8.6 **不随源码发布自动化测试**：顶层 `Makefile.am`、`src/Makefile.am`、
`example/Makefile.am` 中都没有 `TESTS` / `check_PROGRAMS` / `check-local`。
实测 `make check`（原生 Linux 构建）：

```
make[1]: Entering directory '.../intl'   -> Nothing to be done for 'check'.
make[1]: Entering directory '.../po'     -> (无输出)
make[1]: Entering directory '.../src'    -> Nothing to be done for 'check'.
make[1]: Entering directory '.../example'-> Nothing to be done for 'check'.
```

因此上游用例数 = 0（`test_package/MANIFEST.yml` 中 `upstream_tests: []`），
适配后以 `test_package/test.c` 从消费者视角补全核心 API 验证（56 项断言）。

## 关键适配点

### 1. `--disable-nls`：彻底去掉 libintl（规避设备符号改名）

OHOS sysroot 的 `<libintl.h>` 是空壳（只有宏，无任何声明），sysroot 里也没有
libintl 提供者；而设备上的 `libintl.so.8.proxy` 把 GNU gettext 入口改名为
`g_libintl_*`，动态链接后运行时表现为 `libintl_dgettext: symbol not found`
（历史归档 `archives/m/m17n-lib/1.8.6/notes.md` 记录过该现象）。

m17n-lib 的 gettext 调用全部被 `#if ENABLE_NLS` 包住
（`src/internal.h:38`、`src/m17n-core.c:635`、`src/input.c:1801`），
关闭 NLS 后 `#define _(String) (String)`，既不需要 `<libintl.h>` 也不需要
libintl 库：

```
$ nm -D --undefined-only lib/libm17n-core.so.0.4.2 | grep -i gettext   # 无输出
$ readelf -d lib/libm17n-core.so.0.4.2 | grep NEEDED
  (NEEDED)  Shared library: [libxml2.so.16]
  (NEEDED)  Shared library: [libz.so]
  (NEEDED)  Shared library: [libc.so]
```

（`libz.so` 来自 configure 的 libxml2 回退链接串；OHOS sysroot 的基础库 stub
`libz.so` 本身带 SONAME `libz.so`，设备上可解析。）

### 2. 绕过 libxml2 制品包里前缀写错的 `xml2-config`

`src/configure.ac` 用 `AC_CHECK_PROG(xml2-config)` 探测 libxml2，并把
`xml2-config --cflags/--libs` 的输出直接当成编译/链接参数。制品仓的
`libxml2/2.15.3.1` 包内 `bin/xml2-config` 是它自身构建残留，硬编码
`prefix=/usr/local`：

```
$ <libxml2-pkg>/bin/xml2-config --cflags
-I/usr/local/include/libxml2
$ <libxml2-pkg>/bin/xml2-config --libs
-L/usr/local/lib -lxml2 -lpthread -lm -ldl
```

于是 `checking for xmlParseMemory in -lxml2... no`、`checking for libxml/tree.h... no`
→ `HAVE_XML2` 未定义 → **库被"编译成功"却不含 XML 数据库后端**（静默降级）。

修复：配方预置 `HAVE_XML2_CONFIG=no`（`AC_CHECK_PROG` 在变量已赋值时不再搜索），
走 configure.ac 的回退分支，同时把依赖包的真实 `include` / `lib` 路径注入
`CPPFLAGS` / `LDFLAGS`。修复后制品：

```
$ readelf -d lib/libm17n-core.so.0.4.2 | grep NEEDED
  (NEEDED)  Shared library: [libxml2.so.16]     <- XML 后端已启用
```

### 3. 交叉编译下 `rpl_malloc` 假阳性

`AC_FUNC_MALLOC` / `AC_FUNC_REALLOC` 的判定依赖运行测试程序；交叉编译无法运行时
autoconf 默认判定"malloc(0) 返回 NULL"，于是 `config.h` 出现
`#define malloc rpl_malloc`，而 m17n-lib 不提供 `rpl_malloc` 实现：

```
src/face.c:549:23: error: incompatible integer to pointer conversion assigning to
                   'MGlyph *' from 'int' [-Wint-conversion]
../config.h:561:16: note: expanded from macro 'malloc'
#define malloc rpl_malloc
```

修复：预置 `ac_cv_func_malloc_0_nonnull=yes` / `ac_cv_func_realloc_0_nonnull=yes`
（glibc 与 OHOS musl 均为"malloc(0) 返回唯一指针"），并一并预置
`ac_cv_func_alloca_works` / `ac_cv_func_memcmp_working` / `ac_cv_func_strcoll_works`
避免同类运行测试在交叉场景下误判。

### 4. GUI 层无法在 configure 阶段关闭

`configure.ac` 用 `AC_ARG_ENABLE(gui, …)` 但判断的是 `$with_gui`
（`AM_CONDITIONAL(WITH_GUI, test x$with_gui != xno)`），`--disable-gui` 只写入
`enable_gui`，实际不起作用；强行传 `with_gui=no` 反而令 configure 中止：

```
configure: error: conditional "HAVE_PKG_CONFIG" was never defined.
```

因为 `PKG_PROG_PKG_CONFIG` / `AM_CONDITIONAL(HAVE_PKG_CONFIG)` 都在
`if test x$with_gui != xno` 块内。因此 GUI 源码照常编译（无外部库时也能编译通过），
其产物（`libm17n-gui.so*`、`lib/m17n/1.0/*`、`m17n-gui.pc`、`m17n-gui.h`、`m17n-X.h`）
在 `package()` 中删除。

### 5. pkg-config 搜索路径收敛

`PKG_CONFIG_PATH` / `PKG_CONFIG_LIBDIR` 都指向 conan 生成目录，只暴露已声明依赖的
`.pc`：避免把设备上碰巧存在的 libthai/anthy/wordcut 自动探测进链接串（那会引入
未声明的运行时依赖）。

### 5. config.guess 不识别 HarmonyOS（CI 实测失败 → 唯一补丁）

**CI 现象**（PR #10176 首轮构建，worker OpenHarmonyPCDeveloper-CI-012）：

```
checking build system type... config.guess: line 1613:
    .../cache/tmp/cgEBeofm/dummy.c: Permission denied
config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one
```

**根因**：OHOS 上 `uname -s` 返回 `HarmonyOS`，而 1.8.6 自带的 GNU config.guess
（timestamp 2024-07-27）没有 HarmonyOS/HongMeng 分支，于是走"uname 无法识别"的
兜底路径——在 mktemp 临时目录里编译并**执行** `dummy.c` 探测程序；该临时目录位于
worker 的 HMDFS 风格存储上，执行被拒绝（Permission denied），configure 直接中止。
注意 CI 是**设备原生**构建（`-pr:h` 与 `-pr:b` 同为 `ohos-aarch64`），conan 不会
注入 `--build/--host`，所以必须让 config.guess 自己认出来。

**修复**（补丁，唯一改动上游文件之处）：在大 case 中插入与机器无关的分支

```sh
    *:HarmonyOS:*:* | *:HongMeng*:*:*)
	GUESS=$UNAME_MACHINE-unknown-linux-ohos
	;;
```

- 输出三元组与 OHOS 工具链/conan 的 `linux-ohos` 口径一致；本包的 config.sub
  （2024-05-27）已接受该三元组（`./config.sub aarch64-unknown-linux-ohos` 回显自身），
  因此**不需要**再补 config.sub。
- 本地验证（伪 `uname` 模拟 HarmonyOS）：打补丁后 `sh ./config.guess` 输出
  `aarch64-unknown-linux-ohos`；未打补丁的同一脚本则落入 dummy.c 兜底路径并打印
  `uname` 诊断信息（在设备上即 configure 失败）。
- 补丁上下文为 `*:Minix:*:*)` / `aarch64:Linux:*:*)` 两个稳定锚点，`patch -p1` 干净应用。

> 说明：本仓库既有经验中，`--build/--host` 显式三元组是常见绕行方式，但知识库
> E205/E146/E161 明确把"用 --build/--host 绕过 config.guess"列为禁用做法（会改变
> autoconf 的 native/cross 判定、跳过运行测试），故此处采用补 config.guess 的正路。

### 5.2 configure 的辅助临时目录：umask 077 → 022（HMDFS）

修好 config.guess 后 CI 第 2 轮（构建 #48284）继续推进，configure 全部检测项通过
（`checking for xmlParseMemory in -lxml2... yes`、`checking for libxml/tree.h... yes`、
`GNU libc compatible malloc... (cached) yes` —— 前两节的修复生效），但在生成配置文件的
收尾阶段失败：

```
configure: creating ./config.status
./config.status: line 831: ./confIdBgbE/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**根因**：autoconf 生成的 configure/config.status 用
`(umask 077 && mktemp -d ./confXXXXXX)` 建辅助目录；在 worker 的 HMDFS 风格存储上，
0700 目录的 owner 受 UID 映射影响，进程无法访问/执行其中生成的辅助脚本
（知识库 E011/E533、`DRAFT-hogweed-3.9.1-ohos-config-and-recovery` 记录同一现象；
已合入的 `libthai` 配方用同一处修复通过 CI）。

**修复**：`patches/0002-configure-umask-hmdfs.patch` 把 configure 中两处
`umask 077` 改为 `umask 022`（config.status 由 configure 生成，随之继承），
辅助目录保持组/其他可读可执行。

### 6. 打包收尾：ELF 代码签名与 .pc 说明

- `package()` 末尾（所有会改动字节的步骤之后）调用 `_sign_libraries()`：
  `/data/service/hnp/bin/binary-sign-tool sign -selfSign 1` 对 `lib/*.so*` 逐个签名
  （签名覆盖文件字节，签名前先 `llvm-objcopy --remove-section .codesign`）。该工具
  仅存在于 OHOS worker，其他机器上是 no-op（E135/E077/E489）。
- 包内上游安装的 `m17n-core.pc`/`m17n-shell.pc`/`m17n-flt.pc` 沿用了 conan 构建前缀
  `prefix=/`（即 `libdir=/lib`），直接使用会指向系统路径；消费方应使用 conan 依据
  `cpp_info` 生成的 `.pc`/CMake 目标（`m17n-core`），或 `deployer` 部署到
  `~/usr/local` 后再按需改写。

## 验证结果

### CI 流水线（PR #10176，worker OpenHarmonyPCDeveloper-CI-012）

| 轮次 | 结论 | 说明 |
|---|---|---|
| 第 1 轮（构建 #48277） | ❌ | `configure: error: cannot guess build type` —— config.guess 无 HarmonyOS 分支 + dummy.c 探测被拒（§5.1），修复见 `patches/0001` |
| 第 2 轮（构建 #48284） | ❌ | configure 全部检测项通过（libxml2 后端已启用、ac_cv 预置生效），但收尾时 `confXXXXXX/subs1.awk: Permission denied`（§5.2），修复见 `patches/0002` |
| 第 3 轮 | ⏳ | 本地 W3（同补丁、同 profile 设置）已通过；设备原生结果以 PR 评论区 CI 报告为准 |

### 本地（WSL Ubuntu + Linux OHOS SDK 交叉工具链，profile 与 CI 设置一致）

```
$ conan create recipe -pr:h=ohos-aarch64-wsl -pr:b=default --build=missing
conan create exit=0
libm17n-core/1.8.6: package(): Packaged 3 '.so' files: libm17n.so, libm17n-flt.so, libm17n-core.so
libm17n-core/1.8.6: package(): Packaged 3 '.2' files: …
libm17n-core/1.8.6: package(): Packaged 3 '.0' files: …
libm17n-core/1.8.6: package(): Packaged 3 '.pc' files: m17n-flt.pc, m17n-core.pc, m17n-shell.pc
libm17n-core/1.8.6: package(): Packaged 4 '.h' files: m17n-misc.h, m17n-flt.h, m17n-core.h, m17n.h
======== Testing the package: Executing test ========
libm17n-core/1.8.6 (test package): cross build: compile and link verified only
```

制品检查（aarch64 ELF）：

| 文件 | Class/Machine | SONAME | DT_NEEDED |
|---|---|---|---|
| libm17n-core.so.0.4.2 | ELF64 / AArch64 | libm17n-core.so.0 | libxml2.so.16, libz.so, libc.so |
| libm17n.so.0.4.2 | ELF64 / AArch64 | libm17n.so.0 | libm17n-core.so.0, libxml2.so.16, libz.so, libc.so |
| libm17n-flt.so.0.4.2 | ELF64 / AArch64 | libm17n-flt.so.0 | libm17n-core.so.0, libxml2.so.16, libz.so, libc.so |

### 测试程序（原生 Linux 构建 + 真实执行）

`test_package/test.c` 在原生（glibc）构建上编译链接并运行：

```
56 checks, 0 failure(s)
RESULT: PASSED
```

覆盖：版本宏、MSymbol 符号表（interning/查询/属性）、MPlist（追加/前插/pop/长度/
按键查找）、MCharTable（默认值/赋值/范围）、MText（创建/追加/插入/删除/复制/比较/
`mtext_search`/`mtext_text`/`mtext_chr`/文本属性与属性范围），并含 U+4E2D 非 ASCII
字符的往返与 UTF-8 交叉格式比较。

## 已知限制

1. 运行时完整功能依赖独立的 `m17n-db` 数据包（编码/语言/输入法定义）；本包只提供库。
2. 泰文分词未启用 libthai（配方未声明该依赖，故 configure 走内建回退）；
   制品仓已有 `libthai/0.1.29`，需要时可在后续版本追加。
3. GUI 层未纳入（OHOS 无 X11/freetype/fontconfig/libotf）。
4. 两个上游补丁都只做平台可移植性修复（`config.guess` 的 HarmonyOS 分支、`configure`
   辅助目录 umask），不触碰任何 C 源码；包内上游 `.pc` 的 `prefix=/` 问题见 §6。
5. `test_package/test.c` 只覆盖 `libm17n-core` 的公开 API，`libm17n`/`libm17n-flt`
   仅做链接验证（本包交付物为 core；两个库的 API 属于各自任务范围）。

## 状态

`built` —— 本地 `conan create`（OHOS aarch64 交叉）+ test_package 编译链接通过；
CI 设备原生构建结果以 PR 评论 `/rebuild` 的流水线为准（首轮失败原因与修复见 §5）。
