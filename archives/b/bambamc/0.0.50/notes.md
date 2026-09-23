# bambamc 0.0.50 适配笔记

## 编译环境
- 构建系统: autotools（上游 tag tarball 不含生成的 configure，需 autoreconf 自举）
- 编译日期: 2026-09-11
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`）
- 平台: OHOS aarch64（`uname -s` = HarmonyOS，kernel HongMeng 1.12.0）
- 状态: built
- 工具链: conan 2.29.1、GNU Make 4.4.1、autoconf 2.73 / automake 1.18.1 / libtool 2.6.2、pkg-config 0.29.2
- 依赖: zlib/1.3.1.1（OHOS armv8 binary），tool_requires automake/1.18 + libtool/2.5.4

## 编译步骤

配方 `build()` 的顺序是有约束的，不能调换：

```bash
# 1) 先把随配方携带的 pkg.m4 放进源码树 m4/（configure.in 声明了 AC_CONFIG_MACRO_DIR([m4])）
cp <export_sources>/m4-pkg.m4 <source>/m4/pkg.m4
# 2) 自举：tag tarball 无 configure/aclocal.m4/config.guess
autoreconf --force --install
# 3) config.guess/config.sub 的 OHOS 变换必须在 autoreconf 之后（否则被 autoreconf 覆盖）
#    -> patches/0001、patches/0002
# 4) 生成 configure 后把 config.status 的 umask 077 归一化为 022（HMDFS 权限）
./configure --prefix=<pkg> --enable-static --disable-shared
make -j1
# 5) 上游测试（make check 是空套件，真实入口是两个 assert 程序）
src/bamwritertest > bamwritertest.bam
src/bamreadertest < bamwritertest.bam
```

`conan create` 命令（与采信轮一致）：

```bash
conan create archives/b/bambamc/0.0.50 --user=ohpcd --channel=stable \
  -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<repo>/ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./configure[14127]: PKG_PROG_PKG_CONFIG: inaccessible or not found` + `syntax error: unexpected 'zlib,zlib'` | `PKG_PROG_PKG_CONFIG`/`PKG_CHECK_MODULES` 定义在 pkg-config 的 `pkg.m4`，该文件不在 aclocal 隐式搜索路径（设备装在 `/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal/`）→ 宏未展开原样残留被 /bin/sh 当语法 | 配方 `export_sources` 携带 `m4-pkg.m4`，`build()` 内先拷到 `<source>/m4/pkg.m4` 再 autoreconf（同已合入的 libfyaml 0.9.6 做法） |
| 2 | `configure: error: cannot guess build type; you must specify one` | 上游仓不含 `config.guess`；autoreconf 现场生成的是 automake/autoconf 自带的 2024-07-27 版，无 HarmonyOS 分支；本机 `uname -s` 就是 `HarmonyOS` | 按仓内 `scripts/patch-autotools-ohos.pl` 的 config.guess/config.sub 变换生成 `patches/0001`、`patches/0002`，在 autoreconf **之后**应用；产出标准三元组 `aarch64-unknown-linux-ohos`。config.guess 只取该脚本的 HarmonyOS 主 case 一处（不取 `__OHOS__` LIBC 分支），理由见下文「关于 `__OHOS__` 平台宏」 |
| 3 | `./config.status[977]: can't create ./confwdcjHD/subs1.awk: Permission denied` + `could not setup config files machinery` | autoconf 的 `config.status` 模板用 `umask 077 && mktemp -d`，HMDFS 下该目录对创建者自身不可写 | 生成 configure 后把 `umask 077` 替换为 `umask 022`；配方内保留锚点断言，模式消失即报错而不是静默跳过 |
| 4 | `ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'; recompile with -fPIC`（链接 `libbambamc.so` 时） | 依赖 `zlib/1.3.1` 的 OHOS 二进制是**非 PIC** 静态库（其配方未注入 `-fPIC`）；其 `zutil.o` 对全局 `z_errmsg` 用 `ADR_PREL_PG_HI21`。`zlib/1.3.1`、`zlib/1.3.1.1`、`zlib/1.3.2` 三者在本 profile 下是**同一个 package_id**（`6b129b06…`），而后两者注入了 `CFLAGS="-fPIC -O2"` 故为 PIC——`package_id` 不编码 CFLAGS | 配方 `requirements()` 固定 `zlib/1.3.1.1`（PIC 变体）；判定方法（必须用 `conan cache path <ref>:<pid>` 精确解析，禁用目录通配）与三方对照证据见 `reports/conan-verify-supplement.md` 与知识草稿 DRAFT-E2188 |
| 5 | 上游测试程序是 `assert` 自检式，Release profile 会全部编译掉 | `AutotoolsToolchain` 对 Release/RelWithDebInfo/MinSizeRel 默认注入 `-DNDEBUG`；上游 `--enable-fast` 默认 `no`（即断言开启），Conan 默认与其相反 | 配方内 `tc.ndebug = None`，使断言保持启用；实测 `nm` 可见 `__assert_fail` 未定义符号 |
| 6 | 源码中直接用 `<zlib.h>` 的翻译单元找不到头文件（AutotoolsToolchain 场景） | `AutotoolsToolchain` 不把依赖 `cpp_info` 翻译成 `CPPFLAGS`/`LDFLAGS`；上游 `src/Makefile.am` 只消费 `CPPFLAGS`（`ZLIBCPPFLAGS` 来自 .pc 但未被任何规则引用） | `generate()` 中显式 `AutotoolsDeps(self).generate()` 补齐依赖头/库路径 |
| 7 | `make check` 什么都不跑 | 上游 `src/Makefile.am` 只有 `noinst_PROGRAMS`，没有 `TESTS`/`check_PROGRAMS` 注册（`grep -n '^TESTS\|^check_PROGRAMS' src/Makefile` 无命中） | 配方在 `build()` 内显式运行两个测试程序，并校验输出：非空 + gzip magic `1f 8b` + 解压后 `BAM\1`；同时写入 MANIFEST.yml 的 `upstream_not_compiled` 说明被注释掉的 `lineBufferTest`/`samBamSamTest` |

