# libtiger

libtiger 是 Ogg Kate 字幕流渲染库，使用 Pango 负责文字排版、Cairo 负责光栅化输出。
Kate 字幕流相关背景见 https://wiki.xiph.org/OggKate。

## 描述

libtiger 提供面向 Kate 事件流的渲染器：调用方创建 `tiger_renderer`，
绑定一块 ARGB 像素缓冲，送入 `kate_info`/`kate_event` 后更新并渲染，
即可得到叠加字幕帧。公开 API 全部在 `tiger/tiger.h` 中。

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 0.3.4 | built | 2026-09-18 |

## 依赖

- libkate（Kate 解码；公开头包含 `kate/kate.h`）
- cairo（像素缓冲与绘制后端）
- pango（经 pangocairo 的文字排版）

## 编译说明

使用 autotools 构建系统。关键配置选项：

- `--disable-doc`：关闭 doxygen 文档（构建环境无 doxygen）
- `--disable-shared --enable-static`：默认静态构建
- HarmonyOS 构建需给 bundled config.sub 打补丁（见 `0.3.4/patches/`），
  使其识别 `aarch64` CPU 与 `linux-ohos` 目标

## 上游测试说明

上游发布包不含单元/集成测试框架；`make check` 运行 3 组 check-local
源码规范检查（符号命名空间、内存分配封装、残留调试打印），配方在
`build()` 中完整运行。消费者测试见 `0.3.4/test_package/`。
