# COIN-OR 大 tarball 捆绑依赖子树的 x86 ISA 头：字面 grep 判据与构建面的系统性偏差，以及外部依赖 flags 模式的防触达机制

> Draft: DRAFT-BCP-144-COINOR-BUNDLED-X86-INTRINSICS-EXTERNAL-FLAGS
> Stem: `bcp-1.4.4-coinor-bundled-x86-intrinsics` — pairs with the same-stem `.kv`
> 知识号: E693

## 基本信息

- **ID**: DRAFT-BCP-144-COINOR-BUNDLED-X86-INTRINSICS-EXTERNAL-FLAGS
- **严重度**: 2
- **类别**: portability|build-system|ohos-platform
- **触发工具**: grep|clang|configure|conan
- **阶段**: precheck|configuration|compilation

## 错误特征

两层形态，按层判读：

1. **预检层（多数情况，不报错）**：W0 平台可移植性判据对整个源码树做
   `grep -E 'altivec|mmx|3dnow|mmintrin|arm_neon|immintrin'` 字面扫描，
   在 COIN-OR 捆绑式大 tarball（Bcp/Cbc/Clp 系）上必然命中捆绑子树，
   看起来像「命中即止损」，实际命中面与构建面是两个集合。
2. **强制层（若捆绑子树真被编译，必炸）**：
   ```
   .../include/immintrin.h:14:2: error: "This header is only meant to be used on x86 and x64 architecture"
   .../include/hresetintrin.h:42:27: error: invalid input constraint 'a' in asm
   __asm__ __volatile__("cpuid" : "=a"(ax) ...): error: invalid output constraint '=a' in asm
   ```
   设备一手探针（aarch64 clang15 `aarch64-unknown-linux-ohos`）rc=1。

## 根因分析

COIN-OR release tarball 的 `Dependencies` 文件声明硬依赖，但**同时把全部依赖
子树捆进 tarball**（Bcp-1.4.4 捆绑 CoinUtils/、Osi/、Vol/、Clp/、Cgl/ 五个目录）。
捆绑子树是历史 x86 时代代码：

- `Clp/src/ClpSimplexDual.cpp:3556` 与 `Clp/src/ClpPackedMatrix.cpp:6753`
  在 `#ifdef _MSC_VER … #else` 分支**无条件** `#include <immintrin.h>`
  （不是 AVX 宏守卫）；
- prefetch/cpuid x86 asm 分别在 `#ifdef COIN_PREFETCH`（CoinAbcHelperFunctions.hpp:515
  的定义本身被注释 = 默认关）与 `#if 0` 死块里；
- 其余 immintrin 命中在 `#if AVX2 == 1/2/3` 守卫内（AVX2 未定义 → 全部跳过）。

于是形成**系统性偏差**：字面 grep 是对「源码树」的判据，而平台可移植性真正
要判的是「构建面」（实际会进编译命令的文件集合）。捆绑子树命中 ≠ 构建面命中；
Bcp 自身子树（Bcp/、Applications/）命中 0、glibc printf 钩子族命中 0。

防触达机制（外部依赖 flags 模式，同已发布 coinor-cbc 2.10.13 先例）：

1. 直接驱动子包 `Bcp/configure`，给 `--with-clp-incdir/--with-clp-lib`、
   `--with-vol-*`、`--with-cgl-*` → 旧式 `AC_COIN_CHECK_PACKAGE` 的 flags 分支
   直接置 `coin_has_*=yes`，跳过 pkg-config 与 bundled 检测；
2. 顶层 `configure` 只在 bundled 分支才 `subdirs="$subdirs Clp"`（Bcp tarball
   顶层 configure:21245 实证）；`Bcp/Makefile.am` 的 `SUBDIRS = src`；
   → flags 模式下 5 个捆绑子树**一个都不进编译面**；
3. 头文件改由合并 staging 的 `-I` 提供（五包 `include/coin` 合一），链接串
   按「依赖方在前」直连 `.a` 绝对路径（已发布包 `.la` 固化 `libdir='//'`）。

## 三步裁量判据（替代「命中即止损」的字面执行）

1. **命中归类**：按目录把 grep 命中分桶——Bcp 自身/捆绑子树/死块守卫
   （`#if 0`、注释掉的宏定义、未定义的条件宏）；
2. **一手探针定性**：把命中头/asm 抽成最小 `.c` 在设备编译，拿到 rc=1 的
   实证（不是推测）；
3. **configure 机制实证**：读 flags 分支与 `subdirs` 追加条件，确认「外部依赖
   即不进 SUBDIRS」；构建后**自证**——configure/编译日志不得出现捆绑子树
   （`Clp/` 等）的编译行。

三步全过 → 判「命中不在构建面」不止损；任一步不过（尤其被迫 `--with-bundled`
或外部依赖不可得时）→ 转强制路径，按止损上报。

## 复现命令（设备可执行，全部落 $TASK_DIR 下，不用 /tmp）

```sh
# 0) 预检层：命中归类（第一段目录为分桶键）
D="$HOME/tmp/bcp-1.4.4/src/extract/Bcp-1.4.4"
grep -rIlnE 'altivec|mmx|3dnow|mmintrin|arm_neon|immintrin' "$D" \
  | sed "s|$D||" | cut -d/ -f1 | sort | uniq -c
# 期望：命中只出现在 Clp/（捆绑子树），Bcp/ 为 0

# 1) 强制层：一手编译探针（aarch64 clang15，期望 rc=1 与 #error x86 only）
mkdir -p "$HOME/tmp/bcp-1.4.4/w0"
printf '#include <immintrin.h>\nint main(void){return 0;}\n' \
  > "$HOME/tmp/bcp-1.4.4/w0/probe_isa.c"
clang -c "$HOME/tmp/bcp-1.4.4/w0/probe_isa.c" \
  -o "$HOME/tmp/bcp-1.4.4/w0/probe_isa.o"; echo "rc=$?"

# 2) 防触达自证：构建日志里不得有捆绑子树编译行
grep -nE '(^| )Clp/[^ ]*\.(cpp|c)' <conan-create 日志> | head; echo "hits_rc=$?"
```

## 处置建议

见 `.kv` 的 `rec_description`：默认走外部依赖 flags 模式（防触达），配合三步
裁量判据做 W0-3 定性；把裁量登记进 `notes.md` 问题表（4 文件路径 + 探针读数 +
防触达机制 + 复发条件），并把「W0-3 是全仓字面扫描、与构建面有系统性偏差」
写进反馈（判据改进建议：预检命中应先按目录分桶/守卫识别，再要求裁量）。
