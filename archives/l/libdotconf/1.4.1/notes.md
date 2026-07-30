# libdotconf 1.4.1 适配笔记

## 构建策略

- 源码：上游 `v1.4.1` 标签归档，SHA256 已固定。
- 构建系统：直接使用 Clang 编译 `dotconf.c` 和 `readdir.c`。
- 产物：静态库 `libdotconf.a`、公共头文件 `dotconf.h` 和许可证。
- Conan 依赖：无。

上游标签归档仅包含 `configure.ac`，没有生成后的 `configure`。配方直接编译
上游库源文件，避免在受限 CI 环境中引入 Autoconf、Automake 和 Libtool。

## 上游测试

上游未注册 Automake `TESTS` 或 `make check` 测试目标，但
`examples/maketest.sh` 定义了 9 个示例回归场景。每个场景会编译示例、
运行示例并使用 `cmp` 对比上游维护的期望输出：

1. caseinsensitive
2. errorhandler
3. fallback
4. modules
5. noinline
6. simple
7. argdouble
8. context
9. duplicates

配方在目标二进制可运行时执行这 9 个场景，不修改上游示例源码或期望输出。
OHOS 对重定向后的标准输出和标准错误采用不同的缓冲顺序，因此 `context`
场景按完整输出行集合比较；仍严格检查全部 12 行的内容和出现次数。

## 消费者测试

`test_package/test_libdotconf.c` 通过打包后的公共 API 执行 12 项断言，覆盖：

- 配置对象创建和完整解析；
- 严格校验 `dotconf_command_loop()` 的成功返回值为 `1`，与上游实现及示例一致；
- 字符串、整数、开关、浮点和列表参数；
- 无参数回调；
- 大小写不敏感的选项匹配；
- 六个回调均被调用。

## 验证边界

- Linux/Clang 14 原生 Conan 构建：通过。
- 上游示例回归：9/9 通过。
- 打包后消费者断言：12/12 通过。
- 本地 OHOS AArch64：未运行。
- OHOS 构建和运行：以赛事官方 CI 为最终验证。
