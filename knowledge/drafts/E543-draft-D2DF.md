# E543 — init-build URL 关键字误判 CMake 项目 + Catch2 CMakeDeps 缺模块路径

## 错误特征

- `init-build` 输出 `.build-context-<lib>-<ver>` 中 `BUILD_SYSTEM="autotools"`，`conan-init` 提示
  `conanfile.py 模板不可用（autotools）` 并生成 autotools 模板配方，而源码根目录只有 `CMakeLists.txt`；
- 配置上游 Catch2 测试时：`CMake Error ... include could not find requested file: Catch` /
  `Unknown CMake command "catch_discover_tests"`。

## 触发条件

- 构建系统: CMake（源码含 CMakeLists.txt），但源 URL 不含 "cmake" 字样（典型 codeload
  `https://codeload.github.com/<owner>/<repo>/tar.gz/refs/tags/<tag>`）；
- 阶段: init-build / conan-init / 测试配置（configuration、testing）；
- 上游测试用 Catch2 3.x 的 `include(Catch)` + `catch_discover_tests()`，且通过 Conan 2 CMakeDeps
  （CMakeToolchain + CMakeDeps）提供 Catch2。

## 根因分析

1. `init_build.py` 的构建系统检测是 URL 关键字启发式：URL 含 "cmake" → cmake，否则回退 `autotools`。
   codeload refs/tags 归档 URL 末段是 tag 名、不含 "cmake" → CMake 项目被误判为 autotools，
   随后 `conan-init` 按 autotools 模板生成错误配方（configure/make），与真实构建系统不符。
2. 上游 `tests/CMakeLists.txt` 的 `include(Catch)` 需要 `Catch.cmake` 模块文件在 `CMAKE_MODULE_PATH`
   中；Conan 2 CMakeDeps 生成的 Catch2 config 只提供 target/路径变量，不自动把
   `<catch2 包>/lib/cmake/Catch2` 加入 `CMAKE_MODULE_PATH`，因此 `catch_discover_tests` 无法解析。

## 解决方案

### 推荐方案

1. init-build 后按源码实际标记核对构建系统（`ls $BUILD_SRC_DIR/CMakeLists.txt`），CMake 项目用
   `templates/conanfile-cmake.py.tmpl` 重写 `conanfile.py`（`CMake`/`CMakeToolchain`/`cmake_layout`），
   不要沿用 autotools 模板；
2. 配置测试构建时显式传入 Catch2 模块路径：
   `-DCMAKE_MODULE_PATH=$(find ~/.conan2/p -name Catch.cmake -path "*cmake/Catch2*" | xargs dirname)`；
3. 重跑 `conan-verify`（G1-G4/L2/L4/L5）与上游测试确认。

### 禁止做法

- ❌ 用 `sed` 改 init-build 检测逻辑或伪造构建系统标记绕过（掩盖真实构建系统，配方与源码不符）；
- ❌ 空壳 test_package（R34/PF3 拦截）。

## 验证

```bash
# 真实构建系统核对
test -f "$BUILD_SRC_DIR/CMakeLists.txt" && echo "cmake"
# 配方验证
python3 scripts/ohc-run.py conan-verify microservice-essentials 0.1.0   # G1-G4/L2/L4/L5 PASS
# 上游测试配置 + 实跑（36/36 通过，707 assertions）
./tests   # All tests passed (707 assertions in 36 test cases)
```

microservice-essentials 0.1.0 实测：conan-verify 全过、上游测试 36/36、finish W3 本地 CI 通过。

## 关联条目

- 相关: E195（CMakeLists.txt 关键字相似，根因不同）、E216（CMakeDeps 组件传播）、E393（CMakeAutoGen 模块路径）
