# DRAFT: 上游 find_package(googletest) 与 registry gtest 包 CMakeDeps 目标名不一致时用测试专用 INTERFACE shim 桥接

## 基本信息
- **严重度**: 2
- **类别**: testing | cmake | conan | gtest
- **作者**: AtomCode (executor pc7-24)
- **来源任务**: glbinding 3.5.0 适配（task glbinding-3.5.0-r01-pc7-24）

## 错误特征
```
-- Tests skipped: googletest not found
（上游测试目标未注册，双口径台账只剩枚举、无法实际运行）

或者（REQUIRED 时）：
CMake Error ... googletest::googletest but the target was not found
```

## 根因分析
- registry（ohpcd）的 `gtest/1.17.0` 包由发版配方决定 CMakeDeps 包名与目标：
  生成 `gtest-config.cmake`，暴露 `gtest::gtest`（含 `gtest/gtest.h` 与 `libgtest.a`）。
- 上游库（glbinding 3.5.0）的测试目录按 GoogleTest 官方惯例写
  `find_package(googletest QUIET)` 并链接 `googletest::googletest`。
- 两处命名（包名 `gtest` vs `googletest`、目标名 `gtest::gtest` vs
  `googletest::googletest`）不一致时，CMakeDeps 无法自动对账：
  - `find_package(googletest)` 找不到 → QUIET 模式下测试被静默跳过；
  - 若上游用 REQUIRED 则直接配置失败。

## 推荐方案（四步桥接，glbinding 实证 16/16 用例通过）
1. 用 registry 安装测试依赖到独立测试目录：
   `conan install --requires=gtest/1.17.0 --requires=glfw/3.5.1 ... -g=CMakeToolchain -g=CMakeDeps -of $TESTDEPS`
2. 写测试专用 shim 的 `googletest-config.cmake`：
   - **必须先** `include($TESTDEPS/cmakedeps_macros.cmake)`（其中定义
     `conan_find_apple_frameworks` 等宏，直接 include gtestTargets.cmake 会报
     `Unknown CMake command "conan_find_apple_frameworks"`）；
   - 再 `include($TESTDEPS/gtestTargets.cmake)`；
   - 然后 `if(NOT TARGET googletest::googletest)` 创建
     `add_library(googletest::googletest INTERFACE IMPORTED)` 并把
     `INTERFACE_LINK_LIBRARIES` 指向 `gtest::gtest`。
3. 配置测试工程时传：
   `-Dgoogletest_DIR=$SHIM -DCMAKE_PREFIX_PATH=$TESTDEPS`。
4. 若上游 main 用 `InitGoogleMock`（gmock），gtest 包内 `libgmock.a` 与
   `libgtest.a` 并列存在，需 `find_library(gmock PATHS <gtest pkg lib>)`
   显式链接（`gtest::gtest` 目标默认不含 gmock）。

## 验证/命令
```
# shim 文件（测试专用，不进交付配方）
cat > $SHIM/googletest-config.cmake <<'EOF'
include($TESTDEPS/cmakedeps_macros.cmake)
include($TESTDEPS/gtestTargets.cmake)
if(NOT TARGET googletest::googletest)
  add_library(googletest::googletest INTERFACE IMPORTED)
  set_property(TARGET googletest::googletest PROPERTY INTERFACE_LINK_LIBRARIES gtest::gtest)
endif()
EOF

cmake -B build -S <upstream tests> \
  -DCMAKE_TOOLCHAIN_FILE=$TESTDEPS/conan_toolchain.cmake \
  -DCMAKE_PREFIX_PATH=$TESTDEPS -Dgoogletest_DIR=$SHIM \
  -DCMAKE_AR=... -DCMAKE_RANLIB=...
cmake --build build -j4
LD_LIBRARY_PATH=<glfw pkg lib> ./build/glbinding-test
# 结果：16 tests from 7 test suites ran, 16 passed
```

## 适用边界
- 仅用于**上游测试的本地构建与运行台账**；交付的 `conanfile.py`/`test_package`
  不应携带 shim（主配方 test_package 用正确目标名）。
- 对 `find_package(GTest)`（大写）或 `FetchContent` 拉取 googletest 的工程不适用，
  需按 E342（禁用联网上游测试/离线化）另行处理。
- 双口径台账：shim 让"配置可执行集合"从 0 恢复到上游注册数（glbinding 16/16 通过），
  源码声明总数不变（18，其中 2 个未注册文件仍 uninstantiated）。

## 关系
- similar_to: E342（googletest 测试获取/离线），DRAFT-400（CMakeDeps 目标断链）
- 覆盖差异：E342 解决"没有 gtest 可用"，本条目解决"有 gtest 但包名/目标名不匹配"；
  两者可组合使用。
