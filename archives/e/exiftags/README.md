# exiftags

**JPEG Exif 标签解析工具集**（命令行工具，BSD-4-Clause 许可）

exiftags 是一组用于读取和设置 JPEG 文件中 Exif 标签的命令行工具，包含三个程序：

- **exiftags**：解析并显示 JPEG 文件中的 Exif 标签数据（相机型号、拍摄参数、GPS 等）
- **exifcom**：读取或设置 JPEG 文件中的 Exif 注释（comment）标签
- **exiftime**：显示或调整 JPEG 文件中的 Exif 时间戳（拍摄时间、数字化时间等）

## 用法

```bash
exiftags [options] [files]      # 显示 Exif 数据
exifcom [options] file ...      # 读取/设置注释
exiftime [options] file ...     # 显示/调整时间戳
```

常用选项：

| 选项 | 工具 | 说明 |
|------|------|------|
| `-a` | exiftags | 显示全部属性 |
| `-v` | exiftags | 显示详细属性 |
| `-w string` | exifcom | 设置注释 |
| `-v` | exifcom | 详细注释信息 |
| `-l` | exiftime | 按时间戳排序列出文件 |
| `-w` | exiftime | 写入调整后的时间戳 |

## 构建

- 构建系统：纯 Makefile（无 configure 脚本）
- 版本：1.01（2007 年发布）
- 许可证：BSD-4-Clause
- 源码：https://johnst.org/sw/exiftags/exiftags-1.01.tar.gz
- 依赖：无外部依赖（仅 libc + libm）

## OHOS 适配

- 无需源码修改，原始源码在鸿蒙 aarch64 上使用 clang 编译通过
- 传 CC=clang CFLAGS="-fPIC -O2" 覆盖 Makefile 默认的 CC=cc
