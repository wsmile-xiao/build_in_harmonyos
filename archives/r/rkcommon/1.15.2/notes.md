# rkcommon 1.15.2 适配笔记

## 编译环境
- 构建系统: cmake（单层，`cmake_minimum_required(3.10)`，不触发 CMake4 policy 问题）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，/data/service/hnp/bin，ohos-sdk 26）
- conan 2.29.1，profile `ci/conan/profiles/ohos-aarch64`（build==host 原生构建）
- 状态: built（conan-verify 全绿）

## 编译步骤

1. `conan create archives/r/rkcommon/1.15.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`（经 `ohc-run.py conan-verify`）
2. 关键配方变量：
   - `RKCOMMON_TASKING_SYSTEM=Internal`：tasking 走源内捆绑 enkiTS（3 个裸源文件直编），不引 TBB 外部依赖
   - `CMAKE_SYSTEM_NAME=OHOS` + `cmake_system_processor=aarch64`（经 toolchain block，保 SONAME 机制）
   - `BUILD_SHARED_LIBS=ON`、`BUILD_TESTING=ON`、`RKCOMMON_WARN_AS_ERRORS=OFF`、`CMAKE_INSTALL_LIBDIR=lib`
3. package() 内 ELF 自签（llvm-objcopy 去 `.codesign` + binary-sign-tool selfSign，跳软链）
4. 消费者测试 test_package：裸 clang++ 编译 `test.cpp` → `test_probe`，链接 package 内 `librkcommon.so`，原生运行断言

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 配方 `-DRKCOMMON_TASKING_TBB=OFF` 无效，configure 仍找 TBB 并在 `FindTBB.cmake` 报 `TBB_ROOT-NOTFOUND` | 上游用户开关是缓存变量 `RKCOMMON_TASKING_SYSTEM`（默认 TBB）；`RKCOMMON_TASKING_TBB` 是 `rkcommon_configure_tasking_system` 宏的输出变量，配方设置在 configure 阶段被覆盖 | 配方改设 `RKCOMMON_TASKING_SYSTEM=Internal`（Embree/OSPRay 系同款宏，同族库适用） |
| 2 | `rkcommon/memory/malloc.cpp` 编译失败：`xmmintrin.h:14:2: error: "This header is only meant to be used on x86 and x64 architecture"` | 平台守卫只枚举 _WIN32 / Apple-arm64 / x86-Unix 三分支，Linux/OHOS aarch64 落入 x86 `_mm_malloc` 分支 | 移植补丁 `patches/0001-aarch64-aligned-malloc-posix_memalign.patch`：三处把 Apple-arm64 条件放宽为通用 `__aarch64__\|\|__arm64__`，走 posix_memalign/free（musl 自带）。已沉淀 B 草稿 `DRAFT-rkcommon-1.15.2-aarch64-aligned-malloc-posix-memalign`（draft-review 判 create：与 jsonifier 指令集位草稿同签名、不同根因解法） |
| 3 | 首次构建 source() 下载超时（ghfast.top 连接超时） | 共享 dlcache 预置条目的 sidecar 未登记 E017 注入的 ghfast URL，conan 判缓存"未验证"强制重下 | sidecar 同时登记官方 URL 与 ghfast URL（AGENTS §12.39），缓存重种后命中 |

## 依赖版本

无外部第三方依赖（tasking=源内捆绑 enkiTS；Threads=pthread 系统提供）。

## 测试统计（五维账本）

- `N_static`：**137** 个 `TEST_CASE(`（bundled catch v2 单套件 `rkcommon_test_suite`，tests/ 目录）
- `N_registered`：**16** 个 CTest 注册项（`add_test(NAME <Tag> COMMAND rkcommon_test_suite "[Tag]")`，tests/CMakeLists.txt）
- `N_executed`：**16/16 全部通过**（`cmake.test()` 在配方 build() 内真实执行，`100% tests passed, 0 tests failed out of 16`，Total Test time 1.38s）
- 未执行分类：**0**（无条件跳过项）
- `N_consumer`：**1** 个消费者程序 `test_probe`，**10 项断言**全过（`rkcommon consumer test OK: vec/Optional/AlignedVector/OnScopeExit`）

说明：每个 CTest 注册项以 catch `[Tag]` 过滤器运行套件子集，137 个 TEST_CASE 全量被 16 个注册项覆盖执行；rule4 口径按注册入口 16 申报。

## 知识库使用记录

- G0 知识图谱预查询：命中 E540（zlib shadow-ci runner PATH），核对后与本任务无关（关键词误报），未采用其方案
- 配方路线参照已合入 hdf5/1.14.6 的 OHOS toolchain block（SONAME 机制）
- 路径 B：新增 `DRAFT-rkcommon-1.15.2-aarch64-aligned-malloc-posix-memalign.{kv,md}`（draft-review 结论：create，疑似新知无高相似，TOP1 相似度 0.08）

## 验证结果

- `ohc-run.py conan-verify rkcommon 1.15.2`：G0/G1/G2 全部 PASS（报告 reports/conan-verify-report.md）
- 上游测试：ctest 16/16 通过；消费者测试：10/10 断言通过
- E017 防回归：`git diff` 复核 conandata.yml URL 为官方形态 `https://github.com/ospray/rkcommon/archive/refs/tags/v1.15.2.tar.gz`（原 `RenderKit/rkcommon` 写法已更正——该组织不存在，上游为 **ospray/rkcommon**），sha256 `9128642e5187b963385dbf1655f3b143d3ef46310cc2e27114d220b347d0e2f2` 与两条官方 URL 实测下载一致（330695 字节）
- 本轮 conan-verify（2026-09-23 19:22，低内存慢速档 `memcap-run --slow --mb 3000`，峰值 526MB/97.3s）：**Verdict = PASS**，G0/G1/G2/G3/G4 全绿（报告 `reports/conan-verify-report.md`，Date 2026-09-23T19:22:03.795316）；E017 注入经 `finally` 正常回滚，conandata 零 ghfast 残留

---

**编译结束**: 2026-09-23 19:22
**最终状态**: built
