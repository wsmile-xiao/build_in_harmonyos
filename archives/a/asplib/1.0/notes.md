# asplib 1.0 适配笔记

## 编译环境
- 构建系统: CMake (C++11)
- 编译日期: 2026-08-25
- 编译器: clang 15.0.4 / clang++ (OHOS SDK)
- 状态: built

## 编译步骤

1. `init-build` 下载源码: https://github.com/AchimTuran/asplib/archive/refs/heads/master.tar.gz
2. 修改源码以适配 OHOS (4个补丁)
3. CMake 配置: `cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5`
4. 编译: `cmake --build . -j1`
5. 安装: `make install DESTDIR=...`
6. conan-init 生成配方骨架，AI 完善 conanfile.py (CMakeToolchain)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required(VERSION 3.0) 失败 | CMake 4.x 不再兼容 < 3.5 | 改为 cmake_minimum_required(VERSION 3.5) |
| 2 | CMAKE_SYSTEM_NAME 不匹配 "Linux" | OHOS 上 CMAKE_SYSTEM_NAME="HarmonyOS" | 添加 "OHOS" 和 "HarmonyOS" 到平台检查 |
| 3 | NEON_2_SSE.h 未找到 | NEON2SSE 通过 git clone 下载，Conan 构建环境中不可用 | 跳过 NEON2SSE git clone (aarch64 上 NEON 原生) |
| 4 | ASPLIB_NEON 未定义 | 在 aarch64 上应使用 arm_neon.h 而非 NEON2SSE | 在 CMake 中定义 -DASPLIB_NEON |
| 5 | cpuid.h x86-only 错误 | ComputeDeviceInfo 模块使用 x86 CPUID 指令 | 禁用 ComputeDeviceInfo 模块 (aarch64 上不可用) |
| 6 | pmmintrin.h/immintrin.h 未找到 | SSE3/AVX ComplexVector 文件包含 x86 专用头文件 | 按 CMAKE_SYSTEM_PROCESSOR 条件编译，排除 x86 文件 |
| 7 | non-const lvalue reference 绑定临时对象 | NativeFloat operator*(float) 返回引用 | 改为返回值 (bugfix) |
| 8 | PortAudio/KissFFT 外部依赖 | AudioInterfaces/FFT/SpectrumVisProcessor/Convolution 模块需要外部依赖 | 禁用这些模块 (asplib 自包含部分仍可用) |

## 源码修改

| 补丁文件 | 修改内容 |
|---------|---------|
| 0001-CMakeLists.txt.patch | cmake_minimum_required 3.0→3.5; 添加 OHOS/HarmonyOS 平台检测; 定义 ASPLIB_NEON |
| 0002-asplib_modules-CMakeLists.txt.patch | 跳过 NEON2SSE git clone; 禁用 AudioInterfaces/FFT/Convolution/SpectrumVisProcessor/ComputeDeviceInfo 模块 |
| 0003-asplib_modules-Core-CMakeLists.txt.patch | 移除 NEON2SSE include 路径; 按架构条件排除 SSE3/AVX 源文件 |
| 0004-asplib_ComplexVector_NativeFloat.hpp.patch | 修复 operator* 返回临时对象引用的 C++ bug |

## 依赖版本

无外部依赖。asplib 自包含 C/C++ 库。

## 验证结果

```bash
# 探索性编译验证 (手动)
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build . -j1
# → 100% built, 8 static libraries generated

# 产物列表
libasplib_Biquad.a
libasplib_Core.a
libasplib_Dynamics.a
libasplib_IIR.a
libasplib_Logger.a
libasplib_Resampling.a
libasplib_Signals.a
libasplib_Timer.a
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (CMakeToolchain, package_type=library) |
| conandata.yml | 源码 URL + sha256 + 4 个补丁声明 |
| test_package/test.cpp | Biquad 滤波器 API 测试 (R34) |
| test_package/CMakeLists.txt | C++ 测试构建 |
| test_package/conanfile.py | Conan 测试配方 |
| patches/0001-0004 | 4 个适配补丁 |
| manifest.yaml | 编译元数据 |
| notes.md | 本文件 |

## 注意事项

- 8 个自包含模块已编译: Core, Biquad, IIR, Dynamics, Logger, Signals, Timer, Resampling
- 4 个模块被排除: AudioInterfaces (需 PortAudio), FFT/SpectrumVisProcessor/Convolution (需 KissFFT), ComputeDeviceInfo (x86-only)
- lld 链接器需要 libxml2.so.16，使用 `-fuse-ld=bfd` 作为替代
- 源码中 TARGET_LINUX 定义通过 `__linux__` 预处理器宏自动回退 (asplib_os.h)，即使 CMake 不添加 -DTARGET_LINUX 也能工作
---

**编译结束**: 2026-08-25 10:03
**最终状态**: built
