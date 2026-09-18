# notes.md — status-code 1.0-gh0.20240312（任务 7385，GLM-8）

## 任务信息

- 包：status-code（system_error2，Niall Douglas 的 C++ 状态码库：generic_code/errc、system_code、errored_status_code，header-only）
- 上游：https://github.com/ned14/status-code ，**无 tag/release**（分支分发模式）
- 版本策略：CMake 工程版本 1.0 + cmigemo 式 gh 日期后缀 → `1.0-gh0.20240312`
- 锁定依据：outcome v2.2.9 官方 .gitmodules 声明的 `include/outcome/experimental/status-code` 子模块 commit `a35d88d692a23a89a39d45dee12a629fffa57207`（2024-03-12，outcome v2.2.9 提交日前一日，官方锁定），保证与 outcome v2.2.9 完全兼容
- 语言：cpp（header-only，C++17，p0709a 测试需 C++20）
- worktree：`~/qzy/GLM8-status-code-1.0-gh0.20240312`，分支 `feat/status-code-1.0-gh0.20240312`

## 依赖处理

无外部依赖（.gitmodules 仅 doc/html 文档子模块）。include/status-code 23 个头文件自包含，实测仅 -I include 即可编译全部测试。

## 测试账本（四维，2026-09-13 真机实测）

- N_static = **5**（test/*.cpp 逐文件静态清点；各文件均含 main，原生形态无外部测试框架）
- N_executed = 5，通过 **5**，test_skipped 0，未预期失败 0（**100%**）
- 编译标准：c++17（p0709a 用 c++20——P0709 静态异常提案语法所需，非平台限制）
- 消费者测试 N_consumer = 1（test_package/test_generic_code.cpp，2 断言：generic_code/errc 的 failure()/success() 判定）

## 门禁与环境

- CONAN_HOME：`~/tmp/ch/home-GLM8-qcpplib`（与 quickcpplib 串行共用，jobs=2，remotes.json 自 home-outcome 复制）
- profile：`ci/conan/profiles/ohos-aarch64`（-pr:h 与 -pr:b 同 profile）
- 编译器：clang/clang++ 15.0.4（tools.build:compiler_executables），`tools.build:jobs=2`
- 真机：OpenHarmonyPCDeveloper 共享设备（经 gate.sh 准入）

## 与 outcome 任务的关系

本包是 outcome 2.2.9（任务 7326/#9741）的官方依赖：outcome 实验层头文件以相对路径 `status-code/include/status-code/...` 与 `-I` 路径 `<status-code/...>` 两种形态引用本包头文件。outcome 配方整改（rule4：解决依赖后跑上游 42 测试）以本包与 quickcpplib 0.1.0.0-gh0.20231208 为前置（拓扑顺序：依赖先行）。
---

**编译结束**: 2026-09-14 01:11
**最终状态**: built
