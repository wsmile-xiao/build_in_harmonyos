# gengen 1.4.2 Test Report

- 日期：2026-09-12
- 平台：HarmonyOS PC aarch64（OHOS），clang 15.0.4，conan 2.29.1（OHOS 适配版）
- Reference：gengen/1.4.2@ohpcd/stable（profile ci/conan/profiles/ohos-aarch64）
- 适配者：GLM-15

## 总结论

- 编译状态：通过（conan create 干净构建成功，W3 本地 CI Success: 1）
- 上游测试：52/52 通过（N_static = N_executed = 52）
- 消费者测试（test_package）：7 项断言 0 失败

## 上游测试（make check）

| 维度 | 数值 | 说明 |
|---|---|---|
| N_static | 52 | tests/ 金标 diff 44（35 生成文件 + 8 错误输出 + 1 verbose）+ tests/otherdir 4 + src/tests 单元测试 4 |
| N_registered | 52 | 全部注册于 make check，无排除项 |
| N_executed / 通过 | 52 / 52 | make check -j1 exit 0 |
| 跳过 | 0 | check-valgrind 不在默认 check 注册链，不计入 |

- 原始日志 evidence：reports/upstream-tests-log.md（含原字节数 21497 / sha256 4060f39a049194588a559b35ce6e7df6119d82ee915cce4cd35fc8abc9e07808）
- 上游测试修改说明：4 条测试链接规则删除命令行上的 .h（2010 GCC 容忍、clang-15 报
  "cannot specify -o when generating multiple output files"；头文件依赖已由
  check-am 先建 BUILT_SOURCES 保证，测试语义不变；测试源文件零修改）

## 消费者测试（test_package/test.py，N_consumer = 1）

闭环：gengen 由最小 .cc_skel 生成 demo.h → 断言生成内容契约（class demo_gen_class /
set_value / set_flag / generate_demo）→ 与消费者 main.cc 一起编译 → 运行并逐字断言输出
（`demo begin\n  value=42\n  flag=yes\ndemo end\n`）。

- W3 conan create 内真实运行：7 项断言，失败 0 项（reports/conan-create.log 724-732 行）

## W3 本地 CI

- .ci-result.json：exit_code = 0（W3_local_ci）
- JC/L0/L1/L2/L4/L5 全部 pass（reports/w3-local-ci.log：涉及软件数 1（合规），test_package executed，gengen --version OK）

## conan-verify

- G0/G1/G2/G3/G4 全部 PASS（第 3 轮，reports/conan-verify-report.md）
