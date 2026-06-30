# ttygif

> ttygif converts a ttyrec file into gif files.
> It's a stripped down version of ttyplay that captures every frame.

## 版本历史

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.4.0 | built | 2026-05-29 |

## 运行时依赖

- **ImageMagick** (`convert` command): Required at runtime for GIF generation
- **ttyrec**: Required for recording terminal sessions

## 鸿蒙适配说明

- 构建系统：makefile（纯Makefile，需configure wrapper）
- 添加了DESTDIR支持用于staging隔离安装
- 修复了硬编码/tmp路径（改为读取TMPDIR环境变量）
- 需要configure wrapper脚本以兼容G0 clean-verify流程