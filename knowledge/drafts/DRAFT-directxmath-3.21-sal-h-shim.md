# DRAFT-directxmath-3.21-sal-h-shim — 上游头文件无条件 include Windows 专用 sal.h 时的 SAL 注解空宏 shim

## 基本信息
- **ID**: DRAFT-directxmath-3.21-sal-h-shim
- **来源库**: directxmath 3.21（微软 DirectXMath，tag may2026）
- **阶段**: 路径 B（知识库扩展）
- **草稿状态**: draft（待审核 promote）

## 问题
DirectXMath.h（第 156 行）**无条件** `#include "sal.h"`。sal.h 是 Microsoft Source
Annotation Language 头文件，仅随 Windows SDK 提供。在 HarmonyOS PC（clang
aarch64-linux-ohos）上消费者编译直接报：
```
fatal error: 'sal.h' file not found
```
官方 README 也明确：非 Windows 平台构建必须自行在 include 路径提供 sal.h。

## 根因
上游头文件以 Windows 为唯一目标平台，把平台专属注解头作为必选依赖引入，
未提供非 MSVC 工具链的替代路径。

## 方案
在配方补丁中把该 include 变为条件包含，并就地定义库内实际用到的 SAL 注解
宏为空宏（纯注解、无代码生成语义，空展开等价）：

```c
#if defined(_MSC_VER)
#include "sal.h"
#else
#define _In_
#define _In_reads_(x)
#define _In_reads_bytes_(x)
#define _Out_
#define _Out_opt_
#define _Out_writes_(x)
#define _Out_writes_bytes_(x)
#define _Success_(x)
#define _Use_decl_annotations_
#define _Analysis_assume_(x)
#endif
```
（以 directxmath 3.21 为例，覆盖库内全部 10 个 SAL 标记。）

## 验证
- `conan create`（-pr:h/-pr:b=ohos-aarch64，clang 15）：EXIT:0
- test_package 消费者 test_directxmath：编译链接运行通过，4 项公开 API 断言
  （向量往返/向量加法/矩阵旋转 90°/XMFLOAT3 载入）全过
- test_ohos：5 项鸿蒙专项检查（ELF64 AArch64/musl 无 glibc/.codesign/无宿主
  路径泄漏/真实 NEON SIMD 计算）全过

## 适用边界
- **适用**：任何随 Windows SDK 系头文件或源码带入 sal.h（或同类 Windows-only
  注解头）的 C/C++ 库，在非 MSVC 工具链（clang/gcc, Linux/OHOS）编译报
  `sal.h file not found`。
- **反例（不适用空宏）**：若 SAL 宏参与实际逻辑/代码生成（如 `_Success_` 被
  静态分析工具消费、宏展开影响 ABI），必须提供真实 sal.h（dotnet/runtime
  `src/coreclr/pal/inc/rt/sal.h` 开源版），不得用空宏替代。

## 查重差异
- 七轴查重（vs knowledge/graph/index.tsv 766 条 + doc/ + drafts/）：
  exact_duplicate 否 / causal_duplicate 否 / trigger_overlap 否 /
  solution_overlap 部分（与 E375 同为条件编译族，但 E375 针对 CMake 平台分支）/
  combination_novelty 是 / boundary_novelty 是 / test_migration_novelty 是。
- similar_to: 无直接条目（近似 E375 条件编译族）
- caused_by: 上游 Windows 平台假设
- prerequisite_of: 无；conflicts_with: 无

## 相关文件
- patches/0001-DirectXMath-sal-shim.patch（本库归档内）
- notes.md 知识候选台账（K1）
