# Msieve 1.53 OpenHarmony/HarmonyOS 适配笔记

## 编译环境

- 目标平台: OpenHarmony/HarmonyOS PC arm64
- Conan settings: `os=OHOS`, `os.version=6.0`, `arch=armv8`
- 构建系统: 纯 Makefile（上游无 configure，仅 all/clean/help 目标）
- 编译器: clang 15.0.4（`aarch64-unknown-linux-ohos` 交叉）
- 构建类型: 静态库 `libmsieve.a` + 可执行 `msieve`
- 源码 SHA256: `c5fcbaaff266a43aa8bca55239d5b087d3e3f138d1a95d75b776c04ce4d93bb4`
  （SourceForge msieve153_src.tar.gz，976135 字节，与 Arch/Gentoo 记录一致）
- 许可证: Public Domain（Makefile:1-10 明确声明）
- 状态: `built`

## 源码与分支确认

- 分支: `feat/msieve-1.53`
- 上游 URL: `https://downloads.sourceforge.net/project/msieve/msieve/Msieve%20v1.53/msieve153_src.tar.gz`
- 上游版本 v1.53 为 SourceForge 最后正式发布（2016-01-04，对应 SVN r989）

## 构建配置

上游 Makefile 关键变量与覆盖（零源码补丁，全部通过 make 命令行覆盖）：

```text
CC       = clang (aarch64-unknown-linux-ohos)
AR       = llvm-ar
RANLIB   = llvm-ranlib
OPT_FLAGS= -O3 -fomit-frame-pointer -D_FILE_OFFSET_BITS=64 -DNDEBUG -D_LARGEFILE64_SOURCE
```

上游 `OPT_FLAGS` 无条件含 `-march=native`（x86 专用）：AArch64 clang 报
`unknown target feature`，必须整体覆盖。其余构建差异同样以命令行变量注入
（GMP/zlib 的 -I/-L 路径来自 conan 依赖信息）。

## 架构代码审查（x86/x86_64 汇编 → AArch64 可移植回退）

上游在 AArch64 上**无需任何补丁**即可编译为纯可移植 C 实现。逐文件审查结论：

| 文件 | x86 专属内容 | AArch64 行为 |
|---|---|---|
| `common/util.c` | `get_cpu_type()` 运行时 CPUID 探测（x86 分支） | 非编译期 x86 宏路径 → 返回 `cpu_unknown`，代码全部走可移植分支 |
| `include/util.h` | `GCC_ASM32X/GCC_ASM64X` 宏定义（`__i386__`/`__x86_64__` 守卫） | 宏未定义 → 使用点全部展开为可移植 C |
| `include/dd.h` | x86 SSE2 double-double 快速路径 | 宏守卫外为纯 C 版本 |
| `mpqs/sieve_core.c` | SSE2 筛法位循环内联汇编（`GCC_ASM32X/64X` 守卫） | 可移植 C 回退 |
| `mpqs/sieve.c` / `mpqs/mpqs.h` | `HAS_SSE2` 条件编译 | 宏守卫内代码不激活 |
| `gnfs/poly/stage1/cpu_intrinsics.h` | SSE2/AVX intrinsics | `__SSE2__`/`__AVX__` 编译器预定义在 AArch64 上不存在 → 回退 |
| `gnfs/sieve/sieve_line.c` | x86 汇编辅助 | 宏守卫 → 可移植 C |

关键事实：

1. Makefile:295/300 给两个 generic sieve_core 变体无条件传 `-DHAS_SSE2`，
   但 `mpqs/sieve_core.c` 中所有 `HAS_SSE2` 代码块内部再有
   `GCC_ASM32X/GCC_ASM64X/MSC_ASM*` 双重守卫 —— 在 AArch64 上 `HAS_SSE2`
   定义是惰性的（inert），编译产物不含任何 x86 指令。
2. **未伪造 CPU 特性**：`common/util.c:get_cpu_type()` 在 AArch64 上如实
   返回 `cpu_unknown`（未宣称 SSE2/AVX），所有性能路径自动选择可移植实现。
