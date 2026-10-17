# libmpeg3 1.8.dfsg 适配笔记

## 编译环境
- 构建系统: GNU Make
- 编译日期: 2026-09-13
- 编译器: OHOS clang 15
- 目标平台: OHOS/aarch64
- 状态: built

## 编译步骤

使用 Conan OHOS profile，调用上游 Makefile，链接已发布的 `a52dec/0.7.4` 静态库。构建命令由 recipe 读取 Conan compiler executable，并注入依赖 include/lib 路径。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 引用缺失的 `mpeg3css.c` | 发行源码只提供可分发的 CSS fake 实现 | 使用 `mpeg3css_fake.c` 作为构建源 |
| 2 | OHOS 不提供 `__off64_t` | 非可移植 libc 类型 | 改用标准 `off_t` |
| 3 | `mpeg3toc.c` 缺少 timeval 声明 | 旧源码依赖间接头文件 | 显式包含 `<sys/time.h>` |
| 4 | 公开头文件依赖 `mpeg3private.h` | 上游 API 头文件设计 | 将该头文件一并安装 |
| 5 | `cmake.test()` 在本环境启动测试时 SIGSEGV | OHOS worker 的 Conan test runner 陷阱 | test_package 使用 Python subprocess 直启测试程序 |

## 源码修改

- `0001-Makefile.patch`: 使用发行包内的 CSS fake 实现。
- `0002-ifo.h.patch`: 使用可移植的 `off_t`。
- `0003-mpeg3toc.c.patch`: 显式包含 `<sys/time.h>`。

## 依赖版本

- `a52dec/0.7.4`

## 验证结果

```text
上游测试: 无。`make check` 返回 No rule to make target 'check'。
本地 Conan create: 通过。
消费者测试: 通过 2/2 次（libmpeg3 OHOS/aarch64 consumer test passed）。
```
---

**编译结束**: 2026-09-13 22:47
**最终状态**: built
