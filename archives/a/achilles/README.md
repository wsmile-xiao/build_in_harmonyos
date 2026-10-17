# achilles

## 简介

Achilles 是一个人工生命与进化模拟器：在一个极简虚拟世界中，自由交互的虚拟生物通过
Hebbian 神经网络边打斗、交配、觅食，边进行学习。程序基于 Larry Yaeger 的 PolyWorld
思想，使用 SDL 1.2 与 OpenGL 固定管线渲染。

- 上游主页：https://mrd.github.io/achilles/
- 上游仓库：https://github.com/mrd/achilles
- 许可证：GPL-2.0-or-later

## 版本

| 版本 | 上游版本 | 状态 | 编译日期 |
|------|---------|------|----------|
| 3 | v3 | built | 2026-10-08 |

> 制品名为 `achilles/v3`（Conan 拒绝单字符版本号），归档目录沿用任务卡的 `3`。

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| sdl | 1.2.15 | 窗口/软件表面、事件与计时（静态库） |
| glu | 9.0.3 | GLU 投影/工具函数 |
| mesa | 24.3.4.1（经 glu 传递） | OSMesa 离屏软件渲染（softpipe） |
| libpng | 1.6.58.3 | PNG 截图输出 |
| alsa-lib | 1.2.16 | 静态 libSDL.a 的链接期依赖 |

## 编译说明

构建系统为 autotools（仓库内自带 2.71 版 `configure`，无需 autoreconf）：

```bash
conan create archives/a/achilles/3 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

关键点：

- 需为打包好的 `config.sub` 补充 `aarch64` 与 `linux-ohos`（2001 年版无法识别鸿蒙三元组）。
- `config.status` 的临时目录须以 `umask 022` 创建（setgid hmdfs 会让 0700 目录连创建者都不可写）。
- 鸿蒙 PC 无窗口系统、无窗口 GL；GL 上下文改由 **OSMesa 离屏**提供，帧渲染完成后拷贝到
  SDL 软件表面。运行需 `SDL_VIDEODRIVER=dummy`。
- 链接集需显式传入 `make`：`configure` 的 `AC_CHECK_LIB` 探测会重建 `LIBS`，且平台无 `libGL`。

## 运行

```bash
export LD_LIBRARY_PATH=<conan 依赖 lib 目录>
SDL_VIDEODRIVER=dummy ./bin/achilles -x 4 -z 4 -f 2 1 --fps 10
```

命令行选项：`-v/--version`、`-h/--help`、`-x <n>`、`-z <n>`、`-f <n>`、`--fps <n>`、
`--debug`、`<n>`（初始生物数）。运行中方向键移动、PageUp/PageDown 升降、`p` 暂停、
`s` 截图（screenshot.png）、`ESC` 退出。

## 平台适配说明

| 项 | 说明 |
|----|------|
| 渲染 | 窗口 GL（`SDL_SetVideoMode(SDL_OPENGL)`）在鸿蒙不可用，改为 OSMesa 离屏 + 软件表面拷贝 |
| 视频后端 | 使用 SDL dummy 视频驱动（软件表面） |
| 音频 | 上游仅初始化视频子系统，未调用 SDL 音频 API |
| 补丁 | 见版本目录 `patches/`（4 个可移植性补丁） |

## 测试

上游无任何测试套件（`make check` 目标存在但零用例，详见版本目录
`test_package/MANIFEST.yml` 的清点证据）。适配后补全 3 组消费者测试，共 49 条断言：

| 测试 | 断言数 | 说明 |
|------|-------|------|
| `test_cli.py` | 19 | 已安装命令的 CLI 行为（短/长选项、未知选项、无视频后端时的干净失败） |
| `test_simulation.py` | 12 | 真实无头仿真运行（主循环、帧率节拍、无崩溃） |
| `test_gl_stack.c` | 18 | OSMesa/GLU/SDL 栈探针（离屏渲染、像素回读、SDL 表面/事件/计时） |
| **合计** | **49** | 实测 49 executed, 0 failed |
