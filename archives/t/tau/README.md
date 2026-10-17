# tau (Muon)

Muon — A Micro Unit Testing Framework for C/C++ (header-only).

- 上游: https://github.com/jasmcaus/tau（tag v1.0.0）
- 版本: 1.0.0（HarmonyOS PC / aarch64-linux-ohos 适配）
- 类型: header-only 测试框架（无编译产物，`#include <Muon/Muon.h>` 直接使用）
- 许可证: MIT

## OHOS 适配

- Conan 配方: `archives/t/tau/1.0.0/conanfile.py`（package_type=header-library）
- 上游测试: `MuonInternalTests` 124/124 suites 通过（OHOS clang15/musl）
- 鸿蒙专项测试: `test_ohos.c` 5 suites 全过（含 POSIX 计时路径）
- 消费者验证: test_package 2/2 CTest Passed

## 注意事项

- Muon 断言宏 `CHECK/REQUIRE` 必须携带消息参数（`CHECK(cond, "msg")`）；
  `CHECK_STRNE/REQUIRE_STRNE` 系为 3 参（actual, expected, n）。
  详见 knowledge/drafts/DRAFT-tau-1.0.0-muon-assertion-macro-message-argument。

## 版本索引

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.0.0 | published | 2026-09-19 |
