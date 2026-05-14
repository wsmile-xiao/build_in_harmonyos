# fdk-aac 2.0.3 — OpenHarmony 编译记录

## 基本信息
- **软件**: fdk-aac
- **版本**: 2.0.3
- **构建系统**: cmake（原 autotools，因平台限制改用 cmake）
- **目标**: ohos-aarch64
- **状态**: partial

## 简介

fdk-aac 是 Fraunhofer FDK AAC 编解码库，提供高质量的 AAC 音频编码和解码功能。

## 编译指导

### 依赖
- 无外部依赖

### 构建命令
```bash
# cmake 构建（推荐）
mkdir -p _cmake_build && cd _cmake_build
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

### 注意事项
1. **autotools 失败原因**: HMDFS 文件系统上 mktemp 创建的临时目录权限问题
2. **E007 问题**: config.guess 不识别 HarmonyOS，需要添加处理分支
3. **无测试套件**: 项目未集成 make check

## 预编译包安装

```bash
# 下载预编译包
tar xzf fdk-aac-2.0.3-ohos-aarch64.tar.gz -C ~/usr/local

# 运行安装脚本
cd fdk-aac-2.0.3-ohos-aarch64 && sh install-fdk-aac-2.0.3.sh
```

## 库使用示例

```bash
# pkg-config 查询
pkg-config --cflags fdk-aac    # 返回: -I$PREFIX/include/fdk-aac
pkg-config --libs fdk-aac      # 返回: -L$PREFIX/lib -lfdk-aac

# 验证安装
pkg-config --modversion fdk-aac  # 返回: 2.0.3
```

## API 头文件

| 头文件 | 说明 |
|--------|------|
| aacenc_lib.h | AAC 编码器 API |
| aacdecoder_lib.h | AAC 解码器 API |
| FDK_audio.h | 核心音频处理接口 |
| genericStds.h | 通用标准定义 |
| machine_type.h | 平台类型定义 |
| syslib_channelMapDescr.h | 声道映射描述 |

## 知识沉淀

本次编译发现以下问题，已记录到知识图谱：

- **E007**: config.guess/config.sub 不识别 HarmonyOS
- **HMDFS 限制**: mktemp umask 077 创建的目录权限问题
- **构建系统切换**: cmake 作为 autotools 失败时的备选方案

## 版本历史

| 版本 | 日期 | 状态 | 备注 |
|------|------|------|------|
| 2.0.3 | 2026-05-06 | partial | cmake 构建，无测试套件 |

---

*更新时间: 2026-05-06*