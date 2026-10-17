# C-Turtle

> Python Turtle 图形库的 header-only C++ 移植（Port of Python's Turtle to C++）

## 简介

C-Turtle 是 Berea College 的 Jesse Walker-Schadler 开发的单头（header-only）C++ 图形库，
在 C++ 中提供与 Python `turtle` 模块几乎等价的 Turtle 绘图 API：`ct::TurtleScreen`、
`ct::Turtle`（forward/back/right/left/penup/pendown/pencolor/…）、命名颜色、
动画/回调、undo 等。上游仓库本身不提供 CMake/Makefile 等构建系统，头文件即库本体。

本归档版本 1.0.5 对应上游 master HEAD `1571a066`（commit 消息 "v1.0.5 Patch"，2025-02-06；
上游无 git tag/release）。源码树包含：`CTurtle.hpp`（主库头，~288KB）、`CImg.h`
（内置依赖头，~3.1MB，公开头相对 `#include "CImg.h"`，必须随包分发）、`LICENSE.txt`（MIT）、
`README.md`、`examples/`（9 个示例，含 headless.cpp）、`docs/Doxyfile`。

## OHOS 适配要点

- 纯 header-only：配方无 `build()`，`package()` 把 `CTurtle.hpp` 与 `CImg.h` 装入
  `include/`，LICENSE 装入 `licenses/`；`package_info()` 清空 bin/lib 目录。
- 消费者编译/运行必须定义 `CTURTLE_HEADLESS`（示例 `examples/headless.cpp` 同款用法）：
  该宏在 include `CImg.h` 前设置 `cimg_display 0`，关闭 CImg 的 X11 显示后端，
  因此 OHOS 无需图形栈即可编译链接运行；headless 模式把画面写为 GIF 文件
  （`CTURTLE_HEADLESS_SAVEDIR`，默认 `./cturtle.gif`）。
- 非 headless 的交互 TurtleScreen 依赖窗口/事件（X11），OHOS 上不做启用。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| （无 Conan 依赖） | - | CTurtle.hpp 仅依赖 C++ 标准库（memory/list/unordered_map/thread/mutex 等）与内置 CImg.h |

## 功能验证

```bash
# 消费者验证（headless）：画一个正方形并写 GIF，检查输出文件非空
g++ -std=c++17 -DCTURTLE_HEADLESS -DCTURTLE_HEADLESS_SAVEDIR=./square.gif \
    -I<prefix>/include test_cturtle.cpp -o test_cturtle && ./test_cturtle
```

## 参考

- [官方文档](https://walkerje.github.io/C-Turtle/)
- [源码仓库](https://github.com/walkerje/C-Turtle)
