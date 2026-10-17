# c-turtle 1.0.5 适配笔记

## 编译环境
- 构建系统: custom（header-only，无编译阶段）
- 编译日期: 2026-09-25
- 编译器: clang/clang++（OHOS SDK 26.0.0.18 llvm）
- 状态: built

## 编译步骤

c-turtle 是纯 header-only 库（CTurtle.hpp + 内置依赖头 CImg.h），无 configure/make。
Conan 配方无 `build()`，`package()` 仅搬运头文件与 LICENSE：

```bash
conan create archives/c/c-turtle/1.0.5 --build=missing -pr:h ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时无法下载源码 | 执行端网络到 github.com 443 不可达 | 改用 codeload.github.com commit 归档 URL 下载并核验 SHA-256，conandata 保留官方 GitHub URL（R39） |
| 2 | 上游无 git tag/release | 仓库只维护 master，README 标 1.0.5，头文件宏仍是 PATCH "4" | 以 master HEAD 1571a066（commit 消息 "v1.0.5 Patch"）作为 1.0.5 固定点，conandata 用官方 commit 归档 URL |
| 3 | CTurtle.hpp 公开头相对 include "CImg.h" | 上游把 CImg 3.1MB 单头 vendored 在仓库根 | package() 把 CTurtle.hpp 与 CImg.h 一并装入 include/（同族知识：headeronly-ship-bundled-dep-headers） |
| 4 | CImg 默认开 X11 显示后端 | cimg_display 默认 1 | 消费者 define CTURTLE_HEADLESS → CTurtle.hpp 内部设置 cimg_display=0，headless 输出 GIF，OHOS 无需图形栈 |

## 依赖版本

无 Conan 依赖；CImg.h 为内置 vendored 单头（源码树内）。

## 验证结果

- conan create（ohos-aarch64 profile）G2 通过；
- test_package 消费者：真实 include CTurtle.hpp、调用公开 API
  （TurtleScreen/Turtle/forward/right/xcor/ycor/write/bye），headless 画方并验证 GIF 输出。

## 注意事项

- 消费者必须定义 `CTURTLE_HEADLESS` 才能无图形栈编译运行；非 headless 交互模式依赖窗口事件，OHOS 上不启用。
- 头文件宏 `CTURTLE_VERSION` 自报 v1.0.4，与归档版本 1.0.5（README/commit）不一致，属上游遗留，不影响使用。
---

**编译结束**: 2026-09-25 06:46
**最终状态**: built
