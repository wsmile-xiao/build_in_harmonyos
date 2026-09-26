# E433 — 上游 find_package(GTest) 大写 vs CMakeDeps 小写 gtest：GTest_DIR 指向包内配置

## 错误特征
- conan create 的 CMake configure 阶段报：
  `GTest::gtest ... target was not found` / `find_package(GTest)` 失败
- 典型日志：`Error: The following variables are used in this project, but they are set to NOTFOUND`

## 触发条件
- 测试/工具：使用 CMake + Conan 的 C++ 项目，上游 CMakeLists 调用 `find_package(GTest)`（大写）
  并链接 `GTest::gtest` 目标
- 阶段：configuration
- 平台：无关（Conan/CMakeDeps 跨平台通用）

## 根因分析
ninja 上游 CMakeLists.txt 调用 `find_package(GTest)`（大写 G）并链接 `GTest::gtest`
导入目标；而 Conan CMakeDeps 生成的是小写 `gtest` 配置（gtest-config.cmake），目标名
不匹配导致 configure 失败。解决：在 `generate()` 中把 `GTest_DIR` 指向 conan gtest 包
自带的 `lib/cmake/GTest/GTestConfig.cmake` 目录（该配置定义 `GTest::gtest` 导入目标）。

## 解决方案

### 推荐方案
generate() 注入 GTest_DIR：
```python
gtest = self.dependencies.get("gtest")
if gtest and gtest.package_folder:
    cfg = os.path.join(gtest.package_folder, "lib", "cmake", "GTest")
    if os.path.isdir(cfg):
        tc.variables["GTest_DIR"] = cfg
```
```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   # configure/build/package 全通过
```

### 禁止做法
- ❌ 修改上游 CMakeLists 把 find_package(GTest) 改小写（改库行为）
- ❌ 手工改 CMakeDeps 生成的小写配置为目标名（不可复现）

## 验证
```bash
# 注入前：conan create 报 'GTest::gtest ... target was not found'
# 注入后：conan create 通过（reports/conan-create.log）
```

## 适用边界
- 适用：上游用 find_package(GTest) 大小写目标、Conan 提供 GTest 依赖的 C++ 项目
- 反例：上游 find_package(gtest) 小写时无需注入

## 查重差异
- exact_duplicate: false；causal_duplicate: false（E216=组件 INTERFACE_INCLUDE_DIRECTORIES 传播、E221=target libs 空，均非目标名大小写）
- trigger_overlap: true（同属 CMakeDeps/Conan CMake 配置域）
- combination_novelty: true —— "find_package(GTest) 大写目标 vs CMakeDeps 小写 → GTest_DIR 指向包内 GTestConfig.cmake" 具体方案

## 关联条目
- similar_to: E216、E221
- caused_by: CMakeDeps 配置名与上游 find_package 名大小写不一致
- conflicts_with: 无