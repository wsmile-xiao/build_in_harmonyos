# rtm — OpenHarmony PC 适配

## 基本信息
- 软件: rtm (Realtime Math)
- 版本: 2.3.1
- 描述: Nicholas Frechette 的 SIMD 优化数学库，提供标量/向量/矩阵/四元数/
  变换（QV/QVS/QVV）等类型，header-only C++（C++17）
- 构建系统: CMake（仅安装头文件 + 驱动测试，无编译产物）
- 目标平台: ohos-aarch64 (aarch64-linux-ohos)
- 上游: https://github.com/nfrechette/rtm
- License: MIT

## 编译指导
- header-only 库，`conan create` 仅解包源码 + 拷贝 includes/ 头文件
- 无 configure/make/编译步骤
- 上游测试：tests/main_generic（Catch2 + CTest，175 用例全通过）

## 补丁清单
- patches/0001-cmake-CMakePlatforms.cmake.patch:
  CMakePlatforms.cmake 识别 `CMAKE_SYSTEM_NAME=HarmonyOS` 为 Linux 系平台
  （aarch64-linux-ohos 为 Linux 内核），使上游测试/CI 可在 OHOS 配置下构建

## 使用
- 消费者 include `<rtm/vector4f.h>`、`<rtm/quatf.h>` 等
- CMake: `find_package(rtm REQUIRED)` + `target_link_libraries(... rtm::rtm)`
