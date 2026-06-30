# Bento4

## 软件简介

Bento4 是一个 C++ 类库和工具集，用于读写 ISO-MP4 文件。该格式定义在国际规范 ISO/IEC 14496-12、14496-14 和 14496-15 中。

Bento4 支持：
- MPEG DASH
- CMAF (Common Media Application Format)
- MPEG Common Encryption (CENC)
- H.264/AVC 和 H.265/HEVC 视频解析
- AAC 音频解析
- 多种 DRM 系统支持

## 编译版本

- **当前版本**: 1.6.0-641
- **编译日期**: 2026-05-26
- **构建系统**: CMake
- **编译器**: Clang 15.0.4

## 生成产物

- 静态库：libap4.a
- 26 个命令行工具：
  - mp4info, mp4dump, mp4edit, mp4extract
  - mp4encrypt, mp4decrypt, mp4fragment, mp4split
  - mp4mux, mp42aac, mp42avc, mp42hls
  - 等其他工具

## 依赖关系

无外部依赖，完全自包含。

## 使用示例

```bash
# 查看 MP4 文件信息
mp4info video.mp4

# 转换为 HLS 格式
mp42hls video.mp4

# 创建 DASH 输出
mp4-dash video.mp4
```

## 相关链接

- 官网：http://www.bento4.com
- GitHub：https://github.com/axiomatic-systems/Bento4