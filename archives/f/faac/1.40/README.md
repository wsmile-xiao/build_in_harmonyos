# faac 1.40 — OpenHarmony 编译记录

## 基本信息
- 软件: faac (Freeware Advanced Audio Coder)
- 版本: 1.40
- 构建系统: meson
- 目标平台: HarmonyOS aarch64
- 编译日期: 2026-04-28

## 功能描述

faac 是一个开源的 AAC (Advanced Audio Coding) 编码器，支持将 PCM 音频数据编码为 AAC 格式。

主要功能：
- AAC LC (Low Complexity) 编码
- 支持 RAW PCM 和 WAV 输入
- ADTS 容器格式输出
- 可调节编码质量和比特率
- 支持多声道音频

## 编译指导

### 环境要求
- meson >= 0.50
- ninja >= 1.8
- clang/LLVM 工具链
- HarmonyOS/OpenHarmony aarch64

### 编译命令
```bash
# 1. 设置构建目录
meson setup build --prefix=/path/to/install

# 2. 编译
ninja -C build

# 3. 安装（DESTDIR 模式）
meson install -C build --destdir=/path/to/staging
```

### 编译选项
meson_options.txt 提供以下选项：
- `frontend`: 是否编译命令行工具（默认: true）
- `floating-point`: 浮点精度（single/double，默认: single）

## 补丁清单

本次编译无需补丁，源码直接编译成功。

patches/ 目录: 空

## 已知限制

### 1. 安全弹窗验证
首次在 HarmonyOS 上执行 faac 二进制时，系统会弹出安全确认对话框。用户需手动确认后方可执行。这是鸿蒙系统的预期安全行为。

### 2. 无测试套件
faac 项目未定义自动化测试，需手动进行功能性验证。

## 功能验证

### 编码测试
```bash
# 创建测试 PCM 文件
python3 create_test_pcm.py > test.raw

# 编码为 AAC
faac -P -R 44100 -B 16 -C 1 -o test.aac test.raw

# 验证输出
file test.aac
# 输出: MPEG ADTS, AAC, v2 LC, 44.1 kHz, monaural
```

### 测试结果
- 输入: 88200 bytes PCM (1秒 44.1kHz mono)
- 输出: 2224 bytes AAC
- 压缩率: 39.65x ✅

## 安装产物

| 文件 | 说明 | 大小 |
|------|------|------|
| bin/faac | AAC 编码器命令行工具 | 104KB |
| lib/libfaac.so.0.0.0 | 动态库 | 170KB |
| lib/libfaac.a | 静态库 | 254KB |
| include/faac.h | 主头文件 | 2.5KB |
| include/faaccfg.h | 配置头文件 | 3.3KB |
| lib/pkgconfig/faac.pc | pkg-config 文件 | - |

## 使用示例

### 基本 AAC 编码
```bash
faac input.wav -o output.aac
```

### RAW PCM 输入
```bash
faac -P -R 44100 -B 16 -C 2 -o output.aac input.raw
# -P: RAW PCM 模式
# -R: 采样率
# -B: 位深度 (8/16/24/32)
# -C: 声道数
```

### 调节质量
```bash
faac -q 100 input.wav -o output.aac  # 最高质量
faac -b 128 input.wav -o output.aac  # 128kbps ABR
```

---

**编译状态**: success
**质量门禁**: PASS