# OHOS Clang linker 的宿主运行库闭包

## 场景

OHOS worker 的 `clang` 可能位于任务工具目录，而它启动的 `lld` 位于版本化
SDK；CMake 的编译器探针在编译阶段正常，链接阶段却报
`Error loading shared library libxml2.so.16` 或一串 `Error relocating ... lld`
错误。

## 根因

目标编译器路径和 linker 的宿主运行库目录不是同一目录。配方为了控制
Conan 的 POSIX 环境文件而用 `env=None` 调 CMake 时，worker 的
`LD_LIBRARY_PATH` 不一定包含 SDK 的 `ohos/native/llvm/lib`，导致 lld 无法
装载自己的 `libxml2.so.16`。这不是目标程序缺少 libxml2，也不应通过把系统
库复制到共享目录来掩盖。

## 修复步骤

1. 从 `tools.build:compiler_executables` 取得 C/C++ 编译器路径，在其同级的
   版本化 `ohos-sdk.org/*/ohos/native/llvm/lib` 中只选择实际包含
   `libxml2.so.16` 的目录。
2. 在 recipe 和 `test_package` 调 CMake 前，把这个任务自有路径前置到当前
   进程的 `LD_LIBRARY_PATH`；不修改系统目录、共享 SDK 或其他任务环境。
3. 如果没有可验证的候选，保持失败并记录缺失闭包；不能猜测路径或使用不相关
   的主机 libxml2。

## 验证方式

先用 CMake 编译器探针验证 lld 能完成链接，再执行完整 `conan create` 和真实
消费者。Squirrel 3.2 的旧 CI 在 `lld` 启动时复现 `libxml2.so.16` 缺失；修复
后应同时看到 recipe 构建和 `test_package` 的链接通过，并将当前 HEAD、SDK
路径与日志哈希绑定到 CI 证据。

## 适用范围与安全边界

适用于 OHOS/arm64 交叉构建中编译器包装器与 LLVM 宿主运行库分离的 worker，
尤其是 Conan/CMake 显式控制环境的配方。它不替代目标 sysroot、依赖 binary、
签名、真机执行或平台 CI；运行库发现必须绑定当前编译器和版本化 SDK，不能把
系统同名库或其他任务目录加入闭包。
