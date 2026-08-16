# tachyon

**Tachyon — 并行/多线程光线追踪渲染器**

读一份场景描述文件（`.dat`），渲染出图像。SageMath / passagemath 的三维绘图默认后端之一
（`sage.interfaces.tachyon` 起子进程调它）。

## 用法

```bash
tachyon scene.dat -format PNG -o out.png -res 640 480 -numthreads 4
```

| 选项 | 说明 |
|------|------|
| `-format <FMT>` | 输出格式：TARGA / BMP / PPM / PSD48 / RGB / **PNG**（PNG 需构建时接上 libpng） |
| `-o <file>` | 输出文件名 |
| `-res <w> <h>` | 覆盖场景里的分辨率 |
| `-numthreads <n>` | 渲染线程数 |
| `-aasamples <n>` | 抗锯齿采样数 |

## 构建

- 构建系统：手写 Makefile（`unix/Makefile` + `unix/Make-arch` 的架构目标分派）
- 架构目标：`linux-arm-thr`（**由适配补丁补上**，原始 tarball 无 aarch64 目标）
- 许可证：BSD-3-Clause
- 源码：https://github.com/sagemath/sage-package/releases/download/tars/tachyon-0.99.5.tar.gz
  （与 sage 用的 `tachyon-0.99.5.p0.tar.gz` 逐字节相同）

## 依赖

- libpng（PNG 输出）

## 已编译版本

- 0.99.5 (2026-08-16)

## OHOS 适配

- 补 `linux-arm-thr` 架构目标（沿用 sage/passagemath 的 Make-arch 补丁）
- 显式给 CC/AR/RANLIB/STRIP 绝对路径（目标本身不设 CC，会落到不存在的 `cc`）
- `package()` 重签 `bin/tachyon`：上游 Makefile 在链接后紧跟 strip，链接器自签已失效
