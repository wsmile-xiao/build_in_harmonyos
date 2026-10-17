# DRAFT-asmotor-1.0.0-knr-strict-prototypes-c99: K&R 无原型声明 + `-Werror` 的 C99 CMake 项目 → 追加 `-Wno-strict-prototypes`（不降 gnu89）

> **Contributor**: pc2-8 | **Status**: Draft（pending editor review）| **Updated**: 2026-09-19
> **Source**: asmotor 1.0.0 HarmonyOS PC 适配（build_in_harmonyos，archives/a/asmotor/1.0.0）
> **拟提升编号：由知识库主编确认** —— 本草稿为未提升草稿，尚未分配正式 E 编号

## 场景

把 1990s 的老 C 项目搬到 OHOS PC（clang 15.0.4 + musl）。项目是 CMake 构建、
显式设定 `CMAKE_C_STANDARD 99`，CMakeLists 开启 `-Wall -Wextra -pedantic -Werror`，
但源码混用 K&R 风格无原型函数声明。clang 15 把无原型声明的弃用警告
（`-Wstrict-prototypes`）在 `-Werror` 下升级为错误，编译直接失败。

## 问题

可复用问题签名（日志症状）：

```text
error: a function declaration without a prototype is deprecated in all
       versions of C [-Werror,-Wstrict-prototypes]
```

真实证据（asmotor 1.0.0，util/str.c 与 xasm/common/expression.h）：

```c
/* util/str.c —— K&R 风格函数定义，无原型 */
str_Empty() {
    ...
}

/* xasm/common/expression.h —— 无原型函数声明 */
expr_Pc();
```

## 解决方案

在 CMakeLists.txt 非 MSVC 分支的编译选项追加 `-Wno-strict-prototypes`，
**保持 C99 标准不变**（仅关闭 strict-prototypes 单一警告面）：

```cmake
else(MSVC)
  add_compile_options(-Wall -Wextra -pedantic -Werror -Wno-unused-parameter -Wno-strict-prototypes)
endif(MSVC)
```

## 验证

```bash
# asmotor 1.0.0 实证（worktree: ~/.oh-runner/worktrees/asmotor-1.0.0）
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 <src> && cmake --build . -j2
# → 编译 0 错误；8 个可执行产物链接成功
# conan create（conan-verify G2）→ PASS
```

## 适用边界 / 反例

- **适用**：CMake 显式 `CMAKE_C_STANDARD 99/11` + `-Werror` + K&R 无原型声明的老 C 项目
  （CMake 驱动场景）；Makefile 项目对应形态为 `CFLAGS += -Wno-strict-prototypes`
- **不适用/反例**：纯 C2x 新代码（无 K&R 声明，无此警告面）；项目可接受降标准时
  走 DRAFT-crack-5.0a-knr-clang15 的 `-std=gnu89` 组合

## 查重差异（与既有知识）

- 与 DRAFT-crack-5.0a-knr-clang15（K&R + clang 15 族）：trigger 部分重叠（同
  "deprecated" 警告面），但方案不同——crack 走 `-std=gnu89 -Wno-int-conversion`
  降标准路线；本候选保持 C99 + 仅关 `-Wno-strict-prototypes`，适用于显式 C99 项目
- 与 E063（-Werror 升级通用场景）：E063 未含 strict-prototypes 专项方案
- 与 E103/E187（CMake <3.5 兼容）：无关联（不同问题面）
