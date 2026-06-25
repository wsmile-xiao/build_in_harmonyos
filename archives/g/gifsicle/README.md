# gifsicle

GIF image/animation creator/editor

## 描述

Gifsicle 是一个用于创建、编辑和优化 GIF 图像和动画的命令行工具。它可以：

- 创建 GIF 动画
- 优化 GIF 文件大小
- 提取 GIF 中的帧
- 合并多个 GIF
- 添加透明背景
- 调整动画延迟
- 批量处理 GIF 文件

## 版本

- **1.96** (2026-05-19) - 手动编译成功

## 编译说明

由于 HMDFS 文件系统的限制，版本 1.96 使用了手动编译方法而非标准的 autotools 流程。

## 交付物

- `gifsicle` - GIF 图像/动画创建/编辑工具
- `gifdiff` - GIF 文件比较工具

## 使用示例

```bash
# 查看 GIF 信息
gifsicle --info input.gif

# 优化 GIF
gifsicle -O2 input.gif -o output.gif

# 比较两个 GIF
gifdiff first.gif second.gif

# 创建动画
gifsicle --delay=10 frame1.gif frame2.gif frame3.gif -o animation.gif
```

## 许可证

GPL v2

## 官方网站

https://www.lcdf.org/gifsicle/

## 作者

Eddie Kohler
