# tiv

**终端图像查看器**（Terminal Image Viewer）

用 24-bit RGB ANSI 转义序列配合 Unicode 半块字符（每个字符格 4x8 像素）在现代终端里
渲染图片。相同屏幕面积下比逐字符色块方案分辨率更高。

- 版本: 1.2.1（上游 tag `v1.2.1`，2023-12 发布）
- 许可证: Apache-2.0 OR GPL-3.0-or-later
- 上游: https://github.com/stefanhaustein/TerminalImageViewer

## 用法

```bash
tiv [options] <image> [<image>...]
```

| 选项 | 说明 |
|------|------|
| `-0` | 关闭块字符优化，固定用下半块字符 |
| `-2`, `--256` | 使用 256 色索引模式（macOS Terminal 需要） |
| `-c <num>` | `dir` 模式的缩略图列数（默认 3） |
| `-d`, `--dir` | 强制 `dir` 模式（多输入时自动选中） |
| `-f`, `--full` | 强制 `full` 模式（单输入时自动选中） |
| `--help` | 显示帮助 |
| `-h <num>` | 最大输出高度（行数） |
| `-w <num>` | 最大输出宽度（字符数） |
| `-x` | 使用新的 Teletext/legacy 块字符（实验性） |

示例：

```bash
tiv photo.jpg                 # 全尺寸渲染
tiv -w 80 -h 24 photo.jpg     # 限制到 80x24 字符格
tiv -d -c 4 ./pictures/       # 目录缩略图，4 列
tiv --256 -w 120 banner.png   # 256 色 + 宽幅
```

退出码遵循 `sysexits.h` 约定：`64` 命令行用法错误、`66` 输入文件打不开。

## 构建

- 构建系统: 纯 Makefile（`src/Makefile`，无 configure 脚本）
- 依赖: cimg/3.6.6（header-only）
- OHOS 适配: 见 `1.2.1/notes.md`

## OHOS 适配说明

- Makefile 在 `src/` 子目录里，配方在 `src/` 下调 make。
- 用制品仓 `cimg/3.6.6` 的 `CImg.h` 覆盖 tarball 自带的 3.3.1（Makefile 的
  `tiv.o: CImg.h` 规则要求头文件与源码同目录）。
- 覆盖 `CXXFLAGS` 去掉上游默认的 `-fpermissive`（GCC 专有选项）。
- `tiv.cpp` 自带 `#define cimg_display 0`，不需要 X11。
- **未启用 PNG/JPEG 解码**（未定义 `cimg_use_png` / `cimg_use_jpeg`）。PPM/PNM 可用。
- 输出重定向时无法 `ioctl(TIOCGWINSZ)`，回退 80x24 并在 stderr 打一行 warning。