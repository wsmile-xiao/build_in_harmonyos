# aaphoto — Auto Adjust Photo

## 软件简介

aaphoto 是一个命令行照片自动色彩校正工具。它通过分析输入图像，自动设置最优的对比度、伽马值、色彩平衡和饱和度，让照片看起来更好看。支持 bmp、jpg、png 格式输入。

**主要功能**:
- `-a/--autoadjust`: 自动校正图像色彩（默认开启）
- `-r/--resize`: 按百分比或像素调整图像尺寸
- `--rotate90/180/270`: 旋转图像
- `--flipx/--flipy`: 水平/垂直镜像
- `-q/--quality`: 设置 JPEG 输出质量（1-100）
- `-t/--threads`: 设置工作线程数（OpenMP 并行）
- `--noexif`: 保存时不保留 EXIF 信息
- `-o/--output`: 设置输出目录

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 0.45 | built ✅ | 2026-08-05 | 3 |

## 使用方法

```bash
# 基本用法（自动校正，输出 _new 后缀新文件）
aaphoto photo.jpg

# 校正并调整大小
aaphoto -a -r600 -q85 *.jpg

# 处理整个目录
aaphoto mydir/

# 输出为 PNG（支持 alpha 通道）
aaphoto --png photo.bmp
```

## 平台适配说明

### 鸿蒙系统适配

**编译补丁**:
1. `0001-Makefile.am.patch` / `0002-Makefile.in.patch`: 移除 AM_LDFLAGS 中 GCC 专用的 `-lgomp`
   - 原因: 鸿蒙 OHOS SDK 使用 clang，`-fopenmp` 会自动链接 SDK 自带的 `libomp.so`；不存在 libgomp
2. `0003-configure.patch`: 移除 config.status 临时目录创建时的 `umask 077`
   - 原因: HMDFS 强制目录 setgid，`umask 077` 创建的 `drwx--S---` 目录即使属主也无法写入（知识图谱 E114）

**编译依赖**:
- libjpeg/10（JPEG 编解码）
- libpng/1.6.58（PNG 编解码，传递依赖 zlib/1.3.1.1）
- OpenMP 运行时: OHOS SDK clang 自带 libomp（无需额外依赖）

**构建系统**: autotools

## 验证结果

### 功能测试

| 测试项 | 结果 |
|--------|------|
| 版本显示 `aaphoto --version` | ✅ 通过 |
| 端到端图片处理（BMP→PNG 自动校正） | ✅ 通过 |
| conan create + test_package | ✅ 通过 |

### 质量门禁

| 门禁项 | 结果 |
|--------|------|
| G0 预构建风险评估 | ✅ 通过 |
| G1 配方完整性 | ✅ 通过 |
| G2 conan create | ✅ 通过 |
| G3 系统同名库隔离 | ✅ 通过 |
| G4 产物完整性 | ✅ 通过 |

## 源码信息

- **源码地址**: https://github.com/log69/aaphoto（master 分支即 v0.45，2016-07-09 发布）
- **官方主页**: http://log69.com/aaphoto_en.html
- **许可证**: GPL-3.0-or-later
- **维护者**: Andras Horvath (mail@log69.com)

## 相关资源

- [GitHub 仓库](https://github.com/log69/aaphoto)
- [编译详情](./0.45/notes.md)
- [验证报告](./0.45/reports/conan-verify-report.md)
