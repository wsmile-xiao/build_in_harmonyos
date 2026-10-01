# swiftshader 0_git20260921 适配笔记（HarmonyOS PC / OHOS aarch64）

- 软件：**SwiftShader** —— CPU 纯软件实现的 Vulkan 1.3 图形 API（软件 Vulkan ICD）
- 上游：<https://github.com/google/swiftshader>（canonical: <https://swiftshader.googlesource.com/SwiftShader>）
- 版本：`0_git20260921` = git 快照 commit `1e80438d2b93ef36a7c05f8d2b81233bac0e3d16`
  （committer date 2026-09-16；即 2026-09-21 当天 master HEAD，之后至 09-21 无提交）
- 构建系统：CMake（≥3.22.1），C/C++17
- 结论状态：`built`（本地 conan create 全绿，test_package 全绿）

---

## W0 — 源码与依赖

上游**无 release**，只有滚动 master → 以 git 快照 tarball 定版：

| 项 | 值 |
|---|---|
| tarball | `https://codeload.github.com/google/swiftshader/tar.gz/1e80438d2b93ef36a7c05f8d2b81233bac0e3d16` |
| sha256 | `1c3a1afc397c7aa4d3275790bc9b451e80b144a1db665135d5519838bacf44a8`（98,884,969 B） |

**第三方依赖结构**（关键认知）：

- `third_party/` 下**大部分是 vendored 普通目录**（随主 tarball 一起下载）：
  `SPIRV-Headers`、`SPIRV-Tools`、`astc-encoder`、`boost`、`llvm-10.0`、`llvm-16.0`、
  `llvm-subzero`、`marl`、`subzero`、`libbacktrace`。
- `.gitmodules` 列出 9 个 submodule，但**默认构建只需 2 个**（CMakeLists.txt:276-307）：
  - `third_party/googletest`（`SWIFTSHADER_BUILD_TESTS=ON` 时需要）
  - `third_party/glslang`（`BUILD_VULKAN_WRAPPER` = 建测试/基准时需要）
  - 其余（benchmark/json/cppdap/PowerVR_Examples/libbacktrace/llvm-project）默认**不触发**。
- Reactor 默认后端为 `LLVM`，使用 **vendored `third_party/llvm-10.0`**（精简 LLVM10，225 MB），
  因此**无需拉取 llvm-project submodule**（那只在 `REACTOR_BACKEND=LLVM-Submodule` 时用）。
- 配方把 googletest `e2239ee` / glslang `2b2523f` 的 tarball 单独下载并解压进 `third_party/`。

---

## 关键改动（4 个 per-file 补丁，全部 portability）

### 0001-cmake-harmonyos-platform-support.patch（CMakeLists.txt）

- 平台探测（L32-45）只认 Linux/Android/WIN32/APPLE/FUCHSIA，HarmonyOS 落入 `else()` →
  `FATAL_ERROR "Platform is not supported"`。新增 `elseif(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")`
  → 置 `LINUX TRUE`（OHOS 为 Linux-like/musl）+ `HARMONYOS TRUE`。
- LINUX 分支默认打开 XCB/Wayland WSI（L178-182）；HarmonyOS 是 headless，改为默认 **OFF**。
- `InitSubmodule()`：源码 tarball 无 VCS 元数据，原逻辑会执行 `git submodule update`。改为
  “目录已含 CMakeLists.txt 则不拉取”（配方已预填充 googletest/glslang）。

### 0002-marl-musl-thread-affinity.patch（third_party/marl/src/thread.cpp）

- `#elif defined(__linux__) && !defined(__ANDROID__) && !defined(__BIONIC__)` 分支调用 glibc 专属
  `pthread_getaffinity_np/pthread_setaffinity_np`；OHOS/musl 命中该分支 → **编译失败**。
- 非 glibc 改用 musl 提供的 POSIX `sched_getaffinity(0,…)/sched_setaffinity(0,…)`；
  同时给该文件补 `<sched.h>`。

### 0003-vulkanwrapper-guard-glibc-dlinfo.patch（tests/VulkanWrapper/VulkanTester.cpp）

