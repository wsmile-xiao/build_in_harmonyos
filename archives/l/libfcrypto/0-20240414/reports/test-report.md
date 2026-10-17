# libfcrypto 0-20240414 测试报告

- 分支：`feat/libfcrypto-0-20240414`
- 验证方式：设备 W3 本地 CI 模拟（`ci/conan/build_and_test.sh`，与线上 CI 同源脚本），
  `conan create` 干净轮内完成构建、上游测试与消费者测试
- 证据：`archives/l/libfcrypto/0-20240414/reports/w3-local-ci.log`（本轮生成，任务目录
  evidence 副本绑定 SHA256）；上游测试逐程序输出在该轮构建目录
  `tests/test_library.sh.log`，副本与哈希存任务目录 evidence

## 上游测试（分母 = tests/Makefile.am 的 check_PROGRAMS，6 个 C 测试程序）

| 程序 | 结果 | 证据 |
|---|---|---|
| fcrypto_test_blowfish_context | PASS | `Testing: blowfish_context (PASS)` |
| fcrypto_test_des3_context | PASS | `Testing: des3_context (PASS)` |
| fcrypto_test_rc4_context | PASS | `Testing: rc4_context (PASS)` |
| fcrypto_test_serpent_context | PASS | `Testing: serpent_context (PASS)` |
| fcrypto_test_error | PASS | `Testing: error (PASS)` |
| fcrypto_test_support | PASS | `Testing: support (PASS)` |

- 程序级：N = 6，N′ = 6，PASS 6 / FAIL 0 / SKIP 0 / NOT_RUN 0
- runner 级（automake TESTS = `test_library.sh`，`--disable-python` 下
  `test_python_module.sh` 不在分母；`test_manpage.sh` 仅 check_SCRIPTS）：
  TOTAL 1 / PASS 1 / SKIP 0 / FAIL 0

## 消费者测试（test_package，Conan create 自动执行）

| 程序 | 断言数 | 结果 |
|---|---|---|
| test_libfcrypto（通用消费者） | 15 | 15 PASS / 0 FAIL，退出码 0 |
| test_ohos（鸿蒙特有） | 7 | 7 PASS / 0 FAIL / ≤1 SKIP（仅当只读 `/tmp` 且无 `TMPDIR` 时按 SKIP 记录、不计为通过），退出码 0 |

- 合计 22 断言：22/22（100%）
- 通用断言：版本查询（2）、RC4 上下文初始化/密钥（48 位）/加密/公开测试向量
  （`Secret`/`Attack at dawn`）、第二上下文解密回环（4）、NULL 上下文错误路径
  与 error 置位/释放（5）
- 鸿蒙断言：`__OHOS__` 编译目标（1）、打包共享库真实计算 RC4 向量（1）、
  可写临时目录（1）、临时文件建/写/重开/读回/删除（4）

> 断言为源码决定性计数：每个 `CHECK` 恰好打印一行 `PASS:`/`FAIL:`，程序以
> 失败数非零退出，W3 日志中的逐行输出与退出码即为确认。

## 首轮失败记录（诚实留痕）

首轮 W3（2026-09-18 07:46）：构建与上游测试全部通过；消费者测试 3 项失败——
`libfcrypto_rc4_context_set_key` 校验 `40 <= key_bit_size <= 2048`，首轮使用的
24 位密钥（key `Key`）被拒绝（返回 -1），上下文未初始化导致密文与公开向量不符
（解密回环因空状态 RC4 的确定性而碰巧一致）。修正为 48 位密钥公开向量
（`Secret`/`Attack at dawn`）后重新验证，以本轮结果为准。
