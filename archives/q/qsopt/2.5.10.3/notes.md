# qsopt 2.5.10.3 适配笔记

## 概述

QSopt_ex（jonls/qsopt-ex，tag v2.5.10.3）是 QSopt 精确有理数线性规划求解器（David Applegate / William Cook / Sanjeeb Dash / Daniel Espinoza 的 QSopt_ex 算法实现，Jon Lund Steffensen 维护的现代 autotools 版本）。纯 C 库 `libqsopt_ex`，用 GMP 有理数做精确算术求解 LP 问题，是最小化/最大化线性规划的标准库。

本包以**库类型**适配（ARCHIVE-SPEC R38）：只交付静态库 + 头文件；上游 `esolver` 交互式演示程序不安装（库类型无需 commands.json）。

## 编译环境

- 构建系统: autotools（tag tarball 为 autoreconf 源，无预生成 configure）
- 编译日期: 2026-09-27
- 编译器: clang（macOS 原生验证）/ OHOS SDK clang（ohos-local 交叉验证）
- 状态: built
- 依赖: gmp/6.3.0（必需，configure 硬性检查）、zlib/1.3.1、bzip2/1.0.8（上游 Debian/Fedora 均启用，本包显式声明保证确定性）

## 编译步骤

1. `python3 scripts/ohc-run.py init-build qsopt 2.5.10.3 --url=<官方 GitHub tag URL>`（下载官方 v2.5.10.3 tarball，SHA256 ca221aac…664bf，与 Debian orig 包字节一致）
2. 本地探索编译（work 目录）：
   - `./bootstrap`（autoreconf + libtoolize；本机需 GNU libtool，安装自 TUNA 镜像，`glibtoolize` 符号链接以适配 autoconf 2.73 的 Darwin 行为）
   - `./configure --enable-static --disable-shared --with-pic && make -j1 && make check`（原生 macOS 验证构建系统 + 上游 TAP 套件）
