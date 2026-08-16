# liquid-dsp 1.8.0.1 测试报告

## 验证范围

- 设备：OpenHarmony PC 真机，AArch64
- 编译器：clang/clang++ 15.0.4
- 构建：CMake 4.1.2，static-only，内置 FFT，自动启用 NEON
- 必需外部依赖：无；可选 FFTW 关闭
- 上游源码：v1.8.0，SHA256
  `abef8b2ddfd58c0a84ecda4f62158c4824b916144af4a2b07776e1a144d8cda4`

## Shadow CI

- Run ID：`xuguowei-liquid-dsp-liquid-dsp-issue-2206-shadow-r8r2-d1b4882a00-20260816-001734-29564`
- 被测代码提交：`d1b4882a00e3`
- 被测归档 SHA256：`426dfb52d71c2df908895998605bb6afcc38c5902218f81f831ac030935a35ef`
- 时间：2026-08-16 00:17:34 至 00:22:15 +0800
- runner：heavy + `--try-lock`，0 秒取得锁
- 退出码：外层 SSH 0，runner 内部 0，stderr 0 字节
- Build Summary：Total 1 / Success 1 / Failed 0
- 全局锁：已正常释放

门禁结果：L0 pass、L1 pass、L2 skip（库包无 `bin`）、L4 warn（补丁文本静态扫描，
非阻塞）、L5 pass；L1e 破坏性反向验证通过。

## 上游测试

配方启用 `BUILD_AUTOTESTS=ON`，`build()` 调用 `cmake.test()`。CTest 1/1 通过，
耗时 60.41 秒；聚合 `autotest` target 内部实际执行上游 `xautotest`：

```text
tests  : pass=1341   fail=0   skip=0
checks : pass=716520 fail=0
overall: warn=55     PASS
```

- 上游逻辑用例：1341/1341（100%）
- 上游断言：716520/716520（100%）
- 上游测试修改或裁剪：无

## test_package 消费者

消费者通过 `find_package(liquid CONFIG REQUIRED)` 链接
`liquid::liquid-static`，并在真机执行三项检查：

1. `liquid_nchoosek(5, 2) == 10.0f`
2. `liquid_version` 非空
3. `windowf_create/push/index/destroy` 行为正确

原 Shadow CI 消费者检查为 3/3；AI 检视后于 2026-08-16 01:40 +0800 使用同一
真机隔离包重新编译并运行当前 `test.c`，结果仍为 3/3（100%）。这些是 Conan/CMake
包消费合同检查，不宣称为上游无测试补全。

## B 类 before/after 验证

- Run ID：`xuguowei-liquid-dsp-issue-2206-path-b-evidence-r3-20260815-225009-42915`
- 时间：2026-08-15 22:50:09 至 22:50:52 +0800
- runner：heavy + `--try-lock`，0 秒取得锁，退出码 0

同一份未应用补丁的 v1.8.0 Conan source cache 被复制为 before/after 两份，after
仅应用当前 CMake 补丁：

| 检查 | before | after |
|---|---|---|
| canonical `find_package(liquid)` | 返回 1 | 通过 |
| Config/Targets | `liquid-static*` 且内部引用断裂 | `liquidConfig`/`liquidTargets` 一致 |
| 导出 target | canonical package 无法消费 | `liquid::liquid-static` |
| 消费者运行 | 未配置 | PASS |

stderr 中的 CMake HarmonyOS platform module、`/proc/meminfo` 和 make jobserver FIFO
信息为非阻塞环境告警，不属于本次知识条目的错误根因。

## 产物

- `include/liquid/liquid.h`
- `lib/libliquid.a`
- `lib/cmake/liquid/liquidConfig.cmake`
- `lib/cmake/liquid/liquidTargets.cmake`
- `lib/pkgconfig/liquid-dsp.pc`

结论：基础适配、上游测试、包消费者和 B 类修复前后对照均通过。
