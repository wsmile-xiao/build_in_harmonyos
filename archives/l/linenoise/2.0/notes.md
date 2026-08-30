# linenoise 2.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-29
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 上游源码：https://github.com/antirez/linenoise/archive/refs/tags/2.0.tar.gz（官方仓库，原 waterlan 发行站已失效）
2. `make -j2`：编译 linenoise-example、linenoise-test（Makefile 使用 `$(CC)`，由 CC=clang 环境变量驱动）
3. 库编译：`clang -Wall -W -Os -fPIC -c linenoise.c -o linenoise.o && llvm-ar rcs liblinenoise.a`，同时生成 `liblinenoise.so`（`clang -shared -fPIC`）
4. Makefile 无 install 目标，手动 staging：头文件 → `include/linenoise.h`，库 → `lib/`
5. 验证：静态/动态链接均通过，`linenoiseHistorySetMaxLen()` + `linenoiseHistoryAdd()` 冒烟测试 OK

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | waterlan 官网下载返回 HTML | 原发行站 waterlan.home.xs4all.nl 已失效（重定向 notxs4all） | 改用官方 GitHub 仓库 antirez/linenoise tag 2.0 |
| 2 | `TERM=dumb` 下 make check 14/72 通过（58 失败） | `TERM=dumb` 触发 linenoise 的兼容降级分支，VT100 测试无法获得编辑回显；测试框架的多行启动提示也会污染模拟屏幕 | 设置 `TERM=xterm` 运行编辑路径，并在测试输出解析中过滤非 VT100 的 `Multi-line mode enabled.` 提示；完整 72/72 通过；test_package 继续提供 API 冒烟测试（R34） |
| 3 | 链接冒烟测试最初误判失败 | linenoise API 成功返回 1、失败返回 0，与常规约定相反 | 修正断言方向后通过 |

## 源码修改

新增 `patches/0001-fix-ohos-vt100-test-output.patch`：避免测试子进程 stderr 混入 VT100 模拟器输出，并过滤多行模式启动提示，保证测试框架解析屏幕状态时不受非终端文本干扰。该补丁只修改上游测试程序，不修改 linenoise 库 API 或实现。

## 依赖版本

- 无外部依赖（单文件 C 库，仅依赖 libc）

## 验证结果

```bash
# 上游 VT100 测试（OHOS arm64，本地真实 PTY）
TERM=xterm script -q -c './linenoise-test' /storage/Users/currentUser/tmp/linenoise-2.0-interactive-test.log
# -> Tests run: 72, Tests passed: 72, Tests failed: 0

# 静态链接
clang -I include ln-linktest.c lib/liblinenoise.a -o ln-linktest && ./ln-linktest
# → linenoise static link OK
# 动态链接
clang -I include ln-linktest.c -Llib -llinenoise -o ln-linktest-dyn && LD_LIBRARY_PATH=lib ./ln-linktest-dyn
# → linenoise static link OK
```
---

**编译结束**: 2026-08-29 14:04
**最终状态**: built
