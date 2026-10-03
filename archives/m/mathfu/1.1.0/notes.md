# mathfu 1.1.0 适配笔记

## 编译环境
- 构建系统: 无构建（header-only；上游 CMake 链不可用，见下）
- 编译日期: 2026-10-02
- 目标环境: OpenHarmony HongMeng Kernel aarch64
- 工具链: OHOS Clang 15.0.4、CMake 4.1.2、Conan 2.29.1
- 状态: built

## 编译步骤

上游官方归档（SHA-256 `98f167002085c0ae1b2ac1668d3342fc4bafbe6b2185b3b9e88436d19332f8ca`）。
库本身为纯模板头文件（`include/mathfu/*.h`），无任何编译产物；Conan 包只打包
头文件与 LICENSE。

本地验证命令：

```bash
cd archives/m/mathfu/1.1.0
conan create . \
  -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 \
  -pr:b=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 \
  --build=missing -c tools.build:jobs=2
```

配方在 build() 阶段用工具链 clang++ 直接编译并运行三个上游 Google Test
套件（vector_test / matrix_test / quaternion_test），test_package 阶段构建
并运行 CMake 消费者测试。

## 上游测试

三个上游测试翻译单元（`unit_tests/*/[name].cpp`）以工具链编译器直接编译：

```
clang++ -std=c++11 -O2 -ffp-contract=off \
  -Wall -Wextra -Werror -Wno-long-long -Wno-variadic-macros \
  -Wno-deprecated-copy-with-user-provided-copy -Wno-deprecated-copy \
  -DMATHFU_COMPILE_WITHOUT_SIMD_SUPPORT \
  -Iinclude -Iunit_tests -isystem <gtest>/include \
  unit_tests/<suite>/<suite>.cpp <gtest>/lib/libgtest.a -lpthread -static
```

结果（aarch64 原生执行）：

| 套件 | 用例数 | 通过 | 失败 |
|------|--------|------|------|
| vector_test | 180 | 180 | 0 |
| matrix_test | 129 | 129 | 0 |
| quaternion_test | 16 | 16 | 0 |
| **合计** | **325** | **325** | **0** |

test_package 消费者测试 1 个可执行文件（23 个断言）通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 CMake 无法配置（`Can't find fplutil directory`） | v1.1.0 release tarball 的 `dependencies/` 三个 git 子模块（fplutil、googletest、vectorial）均为空目录，`cmake/find_fplutil.cmake` 必然失败 | 配方跳过上游 CMake，用工具链编译器直接编译三个上游测试翻译单元（参照 array-hash 0.7.2 先例）；googletest 以 build_require（制品仓 googletest/1.12.1 静态包）注入 |
| 2 | matrix_test 的 `InverseNonInvertible_float_3`/`_double_3` 与 quaternion_test 的 `QuaternionTests.Inverse` 共 3 用例失败（奇异矩阵被 `InverseWithDeterminantCheck` 判为可逆；四元数往返精度超差） | OHOS aarch64 clang（15.0.4）默认启用 FMA 收缩（`-ffp-contract=on`，硬件 `__ARM_FEATURE_FMA`），将 `a*b+c` 融合为单步舍入，改变行列式/四元数重建的舍入路径：本应精确相消为 0 的行列式残留非零值，越过 1e-7/1e-15 阈值；x86 默认不收缩，上游 CI 从未暴露 | 编译测试与库时统一加 `-ffp-contract=off` 恢复 IEEE 754 逐步舍入，精确相消成立，325/325 全过（对照复现：不加该 flag 时 3 例确定性失败） |
| 3 | SIMD 路径编译需要 `vectorial/simd4f.h` | vectorial 是 git 子模块，不随 release tarball 分发；且 OHOS clang 仅定义 `__ARM_NEON`（无尾下划线），上游 `__ARM_NEON__` 检测本身也不触发 | 使用上游官方支持的 no_simd 测试变体（`-DMATHFU_COMPILE_WITHOUT_SIMD_SUPPORT`，即上游 `unit_tests/*/no_simd/` 配置），并经 cpp_info.defines 暴露给消费者 |
| 4 | clang 15 `-Werror` 下上游 2014 年代码编译失败 | 用户提供的拷贝构造触发 `-Wdeprecated-copy-with-user-provided-copy`/`-Wdeprecated-copy` 警告（C++11 语义修订，非代码缺陷） | 加 `-Wno-deprecated-copy(-with-user-provided-copy)` 抑制，保持上游其余 `-Wall -Wextra -Werror` 严格级别 |
| 5 | 测试二进制动态链接运行报 `Error relocating ... symbol not found` | OHOS SDK 的 libc++.so 是链接器脚本（INPUT(-lc++_shared)），运行期加载器不识别 | 测试二进制以 `-static` 静态链接，aarch64 设备原生执行（array-hash 0.7.2 同款方案） |

## 源码修改

无补丁（patches_applied: []）。平台差异全部在配方层解决：
FMA 收缩与弃用警告用编译 flag；SIMD 用上游 no_simd 变体宏；googletest 用
build_require 注入。上游源码零修改。

## 依赖版本

- 运行时依赖：无（header-only）
- 测试构建依赖：googletest/1.12.1（制品仓静态包，仅 conan create 期间使用）

## 验证结果

```bash
vector_test:      [  PASSED  ] 180 tests.
matrix_test:      [  PASSED  ] 129 tests.
quaternion_test:  [  PASSED  ] 16 tests.
test_package:     0 checks failed (23 assertions PASS)
conan create:     exit 0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `mathfu/1.1.0` Conan package | header-only | `include/mathfu/*.h`（10 个公共头 + internal/）+ LICENSE |

## 注意事项

- aarch64 消费者若不定义 `MATHFU_COMPILE_WITHOUT_SIMD_SUPPORT`，包含
  `mathfu/vector.h` 会因缺 vectorial 头而编译失败；配方已通过
  `cpp_info.defines` 自动注入该宏。
- FMA 收缩差异的完整诊断（含复现命令与原理）沉淀为知识草稿
  `knowledge/drafts/DRAFT-mathfu-1.1.0-aarch64-fma-contraction-determinant.kv/.md`。
