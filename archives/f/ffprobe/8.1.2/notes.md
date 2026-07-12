# ffprobe 8.1.2 编译笔记

## 基本信息
- 软件：ffprobe（FFmpeg 项目的一部分）
- 版本：8.1.2 "Hoare"
- 发布日期：2026-06-17
- 编译日期：2026-07-09
- 源码：FFmpeg 8.1.2 tarball

## 编译配置

```bash
./configure --cc=/data/service/hnp/bin/clang \
    --prefix=$DEFAULT_PREFIX \
    --enable-gpl \
    --disable-doc \
    --disable-shared \
    --enable-static \
    --disable-vulkan \
    --disable-ffmpeg \
    --disable-ffplay
```

## 鸿蒙适配

### 1. OS 识别补丁 (0001-configure.patch)
FFmpeg configure 通过 `uname -s` 检测 OS，HarmonyOS 返回 "HarmonyOS"，lowercase 后 "harmonyos" 不被识别。补丁添加 harmonyos case 映射为 Linux 行为。

### 2. 编译器指定
FFmpeg configure 不使用 CC 环境变量，通过 `--cc=` 参数指定。

### 3. 仅构建 ffprobe
使用 `--disable-ffmpeg --disable-ffplay` 禁用其他工具，只产出 ffprobe 二进制。

### 4. ELF 签名
使用 `binary-sign-tool` 签名后才能在 HarmonyOS 执行。

## 编译产物

- `ffprobe` - 媒体分析工具（约 20MB，stripped）

## 测试状态

- 编译成功 ✅
- 安装成功 ✅
- ffprobe -version 验证通过 ✅
---

**编译结束**: 2026-07-09 12:18
**最终状态**: built
