# faac — HarmonyOS/OpenHarmony AAC 编码器

## 简介

faac (Freeware Advanced Audio Coder) 是一个开源的 AAC 音频编码器，可以将 PCM 音频数据编码为 AAC 格式。AAC 是 MP3 的升级版本，提供更好的音质和更高的压缩效率。

## 快速安装

### 使用预编译包

```bash
# 下载并解压
tar xzf faac-1.40-ohos-aarch64.tar.gz

# 安装到 ~/usr/local
cd faac-1.40-ohos-aarch64
sh install-faac-1.40.sh
```

### 验证安装

```bash
# 设置环境变量
export LD_LIBRARY_PATH=~/usr/local/lib:$LD_LIBRARY_PATH

# 查看帮助
faac -h

# 编码测试
faac input.wav -o output.aac
```

## 可用版本

| 版本 | 状态 | 编译日期 | 补丁数 | 测试结果 |
|------|------|----------|--------|----------|
| 1.40 | success | 2026-04-28 | 0 | 功能测试通过 |

## 编译指导

### 环境要求
- HarmonyOS/OpenHarmony aarch64
- meson >= 0.50
- ninja >= 1.8
- clang/LLVM 工具链

### 源码下载
```bash
wget https://github.com/knik0/faac/archive/refs/tags/faac-1.40.tar.gz
```

### 编译步骤
```bash
tar xzf faac-1.40.tar.gz
cd faac-faac-1.40
meson setup build --prefix=~/usr/local
ninja -C build
meson install -C build --destdir=/path/to/staging
```

## 使用指南

### 常用命令

| 功能 | 命令 |
|------|------|
| WAV → AAC | `faac input.wav -o output.aac` |
| RAW PCM → AAC | `faac -P -R 44100 -B 16 -C 2 input.raw -o output.aac` |
| 设置质量 | `faac -q 100 input.wav -o output.aac` (100最高) |
| 设置比特率 | `faac -b 128 input.wav -o output.aac` (128kbps) |

### 参数说明

| 参数 | 说明 |
|------|------|
| `-q <0-100>` | 编码质量，100为最高质量 |
| `-b <kbps>` | 目标比特率 (ABR模式) |
| `-P` | RAW PCM 输入模式 |
| `-R <Hz>` | 输入采样率 |
| `-B <bits>` | 输入位深度 (8/16/24/32) |
| `-C <n>` | 输入声道数 |
| `-r` | RAW AAC 输出（无容器） |

## 库文件

### 动态库
- `libfaac.so.0` - AAC 编码动态库

### 静态库
- `libfaac.a` - AAC 编码静态库（用于嵌入）

### 头文件
- `faac.h` - API 定义
- `faaccfg.h` - 配置定义

### pkg-config
```bash
pkg-config --cflags faac   # 获取编译选项
pkg-config --libs faac     # 获取链接选项
```

## 已知限制

### 安全弹窗
首次执行 faac 时，HarmonyOS 会弹出安全确认对话框。这是系统的预期安全行为，用户确认后即可正常使用。

## 性能数据

基于测试音频 (1秒 44.1kHz mono PCM):
- 输入大小: 88,200 bytes
- 输出大小: 2,224 bytes
- 压缩率: 39.65x
- 编码时间: < 0.1秒

## 许可证

faac 采用 GPL 许可证，详见 COPYING 文件。

## 相关链接

- 官方网站: https://github.com/knik0/faac
- 源码仓库: https://github.com/knik0/faac

---

**维护者**: OpenHarmony 编译团队
**更新日期**: 2026-04-28