# semver 1.0.1 — OHOS 适配笔记

## 结论
- header-only C++17，零运行时依赖。
- 上游测试用 vendored doctest（test/3rdparty/doctest/），build() 内直接编译运行所有 test/*.cpp。
- 源码在 OHOS/aarch64 原样编译通过，无补丁。

## 版本对齐
- 任务 #5224 = conan 1.0.1 = 分支 feat/semver-1.0.1 = 目录 archives/s/semver/1.0.1。
---

**编译结束**: 2026-08-31 13:34
**最终状态**: built

## 上游测试执行证据（全量 doctest 套件）
- build() 编译上游主测试目标 9 个源文件（test.cpp 提供 doctest main + 8 个套件文件），-DDOCTEST_CONFIG_USE_STD_HEADERS
- 实测: [doctest] test cases: 89 | 89 passed | 0 failed | 0 skipped; assertions: 52851 | 52851 passed（w3-local-ci.log / conan-create.log）
- 排除: test_config.cpp（需 SEMVER_CONFIG_FILE 覆盖，独立 target）、test_windows_minmax.cpp（MSVC-only）
- test_package: 10 断言全过（日志 semver test_package: 10 checks, 0 failed）
