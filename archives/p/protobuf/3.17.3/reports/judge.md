# protobuf 3.17.3 路径判定·申报意见表（S5）

| 项 | 内容 |
|----|------|
| 目标库/版本 | protobuf 3.17.3 |
| 来源 | 依赖库（方式二） |
| 适配路径 | **A（基础适配 → 【依赖项】）** |
| 是否够格报 B | **否** |

判据1（可跨库复用）逐条：

- **非孤立 bug/单编译 patch**：本次涉及 `cmake/` 子目录入口、`CMAKE_POLICY_VERSION_MINIMUM`、Ninja（无 `/bin/sh`）、protoc 版本符号链接、conan cache layout 冲突等多点。但——
- **"一类"通用问题？** 否。各点均为**本环境适配 + 针对 protobuf 特性的 case-by-case 处理**：
  - `protoc` 的 `VERSION` 符号链接是 protobuf 特有（其 target 设置了 `VERSION` 属性），解法是直接给 protobuf 打补丁去 `VERSION`，属该库个案，非"换库照样成立"的诊断模式。
  - Ninja/`CMAKE_POLICY_VERSION_MINIMUM` 是 OHOS + 老 CMake 项目的通用适配，但**仓库已有类似沉淀**（33.6 已在 Windows 交叉构建用 Ninja + symlink 变 copy 处理过同类问题），本条目增量不足。
  - conan cache layout 冲突是 conan 2 特定环境问题，改用自定义 layout 解决，较通用但单点、且非可复用知识库条目。
- 知识库覆盖判断：已有条目（33.6 等）已覆盖 Ninja、符号链接、pkgconfig 可重定位等模式，本条目无明确增量，不构成"解决一类通用问题"的贡献。

> **换库测试**：把"protoc 去 VERSION 符号链接"放到另一同类库不再成立；"Ninja/CMAKE policy"虽换库成立但属仓库既有做法。→ 均不满足 B 的通用性硬检。

| 是否够格报 C | **否** |

判据2：本次为常规单库 CMake 交叉编译，无 MPI+Boost 深链、OSG/core GL、超大体积依赖爆炸等体系级复杂度；且 protobuf（新版 33.6）经人工评审已确认单库适配不满足路径 C。3.17.3 更不满足。

| 拟新增 draft | 无 |
| 条目主题 | 无 |
| 申报结论 | **不申报 B/C，按路径 A（【依赖项】）提交常规 PR** |
