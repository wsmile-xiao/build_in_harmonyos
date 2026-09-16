# 适配笔记 — joltphysics 5.6.0 (HarmonyOS PC aarch64)

**日期**: 2026-09-13 · **任务**: contrib-7359 · **状态**: 构建验证通过

## 概述

- 上游: https://github.com/jrouwe/JoltPhysics tag v5.6.0（tar.gz 1347 文件，
  sha256=6e069ee0172478cc78182047aac87e5310ba14a67a53348ae14cc37801fd3f8e，
  ghfast.top 镜像下载后 `tar tzf` 验证完整性）
- 构建: CMake（cmake_minimum_required 3.20，cmake 4.1.2 直接支持，无 3.5 拒配问题）
- C++17、自包含数学库、153 个 .cpp → libJolt.a（静态，R26 上游主推消费模式）
- 无强制外部依赖（W0 通过：requirements 为空）

## 关键适配点（验证记录）

1. **ARM NEON 路径**：Jolt.cmake 第 986 行 `CMAKE_SYSTEM_PROCESSOR STREQUAL
   "aarch64"` 分支 = "ARM64 uses no special commandline flags"。x86 SIMD 选项
   （USE_SSE4_1/2、AVX/AVX2、LZCNT、TZCNT、F16C）在该分支全不生效。
   显式全关（对 CI 日志可读性有益，R8 合规：无 x86 指令残留风险）。
   **例外：USE_FMADD 必须 ON（上游默认）**——见关键适配点 12（rule4 修复新增）。

2. **llvm-ranlib 坑（实证）**：OHOS SDK 26.0.0.18 的 llvm/bin 只有 llvm-ar
   没有 llvm-ranlib，但 ohos.toolchain.cmake 把 CMAKE_RANLIB 指向缺失路径。
   153 cpp 全编译通过后在 `libJolt.a` 归档一步报
   `Error running link command: no such file or directory`。
   修复：`-DCMAKE_AR=/data/service/hnp/bin/llvm-ar
   -DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib`（hnp 的 llvm 工具链
   Target=aarch64-linux-ohos）。与 assimp-5 5.4.3 notes 同坑。

3. **Vulkan 计算后端**：默认 JPH_USE_VK=ON 时 find_package(Vulkan) 在 OHOS
   sysroot 命中 libvulkan.so（1.4.309），但缺 glslc/glslangValidator 组件，
   shader 编译 add_custom_command 会挂。显式 JPH_USE_VK=OFF + JPH_USE_DX12=OFF
   + JPH_USE_MTL=OFF + JPH_USE_CPU_COMPUTE=ON（CPU 回退路径，上游默认开关值
   即 ON）。物理模拟核心不依赖 GPU compute。

4. **LTO**：INTERPROCEDURAL_OPTIMIZATION=OFF。上游注释明确 ARM whole program
   optimization 会触发内部编译器错误；OHOS 工具链 LTO 慢/不稳。check_ipo_supported
   本可自动跳过，显式关更稳。

5. **构建系统生成器**：Ninja（-G Ninja）。GNU make jobserver 依赖 FIFO，OHOS
   SELinux 禁 mkfifo（知识库 E074）；Ninja 无此依赖。duckdb 1.2.0 / eigenpy
   3.13.0 同法先例。本地实测 make -j8 可跑，但 CI 环境按纪律统一走 Ninja。

6. **平台检测**：Core.h 走 `__linux__` → JPH_PLATFORM_LINUX 标准路径（OHOS
   内核定义 __linux__），Semaphore 用 POSIX sem_init（musl 支持），
   JobSystemThreadPool 用 prctl(PR_SET_NAME)（标准 syscall）。无 glibc 专有
   API（feenableexcept/backtrace 均未使用）→ 无需平台 patch。

7. **编译标志**：ENABLE_ALL_WARNINGS=OFF（上游 -Wall -Werror 在 OHOS clang 15
   下有差异警告）；OVERRIDE_CXX_FLAGS=OFF（保留 profile 的安全编译标志）；
   GENERATE_DEBUG_SYMBOLS=OFF（Release 包不装调试符号）。

## 测试策略

- **上游 UnitTests（doctest 2.5.2，vendored 于 UnitTests/doctest.h，无外部依赖）
  随包构建并真实运行**（rule4 修复，2026-09-13）：`with_tests=True`（默认）时
  TARGET_UNIT_TESTS=ON，build() 阶段编译 71 个测试源文件（Core/Geometry/Math/
  ObjectStream/Physics/SoftBody/Vehicle/Character/Ragdoll/Compute 十套件）并
  通过 `ctest --output-on-failure` 真实执行——OHOS aarch64 本机实测
  **581 test cases / 514281 assertions 全部通过（581/581 PASS，~35 秒）**。
  运行环境：UnitTests 链接 libc++_shared.so（不在 OHOS 默认加载器搜索路径），
  经 `clang++ -print-file-name=libc++_shared.so` 自省定位 SDK libc++ 目录注入
  LD_LIBRARY_PATH（boost/1.85.0 同法先例）。
