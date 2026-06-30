# advancecomp 2.6

AdvanceCOMP 是一套重新压缩 PNG、MNG、ZIP 文件以减小其大小的工具集。

## OpenHarmony 适配状态

✅ 已成功适配 OpenHarmony，编译状态：built

## 工具列表

| 工具 | 功能 |
|------|------|
| advdef | 重新压缩 ZIP/GZIP 文件 |
| advmng | 优化 MNG 动画文件 |
| advpng | 优化 PNG 图像文件 |
| advzip | 重新压缩 ZIP 文件 |

## 补丁列表

| 补丁 | 说明 |
|------|------|
| 0001-config.guess.patch | 添加 HarmonyOS 平台检测 |
| 0002-config.sub.patch | 更新 config.sub 支持 HarmonyOS 目标 |
| 0003-configure.patch | 修复 umask 设置 |

## 编译要点

1. 使用 clang/clang++ 编译器
2. 应用全部 3 个补丁
3. 标准 autotools 流程

## 来源

- 官网：https://www.advancemame.it/comp-download.html
- 源码：https://github.com/amadvance/advancecomp