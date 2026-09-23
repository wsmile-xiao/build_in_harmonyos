# reflect-cpp 0.17.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos, OHOS SDK 26.0.0.18)
- 状态: published
- 平台: OpenHarmony/HarmonyOS PC aarch64 实机（host == target 架构）
- CMake 4.1.2 + Ninja，Conan 2.29.1（OHOS 适配版），profile: ci/conan/profiles/ohos-aarch64

## 编译步骤

1. `ohc-run.py init-build reflect-cpp 0.17.0 --url=...v0.17.0.tar.gz`（GitHub SSL 证书
   问题由执行端 curl 预下载 + 手工解压 .orig 后 `--no-download` 完成双轨）
2. 原生构建库本体：`cmake -S .work -B .build-native -G Ninja -DREFLECTCPP_BUILD_SHARED=OFF`
   → `cmake --build` → 5/5 目标一次通过（libreflectcpp.a）
3. 上游测试套件：`-DREFLECTCPP_BUILD_TESTS=ON -DGTEST_ROOT=<ohpcd gtest/1.17.0>`
   → 97/97 构建 → `ctest -j20` 193/193 全过（generic 35 + json 142 +
   json_c_arrays_and_inheritance 7 个测试源文件）
4. Conan 配方：`conanfile.py`（name=reflect-cpp，R32/R33 合规，捆绑依赖零外部
   requires）+ `conandata.yml`（sha256 + 10 个补丁）+ test_package（L1 13 断言 +
   鸿蒙专项 15 断言）
5. `ohc-run.py conan-verify` G0-G4 全 PASS；`ohc-run.py finish published`
   档案收尾 + W3 本地 CI（.ci-result.json exit_code=0, log_sha256 记录）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 10 个上游测试文件编译失败 `fatal error: 'source_location' file not found` | OHOS SDK 26 的 libc++ 未提供 `<source_location>` 头（C++20 特性，libc++ 16+ 才引入）；库本体 3 个 header 有 `__has_include` 守卫所以能编译，测试文件无条件 include 且实际从不用 `std::source_location`（grep 0 使用） | 移除 10 处未使用 include（补丁 0001-0010，零行为变更） |
| 2 | conan create 失败 `ConanInvalidConfiguration: reflect-cpp/0.17.0: Invalid 'compiler.cppstd' value` | 共享 ohos-aarch64 profile 声明 `cppstd=17`，而库是 C++20-only，配方 `check_min_cppstd(self, 20)` 直接拒绝 | 配方不再按 profile cppstd 拒绝（C++20 由项目自身 `CMAKE_CXX_STANDARD 20` 强制），并在 `generate()` 显式注入 `CMAKE_CXX_STANDARD=20`；test_package 同样显式锁定 C++20 |
| 3 | test_package 编译失败 `no template named 'remove_cvref_t'` 等 | test_package 使用自己的 CMakeToolchain，继承 profile 的 cppstd=17 | test_package/CMakeLists.txt 顶部 `set(CMAKE_CXX_STANDARD 20)` + `CMAKE_CXX_STANDARD_REQUIRED ON` |
| 4 | G0 clean-verify 报 `configure: command not found` (exit 127) | 非阻塞步骤：G0 clean_verify 按 autotools 约定执行 `./configure`，本项目为 CMake 无 configure 脚本 | 按 SKILL 流程 G0 为非阻塞警告（conan-verify 的 G2 干净构建已独立覆盖），不阻断 finish；记录于此 |

## 源码修改

- 0001-0010：`tests/{cbor,json,msgpack,ubjson}/test_*.cpp` 各删除一行未使用的
  `#include <source_location>`（共 10 文件 × -1 行，零新增，零行为变更）。
  补丁分类标注：type=portability, platform_only=true, guard=pending（OHOS SDK 26
  libc++ 缺 `<source_location>` 头；上游若升级到 libc++ 16+ 环境该 include 可保留）。

## 依赖版本

- 无外部 Conan 依赖：JSON 后端使用源码树捆绑的 ctre 3.9.0 + yyjson 0.10.0
  （`REFLECTCPP_USE_BUNDLED_DEPENDENCIES=ON`，上游默认）→ R36/PF4 门禁天然满足。
- 测试期（不入包）：gtest/1.17.0（ohpcd registry 二进制，本机运行用）。
- 工具链：clang 15.0.4 / CMake 4.1.2 / Ninja / Conan 2.29.1。

## 验证结果

```bash
# Conan 门禁
$ python3 scripts/ohc-run.py conan-verify reflect-cpp 0.17.0
G0 PASS / G1 PASS / G2 conan create PASS / G3 PASS / G4 PASS / L2 PASS / L4 PASS / L5 PASS
exit 0（日志 archives/r/reflect-cpp/0.17.0/reports/conan-create.log）

# W3 本地 CI（finish 步骤 5/10）
.ci-result.json: exit_code=0, log_sha256=a8aa4a5e5bdb0446bc20da989ea72fcee45c84a119c935527c4968c1986f8e9a
（reports/w3-local-ci.log）

# 上游 gtest 套件（本机 OHOS aarch64 实机执行）
$ ctest -j 20 --output-on-failure
193/193 passed, 0 failed（Total Test time 0.98s）

# test_package（conan create 内执行）
test_reflect_cpp: ALL OK（13 断言）
harmonyos_specific_test: 15 checks ALL OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py / conandata.yml | Conan 2.x 配方（CMake，static 默认，捆绑依赖） |
| patches/0001-0010 | 10 个 OHOS 平台可移植性补丁（移除未使用 include） |
| test_package/ | L1 消费方验证 + 鸿蒙专项测试（15 断言）+ MANIFEST.yml |
| reports/ | conan-create.log / w3-local-ci.log / conan-verify-report.md / test-report.md |

## 注意事项

- 库本体在 OHOS 上编译零修改（`__has_include` 守卫已覆盖 `<source_location>`）。
- C++20 是硬要求：profile cppstd=17 不满足但项目自身强制标准，配方不拒绝 profile。
- 其余 JSON 后端（avro/bson/capnproto/cbor/flexbuffers/msgpack/toml/ubjson/xml/yaml）
  在默认构建中关闭，依赖各自的第三方库，不在本包公开面内。

## 发现与知识

- ✅ OHOS SDK 26 libc++ 缺 `<source_location>` 头（C++20 特性），无条件 include 的上游
  测试/代码需移除或 `__has_include` 守卫；已沉淀路径 B 草稿
  `knowledge/drafts/DRAFT-reflect-cpp-0.17.0-ohos-sdk26-libcxx-missing-source-location.md/.kv`
  （知识 ref: DRAFT-reflect-cpp-0.17.0-ohos-sdk26-libcxx-missing-source-location）
- ✅ C++20-only 库与共享 profile `cppstd=17` 冲突：conan `check_min_cppstd` 硬拒绝导致
  conan create 失败；正确做法是配方不拒绝 profile cppstd、由项目/配方显式
  `CMAKE_CXX_STANDARD=20` 强制；已沉淀路径 B 草稿
  `knowledge/drafts/DRAFT-reflect-cpp-0.17.0-cpp20-only-recipe-vs-shared-profile-cppstd17.md/.kv`
  （知识 ref: DRAFT-reflect-cpp-0.17.0-cpp20-only-recipe-vs-shared-profile-cppstd17）

---

**编译结束**: 2026-09-03 07:36
**最终状态**: published
