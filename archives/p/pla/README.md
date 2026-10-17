# pla

**版本**: 1.3
**语言**: C
**许可证**: GPL-2.0-only
**主页**: https://www.arpalert.org/pla.html
**上游源码**: https://github.com/thierry-f-78/pla

## 简介

pla 是一个命令行甘特图（Gantt chart）生成工具。它读取一个简单的任务描述文件
（任务 id / 名称 / 开始时间 / 持续时间 / 依赖 / 完成百分比等），并通过 cairo
渲染输出 PNG / EPS / PDF / SVG 图形，也支持 CSV / TEX 等文本导出。

## HarmonyOS PC 适配

- 构建系统：普通 Makefile（无 configure），通过 `pkg-config --cflags/--libs cairo`
  发现 cairo。
- 唯一三方依赖：`cairo/1.18.4`（依赖链 pixman / libpng / fontconfig / freetype /
  expat 均已发布到 ohpcd 制品仓，R36 满足）。
- 配方要点：
  - `requirements()` 声明 `cairo/1.18.4`；
  - `generate()` 用 `PkgConfigDeps` 生成 cairo 的 `.pc` 并设置 `PKG_CONFIG_PATH`；
  - 编译器从 Conan conf 获取（R33），`make -j1`；
  - 构建时清空宿主 `LD_LIBRARY_PATH`（E132：宿主 /usr/local/lib 的 libxml2 会干扰
    OHOS SDK lld）；
  - test_package 真实执行 `pla` 二进制并用 cairo 渲染 PNG（R34/R40），并对 E073
    （HMDFS 动态加载器无法跟随 .so 符号链接）做真实文件 staging。
- 零源码补丁（无需修改 pla 源码即可编译运行）。

## 适配版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.3 | built | 2026-09-02 |
