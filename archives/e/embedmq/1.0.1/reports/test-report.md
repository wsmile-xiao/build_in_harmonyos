# embedmq 1.0.1 测试报告

## 一、上游测试（双口径台账）

| 口径 | 数量 | 结果 |
|------|------|------|
| source_declared_total（tests/ 用户测试源独立用例） | 16 | - |
| configured_executable_total（CTest 注册可执行） | 2 | test_embedmq、test_embedmq_cpp |
| executed_passed_total | 16 | 全部通过 |
| 失败数 | 0 | - |
| 未运行/未实例化数 | 0 | - |

- 全量通过率：16/16 = 100%（通过数/全量发现数）
- 当前配置可执行集合通过率：16/16 = 100%

映射：`tests/test_embedmq.c`（10 个独立用例）→ 构建目标 `test_embedmq` → CTest `embedmq_tests` → 通过；
`tests/test_embedmq_cpp.cpp`（6 个独立用例）→ `test_embedmq_cpp` → CTest `embedmq_cpp_tests` → 通过。
无互斥编译分支/条件宏实例化差异；FreeRTOS 仿真（默认 OFF）与 examples/benchmark 为非独立用例，台账见 notes.md。

### 实际执行证据

```bash
$ cmake -S . -B build-native -DEMBEDMQ_BUILD_TESTS=ON -DEMBEDMQ_BUILD_EXAMPLES=ON \
    -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++
$ cmake --build build-native -j4        # 100% 成功
$ ctest --output-on-failure             # 2/2 Passed, 100% tests passed
$ ./test_embedmq                         # 10 个 [PASS]
$ ./test_embedmq_cpp                     # 6 个 [PASS]
```

Conan 流程内（ci/conan/profiles/ohos-aarch64, clang 15 aarch64-linux-ohos）：
`conan create` build() 内 `cmake.ctest()` → 2/2 Passed（日志：archives/e/embedmq/1.0.1/reports/conan-create.log，SHA-256 见 .ci-result.json）。

## 二、鸿蒙专项测试（新增）

`test_package/test_ohos.c` — OHOS 运行时 PAL 线程 + POSIX semaphore 分发语义实测：
4 生产者线程 × 250 条消息并发投递，消费者线程实际接收并执行 handler，
显式错误码断言可观察结果（delivered>0）。独立编译运行证据：

```bash
$ /data/service/hnp/bin/clang -fPIC -O2 -O3 -DNDEBUG -std=c11 \
    -I<src>/include test_package/test_ohos.c <lib>/libembedmq.a -pthread -o test_ohos
$ ./test_ohos    # [OHOS-SPECIAL] producers=4 msgs_per_producer=250 delivered=1000 last_value=254
                 # [OHOS-SPECIAL] PASS: PAL thread + POSIX sem dispatch works on OHOS runtime (exit 0, 5/5 稳定)
$ file test_ohos # ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1) — OHOS 目标
```

Conan test_package 内：ctest 2/2 Passed（test_embedmq + test_ohos）。

## 三、test_package 消费者测试

`test_package/test.c` — 通过公开 API（embedmq_create/register/post/destroy）模拟业务上层消费者：
注册 handler、投递 payload、验证 handler 实际执行且 payload 正确（value=42、delivered=1）。
Conan create 内通过（1/1）。

## 四、测试结论

- 上游测试全量通过（16/16, 100%）
- 鸿蒙专项测试通过（并发线程分发在 OHOS 运行时真实工作）
- 消费者验证通过（公开 API 编译/链接/调用/可观察结果）
- 编译状态：built（W3 本地 CI 通过，JC/L0 全绿）