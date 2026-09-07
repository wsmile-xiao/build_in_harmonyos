# sqlitecpp 3.3.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang/clang++（/data/service/hnp/bin，OHOS aarch64 工具链）
- 状态: built（conan-verify G0-G4 + L2/L4/L5 全通过）

## 编译步骤

1. 下载官方 tag 源码：`https://github.com/SRombauts/SQLiteCpp/archive/refs/tags/3.3.3.tar.gz`，SHA-256 实测与 conandata.yml 一致（33bd4372d83bc43117928ee842be64d05e7807f511b5195f85d30015cad9cac6）。
2. 本地探索构建（build-ohos，OHOS clang 工具链）：
   `cmake -B build-ohos -DSQLITECPP_INTERNAL_SQLITE=ON -DSQLITECPP_RUN_CPPLINT=OFF -DSQLITECPP_RUN_DOXYGEN=OFF` → make → libSQLiteCpp.a 构建成功。
3. 上游 googletest 单测实跑：`./bin/SQLiteCpp_tests` → 49/49 PASSED（10 个 suite）。
4. conan create（ohos-aarch64 profile）通过：G2 conan create 成功、G3 系统同名库隔离通过、G4 产物完整。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package 消费者链接失败：`undefined symbol: sqlite3_*` | SQLiteCpp 内部静态编译 libsqlite3.a，但 conanfile.py `package_info()` 只声明了 `cpp_info.libs = ["SQLiteCpp"]`，静态库依赖链未传递给消费者 | `package_info()` 改为 `cpp_info.libs = ["SQLiteCpp", "sqlite3"]`，按链接顺序声明两个静态库 |

## 源码修改

无（patches/ 为空，.edit-tracker 无修改记录，源码与官方 tarball 一致）。

## 依赖版本

- sqlite3：内嵌源码编译（SQLITECPP_INTERNAL_SQLITE=ON，上游默认），无外部依赖。

## 验证结果

```bash
# 上游单测（build-ohos 构建产物，OHOS 工具链编译）
./bin/SQLiteCpp_tests
# → [==========] 49 tests from 10 test suites ran. (95 ms total)
# → [  PASSED  ] 49 tests.
# 完整输出见 reports/sqlitecpp-r01-upstream-tests.log

# Conan 门禁
python3 scripts/ohc-run.py conan-verify sqlitecpp 3.3.3
# → G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS，报告见 reports/conan-verify-report.md
```

## 注意事项

- `package_info()` 必须同时声明 `SQLiteCpp` 与 `sqlite3` 两个静态库（链接顺序：SQLiteCpp 在前），否则下游消费者链接报 `undefined symbol: sqlite3_*`。
- 上游测试使用 googletest 子模块；conan 配方中 `SQLITECPP_BUILD_TESTS` 保持 OFF（测试在 W3 探索构建中已全量验证）。
---

**编译结束**: 2026-09-03 13:17
**最终状态**: built
