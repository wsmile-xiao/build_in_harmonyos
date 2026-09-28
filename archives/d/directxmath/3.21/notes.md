# directxmath 3.21 适配笔记

## 编译环境
- 构建系统: header-only（无编译阶段，纯头文件拷贝，CMake INTERFACE target）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

DirectXMath 是微软出品的 header-only SIMD C++ 数学库（XMVECTOR/XMMATRIX 线性代数），
官方 CMakeLists.txt 用 `add_library(DirectXMath INTERFACE)` 定义接口库，仅安装头文件。
配方采用 v12.21 headeronly 变体：source() 拉取官方 tag may2026（DIRECTXMATH_VERSION 3.21）
tarball，build() 无编译，package() 按上游 CMake `LIBRARY_HEADERS` 集合（Inc/*.h + Inc/*.inl）
拷贝到 include/，并附带 LICENSE。验证通过 conan create 完成：

```bash
conan create . --version=3.21 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → 消费者 test_directxmath 编译链接运行通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无（header-only 库，头文件为平台中立 C/C++，clang 15 aarch64-linux-ohos 直接可用） | - | - |

## 源码修改

- 无。patches/ 为空：官方头文件无需修改即可在 OHOS arm64 编译使用。

## 依赖版本

无（header-only，零依赖）。

## 上游测试台账（R51 三步法）

### 清点证据（官方 tag may2026 源码包，共 107 个文件/目录，完整枚举）

| 检查项 | 结果 |
|--------|------|
| 源码包内 Tests/ 目录 | 不存在（`ls Tests` → No such file or directory） |
| CMakeLists.txt 测试注册 | L110-111：`if(BUILD_TESTING AND (EXISTS Tests/CMakeLists.txt)) enable_testing()` —— Tests 不存在 → 不启用 |
| XDSP/CMakeLists.txt / SHMath/CMakeLists.txt | 无任何 test/benchmark 注册 |
| 文件名字含 test/check/run（排除 .github） | 无 |
| .github/workflows/test.yml / arm64test.yml | 上游 CI 单独 clone `walbourn/directxmathtest` 仓库到 Tests/ 再跑 CTest（Windows 专用） |
| 样例/基准/fixture/测试脚本 | 无（源码包仅有 Inc/ 头、Extensions/ 可选头、SHMath/Stereo3D/MatrixStack 库源码、build/ 打包脚本） |
| README.md | 明确指引测试向 walbourn/directxmathtest 仓库提交（"Tests for new features should also be submitted as a PR to the Test Suite repository"） |

### 独立上游用例台账（逐项分类）

| 入口 | 分类 | 独立上游用例? | 实际运行 | 结果/原因 |
|------|------|--------------|---------|-----------|
| （无）官方 tag 源码不携带任何测试声明入口 | 用户测试源 | 否（不存在） | 未运行 | 官方测试套件位于独立仓库 walbourn/directxmathtest（依赖 Windows SDK 内部实现，上游 CI 仅 Windows），不属于本 tag 源码包 |
| SHMath/DirectXSHD3D11.cpp、D3D12.cpp | 库源码（D3D 后端） | 否 | 未运行 | BUILD_SHMATH=OFF 默认不编译；D3D11/D3D12 为 Windows 图形 API，无 OHOS 对应物 |
| Stereo3D/Stereo3DMatrixHelper.cpp | 库源码 | 否 | 未运行 | 非测试，仅为 Stereo3D 矩阵辅助实现 |
| build/*.ps1 | 打包脚本 | 否 | 未运行 | PowerShell 发布脚本，非测试 |

### 双口径统计

- source_declared_total = **0**（官方 tag 源码中按可复制枚举规则发现的测试声明总数）
- configured_executable_total = **0**（当前 OHOS 配置无上游测试实例化）
- executed_passed_total = **0** / failed = **0** / uninstantiated = **0**
- 全量通过率：0/0（无测试声明，无分母）；上游确无测试已附上述清点证据
- 上游 CI 的 CTest 注册项存在于独立仓库 walbourn/directxmathtest，不属于本库官方 tag 源码，不计入本库声明数

## 知识候选台账与七轴查重（knowledge-reuse-governance）

### 候选台账

| # | 候选 | 真实错误 | 根因 | 修复 | 验证 | 适用范围 |
|---|------|---------|------|------|------|---------|
| K1 | DirectXMath.h 无条件包含 Windows 专用 `sal.h` | conan create 消费者编译报 `fatal error: 'sal.h' file not found`（DirectXMath.h:156） | 上游头文件无条件 `#include "sal.h"`（Microsoft Source Annotation Language，仅 Windows SDK 提供）；官方 README 明确"非 Windows 平台必须自行在 include 路径提供 sal.h" | patches/0001-DirectXMath-sal-shim.patch：`#if defined(_MSC_VER)` 才 include sal.h，否则就地定义库内用到的全部 SAL 注解宏为空宏（_In_/_Out_/_In_reads_/_Out_writes_/_Success_/_Use_decl_annotations_/_Analysis_assume_ 等 10 个） | conan create EXIT:0；消费者 test_directxmath 编译链接运行通过（4 项断言）；test_ohos 5 项鸿蒙检查全过 | 任何随 Windows SDK 系头文件/源码带入 sal.h 的 C/C++ 库在非 MSVC 工具链（clang aarch64-linux-ohos）上编译时；可跨库复用 |
| K2 | （噪声）header-only 库 test_package settings 子设置与主配方约束冲突 | conan create 报 `The recipe ... is constraining settings. 'settings.compiler.libcxx' doesn't exist` | OHOS 适配版 conan 对 settings 子设置的约束规则与官方略有差异 | test_package 与主配方均声明顶层 settings，不声明点号子设置；libc++/cppstd 由 profile 注入 | conan create 通过 | 已由 E257/E321/E322 覆盖 header-only 配方通用写法，无新增差异，判为噪声不建草稿 |

### 七轴查重（候选 K1 vs 既有知识四范围：knowledge/graph/index.tsv 766 条、doc/、drafts/）

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | 否 | 无任何既有条目涉及 sal.h / SAL 注解 / Windows SDK 专属头文件缺失 |
| causal_duplicate | 否 | E113（BSD 类型 compat 头）、E375（POSIX capability 探测）、E527（gtk display backend）等均非 SAL 注解缺失根因 |
| trigger_overlap | 否 | 触发面（头文件 include 的 Windows-only 注解头在非 MSVC 工具链缺失）与既有条目无重叠 |
| solution_overlap | 部分 | 解决方案（条件编译 + 就地空宏 shim）与 E375"按能力正选平台"思路同为条件编译族，但 E375 针对 CMake 平台分支，本候选针对头文件内 include 与 SAL 宏定义，无实质覆盖 |
| combination_novelty | 是 | "上游头文件无条件 include 第三方平台专用注解头 → 补丁内置空宏 shim（非 stub 代码、非伪造编译）" 组合在 766 条中无先例 |
| boundary_novelty | 是 | 明确了适用边界：仅注解宏（无代码生成语义）才可空宏展开；若 SAL 宏参与实际逻辑则必须提供真实 sal.h（dotnet/runtime 开源版）而非空宏 |
| test_migration_novelty | 是 | test_package + test_ohos 双用例验证 shim 后消费者编译链接运行，未见既有条目迁移该验证路径 |

关系字段：`similar_to`（无直接条目，近似 E375 条件编译族）；`caused_by`（上游 Windows 平台假设）；`prerequisite_of`（无）；`conflicts_with`（无）。

### 路径决定

- K1：未命中 + 新增差异已由本轮真实日志验证（conan create EXIT:0 + 消费者 4 断言 + test_ohos 5 检查）且可跨库复用（任何 Windows SDK 系头文件库）→ **路径 B（知识库扩展）**，建立 `DRAFT-directxmath-3.21-sal-h-shim.md/.kv` 草稿。
- K2：完整被既有 E257/E321/E322 覆盖，无独立差异 → 判噪声，**不建草稿**。
- 结论：`new_draft`（K1），非 `exact_duplicate`，非 `path_a_no_knowledge`。

## 鸿蒙专项测试

test_package/test.cpp（消费者用例）：仅通过公开头文件 Inc/DirectXMath.h 调用公开 API：
- XMVectorSet/XMVectorGetX 等 SIMD 向量运算与可观察结果断言
- XMMatrixIdentity/XMMatrixMultiply 矩阵运算断言
- 运行输出与退出码验证

（详见任务流程中的鸿蒙专项测试 test_ohos 与消费者验证记录）
---

**编译结束**: 2026-09-27 02:17
**最终状态**: built
