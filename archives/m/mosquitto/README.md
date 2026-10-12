# mosquitto for HarmonyOS

## 概述

mosquitto 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | mosquitto |
| 版本 | 2.0.18 / 2.0.22 |
| 下载地址 | https://mosquitto.org/files/source/ |
| 官方文档 | https://mosquitto.org/documentation/ |
| 上游仓库 | https://github.com/eclipse/mosquitto |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | cmake |

## 编译步骤（以 2.0.22 为例）

```bash
# 1. 下载源码
wget https://mosquitto.org/files/source/mosquitto-2.0.22.tar.gz

# 2. 应用补丁（pthread_cancel 的 __OHOS__ 守卫）
patch -p1 < patches/0002-config.h.patch

# 3. 构建（经 Conan）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

## 补丁说明

### 0002-config.h.patch（2.0.18/2.0.22 语义共用，2.0.22 版按新源码树重新生成）

**目的**: HarmonyOS 不实现 pthread_cancel/pthread_testcancel（与 Android Bionic 同）

**修改文件**:
- `config.h`: `#ifndef ANDROID` → `#if !defined(ANDROID) && !defined(__OHOS__)`

### 0004-src-CMakeLists.txt-harmonyos-dynamic-list.patch（2.0.22 新增）

**目的**: CMake 视 HarmonyOS 为未知平台致 `UNIX` 变量未设，上游 `if (UNIX)` 的 broker 插件符号导出（`-Wl,-dynamic-list=src/linker.syms`）被跳过，插件加载报 `mosquitto_* symbol not found`

**修改文件**:
- `src/CMakeLists.txt`: `if (UNIX)` → `if (UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`

> 2.0.18 曾带 0001-CMakeLists.txt.patch（cmake_minimum_required 3.1→3.5）；
> 上游 2.0.22 已自带 cmake_minimum_required(VERSION 3.18)，该补丁不再需要。

## 遇到的问题

### 问题1: pthread_cancel 未实现

**现象**: 链接期/运行期找不到 pthread_cancel 符号

**原因**: HarmonyOS musl/libpthread 不提供 pthread_cancel

**解决**: config.h 增加 __OHOS__ 守卫，编译期不定义 HAVE_PTHREAD_CANCEL（见 0002 补丁）

## 测试结果

详见各版本目录 [notes.md](./2.0.22/notes.md)

| 测试项 | 结果 |
|--------|------|
| mosquitto_lib_init/lib_version | ✅ |
| mosquitto_new/destroy 实例创建 | ✅ |
| 消费者链接 libmosquitto | ✅ |

## 验证安装

```bash
# 检查安装
ls -la lib/libmosquitto*

# 功能验证
./test_package/build/Release/test_mosquitto
```

## 版本历史

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.0.18 | uploaded | 初版适配 |
| 2.0.22 | built | 升级件：2.0.19..2.0.22 bugfix 线（含安全修复 #248 恶意 SUBSCRIBE 泄漏、CVE-2023-28366 追加修复） |

## 参考资料

- https://mosquitto.org/
- https://github.com/eclipse/mosquitto
