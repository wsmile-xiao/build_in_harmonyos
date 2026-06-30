# AtomicParsley

## 软件简介

AtomicParsley 是一个轻量级命令行工具，用于读取、解析和设置 MPEG-4 文件的元数据，特别是 iTunes 风格的元数据。

## 功能特性

- 支持 MPEG-4 文件及其衍生格式的元数据处理
- 支持三种标签方案：
  - iTunes 风格元数据
  - 3GPP 资产
  - ISO 定义的版权通知
- 支持读取和显示 MP4 文件结构（atom树）
- 支持设置艺术家、标题、专辑、封面等多种元数据标签
- 支持 ID3 标签写入
- 支持自定义私有标签扩展（uuid）
- 支持 Unicode 字符编码（UTF-8）

## 主要用途

1. **媒体文件管理**: 为 MP4/M4V/M4A 文件添加 iTunes 元数据
2. **文件信息查询**: 查看 MP4 文件的 atom 结构和标签信息
3. **批量元数据处理**: 通过脚本批量设置媒体文件元数据
4. **音频/视频文件整理**: 为音乐和视频文件添加完整的元数据信息

## 编译版本

- **当前版本**: 20240608.083822.1ed9031
- **编译日期**: 2026-05-21
- **编译平台**: HarmonyOS (OpenHarmony)
- **编译器**: Clang 15.0.4
- **构建系统**: CMake 4.1.2

## 安装方式

### 预编译包安装

使用 cmd-pkgs 公共安装脚本：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- atomicparsley 20240608.083822.1ed9031
```

### 使用示例

```bash
# 查看 MP4 文件结构
AtomicParsley video.mp4 -T 1

# 查看文件标签信息
AtomicParsley video.mp4 -t

# 设置元数据
AtomicParsley music.m4a --artist "艺术家" --title "标题" --album "专辑"

# 设置封面图片
AtomicParsley video.mp4 --artwork cover.jpg
```

## 依赖关系

- **zlib**: 用于压缩 ID3 帧

## 相关链接

- **官方主页**: https://github.com/wez/atomicparsley
- **源码仓库**: https://github.com/wez/atomicparsley
- **问题反馈**: https://github.com/wez/atomicparsley/issues

## 编译历史

| 版本 | 编译日期 | 状态 | 备注 |
|------|---------|------|------|
| 20240608.083822.1ed9031 | 2026-05-21 | ✅ published | 首次编译，所有测试通过 |