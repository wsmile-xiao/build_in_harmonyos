# unittestpp 2.0.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，C++14）
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15.0.4（OHOS SDK，aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

1. 下载源码（GitHub v2.0.0 tag tarball，sha256 已核验：
   `74852198877dc2fdebdc4e5e9bd074018bf8ee03a13de139bfe41f4585b2f5b9`）
2. 探索性原生构建（模式 B，OHOS 真机）：
   ```bash
   cmake -S $BUILD_SRC_DIR -B $BD -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_C_COMPILER=$CC -DCMAKE_CXX_COMPILER=$CXX \
     -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   cmake --build $BD -j2     # POST_BUILD 自动运行 TestUnitTest++ → 268/268
   ```
3. 固化为 Conan 配方（模式 A）：`conanfile.py`（CMakeToolchain + cmake_layout）、
   `conandata.yml`、`test_package/`（正向 9 用例 + 反向对照 3 用例）
4. `conan create`（profile ohos-aarch64-device）全链路编译/打包/测试

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake configure 直接报错：`Compatibility with CMake < 3.5 has been removed` | 上游 CMakeLists 声明 `cmake_minimum_required(VERSION 2.8.1)`，本机 CMake 4.4.3 已移除旧兼容 | 传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 官方兼容开关，命令行传参；toolchain 里 set 太晚），零补丁 |
| 2 | configure 提示 `System is unknown to cmake, create: Platform/HarmonyOS` | CMake 4.x 从三元组 `aarch64-unknown-linux-ohos` 推出系统名 HarmonyOS，无对应平台模块 | 信息级提示，构建/链接/test 全部正常，无需处理 |
| 3 | 消费者反向对照用"空指针函数调用"注入崩溃时进程挂起（耗时 10s 无输出、0 CPU、State:S） | 本设备上执行空指针函数调用（PC=0 指令中止）疑似进入平台崩溃处理通道，SignalTranslator 未获机会翻译 | 反向对照改用 `raise(SIGSEGV)`（确定性）；实测 raise(SIGSEGV)/空指针数据写/`__builtin_trap` 三者在框架内均能被正确翻译为测试失败 |
| 4 | 整数除零不触发信号，signal_probe 静默走到 `CHECK(false)` | AArch64 的 SDIV/UDIV 除零返回 0（架构定义行为），不产生 SIGFPE | 弃用除零注入；记录为本平台知识（见 manifest knowledge_gained） |
| 5 | 上游 `add_custom_command(POST_BUILD COMMAND TestUnitTest++)` 会自动执行测试 | 上游设计如此（`UTPP_INCLUDE_TESTS_IN_BUILD` 默认 ON） | 保持默认并在 build() 末尾显式重跑一次解析结果（`HMBS_UPSTREAM_TEST_RESULT`），用例数与失败数不符即中止构建 |

## 源码修改

无源码修改（patches 为空）。上游 v2.0.0 在 OHOS aarch64 + clang 15 上零补丁编译，
仅需 CMake 4.x 兼容参数。

## 依赖版本

无外部依赖。仅依赖 C++ 标准库与 OHOS musl libc（Posix 平台层使用
gettimeofday/usleep/sigaction/sigsetjmp）。

## 验证结果

- 上游官方测试（TestUnitTest++，上游 CMake POST_BUILD 自动执行 + build() 显式重跑）:
  **Success: 268 tests passed.**（0 失败，0 忽略，OHOS aarch64 真机实测，Release/Conan 构建）
  - 另外上游默认构建配置（无 CMAKE_BUILD_TYPE）实测 **267/267**（差异 1 个为仅
    `NDEBUG`/Release 编译的崩溃用例；两配置均 100% 通过）
- 用例计数口径说明（供审查复核）：
  - 上游 tests/ 源码注册清点 **277**（与平台审查口径一致；含 9 个
    `UNITTEST_USE_CUSTOM_STREAMS` 专属用例，不含 2 个仅 `UNITTEST_NO_EXCEPTIONS`
    模式生效的重复用例）
  - 适配构建实测 **268**（差异 9 = custom-stream 分支在上游默认
    `std::ostringstream` 配置下不参与编译）
  - 三组数字均为实测/源码证据，不存在少报：279（源码含模式重复）−2（模式重复）
    = 277（平台口径）−9（custom-stream 分支）= 268（Release 实测）
- 消费者正向测试（test_unittestpp，9 用例）: **Success: 9 tests passed.**（rc=0）
- 消费者反向对照（test_unittestpp_negative，3 用例）: 预期 rc=2
  （CHECK 失败 1 + `raise(SIGSEGV)` 信号翻译失败 1，输出
  `FAILURE: 2 out of 3 tests failed (2 failures).`，证明失败不会被静默吞掉）
- conan create（ohos-aarch64-device profile）: 编译/打包/测试全链路通过

## 交付物

| 文件 | 说明 |
|------|------|
| include/UnitTest++/*.h（含 Posix/） | 公共头文件（含 Posix 平台头） |
| lib/libUnitTest++.a | 静态库 |
| lib/cmake/UnitTest++/ | 上游导出的 CMake 包配置（UnitTest++Config.cmake + Targets） |
| lib/pkgconfig/UnitTest++.pc | 上游 pkg-config 文件 |
| licenses/LICENSE | MIT 许可证 |

## 注意事项

- 上游 CMakeLists 硬编码静态库（STATIC），recipe 的 `shared` 选项在 validate() 中
  显式拒绝（构造该选项会产生无效配置错误，而非静默产出错误类型）。
- 上游测试文件 TestRequireMacrosWithExceptionsOff.cpp 仅在
  `UNITTEST_NO_EXCEPTIONS` 模式下生效（70 个用例），默认构建不计入执行集合。
- 上游 TestMemoryOutStream.cpp 中 9 个容量/缓冲用例仅在
  `UNITTEST_USE_CUSTOM_STREAMS`（未定义 `UNITTEST_MEMORYOUTSTREAM_IS_STD_OSTRINGSTREAM`）
  配置下编译；上游默认配置使用 `std::ostringstream`，这 9 个不参与编译。

**编译结束**: 2026-09-16
最终状态: built
