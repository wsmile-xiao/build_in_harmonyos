# gb 0.8.7 适配笔记

## 编译环境
- 构建系统: headeronly（无构建系统，纯头文件库，CONAN headeronly 模板）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，OHOS aarch64）
- 状态: published

## 编译步骤

gb 为 gingerBill 的 stb 风格 single-file C 库（5 个头文件），无编译产物，
按 headeronly 配方打包：

```bash
python3 scripts/ohc-run.py init-build gb 0.8.7 --url=https://codeload.github.com/gingerBill/gb/tar.gz/refs/heads/master
python3 scripts/ohc-run.py conan-init gb 0.8.7
python3 scripts/ohc-run.py conan-verify gb 0.8.7
python3 scripts/ohc-run.py finish gb 0.8.7 published
```

conan create 使用 ohos-aarch64 profile（clang 15 / OHOS 6.0 / armv8），
test_package 消费者测试通过公开头文件 gb.h（消费者单 TU 定义
GB_IMPLEMENTATION 实例化实现）实际编译链接运行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | gb.h:250 Unknown CPU Type | 上游 CPU 检测块无 aarch64 分支 | patch 0001：ARM 分支加 `__aarch64__` |
| 2 | gb.h:4419 TODO Implement Atomics | 实现段原子操作仅 x86/PPC | patch 0002：用 `__atomic_*` 内建实现 32/64 原子 |
| 3 | gb.h:4547/4559/4571/4583 Unknown architecture | fence/yield 无 ARM 分支 | patch 0002：`__sync_synchronize()`/`dmb ishst`/`dmb ishld` |
| 4 | gb.h:4760 Unsupported thread_current_id | 线程 ID 仅 x86/OSX | patch 0002：`(u32)(uintptr_t)pthread_self()` |
| 5 | ld: undefined symbol gb_rdtsc | rdtsc 仅 x86/PPC 分支 | patch 0003：`mrs %0, cntvct_el0` |
| 6 | GB_ARCH_64_BIT 误判 32 位 | 位宽检测无 `__aarch64__` | patch 0002：补 `__aarch64__`/`__arm64__` |
| 7 | 消费者链接 undefined gb_strlen 等 | stb 风格需 GB_IMPLEMENTATION 实例化 | test.c `#define GB_IMPLEMENTATION` 后 include |
| 8 | lang-preflight 误判 other/none | 纯头文件库无 .c/.cpp 源文件 | 按证据继续 header-only 适配（不属语言不匹配） |

## 源码修改

- patches/0001-aarch64-cpu-detection.patch：CPU 检测 ARM 分支加 `__aarch64__`
- patches/0002-aarch64-implementation.patch：GB_ARCH_64_BIT 位宽检测 +
  __atomic 原子实现 + dmb fence + pthread_self 线程 ID
- patches/0003-aarch64-rdtsc.patch：gb_rdtsc 用 ARM cntvct_el0 通用计数器

## 依赖版本

无第三方 Conan 依赖（单头文件库，仅依赖 C 标准库）。

## 验证结果

- conan-verify：G1 配方完整性 / G0 预检 / G2 conan create / G3 隔离 /
  G4 产物 / L2 / L4 / L5 全 PASS
- OHOS 专项测试（reports/ohos-test/ohos_test.c）：6 组断言 ALL PASS
- test_package 消费者测试：4 组公开 API 断言 PASS
  （HMBS_TEST_PACKAGE_RESULT executed/passed=true, passedCount=4）
- 上游测试：无套件（0 声明），台账见 reports/upstream-tests-ledger.md

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=header-library，cmake_layout） |
| conandata.yml | 官方源码 URL + SHA-256 + 3 个补丁 |
| test_package/ | 消费者测试（CMake + test.c + conanfile.py + MANIFEST.yml） |
| patches/0001-0003 | aarch64 portability 补丁 |
| reports/ | 台账/证据/隔离审计 5 份 |

## 注意事项

- gb 为 single-file 头文件库：消费者须在单个编译单元 `#define GB_IMPLEMENTATION`
  后 include 才能获得实现（stb 风格官方用法）
- 知识草稿：knowledge/drafts/DRAFT-gb-0.8.7-single-file-header-aarch64-support.{kv,md}
  路径 B（知识库扩展），new_draft