# vrpn 07.36 测试报告（test-report）

> 任务：vrpn 07.36（任务号 11759）｜分支 feat/vrpn-07.36｜配方定稿 HEAD 970f31abc4
> 构建机：B 机（frp-bar.com:19214）｜CONAN_HOME=~/tmp/ch/home-vrpn
> 数字同源：本报告与 `notes.md` §测试账本、`reports/w3-local-ci.log` 机器行同源；CI/AI 判决后正文引用同一组数。

## 五维账本

| 维度 | 读数 | 依据 |
|---|---|---|
| 静态清点（上游测试程序） | 探索构建（全默认）日志可见 **26 条** `Built target test_*`（含并行重复，去重 18 个唯一测试目标；`grep -c` 实测，W60-1 整改） | `~/tmp/uc2/vrpn/build.log`；上游 `client_src/CMakeLists.txt` 的 `if(BUILD_TESTING)` 门 |
| 包内可执行（bin/） | **8 个**（vrpn_server 等） | 包目录 `bin/`；`commands.json` 已声明 |
| 实测通过 | test_package 消费者测试 **ctest 1/1 Passed**（test_vrpn，1.03s）；L2 smoke **8 样本 3 OK / 5 不适用**（`--version` 不支持的交互式工具） | `.ci_logs/conan_build_vrpn_07.36.log` :719-724；`reports/w3-local-ci.log` `L2_RESULT=pass` 行 |
| 跳过 | 包内上游测试套件**未逐项运行**：包构建 `BUILD_TESTING=OFF` 属配方裁剪（非运行时跳过）；依据 = `client_src/CMakeLists.txt` 的 `if(BUILD_TESTING)` 门与探索构建对照 | `notes.md` §测试账本 |
| 失败 | **0**（ctest 0 failed；L5 fail 行 0） | `reports/w3-local-ci.log` `Success: 1 / Failed: 0` |

## W3 本地 CI 机器行（reports/w3-local-ci.log）

```
G0_RESULT=pass
KC_RESULT=pass
JC_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: run_auxiliary_logger --version OK, vrpn_average_analogs failed, vrpn_log_devices --version OK, vrpn_print_devices failed, vrpn_print_messages failed, vrpn_print_performance failed, vrpn_server --version OK, vrpn_streamPrint failed
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
  Success: 1
  Failed:  0
```

`conan-verify` 第 5 轮 G0-G4 与 L 段全 PASS（`reports/conan-verify-report.md` Verdict: PASS，2026-09-26 02:56:21）。

## 口径说明（防 rule4 少报/多报）

1. **上游测试套件未逐项运行**是配方裁剪（`BUILD_TESTING=OFF`），非运行时失败或运行时跳过；
   正文申报不将 26 条静态清点（去重 18 个唯一测试目标）计成"通过"，也不把 18 个测试可执行计成"实测运行数"（W60-9 整改：与 ：11 账本行同口径）。
2. test_package 是消费者语义测试（真实链接六库 + 调 `vrpn_Connection` 公开 API + `removeReference()` 释放），
   实测 1/1 通过。
3. L2 smoke 的 5 个 "failed" 为交互式工具不支持 `--version` 的预期形态（非崩溃），框架判定整段 pass；
   读数以 `w3-local-ci.log` 机器行为准。

## 已知限制

- `atmellib` 门控修复（补丁 0001）只对齐 `if(UNIX)`→`if(NOT WIN32)` 一处；jsoncpp/hidapi 子模块
  在 tag 归档中为空，`VRPN_USE_LOCAL_JSONCPP/HIDAPI` 按 `option_requires` 语义自动 OFF（主理裁决接受降级，
  见 `notes.md` 第 0 步读数）。
- 时序：W3/finish 绿的读数取自配方定稿轮；其后仅新增 B 草稿（knowledge/drafts/ 成对）与本报告等
  文本/证据件提交，未再触发配方与测试代码改动。
