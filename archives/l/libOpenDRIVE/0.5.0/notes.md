# libOpenDRIVE 0.5.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-11
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 克隆源码并切换到 0.5.0 标签
2. 创建 build 目录并配置 CMake：
   ```bash
   mkdir build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
         -DCMAKE_CXX_FLAGS="-stdlib=libc++" \
         -DCMAKE_EXE_LINKER_FLAGS="-lc++" \
         -DCMAKE_INSTALL_RPATH="/storage/Users/currentUser/usr/local/lib" \
         -DCMAKE_BUILD_WITH_INSTALL_RPATH=TRUE ..
   ```
3. 编译：`make -j2`
4. 安装到 staging：`make install DESTDIR=/storage/Users/currentUser/test-install-libOpenDRIVE-0.5.0`
5. 安装到本地：`make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test-xodr 链接失败，缺少 C++ 标准库符号 | OpenHarmony 平台需要显式链接 libc++ | 在 CMake 配置中添加 `-DCMAKE_CXX_FLAGS="-stdlib=libc++"` 和 `-DCMAKE_EXE_LINKER_FLAGS="-lc++"` |
| 2 | RPATH 未设置，运行时找不到 libOpenDrive.so | CMake 默认在部分平台不设置 RPATH | 在 CMake 配置中添加 `-DCMAKE_INSTALL_RPATH="/storage/Users/currentUser/usr/local/lib" -DCMAKE_BUILD_WITH_INSTALL_RPATH=TRUE`（但测试程序仍有问题） |

## 源码修改

无源码修改，仅编译参数调整。

## 依赖版本

无外部依赖（libOpenDRIVE 声称 dependency-free）。

## 验证结果

```bash
# 设置 LD_LIBRARY_PATH 后可运行
export LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib
/storage/Users/currentUser/usr/local/bin/test-xodr
# 输出：ERROR: too few arguments（说明程序可执行，但缺少输入文件）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libOpenDrive.so | 843K | OpenDRIVE 格式解析库 |
| test-xodr | 103K | 示例程序（需 RPATH 修复） |
| include/*.h | - | 头文件 |

## 注意事项

1. libOpenDRIVE 使用 CMake 构建系统，不是 autotools
2. 在 OpenHarmony 上编译 C++ 项目需要显式链接 libc++ 标准
3. RPATH 设置问题需要进一步解决（当前通过 LD_LIBRARY_PATH 临时绕过）
4. 无测试套件（make check），test-xodr 为示例程序而非测试工具
---

**编译结束**: 2026-06-11 14:24
**最终状态**: built
