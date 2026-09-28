# geojson-vt-cpp 6.6.5 适配笔记

## 编译环境
- 构建系统: makefile（mason 依赖体系，header-only C++14 库，无编译产物）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（OHOS armv8, aarch64-linux-ohos）
- 状态: published

## 编译步骤
1. init-build: 官方 tag v6.6.5 tarball 经 gh-proxy 镜像下载，SHA-256 `4eb669e1...f7f662`（等价官方 archive URL）
2. lang-preflight: task=cpp / detected=cpp 匹配
3. 源码核验: 公共头文件 `include/mapbox/geojsonvt.hpp` + `geojsonvt/*.hpp`（7 个）对制品仓依赖组合（mapbox-variant/1.2.0 + mapbox-geometry/2.0.3）编译冒烟通过（ELF64 AArch64）
4. 上游测试: 按上游锁定版本组合（variant 1.1.5 + geometry 1.0.0 + geojson-cpp 0.4.3 + gtest 1.17.0 + rapidjson 1.1.0）编译 test/test.cpp + util.cpp，23/23 PASS
5. HarmonyOS 专项测试 test_ohos/test_ohos.cpp（H1/H1b/H2 全过，ELF64 AArch64）
6. 消费者用例 test_package/test_consumer.cpp（仅用公共 API，C1-C3 全过）
7. conan create + conan-verify: G1-G4/L2/L4/L5 全绿
8. finish: W3 本地 CI L0=pass（prdiff 单包口径），W2 原子性通过，状态 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试用制品仓 variant 1.2.0 编译报 `to_value` 不匹配 | variant 1.2.0 visit/dispatcher 模板解析变化 × geojson-cpp 0.4.3 旧访问器 API 差异 | 上游测试按上游锁定版本组合编译；配方用发布版本 + 消费者冒烟（草稿见 knowledge/drafts/） |
| 2 | conan create 报 `Package type is 'library', but no 'shared' option declared` | header-only 需 header-library 类型 | package_type="header-library"（E321/E322/E470/E283 复用） |
| 3 | package() 后包内无 include（Imported target non-existent path） | copy() dst 相对路径解析到 build 目录 | copy() 用绝对路径 `os.path.join(package_folder, "include")`（DRAFT-boost-te 复用） |
| 4 | W3 junk_check JC1/JC5 全仓命中 cloog/kics 等 main 基线历史文件 | 新库分支零提交时 junk_check 回退 full 模式 | JUNK_PR_DIFF=pr.diff 单包口径（DRAFT-boost-te 复用） |
| 5 | finish W3 拦截 conandata.yml.ghfast-bak | E017 镜像注入残留备份 | 提交前清理 bak，核验 conandata 官方 URL（DRAFT-E323 复用） |

## 依赖版本

- 配方 requires: mapbox-geometry/2.0.3 + mapbox-variant/1.2.0（制品仓已发布）
- 上游测试锁定组合: variant 1.1.5 + geometry 1.0.0 + geojson-cpp 0.4.3 + gtest 1.17.0 + rapidjson 1.1.0

## 验证结果

```bash
# 上游测试
cd /storage/Users/currentUser/tmp/builds/geojson-vt-cpp-6.6.5.work && ./gvt-test
# [==========] 23 tests from 7 test suites ran. [  PASSED  ] 23 tests.

# HarmonyOS 专项测试
./gvt-ohos-test  # H1/H1b/H2 ALL PASS, ELF64 AArch64

# 消费者验证
./gvt-consumer   # C1/C2/C3 ALL PASS
```

## 交付物

- 配方: conanfile.py + conandata.yml + test_package/（header-only，版本 6.6.5）
- 报告: reports/upstream-test-ledger.md、test-report.md、knowledge-candidate-ledger.md
- 草稿: knowledge/drafts/DRAFT-geojson-vt-cpp-6.6.5-mapbox-dep-family-version-lock-api-drift.{kv,md}

## 注意事项

- 上游无官方 CMake；库本质为 header-only，测试/基准经 Makefile + mason 提供
- 未发布依赖: mapbox-geojson（geojson-cpp 0.4.3）仅在测试源码 include，不属于库公共 API 依赖，测试经官方镜像源码获取