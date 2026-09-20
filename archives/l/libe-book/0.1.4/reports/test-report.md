# libe-book 0.1.4 — 测试报告（W3 本地验证 + 上游套件真跑）

日期：2026-09-20
环境：HarmonyOS PC aarch64（clang 15 / Conan 2.29.1 OHOS 适配版，设备本地 W3）
profile：ci/conan/profiles/ohos-aarch64（host/build 同 profile，OHOS armv8）
状态：**通过**（conan create RC=0；上游 `make check` 1/1 程序 PASS；
test_package 消费者测试 1/1，`all checks passed`；conan-verify verdict PASS）

## conan create 结果

```
$ conan create archives/l/libe-book/0.1.4 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable

G2: conan create (干净构建) … PASS
libe-book/0.1.4@ohpcd/stable: 配方 revision b79a75e4840e36153038ca2945b15b55
包ID: 0869638258f869bbad653f69444c4ceb541627b5（包 revision 1b73f69e12a79f9c4acf71cb5addebea）
```

- `.ci-result.json`：`exit_code: 0`，log_sha256 见该文件（finish 自动写入，非手改；每轮私有缓存重建后哈希更新，权威值以 HEAD 对应轮次的 .ci-result.json 为准）
- 完整日志：`reports/conan-create.log`、`reports/w3-local-ci.log`（本轮 finish 生成原件）

## 上游测试真跑（make check，R51）

上游测试体系：`src/test/` 一个 cppunit 程序 `test`，同时登记于
`check_PROGRAMS` 与 `TESTS`（`--enable-tests`，上游默认开启；本配方显式传入）。
automake testsuite 汇总（conan-create.log 原文）：

```
PASS: test
============================================================================
Testsuite summary for libe-book 0.1.4
============================================================================
# TOTAL: 1
# PASS:  1
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
```

- 计数单位：**上游测试程序**（automake `make check` 粒度）。程序 `test` 聚合
  4 个 cppunit 翻译单元：EBOOKBitStreamTest / EBOOKMemoryStreamTest /
  PDBLZ77StreamTest / SoftBookLZSSStreamTest（+test.cpp 运行器）。
- 排除项（如实申报）：EBOOKLanguageManagerTest 随 `--without-liblangtag`
  被上游自身条件编译排除；XMLCollectorTest / XMLTreeWalkerTest 属
  `--enable-experimental`（libcss/hubbub），上游默认关闭、本包未启用。

## test_package 消费者测试

```
test_libe_book（CMakeDeps 消费构建，conanrun 环境直跑）
all checks passed（10 项断言，RC=0）
```

10 项断言（含 2 项夹具写入检查）：PalmDoc 识别（EXCELLENT/WEAK 二选一 + 类型 TYPE_PALMDOC，2 项）、
parse 成功且 RVNGTextTextGenerator 产出原文（2 项）、纯文本拒识 CONFIDENCE_NONE
（1 项）、被拒流类型停留 TYPE_UNKNOWN（1 项）、不支持流 parse 非 OK（1 项）、
isSupported(nullptr) 契约（1 项）、夹具写入（2 项）。

## 计数汇总（与 PR 表格同口径）

| 口径 | 数量 | 证据 |
| --- | --- | --- |
| 上游单元测试（程序级） | 1，PASS 1/1 | make check testsuite 汇总（本文件上方原文） |
| test_package 消费者用例 | 1（10 断言），PASS 1/1 | conan-create.log `all checks passed` |
| 通过率 | 上游 1/1（100%）；新增 1/1（100%） | 同上 |

## 关联证据

- conan-verify：`reports/conan-verify-report.md`（verdict PASS；G0 知识命中
  E490 为建议项——本配方 `_restore_script_modes()` 已实现其修复方案）
- 结构完整性（W2/L0）：test_package/、conanfile.py、测试源、MANIFEST.yml 齐全
- 补丁：`patches_applied: []`（零补丁，源码未修改，R6 track-edit 无残留）
