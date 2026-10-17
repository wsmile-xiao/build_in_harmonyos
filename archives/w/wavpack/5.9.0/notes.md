# wavpack 5.9.0 适配笔记

## 基本信息
- 软件: WavPack (wavpack)
- 版本: 5.9.0
- 上游: https://github.com/dbry/WavPack
- 许可证: BSD-3-Clause
- 构建系统: CMake (源码同时提供 autotools)

## 适配决策

### 构建系统选择: CMake
- WavPack 5.9.0 同时提供 CMakeLists.txt 和 configure (autotools)
- 选用 CMake 避免 config.guess/config.sub 补丁和 shebang/umask 修复
- 使用 libdeflate 模式: 自发现 ohos.toolchain.cmake + 裸 cmake,绕开 conan_toolchain (ML-0035)

### 构建选项
- `BUILD_SHARED_LIBS=ON`: 共享库 (非系统同名库,默认动态)
- `WAVPACK_BUILD_PROGRAMS=OFF`: 禁用命令行工具 (wavpack/wvunpack/wvtag/wvgain),消除 iconv 依赖
- `WAVPACK_ENABLE_THREADS=ON`: 启用线程支持
- `WAVPACK_ENABLE_DSD=ON`: 启用 DSD 音频支持
- `WAVPACK_INSTALL_CMAKE_MODULE=ON`: 安装 CMake 配置文件
- `BUILD_TESTING=ON`: 构建上游 wvtest 并在 OHOS 环境原生运行 (见下「测试」)
  - wvtest (cli/wvtest.c) 仅链接 libwavpack + Threads + m，不依赖 iconv
  - iconv 仅 wavpack/wvunpack 等 CLI 程序需要，已由 WAVPACK_BUILD_PROGRAMS=OFF 关闭

### 无需补丁
- CMake 构建不需要 config.guess/config.sub 补丁
- 无需修改源码

## 依赖
- 无外部编译依赖 (仅标准 C 库)
- 命令行工具需要 iconv,已通过 WAVPACK_BUILD_PROGRAMS=OFF 禁用

## 产物
- libwavpack.so (共享库)
- include/wavpack/wavpack.h (头文件)
- lib/cmake/WavPack/ (CMake 配置)
- lib/pkgconfig/wavpack.pc (pkg-config)

## 测试

### 上游官方测试 (L1)
- wvtest (cli/wvtest.c): libwavpack 测试器，在 conanfile.py build() 末尾由
  `ctest --output-on-failure` 原生运行于 OHOS 环境
- 注册命令: `wvtest --exhaustive --short --no-extras`
- 覆盖范围: 纯无损(44)/混合无损(40)/混合有损(40)/忽略 wvc 解码(40) 四大类，
  含 8/16/24/32-bit、单声道/立体声/5.1、整数/浮点等组合，共 164 个子测试

#### OHOS 真机实测结果 (2026-08-01)
- 运行环境: 鸿蒙 PC (aarch64), OHOS SDK 26.0.0.18
- 编译器: /data/service/hnp/bin/clang
- 构建选项: BUILD_TESTING=ON, WAVPACK_BUILD_PROGRAMS=OFF
- 子测试总数: 164
- 通过数: **164**
- 通过率: **100%**
- 全过标志: 1 (all tests pass)
- 失败标志: 0 (无失败)

### 鸿蒙特有测试
- test_package/test_wavpack.c: 编码→解码 roundtrip 烟雾测试
  - 获取库版本
  - 创建 WavPack 文件 (100 个采样, 44100Hz, 单声道, 16-bit)
  - 读回文件并验证采样数据一致
