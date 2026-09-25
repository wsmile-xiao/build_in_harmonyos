# cajun-jsonapi 2.1.1 适配笔记

## 编译环境
- 构建系统: makefile（上游仅 Makefile：example 与 Boost.Test 测试目标）
- 编译日期: 2026-09-22
- 编译器: clang/clang++ (OHOS SDK 26.0.0.18, llvm 15.0.4)
- 状态: built

## 编译步骤

cajun-jsonapi 是 header-only 库（include/cajun/json/*.h + *.inl），无编译产物；
Conan 配方按 `package_type = "header-library"` 打包头文件，`conan create` 即完整交付。

1. 上游测试（Boost.Test 38 用例）：
   `clang++ -o test_prog test/*.cpp -I include/cajun/ -I <boost-headers> -include <ohos_pthread_compat.h> -std=c++11`
   → `./test_prog` 38/38 PASS（exit 0）
2. 鸿蒙专项测试 + 消费者验证：test_package/test_ohos.cpp、test_package/test.cpp 编译运行全部 PASS
3. conan-verify：G1-G4 全 PASS；finish W2/W3 通过；PR 前置预检项补齐

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Boost.Test 框架头报 `pthread_setcancelstate undeclared` | OHOS sysroot pthread.h 不声明 GNU pthread 取消系列；libc.a 仅内部 `__pthread_setcancelstate`，libc.so dynsym 无公开符号 | 测试构建仅用 `-include` 注入 static inline compat shim（ohos_pthread_compat.h），不进入库交付物 |
| 2 | conan-verify G1 FAIL：缺 build()/export_sources()/补丁调用 | header-only 库配方完整性门禁同样要求标准骨架 | 补 export_conandata_patches/apply_conandata_patches（no-op） |
| 3 | W3 junk_check 命中其他库空基线文件（cloog/kics 的 .build-closed/.staging-verified） | 本分支无 commit 时 junk_check 回退全仓 git ls-files 扫描，把其他库已提交文件算作 junk | 基线隔离复验：pre SHA-256 → 临时移出+update-index --force-remove → 复跑 W3 通过 → 原样恢复+git add -f（与 HEAD 零差异）→ post SHA-256 == pre |
| 4 | W3 conan create sha256 失败（62b6824f ≠ 88f1eecf） | predl_cache 缓存了 404 HTML 与 9KB 截断包 | 删除坏缓存文件，预下载重新从官方源获取 |

## 源码修改

无补丁（header-only，未改上游源码）。

## 依赖版本

- Boost 1.84.0（仅测试构建使用头文件，非库依赖）
- Conan 2.29.1 / CMake 4.1.2

## 验证结果

- 上游测试：38/38 PASS (100.0%)，日志 reports/upstream-test-full.log
  （SHA-256: a9460ab4c751a284ee569fb0b104910aad6285fe07aff907239e6b4d4eb66dde）
- 鸿蒙专项：test_ohos ALL PASSED（UTF-8/双精度/异常路径/嵌套）
- 消费者：test_cajun_jsonapi ALL PASSED
- conan-verify：G1/G2/G3/G4 全 PASS；W3 本地 CI 通过（隔离复验后）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py / conandata.yml | header-only Conan 2.x 配方（官方源 + SHA-256 核验） |
| test_package/ | test.cpp（消费者）+ test_ohos.cpp（鸿蒙专项）+ conanfile.py + CMakeLists + MANIFEST.yml |
| reports/test-report.md | 双口径测试台账（38/38） |
| reports/knowledge-ledger.md | 知识候选台账 + 七轴查重 + 路径判定（reuse_existing / path_a_no_knowledge） |

## 注意事项

- OHOS libc 未导出公开 pthread_setcancelstate：仅测试框架需要，shim 只作用于测试编译，不入库。
- W3 全仓 junk 扫描会命中其他库已提交的空基线文件：处理按 SKILL 恢复规则 #3 基线隔离复验，不修改、不提交基线文件。
