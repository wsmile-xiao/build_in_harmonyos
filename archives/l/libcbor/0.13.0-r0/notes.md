# libcbor 0.13.0-r0 编译笔记

**软件**: libcbor  
**版本**: 0.13.0-r0  
**构建系统**: CMake  
**编译日期**: 2026-05-19

## 编译流程

### 1. 源码获取

从 GitHub 下载源码：https://github.com/PJK/libcbor/archive/v0.13.0.tar.gz

### 2. CMake 配置

```bash
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..
```

### 3. 编译

```bash
make -j$(nproc)
```

编译成功，生成静态库 libcbor.a。

### 4. 安装

```bash
make install DESTDIR=$TEST_PREFIX
make install
```

### 5. 验证

- 库文件: 151KB
- 头文件: 23 个（包括 cbor.h 和 cbor/ 目录下的所有头文件）
- pkgconfig: libcbor.pc
- cmake config: libcborConfig.cmake, libcborConfigVersion.cmake

示例程序验证通过：
- hello 程序输出: "Hello from libcbor 0.13.0"
- Pretty-printer support: yes
- Buffer growth factor: 2.000000

## 编译问题

### CMake 平台识别

CMake 显示 "System is unknown to cmake"，但不影响编译。
建议：未来可以为 HarmonyOS 创建 Platform/HarmonyOS 配置文件。

### 无测试用例

libcbor 源码中未包含预定义的测试用例，CMake 配置未启用测试功能。

## 知识提取

本次编译为标准 CMake 编译流程，无特殊错误模式需要记录。
---

**编译结束**: 2026-05-19 18:56
**最终状态**: built
