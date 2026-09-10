# clac 0.3.5 适配笔记

## 编译环境
- 构建系统: makefile（纯 make，无 configure）
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4（OHOS aarch64）
- 状态: built

## 编译步骤

1. `make CC=clang -j1`：顶层 makefile 依次构建内嵌依赖（`deps/linenoise/linenoise.o`、`deps/sds/sds.o`，各自子 make）并链接 `clac`（`-lm` + 两个 .o）。命令行传入的 `CC=clang` 会自动传播到子 make，无需改任何 makefile。
2. 上游测试：`CLAC_WORDS=./test/words sh test/tests.sh`（tests.sh 通过 `assert_equal` 比较 `./clac` 实际输出，失败时输出 `F:` 行）。
3. Conan 配方：`build()` 显式 `make -j1 CC=<profile clang>`；`package()` 直接拷贝 `clac` 与 `clac.1`（makefile 的 install 目标会运行 strip 并假设系统 PREFIX，不适合交叉环境）。

## 上游测试统计

| 口径 | 数值 |
|------|------|
| 上游静态断言总数（`grep -c assert_equal test/tests.sh`） | 31 |
| 实际执行 | 31 |
| 通过 | 31 |
| 失败 / 跳过 | 0 / 0 |

tests.sh 对每个断言失败时打印 `F:` 行；本次运行 stderr 为空、无 `F:` 输出，31/31 全部通过。`test/words` 提供 2 个用户自定义词（pi、tau），由 `CLAC_WORDS` 环境变量加载。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备无 `cc`，makefile 隐式使用 `$(CC)` 默认值会失败 | OHOS host 只提供 clang | `make CC=clang` 显式传入；命令行变量自动传播到 deps/ 子 make |

## 源码修改

无补丁。上游 makefile 原样可用（仅需命令行传 CC）。

## 依赖版本

无外部依赖。linenoise、sds 为官方源码包内嵌（deps/ 目录，随包构建）。

## 验证结果

```bash
$ make CC=clang -j1   # 构建成功
$ ./clac "3 4 +"      # => 7
$ CLAC_WORDS=./test/words sh test/tests.sh   # 31/31 通过，无 F: 输出
```

test_package（消费者测试）：`bash test.sh`，5 项断言——单数字、算术 `3 4 +`、求和 `sum`、用户自定义词 pi/tau，全部通过。

## 注意事项

- clac 为交互式 TUI 工具（linenoise），非交互模式下带参数求值并打印结果栈，消费者测试全部使用非交互模式。
- makefile 文件名为小写 `makefile`，GNU make 可自动识别。
- 二进制为 OHOS 本机可执行格式，构建后无需额外签名即可在设备上运行。
---

**编译结束**: 2026-09-08 23:52
**最终状态**: built
