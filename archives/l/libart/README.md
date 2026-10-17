# libart

## 简介
Libart（libart_lgpl）是 LGPL 授权的 2D 图形基元库：affine 变换、bezier 路径、排序向量路径（SVP）扫描线栅格化、UTA（微调平铺数组）等，GTK+ 2 / GdkRgb 时代的渲染后端。2.3.21 为 2010 年发布的最终版本。

## OHOS 适配
- 构建系统: autotools（2009 版 config.guess / 2008 版 config.sub，需 E007 HarmonyOS 识别补丁）
- configure 临时目录 umask 077→022（E011，HMDFS 平台限制）
- 零外部依赖，仅链接 libm；shared/static 由 libtool 完整支持
- 上游无 `make check`，以 noinst 的 testart（5 子命令）/ testuta 构建并运行作最近似验证
- 详见各版本 notes.md 获取适配详情

## 依赖
- 无（仅 system_libs=m）

## 功能验证
- 上游 testart testpat/gradient/dist/dash/intersect + testuta 全部退出码 0。
- Conan 消费者测试验证版本常量、affine 数学、vpath→SVP 转换。

## 参考
- 上游: https://gitlab.gnome.org/GNOME/libart_lgpl
- 归档规范: knowledge/ARCHIVE-SPEC.md
