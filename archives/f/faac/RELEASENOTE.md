# faac 1.40 — 发布说明

**发布日期**: 2026-04-28
**版本**: 1.40.0
**平台**: HarmonyOS/OpenHarmony aarch64

## 新版本亮点

这是 faac 在 HarmonyOS/OpenHarmony 平台上的首次预编译发布。

## 安装方法

### 方法一：使用预编译包（推荐）

```bash
# 下载预编译包
tar xzf faac-1.40-ohos-aarch64.tar.gz -C ~/usr/local

# 运行安装脚本
cd ~/usr/local/faac-1.40-ohos-aarch64
sh install-faac-1.40.sh
```

### 方法二：手动安装

```bash
tar xzf faac-1.40-ohos-aarch64.tar.gz
cp faac-1.40-ohos-aarch64/bin/faac ~/usr/local/bin/
cp faac-1.40-ohos-aarch64/lib/libfaac.so* ~/usr/local/lib/
cp faac-1.40-ohos-aarch64/include/faac*.h ~/usr/local/include/
```

## 包内容

| 组件 | 文件 | 说明 |
|------|------|------|
| 命令行工具 | `bin/faac` | AAC 编码器 (104KB) |
| 动态库 | `lib/libfaac.so.0.0.0` | 共享库 (170KB) |
| 静态库 | `lib/libfaac.a` | 静态链接库 (254KB) |
| 头文件 | `include/faac.h` | API 头文件 |
| 头文件 | `include/faaccfg.h` | 配置头文件 |
| pkg-config | `lib/pkgconfig/faac.pc` | 编译配置 |

## 包大小

| 包 | 大小 |
|---|---|
| faac-1.40-ohos-aarch64.tar.gz | 789KB |
| faac-1.40-ohos-aarch64-debug.tar.gz | 389KB (含调试符号) |

## 编译信息

| 配置项 | 值 |
|--------|-----|
| 构建系统 | meson 1.11.0 |
| 编译器 | clang 15.0.4 |
| 目标平台 | HarmonyOS aarch64 |
| 质量门禁 | G1-G4 PASS |
| 补丁数量 | 0 |

## 测试验证

### 功能测试结果

| 测试项目 | 结果 |
|---------|------|
| 编码功能 | ✅ PASS |
| 文件格式验证 | ✅ PASS (MPEG ADTS AAC) |
| 压缩效率 | ✅ PASS (39.65x) |
| 动态库链接 | ✅ PASS |
| RPATH 配置 | ✅ PASS |

### 测试详情
- 输入: 1秒 44.1kHz 16bit mono PCM (88,200 bytes)
- 输出: AAC 文件 (2,224 bytes)
- 编码器版本: FAAC 1.40.0
- 输出格式: MPEG ADTS, AAC, v2 LC, 44.1 kHz, monaural

## 环境要求

- HarmonyOS/OpenHarmony aarch64
- 动态链接器: /lib/ld-musl-aarch64.so.1
- libc: musl libc

## 已知问题

### 安全弹窗
首次执行 `faac` 命令时，系统会弹出安全确认对话框。这是 HarmonyOS 的安全机制，确认后即可正常使用。

**解决方法**: 点击确认按钮，后续执行无需再次确认。

## 升级说明

这是首次发布，无需升级操作。

## 使用示例

```bash
# WAV 转 AAC
faac music.wav -o music.aac

# 设置高质量
faac -q 100 music.wav -o music.aac

# 设置比特率
faac -b 192 music.wav -o music.aac

# RAW PCM 输入
faac -P -R 48000 -B 16 -C 2 input.raw -o output.aac
```

---

**维护团队**: OpenHarmony 编译组
**下载链接**: archives/f/faac/1.40/packaging/faac-1.40-ohos-aarch64.tar.gz