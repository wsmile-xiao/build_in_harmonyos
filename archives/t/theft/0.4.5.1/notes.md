# theft 0.4.5.1 适配修订记录

## 修订原因

- `theft/0.4.5` 原 recipe 未移除 OHOS profile 提供的 `os.version` 设置。
- 使用 `conan install --requires=theft/0.4.5 -r=ohpcd --build=never` 验证时，Conan 将已发布 binary 判定为 `Invalid: 'settings.os.version' value not defined`。
- 本修订将版本号递增为 `0.4.5.1`，并在主 recipe 和 `test_package` recipe 中通过 `configure()` 移除未使用的 `os.version`，保持原有上游源码、补丁和测试不变。

## 依赖与构建

- Conan requires/tool_requires：无。
- 系统链接依赖：`libm`，由 `cpp_info.system_libs` 声明。
- 构建系统：上游 Makefile，使用 Conan compiler executables 配置 `clang`、`ar`、`ranlib`。

## R8 平台宏例外说明

补丁在上游测试注册点使用 `#ifndef __OHOS__`，仅屏蔽 `forking_privilege_drop_cpu_limit__slow`。该测试依赖 `setrlimit(RLIMIT_CPU, 1)` 触发 CPU-limit 信号；OHOS 独立探针已验证死循环不会收到所需信号，外部 5 秒 timeout 以 137 结束。由于测试框架没有可移植的运行时 skip 接口，且必须保留其余 384 个上游测试，使用平台宏是此次例外的最小修改。PR 描述将同步提供该证据。

探针复核记录：在 OHOS PC aarch64、clang 15、Conan 2.29.1 环境执行 `setrlimit(RLIMIT_CPU, 1)` 后运行与该测试等价的 CPU 密集型死循环，并以 `timeout -k 2 5 ./rlimit_cpu_probe` 保护；结果为外部 `timeout` 触发 SIGKILL，进程返回码 `137`，而不是由 `RLIMIT_CPU` 产生预期的 CPU-limit 信号。该结果与上游测试 `forking_privilege_drop_cpu_limit__slow` 在适配前的设备日志一致。适配后仅该用例跳过，`make -j1 all test` 中其余 384 个 runtime test invocations 全部通过。


- 上游测试库存：385 个 runtime test invocations。
- OHOS 实际执行：384/384 通过；仅因 OHOS 不提供所需的 `RLIMIT_CPU` 到时信号行为跳过 1 个测试。
- 消费者测试：1/1 通过，实际调用 `theft_hash_onepass`。
---

**编译结束**: 2026-09-05 01:04
**最终状态**: built
