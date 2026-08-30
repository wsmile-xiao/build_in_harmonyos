# foonathan-memory 0.7 测试报告

## 验证环境

- 设备：HarmonyOS PC，HongMeng Kernel 1.12.0
- 架构：AArch64 / `os=OHOS`, `arch=armv8`
- 编译器：HNP clang/clang++ 15.0.4
- CMake：4.1.2
- Conan：2.29.1
- Profile：`ci/conan/profiles/ohos-aarch64`

## 测试结果

| 指标 | 数量 | 结果 |
|---|---:|---|
| 总测试数 | 40 | TOTAL |
| 通过 | 40 | PASS |
| 失败 | 0 | FAIL |
| 跳过 | 0 | SKIP |

40 项由 39 个上游 Catch2 测试用例和 1 个 Conan `test_package` 消费者测试组成。

上游 CTest 注册 1 个 CTest，运行结果为 1/1 通过；其 Catch2 汇总为
39/39 test cases、140870 assertions 全部通过。上游测试程序通过 `cmake.test()`
在 Conan `build()` 内执行，消费者测试调用真实的 `heap_allocator`、
`malloc_allocator`、`new_allocator`、`memory_pool` 和 `std_allocator` API，覆盖零字节、普通尺寸及
`std::vector` 对齐/内容检查。

## 运行命令与证据

```bash
PROFILE=/storage/Users/currentUser/ws/foonathan-memory-0.7/ci/conan/profiles/ohos-aarch64
conan create archives/f/foonathan-memory/0.7 \
  -pr:h="$PROFILE" -pr:b="$PROFILE"
```

结果：Conan 包创建完成，CTest 通过，`test_foonathan_memory` 退出码为 0。
独立执行缓存中的上游测试得到：

```text
Passed all 39 test cases with 140870 assertions.
```

工具运行验证：`bin/nodesize_dbg --version` 输出
`nodesize_dbg version 0.7`，退出码为 0。

## 产物

- Conan release payload：`packaging/foonathan-memory-0.7-ohos-aarch64.tar.gz`
- Release SHA-256：`d6577a4178ed9fdc79af9b6437447a8179a96e827736ff2282f7312589f3303c`
- Conan debug payload：`packaging/foonathan-memory-0.7-ohos-aarch64-debug.tar.gz`
- Debug SHA-256：`5d868851b7556ca9897580b322560dce4b216a07fff84840ed3e137e5c709f97`

## 已知限制

- `ohc-run.py finish` 的通用 G0 清洁验证器仍无条件执行 `./configure`，而本项目是
  CMake-only；因此该旧验证步骤不能代表本 Conan W3。官方 Conan W3、完整上游 CTest
  和消费者测试均已在同一设备/profile 上通过。
- 设备端相对路径 profile 会回退到默认 profile；验证命令使用绝对路径，避免缺少
  `os.version=6.0`。
- 远端 `ohpcd` 查询当前受 `system acceleration policy not enabled` 限制，未据此宣称
  registry 已发布。
