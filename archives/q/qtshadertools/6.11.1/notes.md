# qtshadertools 6.11.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-30
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境: `ohc-run.py init-build qtshadertools 6.11.1 --url=...`
2. 修复 src/glslang/CMakeLists.txt（添加 HarmonyOS 平台支持）
3. CMake 配置: `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DQT_QMAKE_TARGET_MKSPEC=harmonyos-clang ..`
4. 编译: `cmake --build . -j2`
5. DESTDIR 安装: `DESTDIR=$TEST_PREFIX cmake --install . --prefix $DEFAULT_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 报错：Cannot find source file: //ossource.cpp | CMake 不识别 HarmonyOS 为 UNIX，导致 GLSLANG_OSDEP_PATH 未被设置 | 在 src/glslang/CMakeLists.txt 添加 elseif(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS") 和 else() 兜底条件，使 GLSLANG_OSDEP_PATH 默认使用 Unix 路径 |
| 2 | CMake 报错：Platform is not detected | CMake 不内置支持 HarmonyOS 平台 | 使用 -DQT_QMAKE_TARGET_MKSPEC=harmonyos-clang 参数指定平台 |

## 源码修改

- `src/glslang/CMakeLists.txt`: 添加 HarmonyOS 平台检测条件，确保 GLSLANG_OSDEP_PATH 使用 Unix/ossource.cpp

## 依赖版本

- qtbase 6.11.1

## 验证结果

编译成功，所有目标已构建：
- BundledGlslang_Osdependent (静态库)
- BundledGlslang_Spirv (静态库)
- BundledGlslang_Glslang (静态库)
- BundledSpirv_Cross (静态库)
- ShaderTools (共享库 libQt6ShaderTools.so)
- qsb (命令行工具)

## 交付物

| 文件 | 说明 |
|------|------|
| qtshadertools-6.11.1-aarch64.tar.gz | 运行时二进制包 |
| qtshadertools-6.11.1-aarch64-debug.tar.gz | 调试符号包 |

## 注意事项

- HarmonyOS 不被 CMake 识别为 UNIX 系统，需要在 Qt 的 3rdparty 模块中显式处理
- Qt 模块需要通过 QT_QMAKE_TARGET_MKSPEC 指定目标平台
---

**编译结束**: 2026-08-08 09:48
**最终状态**: built