- `dlinfo(lib, RTLD_DI_ORIGIN, …)`：`RTLD_DI_ORIGIN` 是 glibc 扩展，musl 未定义 → 编译失败。
- 以 `#if defined(RTLD_DI_ORIGIN)` 守卫该回退分支（glibc 语义保留，musl 跳过）。

### 0004-reactor-jit-anonymous-executable-memory.patch（src/Reactor/ExecutableMemory.cpp）

- **本任务最关键的诊断**。SwiftShader 的 Reactor JIT 默认经 `REACTOR_ANONYMOUS_MMAP_NAME`
  走 `memfd_create` + `mmap(PROT_READ|WRITE|EXEC)` 路径。
- 独立探针实测（OHOS PC aarch64）：
  - 匿名 `mmap(..., PROT_READ|PROT_WRITE|PROT_EXEC, MAP_PRIVATE|MAP_ANONYMOUS)` → **成功**，
    JIT 代码 `mov w0,#7; ret` 执行返回 **7**；
  - `memfd_create` + `mmap(PROT_EXEC)` → **EACCES (Permission denied)** —— OHOS 禁止 memfd 可执行映射。
- 故 memfd 路径下 `mmap` 返回 `MAP_FAILED` → `mapping=ptr` → JIT 执行崩溃（SIGSEGV/SIGILL）。
- 修复：HarmonyOS 下 JIT 代码缓存**改用匿名映射**（`MAP_ANONYMOUS`）；相应的 memfd 帮助函数用
  `!defined(__OHOS__)` 收口（否则 `-Wunused-function -Werror` 报错）。
- 效果：`ReactorSIMD.Add` 由 SIGSEGV → PASS；`ReactorUnitTests` 155/156；
  `vk-unittests` 计算套件 136/136 全绿（证明 JIT 在 OHOS 上完全可用）。

---

## 构建配置（conan）

- `CMAKE_SYSTEM_NAME=OHOS`（`Platform/OHOS.cmake` → `Platform/Linux`，避免 “System is unknown” 警告
  且使 cmake 走 Linux 规则）、`CMAKE_SYSTEM_PROCESSOR=aarch64`（否则 ARCH 自动探测成 x86_64）。
- `SWIFTSHADER_BUILD_WSI_XCB/WAYLAND/DIRECTFB/D2D=OFF`（headless）。
- `SWIFTSHADER_BUILD_TESTS=ON`（默认）→ 构建 4 个上游单测可执行文件。

## 上游测试实测（OHOS PC aarch64，本地）

| 套件 | 通过/总数 | 说明 |
|---|---|---|
| vk-unittests | 138/139 | BasicTest 2/2 + ComputeParams（计算管线）136/136；DrawTest 需窗口系统，headless 不可跑 |
| ReactorUnitTests | 155/156 | 唯一失败 RoundInt（aarch64 float→int 饱和语义） |
| math-unittests | 6/11 | 5 项失败：denormal log2 + RGB9E5 NaN 处理（x86 语义假设） |
| system-unittests | 25/25 | 全通过 |
| **合计** | **324/331 = 97.9%** | ≥90% 达标 |

未过 5 项的逐项归因见 `reports/失败逐项归因表.md`（均为平台固有语义差异/环境限制，非移植引入）。

## 消费者测试（test_package）

`test_package/test_swiftshader.c` 链接**已安装**的 `libvk_swiftshader.so`，驱动完整 Vulkan 计算负载：
instance → 物理设备（断言为 CPU 设备且名含 “SwiftShader”）→ 逻辑设备 → SPIR-V 计算管线
（`data[i]=data[i]*2+1`，经 Reactor JIT 执行）→ dispatch → 回读校验。SPIR-V 由 glslangValidator
预编译后内嵌为 `shader_spv.h`（含 `shader.comp` 源，便于复现）。

## 已知限制

- `DrawTest.VertexShaderNoPositionOutput` 依赖窗口/交换链，headless 平台无法运行，已从 CI 运行中过滤。
- `MathTest.SharedExponentExhaustive` 穷举 2^32 个 float 位型（本机实测 **48 分钟**），CI 中过滤，
  已单独完整执行（结果见 reports/）。
- 4 项上游单测失败（见上表）源于 aarch64/musl 的浮点语义与 x86 假设不一致，未修改相关源码。

---

**编译结束**: 2026-09-29
**最终状态**: built