3. **未删除任何算法校验**：分解结果的素性验证链（APRCL `mpz_aprcl32.c`、
   trial division、SQUFOF/ECM 小因子）全部原样编译。

## 知识扩展审查（2026-09-10，结论：路径 A，不新增知识）

适配过程中曾拟提交知识草稿（Makefile 硬编码 `-march=native` + 惰性
`-DHAS_SSE2`），经全量查重后判定既有知识已覆盖、未达路径 B 的
"新根因 + 新通用方案 + 正反验证"标准，草稿已删除，本包走**路径 A
（基础适配）**。查重事实记录如下（复评时可据此直达）：

- **`-march=native` 根因已知**：`aeolus/0.10.4`（Makefile 硬编码
  `-march=native`，补丁法解决，notes 问题 3 记录了"命令行覆盖被
  `+=` 追加污染而失效"的边界）；`lua-rapidjson/0.6.0`
  （`0001-fix-platform-detection-and-march-native.patch` 同根因）；
  草稿 `E1000`（header-only CMake 场景的 `-march=native` 透传）。
  三者手法不同（补丁 / 命令行覆盖 / CMake 变量），根因同一；msieve
  因变量在 Makefile 中为 `=` 递归展开且无 `+=` 追加，命令行覆盖有效
  —— 这是对既有方案边界的又一次确认，不是新方案。
- **汇编/架构宏守卫族已有条目**：`E016`（`assembler, unknown
  instruction → reconfigure-no-asm`）、`E006`（openssl no-asm）、
  `E145`（`have_arm_intrinsics_or_asm` meson 变量序）。msieve 与它们的
  差异仅是"构建不报错、宏为惰性"，这是本包源码的结构事实
  （使用点全部双重守卫），不是可跨包复用的故障模式。
- **SSE2/AVX/intrinsic/CPU 探测**：graph 540 条目 + index.tsv 中除上述
  三条外无其他覆盖；msieve 场景无需处理，无可提取的通用故障签名。
- **zsh 嵌套引号陷阱**（`-DX='"y"'` 降层导致 undeclared identifier）：
  graph/drafts 无覆盖，但属配方编写细节，且正确解法（改传上游
  Makefile 已有的展开变量 `SVN_VERSION=unknown`）是本 Makefile 特有
  变量名，不构成通用知识。
- git log --all / worktree 扫描：无 msieve 相关既有知识；
  `DRAFT-8958-clthreads`（Makefile 交叉编译族）不含 march/SSE2。

## 依赖

| 依赖 | 用途 | 制品仓状态 |
|---|---|---|
| gmp/6.3.0.1 | 大整数运算（gnfs 后台、ECM/SQUFOF、APRCL 素性检验） | 已发布（W0 核实） |
| zlib/1.3.1 | NFS 后处理关系数据的压缩读写 | 已发布（W0 核实） |

上游链接行 `-ldl -lz -lgmp -lm -lpthread`：OHOS musl 将 libdl/libpthread
并入 libc，但 sysroot 保留 stub 库，上游链接行原样可用。

## 上游测试调研

- 上游**无** `make test`/`check` 目标，无 CI 测试套件。
- 官方文档（Readme.nfs/Readme.qs）给出的验证方式：用已知合数实际运行分解。
- 因此在 `test_package/MANIFEST.yml` 中通过 `upstream_test_in_build: false` 声明；消费者/功能测试由
  test_package 承担（分解已知合数并验证因子乘积、素性、负向输入）。

## 验证结果

- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 ...`: PASS
- test_package（消费者/功能 1/1）：半素数分解、因子乘积回验、素性验证、
  负向输入（素数/1/0/负数）: PASS
- 鸿蒙特有测试 1/1（ELF64 AArch64、musl 解释器、.codesign 唯一、
  无 RPATH/宿主路径泄漏，真实运行分解）: PASS
- 制品: `lib/libmsieve.a`、`include/msieve.h` 等 8 个公共头、`bin/msieve`

## 状态说明

配方与本地 OHOS arm64 包已完整验证。
