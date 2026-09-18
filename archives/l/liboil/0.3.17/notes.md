# liboil 0.3.17 适配笔记（HarmonyOS PC / AArch64）

上游: https://liboil.freedesktop.org/（0.3.17 为末版，2009-03 发布）
tarball: download.gnome.org/sources/liboil/0.3/liboil-0.3.17.tar.gz
SHA256: 105f02079b0b50034c759db34b473ecb5704ffa20a5486b60a8b7698128bfc69
License: BSD-2-Clause（源码 COPYING，与 Gentoo 记录一致）

## 1. 上游与构建系统

- Autotools 项目（configure.ac + Makefile.am），上游无 CMake。
- 核心库零外部依赖。glib 仅 examples/uberopt 子目录使用；configure
  默认不构建 examples（SUBDIRS 条件进入），不需要 glib。
- 生成脚本齐全；实际适配直接用 tarball 自带的 generated configure
  （autoconf 2.64 产物），不走 autoreconf——本机无 gtkdocize，autoreconf
  会因 gtk-doc.m4 探测失败中止（环境缺失，非源码缺陷）。

## 2. OHOS/AArch64 适配决策

### 2.1 config.guess（E007/E011/E129 复用）

tarball 内 config.guess/config.sub 为 2009-04-27 版:
- 不识别 aarch64-ohos，且 config.guess 的 mktemp 在 HMDFS 上失败
  （E011/E129）。
- 仓库脚本 patch-autotools-ohos.pl 对 2009 版只部分生效（无
  `__ANDROID__` 锚点），不复用。
- **采用 libsmf 1.3 验证过的方案（E007）**：显式
  `--build=--host=aarch64-unknown-linux-gnu`。实测 `sh config.sub
  aarch64-unknown-linux-gnu` 接受该三元组；build==host → configure
  走原生路径。gnu_config/cci.20210814 仍作为 build_requirement 提供
  autoreconf 所需基础设施。
- 不需要 0001-config.guess.patch 类补丁 → patches 为空。

### 2.2 SIMD / CPU feature（上游架构条件，无需补丁）

`m4/as-host-defines.m4` 的 AS_HOST_DEFINES 按 host_cpu 精确匹配
（i386/amd64/arm/powerpc/motovec 各自的 case），据此:

| 上游目录 | CPU 特性 | AArch64 下 |
|---|---|---|
| liboil/i386, i386_amd64, amd64 | MMX/SSE/SSE2/3DNow/CMOV 汇编 | 不进 SUBDIRS |
| liboil/arm | ARM VFP 汇编 | 不进 SUBDIRS |
| liboil/powerpc, powerpc_asm_blocks | AltiVec | 不进 SUBDIRS |
| liboil/motovec | Motorola AltiVec | 不进 SUBDIRS |
| liboil/c, colorspace, conv, copy | 纯 C 参考实现 | 正常构建 |

- CPU 特性检测：aarch64 下只编译 liboilcpu-misc.c（空 getcpu_flags
  回退），不会执行 x86 CPUID/SIGILL 探测 → 无 SIGILL 风险。
- **结论**：x86 专用代码是上游 autotools 按 host_cpu 的自然排除，
  不是"为 OHOS 禁用核心功能"，E016（禁用汇编补丁）不适用，零补丁。
