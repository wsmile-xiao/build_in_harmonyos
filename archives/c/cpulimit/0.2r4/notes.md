# cpulimit 0.2r4 适配笔记

## 编译环境

- 构建系统：Makefile
- 上游提交：f4d2682804931e7aea02a869137344bb5452a3cd
- 下载源：优先使用 gh-proxy 镜像，失败时回退 GitHub
- 编译器：OHOS clang（由 Conan profile 的 tools.build:compiler_executables 注入）
- 编译日期：2026-09-29

## 编译步骤

```sh
make -j1 CC=<OHOS clang>
./tests/process_iterator_test
```

顶层 Makefile 会构建 src/ 与 tests/。上游没有 install 目标，因此配方显式将
src/cpulimit 安装到 package/bin。

## 上游测试

上游 README 指定 `tests/process_iterator_test` 作为测试入口。该程序通过
Linux/OHOS 的 /proc 读取进程、父子/子进程集合与 CPU 使用率，并在断言失败时
返回非零。配方在 build() 中直接执行它，不使用空壳测试替代。

## OHOS 适配点

1. `basename()` 在 OHOS sysroot 中需要显式包含 `<libgen.h>`。
2. `memrchr()` 需要 `_GNU_SOURCE`；Makefile 的 `CFLAGS ?=` 可能被构建环境覆盖，
   因此补丁在源码中固定定义。
3. `sys/sysctl.h` 只适用于 Apple/FreeBSD，OHOS/Linux 下条件排除。
4. `#ifdef __APPLE__ || __FREEBSD__` 不是合法预处理表达式，改为
   `#if defined(...) || defined(...)`。

## 验证

- 上游测试：build() 内执行 `./tests/process_iterator_test`
- 消费者测试：安装后的 `cpulimit --help` 输出与可执行权限检查
- 无外部依赖，仅使用 OHOS libc 与 pthread（测试辅助程序）
