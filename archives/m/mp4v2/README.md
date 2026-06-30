# mp4v2 — MPEG-4 文件读写库

## 简介

mp4v2 是一个用于读取、创建和修改 MPEG-4（MP4）文件的开源 C++ 库。
它提供了完整的 MP4 文件格式支持，包括 ISMA（Internet Streaming Media Alliance）
规范、iTunes 元数据标签（iTMF）以及 QTFF（QuickTime File Format）扩展。

## 核心功能

- **MP4 文件创建与读写**: 支持创建、打开、关闭 MP4 文件
- **轨道管理**: 添加/删除/查询视频、音频、文本等各类轨道
- **样本操作**: 读写轨道中的媒体样本数据
- **元数据标签**: iTunes 兼容标签读写（标题、艺术家、封面等）
- **章节管理**: QuickTime/Nero 格式章节的添加与查询
- **文件优化**: MP4 文件结构优化（moov atom 前置）

## 命令行工具

mp4v2 提供以下 9 个命令行工具：

| 工具 | 功能 |
|------|------|
| mp4art | 封面艺术管理 |
| mp4chaps | 章节标记管理 |
| mp4extract | 轨道内容提取 |
| mp4file | 文件结构查询与优化 |
| mp4info | 文件信息摘要 |
| mp4subtitle | 字幕操作 |
| mp4tags | iTunes 标签管理 |
| mp4track | 轨道属性管理 |
| mp4trackdump | 轨道样本级调试 |

## API 示例

```cpp
#include <mp4v2/mp4v2.h>

MP4FileHandle h = MP4Create("output.mp4", 0);
MP4TrackId vid = MP4AddVideoTrack(h, 90000, 3600, 320, 240, MP4_MPEG4_VIDEO_TYPE);
MP4Close(h);
```

## 编译信息

- 版本: 2.1.3
- 构建系统: autotools
- 编译器: clang 15.0.4（OpenHarmony SDK 26.0.0.18）
- 目标架构: aarch64-linux-ohos
- 依赖: 无必需外部依赖

## 预编译包

```
mp4v2-2.1.3-ohos-aarch64.tar.gz
```

包含：
- libmp4v2.so.2.1.3（共享库）
- 9 个命令行工具（已签名）
- 14 个头文件（include/mp4v2/）
- mp4v2.pc（pkg-config）

## 平台适配要点

- tarball 不含 configure 脚本，需 `autoreconf -fi` 生成
- HMDFS 环境需修复 configure 中 umask 077 → 022（E011）
- make check 需要 DejaGnu，环境缺 runtest 时跳过

## 许可证

MPL 1.1（Mozilla Public License）