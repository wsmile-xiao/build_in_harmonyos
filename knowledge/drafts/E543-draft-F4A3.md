# E543 — ExternalProject configure 期 googletest 下载失败：Conan gtest 包 + 裸 target 桥接

## 错误特征

上游 CMake 项目在 `BUILD_TESTING` 分支用 `googletest.CMakeLists.txt.in` +
`configure_file` + `execute_process` 在 **configure 阶段**驱动
`git clone https://github.com/google/googletest.git`。在无法访问 GitHub 的
OHOS CI worker 上，配置期即失败：

```text
CMake Error at CMakeLists.txt:230 (message):
  CMake step for googletest failed: 1
```

（外层由 `execute_process ... RESULT_VARIABLE result` 捕获后
`message(FATAL_ERROR "CMake step for googletest failed")`。）
下载工程自身用 `cmake_minimum_required(VERSION 2.8.2)`，新 CMake 还会叠加：

```text
Compatibility with CMake < 3.5 has been removed from CMake.
```

## 触发条件

- 构建系统: cmake（`BUILD_TESTING` 分支内嵌 googletest ExternalProject 下载）
- 阶段: configuration
- 环境: GitHub 不可达（OHOS CI 网络）

## 根因分析

- 上游把**测试框架引导**放入配置期网络下载：`GIT_REPOSITORY`
  `https://github.com/google/googletest.git`，与库的编译无关却阻塞整个
  configure。
- 下载子工程用远古 CMake 最低版本（2.8.2），与现代 CMake（≥4.x）策略冲突。
- 只加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 能过版本闸，但仍会 clone 失败——
  必须同时把框架来源从网络改为制品仓/本地。

## 解决方案

### 1) 补丁：下载块 → find_package + 裸 target 桥接

上游 `test/CMakeLists.txt` 里 `link_libraries(gtest gmock_main)` 用的是**裸
target 名**；Conan gtest 包导出的是 **GTest::gtest / GTest::gmock_main**
命名空间目标。二者用 INTERFACE IMPORTED 桥接即可，测试逻辑零改动：

```cmake
find_package(GTest CONFIG REQUIRED)
if(NOT TARGET gtest)
  add_library(gtest INTERFACE IMPORTED)
  set_target_properties(gtest PROPERTIES INTERFACE_LINK_LIBRARIES GTest::gtest)
endif()
if(NOT TARGET gmock_main)
  add_library(gmock_main INTERFACE IMPORTED)
  set_target_properties(gmock_main PROPERTIES INTERFACE_LINK_LIBRARIES GTest::gmock_main)
endif()
```

> 补丁必须走 `refresh-patch --auto` 生成（R6），不得在 source() 里 sed。

### 2) 配方：test_requires + GTest_DIR

```python
def build_requirements(self):
    self.test_requires("gtest/1.17.0")

def generate(self):
    tc = CMakeToolchain(self)
    gtest = self.dependencies["gtest"]
    tc.variables["GTest_DIR"] = os.path.join(
        gtest.package_folder, "lib", "cmake", "GTest").replace("\\", "/")
    tc.generate()
```

`BUILD_TESTING` 保持 `ON`，全套上游测试照常构建、运行、上报（保留覆盖率，
不降级为只跑 test_package）。

### 3) 验证

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   # EXIT=0
# 上游: 27/27 gtest 用例 PASSED；test_package 2/2 PASSED
```

## 禁止做法

- ❌ `BUILD_TESTING=OFF` 跳过上游套件（丢失测试覆盖，或把 consumer 测试冒充上游）
- ❌ 只加 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（不解决 GitHub 不可达）
- ❌ `sed -i` 改上游构建文件绕过补丁管线（不可复现）
- ❌ 把 configure 下载失败 `|| true` 吞掉（配置不完整，CI 前段即挂）

## 适用性与边界

- 适用：上游以 ExternalProject/FetchContent 在 configure 期取 googletest 的
  CMake 项目；制品仓已发布 gtest（OHOS armv8 libc++ 预编译）。
- 边界：若框架未发布，改用 `FETCHCONTENT_SOURCE_DIR_GOOGLETEST=<已核验源码树>`
  注入并记录来源；本方案无法用于框架完全不可获得的情形。
- 反例：上游测试同时依赖非 gtest 的框架（Catch2 等），应查对应条目
  （DRAFT-cmake-test-framework-fetch-to-conan-find-package 覆盖 Catch2 分支）。

## 证据

| 项 | 值 |
|---|---|
| 库 | cpu_features 0.9.0（archives/c/cpu_features/0.9.0） |
| 原始错误 | "CMake step for googletest failed: 1" + CMake<3.5 兼容错误 |
| 补丁 | patches/0001-CMakeLists.txt.patch（+13/-34） |
| 配方 | conanfile.py test_requires gtest/1.17.0 + GTest_DIR |
| 验证 | conan create EXIT=0；上游 27/27；test_package 2/2 |