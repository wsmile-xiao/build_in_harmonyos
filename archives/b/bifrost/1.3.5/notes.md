# bifrost 1.3.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-24
- 编译器: clang 15 / clang++ (aarch64-linux-ohos, libc++)
- 状态: built

## 编译步骤

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

- CMake 配置关键变量：`BUILD_SHARED_LIBS=OFF`（默认）、`COMPILATION_ARCH=OFF`、
  `ENABLE_AVX2=OFF`（OHOS arm64）、`CMAKE_POLICY_VERSION_MINIMUM=3.5`
- 依赖：zlib/1.3.1（conan registry，R36 已发布）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载得到 HTML | 裸仓库页 URL 非 tarball | 使用官方 tag 直链 `archive/refs/tags/v1.3.5.tar.gz`（SHA-256 e1b249...f5341） |
| 2 | CMake 4.x 报 `Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(2.8.12)`，CMake 4.1.2 已移除 <3.5 策略兼容 | 补丁 0001 提升为 `cmake_minimum_required(VERSION 3.5)` |
| 3 | `std::random_shuffle` 编译失败 | C++17 已移除该 API，上游 TinyBitmap.cpp 使用 | 补丁 0003 替换为 `std::shuffle` + `std::default_random_engine{}` |
| 4 | `libbifrost.so` 链接失败：`z_errmsg` relocation 需 -fPIC | 上游无条件构建 shared 库并链 static libz.a（非 PIC，aarch64） | 补丁 0002：`bifrost_dynamic` 仅在 `BUILD_SHARED_LIBS=ON` 时构建；默认链 `bifrost_static` |

## 源码修改

- `patches/0001-CMakeLists.txt.patch` — cmake_minimum_required 2.8.12 → 3.5
- `patches/0002-src-CMakeLists.txt.patch` — bifrost_dynamic 条件构建；Bifrost 默认静态链接
- `patches/0003-src-TinyBitmap.cpp.patch` — std::random_shuffle → std::shuffle（+ <random>）

## 依赖版本

- zlib/1.3.1（conan registry ohpcd）

## 验证结果

- conan create 通过（G0-G4 全过，test_package 消费者测试 ctest 1/1 Passed）
- 鸿蒙专项端到端测试：`Bifrost build -k 15`（exit 0，产物 graph_out.gfa.gz + .bfi）→
  `Bifrost query`（exit 0，18 个 k-mer 全部命中）→ `Bifrost --version`（1.3.5）
- 上游测试：官方 tag 无独立测试用例（0/0），详见 reports/test-enumeration-ledger.md

## 知识候选与路径决定

- 候选 1（CMake 4.x 拒绝 cmake_minimum_required<3.5）→ reuse_existing（E103 完整覆盖；E187/
  DRAFT-E321 部分重叠，本人实测 tc.variables 写入 toolchain 在 min 版本检查前不生效，与 DRAFT-E321 观察一致）
- 候选 2（C++17 移除 std::random_shuffle）→ reuse_existing（DRAFT-pktanon-random-shuffle-cxx17
  覆盖根因与方案；RNG 类型差异为等价实现选择）
- 候选 3（aarch64 非 PIC 静态 libz.a 链入无条件共享库失败）→ **new_draft（路径 B）**：
  `knowledge/drafts/DRAFT-bifrost-1.3.5-gate-shared-lib-nonpic-static-dep.kv/.md`
  （消费侧 `if(BUILD_SHARED_LIBS)` 门控共享库；combination_novelty/boundary_novelty，与
  E005/E539/E541 的依赖侧方案互补，本轮真实日志已验证）
- 候选 4（OHOS arm64 关闭 x86-64 取向 CMake 选项）、候选 5（init-build 用 tag 直链）→
  path_a_no_knowledge（无真实错误支撑/工具使用规范，不建草稿）
- 完整台账见 reports/knowledge-candidate-ledger.md（七轴查重、覆盖/新增差异、关系字段）
---

**编译结束**: 2026-09-24 09:34
**最终状态**: built
