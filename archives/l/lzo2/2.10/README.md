# lzo2 2.10 for HarmonyOS

## 概述

lzo2 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。lzo2 是一个实时无损数据压缩库，专注于解压速度。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | lzo2 |
| 版本 | 2.10 |
| 下载地址 | https://www.oberhumer.com/opensource/lzo/download/lzo-2.10.tar.gz |
| 官方文档 | https://www.oberhumer.com/opensource/lzo/ |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | autotools |

## 编译步骤

```bash
# 1. 下载源码
wget https://www.oberhumer.com/opensource/lzo/download/lzo-2.10.tar.gz
tar -xzf lzo-2.10.tar.gz
cd lzo-2.10

# 2. 应用补丁（更新 config.guess 和 config.sub）
patch -p1 < patches/0001-autoconf-config.guess.patch
patch -p1 < patches/0002-autoconf-config.sub.patch

# 3. 配置（静态链接）
./configure --prefix=$HOME/usr/local --enable-static --disable-shared

# 4. 编译
make -j$(nproc)

# 5. 安装
make install
```

## 补丁说明

### 0001-autoconf-config.guess.patch
添加 HarmonyOS 系统检测支持

### 0002-autoconf-config.sub.patch
添加 ohos 操作系统支持

## 遇到的问题

无重大问题。标准 autotools 构建流程。

## 测试结果

| 测试项 | 结果 |
|--------|------|
| 静态库编译 | ✅ |
| 测试套件 | ✅ 通过 |
| 功能验证 | ✅ |

## 验证安装

```bash
# 检查安装
ls -la $HOME/usr/local/lib/liblzo2.a

# 检查头文件
ls -la $HOME/usr/local/include/lzo/lzo1x.h
```

## 经验总结

1. lzo2 使用 autotools 构建，需要更新 config.guess/config.sub
2. 推荐使用 `--enable-static --disable-shared` 生成静态库
3. lzop 依赖此库进行 LZO 压缩

## 参考资料

- https://www.oberhumer.com/opensource/lzo/