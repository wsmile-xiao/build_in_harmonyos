# DRAFT: CMakeDeps 对 build 上下文（tool_requires）包不生成 INCLUDE_DIRS —— 上游 gtest 测试 TU 全量编译失败

> 状态：DRAFT（mujoco/2.2.2 触发，待 PR 关联）｜severity: P1｜category: cmake, conan, testing
> 提交窗口：DS-10｜日期：2026-09-21

## 1. 可复现症状与稳定错误签名

配方在 `build()` 内编译并运行上游 gtest 套件（`cmake.build()` + `cmake.test()`），configure 阶段一切正常（`find_package(GTest)` 成功、FetchContent 全部短路），进入测试 TU 编译时第一错必现：

```
test/fixture.h:18:10: fatal error: 'gtest/gtest.h' file not found
```

特征：**只有测试 TU 挂，主库与业务源码全绿**；报错的 `#include` 行写法完全标准（`<gtest/gtest.h>`）；换 gmock/benchmark 同样炸（`gmock/gmock.h`、`benchmark/benchmark.h`）。

## 2. 根因与最小复现

根因不在包、不在 profile，在 **CMakeDeps 的上下文选择**：

- 同一构建目录 `build/Release/generators/` 下逐文件对比（mujoco conan create 现场，Conan 2.29.1）：
  - host 依赖 tinyxml2：`set(tinyxml2_INCLUDE_DIRS_RELEASE "${tinyxml2_PACKAGE_FOLDER_RELEASE}/include")` ✅
  - build 上下文的 GTest：`set(gtest_GTest_gtest_INCLUDE_DIRS_RELEASE )` ← **空**（聚合变量与 GTest::gtest/gmock 组件变量全空）
- 即：类属性 `tool_requires = "gtest/..."` + `deps.build_context_activated = [...]` 激活的依赖，CMakeDeps 生成的 CMake config **目标存在（find_package 不报错）、include 目录为空**，编译行自然没有 `-I`。

最小复现：任一配方把 gtest 声明为 `tool_requires` 并在 `build()` 里编译包含 `#include <gtest/gtest.h>` 的 TU。

## 3. 已尝试方案（含失败）

| 方案 | 结果 |
|---|---|
| 检查/重装 gtest 包 binary | 无效——包内 `include/gtest/gtest.h` 完好，是生成器不写 include |
| 检查 profile/toolchain 的 CC/CXX（E540 方向） | 无关——主库源码编译全绿 |
| 给桥接 INTERFACE 目标补 target_include_directories（候选2） | 可行但要在 generate() 里从 build 依赖取 include 再写补丁，链路长、每个包重复造轮子 |

## 4. 最终方案与真实验证

**修法：测试框架从 `tool_requires` 改为 `build_requirements()` 里的 `self.test_requires()`**（host 上下文、测试专用、不传递给消费者）：

```python
def build_requirements(self):
    self.test_requires("gtest/1.17.0.1")
    self.test_requires("abseil-cpp/20240116.1")
    self.test_requires("benchmark/1.9.5")
```

同时删除 `deps.build_context_activated = [...]`（不再需要）。host 上下文数据文件 INCLUDE_DIRS 正常生成 → `find_package(GTest)` 返回的 `GTest::gtest` 自带 include 传播 → 测试 TU 编译行自动获得 `-I`。仓库先例：adept-math/2.1.3（`self.test_requires("gsl/2.8")` 供上游测试）。

真实验证：mujoco/2.2.2 八轮 conan-verify 卡死此点，切换声明方式后 [待 PR 填入：verify 结论与测试数字]。

## 5. 适用范围 / 反例 / 解除条件 / 风险

- **适用**：在配方 `build()` 内编译运行上游测试套件、测试框架以 Conan 包提供的所有场景（gtest/catch2/benchmark 同理）。
- **不适用/反例**：①测试框架走 FetchContent 源码（不经 Conan，无此问题）；②test_package 消费者测试的框架依赖（本就是 host 上下文）；③host/build 三元组不同的纯交叉构建——测试框架必须留在 build 上下文，此时改用 fallback：在 `generate()` 从 `self.dependencies.build` 取 `cpp_info.includedirs`，经 toolchain 变量或桥目标 `target_include_directories` 显式注入。
- **风险**：`test_requires` 进入 host 图，包体不传递给消费者（conan 语义保证），但 RPATH/依赖清单生成逻辑需注意不要把静态测试框架算进交付物。

## 6. 查重与新增价值说明

- **E216**（glib/libxml2 CMakeDeps 组件头文件传播失效）：症状同族（头文件找不到），但 E216 是 **host 上下文内** components 聚合/cpp_info 声明缺陷（修法在 test_package 里 GLOB 兜底）；本条是 **build 上下文整体不生成 INCLUDE_DIRS**（修法是换上下文声明方式）。签名不同（本条带"仅测试 TU 挂 + data.cmake INCLUDE_DIRS 空"双重特征）、根因层不同、修法层不同 → 按 AGENTS §6.2 组合型/新路径知识申报 create。
- **E292**（大型 C++ 库测试分层迁移）：讲环境补齐（TMPDIR/测试数据/时区），不涉及框架 include 传播。
- **E540**（runner-path-prepend）：讲 PATH 注入，无关。
- 新增价值：一条 30 秒判别法（看 `generators/<Pkg>-*-data.cmake` 的 INCLUDE_DIRS 是否为空 + 对照 host 依赖）+ 一个一行修法，可终结此类"看起来像包坏了"的多轮试错（本案实测烧掉 8 轮 conan-verify 迭代）。
