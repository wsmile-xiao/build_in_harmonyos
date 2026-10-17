# tl-expected 1.3.1 — OHOS 适配笔记

## 结论
- header-only C++14，零运行时依赖。
- 1 个补丁：FetchContent Catch2 → find_package(Catch2)。
- catch2/2.13.10-r0 作为 requirements 用于构建上游测试。

## 上游测试执行
- 上游 tests/*.cpp（排除 test.cpp）通过 CMake ctest 执行。
- Catch2 由 conan 提供，不联网。

## 版本对齐
- 任务 #5181 = conan 1.3.1 = 分支 feat/tl-expected-1.3.1 = 目录 archives/t/tl-expected/1.3.1。
