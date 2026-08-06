# codec2 1.2.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `source .build-context-codec2-1.2.0`
2. `cd $BUILD_SRC_DIR/build_dir`
3. `rm -rf * && cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release ..`
4. `make -j1`
5. `make install DESTDIR=$TEST_PREFIX`

CMake 配置选项: `-DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake "Platform/HarmonyOS unknown" 警告 | 鸿蒙平台未被 CMake 内置识别 | 不阻塞编译，仅为信息提示 |
| 2 | /tmp 只读（E002） | 鸿蒙文件系统限制 | 使用 $TMPDIR 替代 /tmp |

## 源码修改

无源码修改，无需补丁。codec2 在鸿蒙平台上原生编译成功。

## 依赖版本

无外部依赖（仅需 libc.so）

## 验证结果

```bash
# 功能测试
c2enc 1300 raw/hts1a.raw $TMPDIR/hts1a.c2  → OK
c2dec 1300 $TMPDIR/hts1a.c2 $TMPDIR/hts1a_dec.raw → OK

# 库验证
readelf -d libcodec2.so → NEEDED: libc.so (仅依赖 libc)
pkg-config --modversion codec2 → 1.2.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libcodec2.so | 1.4M | 共享库 |
| codec2.h 等 | - | 头文件（12个） |
| codec2.pc | - | pkg-config 文件 |
| codec2-config.cmake | - | CMake 配置文件 |

## 注意事项

- codec2 默认不安装命令行工具（c2enc/c2dec 等），仅安装库和头文件
- UNITTEST=OFF 是默认配置，不构建测试二进制
- BUILD_SHARED_LIBS=ON 默认构建共享库
- CMake 在鸿蒙平台上报告 "Platform/HarmonyOS unknown" 但不影响编译
---

**编译结束**: 2026-08-06 04:16
**最终状态**: built
