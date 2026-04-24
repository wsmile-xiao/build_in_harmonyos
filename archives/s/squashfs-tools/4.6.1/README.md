# squashfs-tools 4.6.1 for HarmonyOS

## 概述

squashfs-tools 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | squashfs-tools |
| 版本 | 4.6.1 |
| 下载地址 | https://github.com/plougher/squashfs-tools/archive/refs/tags/4.6.1.tar.gz |
| 官方文档 | 待补充 |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | makefile |

## 编译步骤

```bash
# 1. 下载源码
# wget https://github.com/plougher/squashfs-tools/archive/refs/tags/4.6.1.tar.gz

# 2. 配置
./configure --prefix=/storage/Users/currentUser/usr/local

# 3. 编译
make -j$(nproc)

# 4. 安装
make install
```

## 补丁说明

待补充（查看 patches/ 目录）

## 遇到的问题

待补充

## 测试结果

| 测试项 | 结果 |
|--------|------|
| 编译成功 | partial |

## 验证安装

```bash
# 检查安装
# squashfs-tools --version
```

## 经验总结

待补充

## 参考资料

- 待补充
