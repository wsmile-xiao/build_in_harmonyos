# theft

Property-based testing framework for C, packaged as a Conan static library.

## OHOS 适配

- 使用上游 Makefile，以 `clang`、`ar`、`ranlib` 配置构建。
- 安装 `theft.h`、`theft_types.h` 和 `libtheft.a`，并声明 `libm` 系统依赖。
- 本次为路径 A 基础适配，未修改上游源码，也没有新增知识库扩展。

## 验证

- 上游测试：384/384 通过；原始上游 385 个运行时 test invocations 中，`forking_privilege_drop_cpu_limit__slow` 因 OHOS 不提供所需的 `RLIMIT_CPU`/信号行为而仅在 `__OHOS__` 下跳过。
- Conan 消费测试：1/1 通过，实际调用 `theft_hash_onepass`。

上游：https://github.com/silentbicycle/theft
