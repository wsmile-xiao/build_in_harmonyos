# libsbp 6.5.1 适配笔记

## 基本信息

- 上游：https://github.com/swift-nav/libsbp（tag v6.5.1）
- 类型：纯 C 库（SBP 二进制协议编解码：34 个消息模块的生成 C 源 + edc CRC + sbp 帧核心 + string 容器）
- 构建系统：CMake >= 3.13（swift-nav cmake 框架，submodule 提供）
- 许可证：MIT
- 零 conan 依赖（库本体无任何运行时依赖）

## 依赖分析

| 依赖 | 上游形态 | 适配决策 |
|------|---------|---------|
| swift-nav/cmake | git submodule（c/cmake/common） | source() 按 v6.5.1 锚定 commit d5558e3 下载补齐（E150） |
| googletest | git submodule（c/third_party/googletest） | 仅测试期依赖，同上按 commit b796f7d 补齐，不进 requirements |
| 库本体运行时依赖 | 无 | 零依赖纯 C |

## 关键决策与理由

### 1. submodule 补齐（E150 manual-download 模式）

GitHub tag tarball 只含 .gitmodules 不含 submodule 内容，CMake configure
第一步 `include(SwiftCmakeOptions)` 即失败。conandata.yml `submodules:` 段
按 v6.5.1 tree 中锚定的两个 submodule commit（GitHub contents API 查询：
swift-nav/cmake@d5558e3ad3c2、google/googletest@b796f7d446）精确下载，
sha256 固定，可复现。

### 2. patch 0001：SKIP_CROSS_COMPILING_CHECK

`swift_create_project_options()` 在 CMAKE_CROSSCOMPILING 时无条件
`set(tests_possible OFF)`（SwiftCmakeOptions.cmake:202-207）。上游框架
自带逃生口 `SKIP_CROSS_COMPILING_CHECK`（跳过交叉编译检查），一行 patch
加入 CMakeLists 的 swift_create_project_options 调用即可在 OHOS 交叉
工具链下构建测试目标。

### 3. 测试执行方式（swift_add_test 不注册 ctest）

swift cmake 框架的 swift_add_test 只创建 `do-<name>` custom target，
不调用 add_test——上游测试不能 ctest 驱动。build() 流程：
`cmake.build()`（库本体）→ `cmake.build_target("build-all-tests")`
（三个测试二进制）→ 直接运行二进制（can_run 时）。

- test/test-libsbp：249 用例（手写 edc/sbp/bitfield/utils + 240 auto_check roundtrip）
- test/cpp/test-libsbp-cpp：12629 用例（439 个 DISABLED_SlowWrite 上游默认跳过）
- test/string/test-libsbp-string：46 用例

### 4. OHOS 运行时注意点

- 测试二进制链接 libc++_shared.so：musl ld.so 需
  `LD_LIBRARY_PATH=/system/lib64`（scnlib/glib2 同款先例）
- 库本体纯 C，交付静态 .a，消费者测试仅依赖 libc

### 5. 构建产物

- lib/libsbp.a（目标名 sbp，install 别名 swiftnav::sbp）
- include/libsbp/*.h + 子目录（全部消息定义头）
- share/libsbp/cmake/（libsbpConfig.cmake 导出，find_package(libsbp) 可用）

## 上游测试实测（2026-09-16，OHOS aarch64 clang 15）

| 套件 | 注册用例 | 实跑 | 通过 |
|------|---------|------|------|
| test-libsbp | 249 | 249 | 249 ✅ |
| test-libsbp-cpp | 12629 | 12190 | 12190 ✅ |
| test-libsbp-string | 46 | 46 | 46 ✅ |
| 合计 | 12924 | 12485 | 12485 ✅（439 = 上游 DISABLED_SlowWrite 默认跳过） |

## 版本号策略

6.5.1 = 上游 tag v6.5.1 原版（首次适配，无适配修复后缀）。
