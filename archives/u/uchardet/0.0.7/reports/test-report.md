# 测试报告 — uchardet 0.0.7 (HarmonyOS PC, aarch64)

## 结论

- 上游测试（`ctest`，conan build() 内 `cmake.test()` 触发）：**116/116 (100%) 通过**
- test_package 消费者测试（真实 C API 调用）：**8/8 断言通过**（4 编码检测 + 4 reset 复用）
- 双变体验证：`shared=False`（默认，CI 路径）与 `shared=True` 均通过 conan create 全流程
- 全量通过率口径：`executed_passed_total/source_declared_total = 116/116 (100%)`
- 权威执行日志：`reports/conan-create.log` 与 `reports/w3-local-ci.log`（W3 本地 CI 模拟）

## 上游测试入口

- 入口命令：`ctest`（conan build() 内 `cmake.test()` 自动执行；等价上游 `make test`）
- 测试程序：`test/uchardet-tests.c`（C 编写，链接 libuchardet）
- 语料库：`test/<lang>/<charset>/` 目录，每个语料文件注册一项 ctest，
  断言检测结果与目录名（编码名）一致
- 上游 CMakeLists 显式跳过 5 项已知损坏用例（不注册 ctest，不计入总数）：
  `ja:utf-16le`、`ja:utf-16be`、`es:iso-8859-15`、`da:iso-8859-1`、`he:iso-8859-8`
- 语料覆盖 41 种语言/编码组合（ar/bg/cs/da/de/el/en/eo/es/.../zh 等），
  含 UTF-8/UTF-16/UTF-32/ISO-8859 系列/Windows 代码页/EUC-JP/EUC-KR/
  EUC-TW/GB18030/Big5/Shift_JIS/HZ-GB-2312/ISO-2022-* 等

## 消费者验证（test_package，R34 实质依赖）

`test.c` 通过公共 C API（uchardet_new/handle_data/data_end/get_charset/reset/delete）
检测 4 段预先用上游 CLI 在 OHOS 实测校准的字节序列：

| 样本 | 期望检测 | 实测 |
|------|---------|------|
| 纯 ASCII 英文 | ASCII | PASS |
| UTF-8 中文 | UTF-8 | PASS |
| GBK/GB18030 双字节中文 | GB18030 | PASS |
| Big5 中文 | BIG5 | PASS |

另含 4 项 reset 复用断言（reset 后重喂数据，检测结果须与首次一致）：全部 PASS。

## 双口径说明

| 口径 | 数量 |
|------|------|
| source_declared_total（ctest 注册项） | 116 |
| configured_executable_total | 116（5 项上游已知损坏由上游 CMakeLists 跳过，未注册） |
| executed_passed_total | 116 |
| failed / uninstantiated | 0 / 0 |
| 全量通过率 | 116/116 (100%) |

## 历史对照

- 2026-05-25 历史归档（built，无 Conan 配方）：`make test` 116/116 通过——与本次一致
- 本次（2026-09-18，Conan 适配）：conan create 内 ctest 116/116 通过 + test_package 8/8

## 环境

- 平台：HarmonyOS PC aarch64（os=OHOS, os.version 6.0）
- 工具链：clang 15.0.4 / clang++ libc++（profile `ci/conan/profiles/ohos-aarch64`）
- 构建：conan 2.29.1（OHOS 适配版）；CMake 4.1.2（CMAKE_POLICY_VERSION_MINIMUM=3.5）
- 配方关键点：CMAKE_SYSTEM_NAME=Linux（OHOS 上 CMake 自检为未知平台 HarmonyOS，
  无 SONAME 版本化规则；按 abcmidi 先例显式走 Linux 规则，shared 变体获得
  SONAME=libuchardet.so.0 与规范 NEEDED）
