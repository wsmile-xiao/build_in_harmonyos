# rocm-core

rocm-core 是 ROCm 软件栈的**基础组件**：任何其它 ROCm 包都依赖它来查询 ROCm
的发行版本号与安装路径。它本身只是一段主机侧 C++ 代码，不含任何 GPU 设备逻辑。

## 功能概述

- `getROCmVersion(unsigned int* Major, unsigned int* Minor, unsigned int* Patch)`
  —— 返回编译期固化的 ROCm 版本（`ROCM_VERSION_MAJOR/MINOR/PATCH`）。
- `printBuildInfo()` —— 打印并返回构建信息串 `ROCM_BUILD_INFO`。
- `getROCmInstallPath(char** InstallPath, unsigned int* InstallPathLen)`
  —— 解析 ROCm 安装根目录（优先环境变量 `ROCM_PATH`；共享库模式下回退到
  `dlopen` 自省）。

## OHOS/HarmonyOS 适配要点

- **只做主机侧适配**。平台自带的 OHOS clang 15.0.4（target
  `aarch64-unknown-linux-ohos`）只注册 CPU 后端，既无 `amdgcn`/AMDGCN
  target，设备也无 `/dev/kfd`、`/dev/dri`。rocm-core 本身不含设备代码，
  因此不启用任何 GPU 工具链，也不使用 hipcc。
- 使用 `-DROCM_VERSION=7.2.4` 驱动上游 `utils.cmake` 的版本解析。
- 上游未调用 `enable_testing()`，配方通过 `CMAKE_PROJECT_INCLUDE` 注入
  `enable_testing()`，使 `cmake.test()`（`cmake --build --target test`）可运行。
- 打包时移除上游 `bin/` 下的 python 辅助工具（`rdhc.py`、`runpath_to_rpath.py`），
  它们在 OHOS 上缺少 prettytable/PyYAML/pyelftools 依赖，且会让库包被误判为命令行工具。
- 默认构建**静态库**（`BUILD_SHARED_LIBS=OFF`）：小体量辅助库，静态产物自包含，
  `getROCmInstallPath()` 在静态模式下依赖 `ROCM_PATH`，行为确定。

## 依赖关系

- 无外部依赖（自包含 CMake 项目，零 `requires`/`tool_requires`）。
- 运行期仅依赖 C 运行库。

## 测试

- **层 1（上游测试）**：上游 7.2.4 不附带测试（0 个 ctest 用例，三处清点口径见
  `7.2.4/test_package/MANIFEST.yml`）；配方仍驱动 `cmake.test()`，保留 ctest 执行轨迹。
- **层 2（消费者 API 断言）**：`7.2.4/test_package/test_rocm_core.cpp` 真实链接
  `librocm-core` 并调用导出 C API，31 条断言覆盖正常路径与全部可达错误/边界路径。
- **鸿蒙特有测试（完整消费者端到端用例）**：`7.2.4/test_package/test_rocm_core_ohos.cpp`
  为 OHOS 目标专属（`ROCM_CORE_TEST_OHOS` + `#ifndef __OHOS__ #error` 双重约束），
  3 个具名完整消费者用例——HC-1 安装树发现与真实产物消费 / HC-2 下游版本门禁决策流程 /
  HC-3 安装根重定位流程，实测 3/3 通过（35 项内部检查，0 失败）。

## 参考资料

- 上游仓库：https://github.com/ROCm/rocm-core
- 上游 tag：rocm-7.2.4