- test_package 端到端物理仿真（上游 HelloWorld 派生：球体落地→碰撞→休眠，
  静止高度断言 0<Y<1.5，实测 48 步收敛 Y=0.48）验证已安装包的消费视角。
- can_run 判定：OHOS 本机可跑（真实执行 doctest 套件 + test_package 仿真）；
  交叉编译环境只做编译+链接+ELF 魔数校验。

8. **JPH_VERSION_FEATURES ABI 门禁（重要）**：Jolt 在运行时校验消费者与库的
   编译定义集一致性（Core.h JPH_VERSION_FEATURES bit 编码）。默认 Release 构建
   带 JPH_PROFILE_ENABLED / JPH_DEBUG_RENDERER / JPH_OBJECT_STREAM 三个 PUBLIC
   define（Jolt.cmake PROFILER_IN_DEBUG_AND_RELEASE/DEBUG_RENDERER_IN_DEBUG_AND_
   RELEASE/ENABLE_OBJECT_STREAM 默认 ON），CMake 消费者经 find_package 自动继承，
   但命令行编译者必须显式同定义——已在 package_info().defines 暴露，test_package
   从 cpp_info.defines 读取。缺定义时报
   "Version mismatch, make sure you compile the client code with the same Jolt
   version and compiler definitions!"（abort -6）。

9. **JPH_PROFILE_ENABLED 的接口涟漪**：BroadPhaseLayerInterface 的
   GetBroadPhaseLayerName 在 JPH_PROFILE_ENABLED 下变为纯虚函数，消费者
   BroadPhaseLayerInterface 实现类必须提供（HelloWorld.cpp 有 #if 守卫示范）。

10. **libc++_shared.so 运行时**：OHOS clang 默认动态链接 libc++_shared.so，
    不在加载器默认搜索路径。`clang++ -print-file-name=libc++_shared.so` 自省
    定位 SDK libc++ 目录（llvm/lib/aarch64-linux-ohos）注入 LD_LIBRARY_PATH
    （boost/1.85.0 同法）。缺它报 rc=127 大量 std::__n1 符号重定位失败。

11. **NDEBUG 传递**：test 二进制编译必须 -DNDEBUG 匹配 Release 库——否则
    Core.h 激活 JPH_DEBUG→JPH_ENABLE_ASSERTS→引用 JPH::AssertFailed 符号
    （Release 库无此符号，链接失败 undefined symbol）。

12. **USE_FMADD 在 aarch64 上不是无效选项（rule4 攻坚实证，重要）**：
    首版适配把 USE_FMADD 与其他 x86 SIMD 选项一起 OFF，理由是"ARM64 走 no
    special commandline flags 分支"。**实测推翻**：Build/CMakeLists.txt 第
    263-273 行——`CROSS_PLATFORM_DETERMINISTIC OR NOT USE_FMADD` 为真时加
    `-ffp-contract=off`，而 Jolt/Core/Core.h 第 134 行在 aarch64 上因
    `__ARM_FEATURE_FMA`（ARMv8 基线特性）**自动定义 JPH_USE_FMADD**——即
    编译时代码走 FMA 分支（Vec3/Vec4::sDifferenceOfProducts 用 NEON
    vmlaq_f32），但 `-ffp-contract=off` 让 clang 把 vmlaq_f32 内在函数降级为
    分离的 mul+add（融合被禁），上游 TestDifferenceOfProducts 断言融合结果
    必然失败（Vec3Tests.cpp:463 / Vec4Tests.cpp:862，得 -128/64/0 而期望
    -75.1656/103.169/36.8369）。最小复现（OHOS clang --target=aarch64-linux-ohos
    -O2 -ffp-contract=off/on/fast 对比）：off → dop=-128.0（失败），on →
    result=-75.165604（融合正确，汇编 fmla v.4s 真实生成）。**修复：恢复
    上游默认 USE_FMADD=ON**（ARM64 分支不加 -mfma 之类的 flag，只影响
    ffp-contract 走向），581/581 全绿。此坑亦解释了为何 aarch64 上游默认
    USE_FMADD=ON 而非 x86 之外的摆设。

## 遗留

- shared=True 构建路径已留 options 接口但默认 False（上游文档主推静态链接，
  JPH_SHARED_LIBRARY 符号导出宏需消费者配合）。
- DOUBLE_PRECISION / USE_ASSERTS / CROSS_PLATFORM_DETERMINISTIC 作为 conan
  options 暴露（保持上游默认 OFF）。
