# exiftool 13.50 — HarmonyOS aarch64 预编译包

## 快速安装

```bash
# 解压预编译包
tar xzf exiftool-13.50-ohos-aarch64.tar.gz

# 安装到 ~/usr/local
cd exiftool-13.50-ohos-aarch64
sh install-exiftool-13.50.sh

# 验证安装
~/usr/local/bin/exiftool -ver
# 输出: 13.50
```

## 包内容

| 目录/文件 | 说明 |
|----------|------|
| bin/exiftool | 主命令行脚本 |
| bin/lib/Image/ExifTool/ | Perl 模块（200+ 文件） |
| bin/lib/File/RandomAccess.pm | 依赖模块 |
| lib/site_perl/... | 标准安装路径（兼容） |

**包大小**: 38.8 MB (38,837 KB)

## 编译信息

| 属性 | 值 |
|------|-----|
| 版本 | 13.50 |
| 构建系统 | Perl MakeMaker |
| 编译状态 | partial |
| 测试结果 | 113/113 PASS, 600 断言 |
| 补丁数 | 0 |
| 质量门禁 | PASS |

## 测试结果

```
Files=113, Tests=600, 37 wallclock secs
Result: PASS
All tests successful
```

## 功能验证

```bash
$ exiftool -ver
13.50

$ exiftool -listf
（显示支持的文件类型列表）

$ exiftool image.jpg
（显示图片的 EXIF 元数据）
```

## 环境要求

- HarmonyOS/OpenHarmony aarch64
- Perl 5.42.0 或更高版本（已预装）
- 无其他依赖

## 已知限制

### Perl 模块路径
exiftool 脚本在 BEGIN 块自动添加 `bin/lib` 到 Perl @INC。预编译包已正确配置此结构。

## 支持的文件格式

exiftool 支持以下格式的元数据读写：
- 图像: JPEG, PNG, GIF, TIFF, RAW (CR2/NEF/DNG), HEIC, AVIF
- 视频: MP4, MOV, AVI, M2TS
- 音频: MP3, FLAC, AAC
- 文档: PDF, OOXML

完整列表: https://exiftool.org/

---

**发布日期**: 2026-04-22
**编译者**: openharmony-compile-agent