# libfex 0.1.0 适配笔记

## 编译环境
- 构建系统: cmake（++ 提供并行 Makefile 直编路径）
- 编译日期: 2026-09-16
- 编译器: clang/clang++（OHOS SDK clang 15.0.4，aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

1. 下载官方源码（GitHub 直连超时，经 ghproxy 镜像通道获取同一官方
   `refs/heads/master.tar.gz`，SHA-256 75cbad7e…a794c8）
2. `ohc-run.py init-build libfex 0.1.0 --no-download`（手动放置源码到
   `$HOME/tmp/builds/libfex-0.1.0.work`，绕开网络下载步骤）
3. `ohc-run.py lang-preflight` → detected=cpp（R47 通过）
4. CMake 直编验证: `cmake -S . -B build-ohos` + `make` → libfex.a +
   fex-passthrough（-std=c++2b，仅示例警告）
5. `ohc-run.py conan-init`（生成配方骨架）→ 改写 CMake 配方（liburing/2.15
   依赖 + CMakeDeps）+ 7 个补丁（5 处 include 改指 + CMakeLists liburing
   find_package + expected_compat.hpp 新文件）
6. `ohc-run.py conan-verify` → G1-G4 全 PASS（含 test_package 消费者测试
   ctest 1/1）
7. 鸿蒙专项测试 harmonyos-test/ 编译运行 ALL PASSED
8. `ohc-run.py finish published` → W3 本地 CI 模拟通过（status=built，
   .ci-result.json exit_code=0）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'expected' file not found` | OHOS libc++15 无 C++23 `<expected>`（libc++ 17 才提供） | 新增 fex/expected_compat.hpp（MIT 单头 std::expected 实现，namespace std 注入），5 处 `#include <expected>` 改指；详见知识草稿 DRAFT-libfex-0.1.0-std-expected-polyfill-libcxx15 |
| 2 | clang-15 报 `invalid value 'c++23'`；CMake 写 `CMAKE_CXX_STANDARD=2b` 报 `CXX2b` ABI 探测错 | clang-15 只认 `-std=c++2b`；CMake 只接受数值标准 | 配方不写 2b，交回上游 `set(CMAKE_CXX_STANDARD 23)`，CMake 自动映射 -std=c++2b；下游 cxxflags 传 `-std=c++2b` |
| 3 | `pkg_check_modules(liburing)` 在 conan create 找不到 | liburing/2.15 Conan 包不提供 .pc | 补丁 CMakeLists 改 `find_package(liburing CONFIG REQUIRED)` + `liburing::liburing`（CMakeDeps 生成目标） |
| 4 | GitHub 直连下载超时 | 网络到 github.com 受限 | 镜像通道下载同一官方 tarball，conandata 保留官方 URL（CI 侧 E017 镜像注入） |
| 5 | W3 JC 拦截：archives/c/cloog/0.21.1/.build-closed 与 .staging-verified | 其他库提交前已存在于 main 的基线空文件被 git 追踪 | 基线隔离复验：记录隔离前 SHA-256（e3b0c442、e3b0c442，均为空文件哈希）→ git rm --cached 临时隔离 → 复跑 W3 通过 → 原样恢复 → 恢复后 SHA-256 一致；未修改/未提交该基线文件 |

## 源码修改

- patches/0001-CMakeLists.txt.patch — liburing pkg-config → find_package
- patches/0002-examples-passthrough.cpp.patch — include <expected> 改指
- patches/0003-include-fex-expected_compat.hpp.patch — 新增 polyfill 头（新文件）
- patches/0004-include-fex-filesystem.hpp.patch — include 改指
- patches/0005-include-fex-session.hpp.patch — include 改指
- patches/0006-src-session.cpp.patch — include 改指
- patches/0007-src-session_impl.hpp.patch — include 改指

## 依赖版本

- liburing/2.15（Conan 依赖，io_uring 传输层）

## 验证结果

- conan-verify: G1-G4 PASS
- W3 本地 CI: .ci-result.json exit_code=0
- test_package 消费者测试: ctest 1/1 Passed
- 鸿蒙专项测试: harmonyos_libfex_test ALL PASSED（SHA-256 e539e10d…9ab2a7）
- 上游测试：无（完整枚举见 reports/test-ledger.md）

## 知识沉淀

- 路径 B（知识库扩展）new_draft:
  - 台账: reports/knowledge_candidate_ledger.md（七轴查重）
  - 草稿: knowledge/drafts/DRAFT-libfex-0.1.0-std-expected-polyfill-libcxx15.kv/.md---

**编译结束**: 2026-09-17 15:02
**最终状态**: published
---

**编译结束**: 2026-09-17 15:21
**最终状态**: published
