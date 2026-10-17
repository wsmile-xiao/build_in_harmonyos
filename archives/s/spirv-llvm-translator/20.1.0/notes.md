# SPIRV-LLVM-Translator 20.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-24
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 依赖
- llvm/20.1.0 (已发布到 ohpcd 制品仓)
- SPIRV-Headers (commit 2b2e05e, 在 source() 中自动下载)

## 编译步骤

1. **初始化**
   ```bash
   python3 ohc-run.py init-build SPIRV-LLVM-Translator 20.1.0 --url=https://github.com/KhronosGroup/SPIRV-LLVM-Translator/archive/refs/tags/v20.1.0.tar.gz
   ```

2. **CMake 配置**
   ```bash
   mkdir build && cd build
   cmake .. \
     -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
     -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
     -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_SYSTEM_NAME=Linux \
     -DLLVM_DIR=$LLVM_PKG_DIR/lib/cmake/llvm \
     -DLLVM_EXTERNAL_SPIRV_HEADERS_SOURCE_DIR=/path/to/spirv-headers \
     -DLLVM_SPIRV_INCLUDE_TESTS=OFF \
     -DLLVM_SPIRV_BUILD_EXTERNAL=YES
   ```
   - LLVM 20.1.0 通过 Conan 安装
   - SPIRV-Headers 从 GitCode 镜像 clone（GitHub 直连超时）
   - Platform/HarmonyOS.cmake 绕过 HandleLLVMOptions.cmake 平台检测

3. **编译**
   ```bash
   make -j2
   ```
   - 构建产物: libLLVMSPIRVLib.a + llvm-spirv

4. **安装**
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```

5. **ELF 签名**
   - llvm-spirv 二进制需签名才能在 OHOS 上执行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时 | 网络限制 | 通过 GitCode 镜像 clone |
| 2 | HandleLLVMOptions "Unable to determine platform" | CMake 不识别 HarmonyOS 平台 | Platform/HarmonyOS.cmake (include(Platform/Linux)) |
| 3 | FetchContent 下载 SPIRV-Headers 失败 | GitHub 网络限制 | 在 source() 中预下载到本地，设置 LLVM_EXTERNAL_SPIRV_HEADERS_SOURCE_DIR |
| 4 | llvm-spirv "Operation not permitted" | OHOS ELF 签名要求 | package() 中用 binary-sign-tool 签名 |

## 源码修改

无补丁。

## 交付物

| 文件 | 说明 |
|------|------|
| libLLVMSPIRVLib.a | SPIR-V 翻译静态库 |
| llvm-spirv | 命令行翻译工具 |
| LLVMSPIRVLib.h 等 | 头文件 |

---

**编译结束**: 2026-07-24
**最终状态**: built