- liboil 主体 C 代码无内联汇编 x86-only 段（核对 liboil/*.c：内联
  汇编只出现在上述被排除目录）。

## 3. 上游测试清点（testsuite/Makefile.am，共 19 个 TESTS）

`programs =`（TESTS = $(programs)，check_PROGRAMS 同集）:
align, moo, introspect, proto1, proto2, test1, proto3, proto4, stride,
dso_check, abs, md5, md5_profile, trans, copy, zigzag, mmx_engine,
stack_align, double_catch — 共 19 个。
另 `list_impls` 为 noinst_PROGRAMS（编译但不属于 TESTS 清单）。

| # | 测试 | 架构性质 | AArch64/OHOS 行为 |
|---|------|---------|------------------|
| 1 | abs | 无关 | 真实运行 |
| 2 | align | 无关（malloc 对齐） | 真实运行 |
| 3 | copy | 无关 | 真实运行 |
| 4 | double_catch | x86/ppc 条件 | 无 HAVE_I386/HAVE_POWERPC → 打印"不支持"分支正常退出（上游正式处理路径），真实运行 |
| 5 | dso_check | 无关（DSO 符号迭代） | 真实运行 |
| 6 | introspect | 无关 | 真实运行 |
| 7 | md5 | 无关（含已知向量核对） | 真实运行 |
| 8 | md5_profile | 无关 | 真实运行 |
| 9 | mmx_engine | x86-only 主体 | `#if defined(HAVE_I386)\|\|defined(HAVE_AMD64)` 包裹 → 空壳 main，真实运行（输出即上游非 x86 预期） |
| 10 | moo | 无关 | 真实运行 |
| 11 | proto1 | 无关 | 真实运行 |
| 12 | proto2 | 无关 | 真实运行 |
| 13 | proto3 | 无关 | 真实运行 |
| 14 | proto4 | 无关 | 真实运行 |
| 15 | stack_align | 无关（栈对齐数值断言） | 真实运行 |
| 16 | stride | 无关 | 真实运行 |
| 17 | test1 | 无关 | 真实运行 |
| 18 | trans | 无关 | 真实运行 |
| 19 | zigzag | 无关 | 真实运行 |

架构判定方法：对 19 个测试源码 grep `HAVE_I386|HAVE_AMD64|
HAVE_POWERPC|HAVE_ARM|__i386__|__amd64__|__powerpc__|__MMX__|__SSE__`
——17 个零命中（架构无关），仅 mmx_engine 与 double_catch 含条件
编译（两者的源码已全文阅读判定，见 conanfile.py test() 注释）。
- 19 个全部进入 `make check` 真实执行，0 个 skip，0 个因适配被禁用。
- mmx_engine/double_catch 的"空壳/不支持分支"是上游对非 x86/ppc 的
  编译期设计，非本次适配行为；其余 17 个为完整功能测试。

## 4. test_package 设计

- CMake + 源码 consumer（对齐 libsmf 1.3 / orc 0.4.42 格式）。
- 真实 API 调用做确定性计算并核对：
  - `oil_init()` → `oil_splat_u32`（u32 数组填充）→ 断言逐元素相等；
  - `oil_sum_f64`（浮点求和）→ 与 C 参考值精确比对；
  - `oil_copy_u8`（字节拷贝）→ memcmp 全等；
  - `oil_md5`("liboil md5 test\n") → 与独立计算的 MD5 十六进制比对；
  - `oil_abs_f32_f32` → 断言负数取绝对值结果。
- OHOS 专项：
  - ELF64 AArch64 检查（readelf -h: Class ELF64 / Machine AArch64）；
  - shared 下 NEEDED 无 x86-only 依赖、无宿主路径 RPATH/RUNPATH、
    SONAME 核对；
  - static 下 liboil-0.3.a（上游静态库名带版本后缀）存在且成员
    AArch64 ELF；consumer 无 liboil NEEDED（真实静态链入）。
- test() 显式 `self.run(...)`（oil_consumer + readelf/ar 管道，
  env="conanrun"），断言失败即非零退出；无 echo/true/stub。

## 5. 正式 conan create 结果（ohos-aarch64 profile，build==host 原生）

命令：`conan create archives/l/liboil/0.3.17 -pr:h ohos-aarch64
-pr:b ohos-aarch64 --name=liboil --version=0.3.17 -o '&:shared=…'`

| 模式 | rc | make check | test_package |
|---|---|---|---|
| shared=True | 0 | 19/19 PASS | 10 项 API 检查 + ELF 检查全过 |
| shared=False | 0 | 19/19 PASS（含 static-only 修复后） | 10 项 API 检查 + ELF 检查全过 |

- 上游 19 个 TESTS 全部真实执行、全部 PASS（无 skip、无禁用）。
- test_package 的 test() 用真实 `self.run()`：先跑 oil_consumer
  （10 项断言，失败非零退出），再跑 readelf/ar ELF 检查管道。
- ELF 检查结果：shared `liboil-0.3.so.0` 为 ELF64 AArch64，
  SONAME `liboil-0.3.so.0`，NEEDED 仅 `libc.so`；consumer NEEDED
  为 `liboil-0.3.so.0 + libc.so`，无 RPATH/RUNPATH。static
  `liboil-0.3.a` 成员为 ELF64 AArch64 对象，consumer 无 liboil
  NEEDED（真实静态链入）。无 x86-only 指令/依赖（架构目录未编译）。
- 关键教训：`-pr:b default`（x86_64）+ `-pr:h ohos-aarch64` 会被
  Conan 判定为交叉构建；本机是 aarch64 HarmonyOS PC，原生执行
  须用 `-pr:b ohos-aarch64`。且 `can_run()` 在 profile 组合不同时
  恒 False，会静默跳过 test()——本机原生场景不要用它。

### 5.1 上游 static-only 构建缺陷（与 OHOS 无关，非新 OHOS 根因）

- 现象：`--disable-shared` 时 6/19 测试（dso_check/abs/md5/
  md5_profile/copy/zigzag）在输出后 SIGSEGV。
- 根因：`liboil/Makefile.am` 的 `liboilarray.c` 规则（oil_init 的
  类注册表 `_oil_function_class_array[]`/`_oil_function_impl_array[]`）
  从 `.libs/liboiltmp1.exp` 生成，而该文件只由 libtool 在链接
  **shared** liboiltmp1.la 时产出。static-only 下 `.exp` 不存在 →
  数组退化为 `{NULL}` → `oil_init()` 注册 0 个类 → 测试经空
  `klass->func` 间接调用崩溃。x86 static-only 同样会触发。
- 修复（conanfile.py `_make_static_export_file`）：static 构建时先
  `make -C liboil all`，再从 `.libs/liboiltmp1.a` 用 `nm` 按上游
  `-export-symbols-regex 'oil_'` 的同一符号集（实测 417 class +
  867 impl，与 shared `.exp` 完全一致）重建 `liboiltmp1.exp`，删掉
  空壳 `liboilarray.c` 让上游规则重新生成完整数组。
- 该缺陷是上游构建系统问题，不是 OHOS 特有根因 → 不建知识库
  DRAFT（普通构建缺陷不满足"OHOS 可复用根因"标准）。

## 6. 知识库决策

复用: E007（显式 host/build 三元组，libsmf 先例）、E011/E129
（HMDFS mktemp → 不跑 config.guess，umask 077→022 补丁同 libsmf）。
无新可复用 OHOS 根因 → **路径 A**（不建 DRAFT）。
"AArch64 下上游 x86 汇编目录自然不编译"属上游架构条件，不算新知识；
static-only `.exp` 缺失是上游构建缺陷，同样不算 OHOS 知识。