3. Conan 配方（`conanfile.py`）关键点：
   - `generate()`: AutotoolsToolchain；OHOS 追加 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`（vendor 位非空，否则 libtool `case $host_os in linux*)` 匹配不到 ohos，只能产出静态库；libopendbx 同款已发布先例）
   - 交叉视角下 AC_RUN_IFELSE 探针无法执行：pin `ac_cv_func_malloc_0_nonnull` / `ac_cv_func_realloc_0_nonnull` / `ac_cv_func_memcmp_working` / `ac_cv_func_strtod` = yes（否则 configure 会定义上游未实现的 rpl_malloc/rpl_memcmp/rpl_strtod，导致链接失败）
   - AutotoolsToolchain 不聚合依赖 cpp_info：gmp/zlib/bzip2 的 `-I/-L` 经 `extra_cflags`/`extra_ldflags` 手动注入，保证 AC_CHECK_LIB 命中
   - `build()`: 无 configure 则先 `autotools.autoreconf()`；随后对生成的 config.sub 做幂等 OHOS 三元组补丁（仅当不识别 linux-ohos 时，E072/E122 三处修改：basic_os 映射 + OS 白名单 + kernel-os 白名单）；`can_run` 时执行 `make check`（上游 TAP 套件）
   - `package()`: `autotools.install()` 后移除 bin/esolver 与 *.la；`cpp_info.libs=["qsopt_ex"]`，`system_libs=["m","pthread"]`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bootstrap 报 `undefined or overquoted macro: AC_PROG_LIBTOOL` | 本机无 GNU libtool，aclocal 找不到 libtool.m4 | TUNA 镜像源码安装 libtool 2.4.7 到 `$HOME/usr/local`，设 `ACLOCAL_PATH` |
| 2 | autoreconf 报 `Can't exec "glibtoolize"` | autoconf 2.73 在 Darwin 上优先调 glibtoolize | `ln -s libtoolize glibtoolize`（Homebrew libtool 命名惯例） |
| 3 | init-build 挂起 | 直连 github.com 被网络阻断，无超时重试 | 改用 gh-proxy 镜像 URL 初始化并完成全部验证；conandata.yml 最终提交只含官方源（R39，镜像回退由 CI 自动添加） |
| 4 | 旧 automake 生成的 config.sub 可能不认 linux-ohos | automake <1.16.x 无 ohos 条目（E072/E122） | build() 中幂等补丁生成的 config.sub；本机 automake 1.18.1 已原生支持（`config.sub aarch64-unknown-linux-ohos` → OK） |
| 5 | 交叉视角 configure 无法运行 AC_RUN_IFELSE | --build/--host 使 autoconf 判定为交叉编译 | pin 4 个 ac_cv_* 缓存变量（见编译步骤 3） |
| 6 | OHOS 共享库探测需要 SDK libc++ 搜索路径 | libtool 共享探测链接 libc++ 失败 → 判定 static-only | 仅在 shared=True 时注入 SDK llvm/lib -L（当前默认静态，不触发） |
| 7 | CI worker 上 `autoreconf` 失败：`Can't exec "aclocal": No such file or directory` | CI OHOS worker 装有 autoconf（/data/service/hnp/autoconf.org/autoconf_2.72）但无 automake（aclocal 不在 PATH）；tag tarball 不含生成 configure，build() 原方案在构建期 autoreconf | 本地用 autoconf 2.73 + automake 1.18.1 + libtool 2.4.7 一次性生成 configure/Makefile.in/aclocal.m4/config.h.in/ltmain.sh 与 aux 文件（compile/depcomp/install-sh/missing/config.sub/config.guess/test-driver）及 libtool m4 宏，随配方 `autotools/` 携带（等同上游 release tarball 惯例）；build() 检测到无 configure 时还原携带文件，并把 tarball 的 configure.ac/m4/*.m4 与携带的 m4 宏回拨到 2000-01-01（内容不变仅 mtime），使 automake 维护者规则永不触发 aclocal/automake 重生成（缺 m4/libtool.m4* 依赖时 make 会无条件重建 aclocal.m4）；configure 保留正常 mtime（其自检要求"新建文件比分发文件新"，回拨仅作用于输入文件，不冲突）。autoreconf 仅保留为兜底（携带文件也被移除时） |
| 8 | CI 上 configure 全绿后 config.status 失败：`./confXXXXXX/subs1.awk: Permission denied`，随即 "could not setup config files machinery" | **HMDFS 强制 setgid 并重映射属主 UID**：config.status 以 `umask 077` 创建临时目录，落在 HMDFS 上变成 `drwx--S---`，连属主也读/写不了，awk 替换机制读 subs1.awk 即 EACCES（configure 自身探针不受影响，故此前 60 多秒全部通过） | 按仓库 E011/E114 标准解法（948 个 autotools 归档同型，先例 `roll/2.7.0`、`a52dec/0.7.4`）修改携带的 configure：临时目录创建去掉两处 `umask 077`（`mktemp -d` / `mkdir`），内容单处、无平台宏；config.status 由 configure 运行时生成，patch configure 即同时修复生成的 config.status。本包 configure 为携带产物，直接内嵌修复（等同 roll 的 0001-configure.patch，只是打在携带文件而非 tarball） |

## 源码修改

| 补丁 | 修改 | 原因 |
|------|------|------|
| patches/0001-trace-h-ndebug-iftrace2.patch | trace.h NDEBUG 分支：重复的 `#define ILL_IFTRACE` 改为 `#define ILL_IFTRACE2` | 上游 bug：NDEBUG 下漏定义 ILL_IFTRACE2，Release（-DNDEBUG）构建 dstruct.c/simplex.c/ratio.c（及模板生成变体）编译失败；Release 为默认构建类型，CI 同样会触发 |

其余 OHOS 兼容全部在 conanfile.py 构建期处理：携带的生成 autotools 文件还原、config.sub 幂等补丁、探针 pin、依赖注入——均可在 PR 审查中复现验证。

## 依赖版本

- gmp/6.3.0（ohpcd 制品仓，发布版）
- zlib/1.3.1（ohpcd 制品仓，发布版）
- bzip2/1.0.8（ohpcd 制品仓，发布版）
- 构建工具：autoconf 2.73 / automake 1.18.1 / libtool 2.4.7（本机）；CI worker 自带工具链

## 验证结果

```bash
# 1) 原生 macOS（conan create, default profile）：
#    make check → tests/test_qs TAP 8 项全过（上游套件）
#    test_package → ./test 输出 PASS: exact optimum = 42
# 2) OHOS 交叉（conan create, -pr:h=ohos-local）：
#    libqsopt_ex.a 交叉编译成功（静态链接 gmp），can_run=False 跳过 make check/消费者 ./test
#    鸿蒙特有测试 ohos_platform_check.sh 独立于 can_run 执行 → H1/H2 全过（见下）
# 3) 上游测试清点（R51 三步法）：
#    ① Makefile.am: TESTS = tests/test_qs（TAP 套件）+ tap-driver.sh
#    ② tests/test_qs.c（TAP 8 项）、eg_sloan.c（noinst 演示程序，非测试）
#    ③ 仓库 .travis.yml 曾跑 make check（上游 CI 同源测试）
```

## 测试计数口径（统一：独立检查项数）

- **上游**：8 项 —— make check TAP 套件原生报告的 test case 数（tests/test_qs.c，1..8 ok）
- **鸿蒙特有测试**：2 项 —— test_package/ohos_platform_check.sh 的 H1/H2：
  - H1：libqsopt_ex.a 目标对象为 ELF64 AArch64（OHOS armv8 ABI 适配点，对应
    `--host=aarch64-unknown-linux-ohos` 三元组）
  - H2：库内无 rpl_malloc/rpl_realloc/rpl_memcmp/rpl_strtod 符号引用（AC_FUNC
    探针 pin 生效，对应 4 个 ac_cv_* 缓存变量）
- **test_package 消费者断言**：2 项（test.c：QS_LP_OPTIMAL + 精确最优值 42/1）——
  作为 L1 消费者验证证据，不计入鸿蒙特有口径（rule12：test_package 不自动计入，
  仅 ohos_platform_check.sh 的独立检查项计入）
- 全链路数字与 MANIFEST.yml / PR 表格一致（上游 8 + 鸿蒙 2 = 10，+2）

鸿蒙特有测试日志（OHOS 交叉 conan create 实测输出）：
```
qsopt/2.5.10.3 (test package): RUN: sh .../test_package/ohos_platform_check.sh .../libqsopt_ex.a
PASS: H1: archive member ... is ELF64 AArch64 (OHOS armv8 ABI)
PASS: H2: no rpl_malloc/rpl_realloc/rpl_memcmp/rpl_strtod in library (probe pins effective)
ALL PASS: ohos_platform_check (2 checks)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Autotools 配方（OHOS 适配逻辑 + 依赖注入 + 幂等 config.sub 补丁） |
| conandata.yml | 官方源（R39 单 URL）+ SHA256；本地验证期间使用与官方 tarball 字节一致的 gh-proxy 镜像（sha256 相同） |
| test_package/ | test.c（与上游 test_qs.c 同源 LP，断言最优值精确 42）+ ohos_platform_check.sh（鸿蒙特有测试 H1/H2）+ conanfile.py + MANIFEST.yml |
| manifest.yaml / README.md | 软件级 + 版本级元数据 |

## 注意事项

- 本包默认**静态库**（shared=False 默认，与 gmp 同款）；如需共享库，`-o qsopt/*:shared=True` 时注意 OHOS 需 SDK llvm/lib -L（配方已内置探测逻辑）
- GMP 为硬依赖，无法禁用（configure AC_MSG_ERROR）；这与上游设计一致
- esolver 演示程序刻意不打包（库类型，R38）；需要 CLI 工具形态可后续单独适配
- test_package 断言精确最优值 42/1（有理数精确解），验证的是"精确求解"而非浮点近似——这是本库区别于普通 LP 库的核心卖点
