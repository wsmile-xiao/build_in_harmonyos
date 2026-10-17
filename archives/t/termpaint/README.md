# termpaint

## 简介

termpaint 是一个面向现代终端的低层终端接口库，提供终端单元显示和键盘抽象。

## 功能概述

- 终端单元格显示与键盘事件抽象
- 支持全屏与集成模式
- UTF-8 文本处理与宽度测量
- 图像加载/保存支持（libtermpaint_image）
- ttyrescue 终端恢复机制

## OHOS 适配

- Meson 构建系统，设置 `ttyrescue-fexec-blob=false`（fexec blob 仅 Linux 支持）。
- Clang 15 的 `-Werror=strict-prototypes` 将空参数列表 `()` 视为错误，通过补丁修复 `termpaint_input.c`。
- 所有第三方依赖（picojson, docopt, fmt, catch2）内嵌源码树，无 Conan 依赖。
- 产物为两个库：`libtermpaint`（核心）和 `libtermpaint_image`（图像支持）。

## 依赖关系

- 编译依赖：无（全部内嵌）
- 运行依赖：librt（系统库，clock_gettime）

## 参考资料

- 上游仓库：https://github.com/termpaint/termpaint
- 版本：0.3.0
- 许可证：BSL-1.0 (Boost Software License)
