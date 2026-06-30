# rgb

rgb 是 X.Org 提供的 RGB 颜色名称数据库和颜色转换工具。

## 功能概述

- 提供标准 RGB 颜色名称数据库（rgb.txt）
- 将颜色名称转换为 RGB 数值
- 支持从 X 资源文件查找颜色

## OHOS 适配

- **构建系统**: autotools (configure + make)
- **主要补丁**: config.guess/config.sub 平台识别修复 + configure 临时目录路径修复
- **依赖**: xproto, util-macros

## 依赖关系

- xproto (7.0.33)
- util-macros (1.20.2)

## 参考资料

- 官网: https://xorg.freedesktop.org