# epsilon 0.9.2 for HarmonyOS

## 概述

EPSILON 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

EPSILON 是一个基于小波的开源图像压缩C库，支持多线程和MPI并行处理。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | epsilon |
| 版本 | 0.9.2 |
| 下载地址 | https://sourceforge.net/projects/epsilon-project/files/epsilon/0.9.2/epsilon-0.9.2.tar.gz/download |
| 官方主页 | https://sourceforge.net/projects/epsilon-project/ |
| 许可证 | LGPL-3.0-or-later |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.12.0 |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4 |
| 构建系统 | autotools (configure + make) |

## 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| popt | 1.16 | Conan 制品仓 (ohpcd) |

## 补丁

| 补丁 | 说明 | 错误模式 |
|------|------|---------|
| 0001-config.guess.patch | 替换 config.guess 为 automake-1.16 版本（支持 OHOS 检测） | E007 |
| 0002-config.sub.patch | 替换 config.sub 为 automake-1.16 版本（支持 aarch64-ohos triplet） | E007 |
| 0003-configure.patch | umask 077→022，mktemp ./→$TMPDIR 修复 HMDFS setgid 兼容性 | E097 |

## 构建命令

```bash
./configure --prefix=$PREFIX --disable-shared --enable-static --disable-mpi --disable-cluster
make -j1
make install
```