## 源码修改

无源码补丁。两个补丁只改 autoconf 现场生成的辅助脚本：

1. `patches/0001-config-guess-harmonyos.patch` — 给 autoreconf 生成的 `config.guess` 增加
   `*:HarmonyOS:*:*` 主 case 分支（按 `$UNAME_MACHINE` 归一化机器名），输出
   `aarch64-unknown-linux-ohos`。
2. `patches/0002-config-sub-harmonyos.patch` — 给 autoreconf 生成的 `config.sub` 增加
   `ohos-linux)` 基本系统名映射，使 `linux-ohos` 三元组通过合法性校验。

两个补丁**没有**使用 `--build`/`--host` 三元组绕过平台探测（native 编译）。

### 关于 `__OHOS__` 平台宏（R8）

仓内标准脚本 `scripts/patch-autotools-ohos.pl` 的 config.guess 变换含两处：`__OHOS__`
LIBC 探测分支 + `*:HarmonyOS:*:*` 主 case 分支。本包**只采用后者**：

- 本包构建环境的 `UNAME_SYSTEM` 就是 `HarmonyOS`，主 case 分支在 LIBC 相关分支之前命中并
  直接赋 `GUESS=`，`LIBC` 变量在该路径上从不被读取；
- 实测（2026-09-11，设备）：对同一份 autoreconf 产物只打主 case 一处，
  `./config.guess` 输出 `aarch64-unknown-linux-ohos`（rc=0），`./config.sub "<该三元组>"`
  同样通过；与两处都打的产物逐字节比对，config.guess 的目标内容一致；
- 因此 `__OHOS__` 分支对本包**无功能作用**。按 R8「平台条件编译默认禁止、优先运行时探测」，
  去掉它使补丁不含任何平台条件编译，同时避开 CI PF5 的 patches 平台宏闸。

## 依赖版本

