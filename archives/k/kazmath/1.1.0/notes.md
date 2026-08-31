# kazmath 1.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-29
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

```bash
cmake -S . -B build \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DKAZMATH_BUILD_TESTS=OFF \
  -DKAZMATH_BUILD_JNI_WRAPPER=OFF \
  -DKAZMATH_BUILD_LUA_WRAPPER=OFF
cmake --build build -j2
cmake --install build
```

## 测试验证

原始上游 `tests/` 有 39 个 C++ 测试用例，使用 Python 3 兼容入口运行同一测试类和测试方法，结果为 39/39 通过。原始 `test-apps/CUnitTest` 注册 23 个 C 测试用例；初始环境无法执行该 suite，因为缺少 CUnit 且源码包含旧 API 调用。

已安装 OHOS profile 下的 `cunit/2.1.3`，并在临时干净源码副本中应用 `patches/0001-fix-upstream-cunit-tests.patch`。修复了旧 API、错误矩阵期望值、浮点比较容差和 6 个 `CU_ASSERT(0)` 占位断言；修改后的 CUnit suite 实际结果为 23/23 用例、34/34 断言通过。消费者测试为 1/1 通过。适配后独立验证统计为 63/63，通过率 100%。

注意：本次 `conan create` 在源码下载阶段因 GitHub 网络超时而未完成，因此不能把 Conan 端到端流程报告为通过；该限制已记录在 `manifest.yaml` 和 `test_package/MANIFEST.yml`。

## 适配说明

- 通过 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容 CMake 4.x 对旧版 `cmake_minimum_required` 的限制。
- 关闭 JNI/Lua 可选 wrapper，避免引入 Java/Lua51 外部依赖。
- 上游无 release/tag，使用官方 GitHub master tarball，SHA-256 为 `d85f7049de106fe529cfa411bb292353cf46a35a8e2557df48ebd7c7bd86a493`。
- 产物为静态库 `libkazmath.a`，无可执行工具，不需要 `commands.json`。
- 上游 CUnit 测试修改已通过 `conandata.yml` 声明，未将修改后结果冒充原始上游结果。
