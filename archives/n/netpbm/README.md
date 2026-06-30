# netpbm

图像格式转换工具集，支持 100+ 种图像格式的转换和处理。

## 功能

- 图像格式转换（PNG/JPEG/TIFF/PBM/PGM/PPM/PAM 等）
- 图像处理（缩放、裁剪、旋转等）
- 图像分析工具

## OHOS 适配

- 构建系统：custom-perl（交互式 Perl 配置脚本）
- 编译方式：手动创建 config.mk
- 库类型：静态库（避免 RPATH 问题）
- 禁用功能：网络功能、可选图像库支持（可后续添加）

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 10.73.42 | built | 2026-05-22 |

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- netpbm 10.73.42
```

## 验证

```bash
pbmtext --version
# 输出: netpbm 10.73.42
```

## 参考资料

- 官网: https://netpbm.sourceforge.net/
- 源码: https://sourceforge.net/projects/netpbm/