| 依赖 | 版本 | 角色 | 说明 |
|------|------|------|------|
| zlib | 1.3.1.1 | host requires | OHOS armv8 binary，静态 `libz.a`，**PIC**（下游可吸收进 DSO） |
| automake | 1.18 | tool_requires | 提供 aclocal/automake，autoreconf 自举所需（CI 干净环境无系统 automake） |
| libtool | 2.5.4 | tool_requires | 提供 libtoolize/ltmain.sh，autoreconf 自举所需 |

## 验证结果

```bash
# 上游测试（build() 内，采信轮 reports/conan-create-log.md）
$ src/bamwritertest > bamwritertest.bam      # rc=0，186 字节，gzip magic 1f 8b，解压后 BAM\1
$ src/bamreadertest < bamwritertest.bam      # rc=0
$ # 配方输出： [ok] upstream tests: bamwritertest 186 bytes BGZF/BAM, bamreadertest rc=0

# test_package 消费者往返（28 项断言）
$ ./test_bambamc consumer_roundtrip.bam
bambamc consumer round-trip: 28 checks, 0 failures

# 静态库 -> DSO -> dlopen 三跳
$ ./driver ./libbambamc_probe.so
dlopen probe: bambamc_probe_ok() = 1          # rc=0

# 安全属性（消费者 PIE）
$ readelf -h test_bambamc | grep Type          # DYN (Position-Independent Executable file)
$ readelf -lW test_bambamc | grep -E 'GNU_STACK|GNU_RELRO'   # RW(NX) + RELRO
$ readelf -dW test_bambamc | grep -E 'FLAGS'   # BIND_NOW / NOW PIE

# 可复现性（两轮清缓存，30 个归档成员的可分配节聚合指纹）
342d5a0e1a5c617e5441c72bdc128d3292e42ebd25a2c2825eca8377ba66d74c   # 两轮一致
```

- `conan-verify`：`reports/conan-verify-report.md` verdict=PASS（G0-G3 实跑）。
- G4/L2/L4/L5 在工具里走了「⏭️ 跳过（无 cache 路径）」分支，已按 workflow §7.2 人工补测，
  证据在 `reports/conan-verify-supplement.md`。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `lib/libbambamc.a` | 156 KB | 静态库（PIC），`ar` 成员 30 个 |
| `include/bambamc/*.h` | 36 个 | 上游 `libbambamc_include_HEADERS` 全量 + 生成的 `BamBam_Config.h` |
| `lib/pkgconfig/bambamc.pc` | — | 已去掉打包机绝对 `-L` 路径，`Requires: zlib` |
| `licenses/COPYING`、`licenses/GPLv3` | — | GPL-3.0-or-later |

## 注意事项

- 包的 `package_type` 是 `library`，默认 `shared=False`。若下游把本静态库链进共享对象，
  依赖必须是 PIC 变体：`zlib/1.3.1.1` 或 `zlib/1.3.2` 都可以，**不要**用 `zlib/1.3.1`。
  三者在 OHOS profile 下 package_id 完全相同（`6b129b06…`），但 `zlib/1.3.1` 的配方未注入
  `-fPIC`，其 `libz.a` 吸收进共享对象时会以 `R_AARCH64_ADR_PREL_PG_HI21` 报错。
  判据：`P=$(conan cache path "zlib/1.3.1:6b129b06…"); ar p "$P/lib/libz.a" zutil.o | readelf -r /dev/stdin | grep -A1 z_errmsg`
  （详见知识草稿 DRAFT-E2188）。
- 上游源码树里 `src/test/bamreadertest.c` 的 `lineBufferTest()` / `samBamSamTest()`
  在 `main()` 中是被注释掉的（源码第 141-142 行），既不算 PASS 也不算 SKIP，已单列在
  `test_package/MANIFEST.yml` 的 `upstream_not_compiled`。
- 上游 tar 包**不含** `configure`，因此任何绕过 `build()` 直接读 `source()` 产物的做法都会
  拿到不可 configure 的源码树；验证时以 `reports/conan-create-log.md` 里的 `RUN: autoreconf` 行为准。
