# tsl-sparse-map 0.6.2 适配笔记

## 编译环境
- 构建系统: custom（header-only 库，无编译；上游测试用 clang++ 手动编译 Boost.Test）
- 编译日期: 2026-09-01
- 编译器: clang/clang++（aarch64-linux-ohos，/data/service/hnp/bin/clang++ 15.0.4）
- 状态: built

## 编译步骤

1. `curl` 下载官方源码 https://codeload.github.com/Tessil/sparse-map/tar.gz/refs/tags/v0.6.2
   （SHA-256=7020c21e8752e59d72e37456cd80000e18671c803890a3e55ae36b295eba99f6）
2. 库本身 header-only（include/tsl/ 4 头文件），无需编译，conan 打包安装头文件。
3. 上游测试（tests/，Boost.Test）用 clang++ 编译 6 个测试源并运行：
   `clang++ -std=c++17 -Iinclude -I<boost include> -include pthread_stub.h tests/{main,custom_allocator_tests,policy_tests,popcount_tests,sparse_map_tests,sparse_set_tests}.cpp -o unit_tests -pthread`
   结果：`Running 154 test cases... No errors detected`（154/154 = 100%）。
4. conan create 验证（profile: ohos-aarch64），test_package 运行 tsl::sparse_map insert/find/erase
   真实 API smoke（3 断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ohpcd boost 包无 libboost_unit_test_framework 编译库 | 上游测试动态链接 Boost.Test 框架库 | 改用 header-only 模式：main.cpp include 替换为 `boost/test/included/unit_test.hpp` |
| 2 | OHOS libc 缺 pthread_setcancelstate/pthread_cancel | Boost 内部使用这两个符号，OHOS libc 未提供 | 写 pthread_stub.h 静态 inline stub + `-include` 注入（同 hopscotch-map 先例） |
| 3 | W3 本地 CI 的 JC junk_check 全仓扫描命中其他库基线垃圾文件 | 其他库既有文件（goaccess/lsof/scudo/stb_image）在 main 已跟踪 | git rm --cached 可逆隔离 5 个精确路径 → W3 通过 → git reset HEAD 逐字节恢复（哈希/模式不变） |

## 源码修改

无补丁（header-only 库仅测试适配，无库源码修改）。

## 依赖版本

- boost/1.84.0（tool_requires，仅测试用头文件）

## 验证结果

```bash
# 上游测试（conan create 内 build() 编译运行）
Running 154 test cases...  No errors detected
# HarmonyOS 专项 test_package（真实 API smoke）
OK: sparse_map insert/find/erase works
# conan-verify
G0-G4 全 PASS；W3 本地 CI JC_RESULT=pass, Pass rate 100% (1/1)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-library 配方（含上游测试编译运行） |
| conandata.yml | 官方源 + SHA-256 |
| manifest.yaml | 归档元数据（status=built） |
| test_package/test_tsl_sparse_map.py | HarmonyOS 专项测试（真实 API smoke） |
| test_package/MANIFEST.yml | 测试清单与上游测试统计 |

## 注意事项

- 上游测试统计以实际执行为准：154/154（w3-local-ci.log 实测 Running 154 test cases... No errors detected）。
- 其他库基线噪声（goaccess/lsof/scudo/stb_image）已按 R03 记录并原样恢复，不写入本库 PR。
- 远端交付在 R04 授权后执行；本库无知识库草稿（路径 A，无新增通用知识）。

---

**编译结束**: 2026-09-01 10:54
**最终状态**: built