# c10t

> Minecraft cartography tool：将 Minecraft 存档渲染为 PNG 地图图片。

## 简介

c10t 是由 John-John Tedro（udoprog）开发的 Minecraft 地图绘制工具。
它读取 Minecraft 存档（level.dat / region 文件），使用多线程流水线渲染为 PNG 图片，
支持颜色配置、夜间模式、高度图、玩家位置标记等功能。

## OHOS 适配要点

- CMake 构建的命令行工具包，仅发布 `c10t` 二进制（application 包，R38）。
- 内嵌 `libs/unc` 随源码树一起构建（`BUILD_DEV_LIBS=ON`，与 Homebrew 做法一致）。
- 上游 `cmake_minimum_required(VERSION 2.6)` 已提升到 3.5 以兼容设备侧 CMake 4.x；
  `git rev-list` 版本探测在无 .git 的 conan 源码包中回退为固定版本号。
- 针对 Boost >= 1.85 移除了 `filesystem::basename/extension/is_regular` 等旧 API，
  补丁改用 `path::stem()/extension()/is_regular_file()`（Homebrew 同类修复的上游对齐版）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.91.0.1 | thread + filesystem（system 已 header-only，不再列为组件） |
| libpng | 1.6.58 | PNG 图片输出 |
| freetype | 2.14.3 | 文字标注渲染 |
| zlib | 1.3.1.1 | 存档解压（与已发布 libpng/1.6.58 闭包同版本，避免版本冲突） |

## 功能验证

```bash
c10t --help         # 打印用法
c10t --list-colors  # 列出方块颜色表（Homebrew 官方测试同款）
```

## 参考

- [源码仓库](https://github.com/udoprog/c10t)
- [Homebrew Formula](https://formulae.brew.sh/formula/c10t)
