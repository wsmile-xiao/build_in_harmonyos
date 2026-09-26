# 手写多级 Makefile 的“架构分支 + 平台专属子项目”

- **条目**：`knowledge/drafts/DRAFT-makefile-arch-subproject-exclusion.kv`
- **来源软件**：tboot 1.10.5（手写多级 Makefile：`tboot` / `safestringlib` / `lcptools-v2` / `tb_polgen` / `utils` / `docs`）
- **日期**：2026-09-24
- **触发**：本地 `make` 首个错误（aarch64 上 `-march=i686`），修好后暴露第二类错误（x86 内联汇编）
- **关联**：R8/PF5（禁止 `__OHOS__` 平台宏）、R32（`settings.os` 用 `in ("Linux","OHOS")`）

## 错误签名

```
# 第一类：机器参数被拒（x86 专属 branch 被非 x86 目标命中）
clang-15: error: unsupported argument 'i686' to option '-march='
clang-15: error: unsupported option '-m32' for target 'aarch64-unknown-linux-ohos'

# 第二类：平台专属子项目里的内联汇编
../tboot/include/io.h:55:33: error: invalid output constraint '=a' in asm
../tboot/include/processor.h:119:29: error: invalid output constraint '=a' in asm
```

## 根因

1. 上游以 **`uname -m`**（或等价探测）推导 `TARGET_ARCH`，并写成**二元分支**：

   ```make
   ifeq ($(TARGET_ARCH),x86_64)
   CFLAGS += -m64
   else
   CFLAGS += -m32 -march=i686     # ← aarch64 也落这里
   endif
   ```

   aarch64 命中 `else`，clang 直接报错——**这不是交叉编译参数问题，而是上游把“非 x86_64”
   等同于“x86_32”**。

2. 工程里通常混着**只对 x86 有意义**的子项目/工具：freestanding 引导固件
   （`-melf_i386`、`-nostdinc`、32 位汇编）与读 x86 MSR/IO 端口的诊断工具
   （`in/out` 内联汇编、约束 `'=a'`/`'=A'`）。它们不是“没适配”，而是**目标平台不产出**。

3. 因此这类工程的正确修法是**界定范围**（build scope），而不是硬把 x86 代码编到 aarch64 上。

## 推荐方案（source-patch，两层条件）

```make
# ① 机器参数：三态，只有 x86 目标才加
ifeq ($(TARGET_ARCH),x86_64)
LIBDIR := lib64
CFLAGS += -m64
else ifeq ($(TARGET_ARCH),x86_32)
LIBDIR := lib
CFLAGS += -m32 -march=i686
else
LIBDIR := lib                 # aarch64 等：不加任何 x86 机器参数
endif

# ② 平台专属子项目/工具：非 x86 目标剔除（x86 目标保持原列表）
ifneq (,$(filter $(TARGET_ARCH),x86_32 x86_64))
SUBDIRS := tboot safestringlib lcptools-v2 tb_polgen utils docs
else
SUBDIRS := safestringlib lcptools-v2 tb_polgen utils docs
endif
```

实现要点：
- **不要用 `__OHOS__` 等平台宏表达**：① `patches/` 里默认禁止平台宏（R8 / preflight PF5 会直接拦）；
  ② 用**架构能力**表达更准确——同一份补丁也适用于其它非 x86 目标；③ 平台宏会把
  “x86 目标但非 OHOS”的构建行为也改掉，而这里要保的恰恰是 x86 行为不变。
- 条件写在 **Makefile/Config.mk**（构建系统层），不要改源码里的 `#ifdef`；宿主机工具通常是
  可移植 C，不需要改（本例：`lcptools-v2`/`tb_polgen`/`utils/txt-stat` 一行源码未动）。
- 剔除后要**如实申报范围**：`notes.md` / `manifest.yaml`（`build_scope`）/ PR 补充说明 /
  `test_package/MANIFEST.yml` 四处写明哪些产物不在本目标平台产出。
- 相关联的编译期严格性问题（上游自带 `-Werror` + clang 对 GNU 扩展的诊断族）见 **E063**
  （`add-cflags-disable-werror`：逐条 `-Wno-error=<诊断>`，不做 blanket `-Wno-error`）。

## 验证方法

```bash
make CC=clang -j1 2>&1 | head -20          # 首个错误落在哪个子项目
grep -n "uname -m\|TARGET_ARCH" Makefile Config.mk */Config.mk
# 修复后：aarch64 上 make rc=0；并确认 x86 目标仍走原分支（可用 make -n 观察展开）
```

## 现网证据（tboot 1.10.5 实测）

| 项 | 值 |
|---|---|
| 上游位置 | `Makefile:17`（`SUBDIRS`）、`Config.mk:20-21`（`-m32 -march=i686`）、`tboot/Config.mk:50`（`-melf_i386`）、`utils/Makefile:14`（`TARGETS`） |
| 首个错误 | `clang-15: error: unsupported argument 'i686' to option '-march='`（`common/boot.S`，子项目 `tboot`） |
| 第二类错误 | `../tboot/include/io.h:55: invalid output constraint '=a' in asm`（`utils/txt-acminfo`） |
| 修复补丁 | `archives/t/tboot/1.10.5/patches/0001-Config.mk.patch`、`0002-Makefile.patch`、`0009-utils-Makefile.patch` |
| 结果 | aarch64 上 `make rc=0`、`conan create rc=0`（`test_package` 22/22）；x86 目标**保留**原 `SUBDIRS`/`TARGETS` 与机器参数 |

## 适用边界

- 适用于**手写 Makefile（含多级/递归 make）**工程；autotools/CMake/Meson 有各自的
  “host 探测 + 交叉编译”机制，问题形态不同（那类问题应归 `cross-compile` 或对应构建系统条目）。
- 剔除平台专属子项目会缩小交付范围——必须与需求方确认“该目标平台确实不需要这些产物”，
  并在归档四处如实申报；不要用“编不过就删”式做法替代判断。
