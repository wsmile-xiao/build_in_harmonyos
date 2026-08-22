# aview

**高保真终端 ASCII 艺术图像查看器与 FLI/FLC 动画播放器**（AA-Project 家族，与 aalib/aafire/aa3d 同源）

aview 在文本终端中显示 PGM/PPM/PNG/BMP 图像的 ASCII 艺术渲染，并支持 FLI/FLC 动画播放，
特别适合与 lynx 等纯文本浏览器配合展示图像。

## 包含工具

| 工具 | 说明 |
|------|------|
| `aview` | 图像查看器：将 PGM/PPM/PNG/BMP 渲染为 ASCII 艺术 |
| `aaflip` | FLI/FLC 动画播放器 |
| `asciiview` | shell 包装脚本，用 aview 渲染图像 |

## 用法

```bash
aview [options] filename.p[ngbp]m
```

常用选项：

| 选项 | 说明 |
|------|------|
| `-driver stdout\|stderr` | 选择图像输出驱动 |
| `-kbddriver stdin` | 键盘驱动（非交互脚本用 stdin） |
| `-width / -height` | 设置渲染尺寸 |

示例：

```bash
aview -driver stdout picture.ppm          # 将 PPM 渲染为 ASCII 输出
echo q | aview -driver stdout -kbddriver stdin picture.ppm   # 非交互运行
```

## 构建

- 构建系统：autotools（configure 已预生成）
- 依赖：aalib（≥1.4.0，已作为 Conan 依赖声明）
- 平台：HarmonyOS PC / OHOS aarch64（clang 工具链）

## 许可证

GPL-2.0-or-later