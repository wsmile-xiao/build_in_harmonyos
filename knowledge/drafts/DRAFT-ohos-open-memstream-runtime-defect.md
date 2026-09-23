# DRAFT: OHOS 运行期 open_memstream 缺陷 → 依赖 memstream 的上游测试输出为空/失败

- **草稿**: DRAFT-ohos-open-memstream-runtime-defect（.kv 配套）
- **来源**: tinycbor/0.6.0（task tinycbor-0.6.0-r03-pc5-3-20260906T073901Z）
- **日期**: 2026-09-06
- **前身草稿**: DRAFT-qt-test-framework-binary-missing-ohos（R02 曾断言"qt/5.15.19 未发布→0/54 硬阻塞"，
  经 R03 实测证伪，由本条目取代，避免保留未验证结论）

## 错误特征

```
open_memstream → fprintf → fclose 返回 -9 (EBADF)，buffer 为空
Signal 5 (SIGTRAP) / exit 133 / core dumped
Qt Test: decoded 恒为空 → QCOMPARE 全失败
cbortojson.c: fclose<0 || *key==NULL → CborErrorInternalError ("internal error")
```

## 根因

OHOS aarch64 运行期（SDK 26.0.0.18 musl 系 libc）的 `open_memstream()` 损坏：
流可打开、fprintf 正常，但 `fclose()` 返回 -9/EBADF，内存缓冲未刷新恒为空，进程可能
以 Signal 5 (SIGTRAP) 崩溃。任何用 open_memstream 做流式转换的上游测试辅助
（tinycbor tests/tojson 的 parseOne()、cbortojson.c 的 convert_json_value）都会得到
空 decoded 而全部失败——**库本身无缺陷**（parser/encoder 用同一 libtinycbor.a 100% 通过；
最小复现程序不链接任何 tinycbor 代码即复现）。

## 处置方案（正确归因 + 双口径台账）

1. 独立纯 libc 最小复现证明缺陷在运行环境而非库。
2. 双口径如实记录：configured_executable_total=54（qt/5.15.19 OHOS 二进制存在），
   executed=54，42/54 通过、12/54 失败（根因=open_memstream 运行期缺陷），
   恢复条件=OHOS SDK 修复 open_memstream 或以非 memstream 流式回调替代测试辅助。
3. 不得降级为"测试无法运行"(0/54)，也不得把环境缺陷记成库失败。
4. 制品可用性判定一律用 `conan install --build=never` + `conan graph info`
   （R35 口径），禁用 conan list / download --only-recipe 推断。

## 适用边界 / 反例

- 适用：上游测试/转换辅助用 open_memstream 流式输出的 C/C++ 库在 OHOS 上的适配；
  现象为"decoded 空 / Compared values not the same / internal error"而同库其他测试全过。
- 反例：同现象但 parser/encoder 也失败 → 属库缺陷，走编译/逻辑修复；
  Qt 测试框架二进制本身未发布 → 那是依赖发布门禁（但须先以 conan install --build=never 证实）。
- 同类既有归档: archives/l/libtinycbor/v7.0（同上游）以 BUILD_TESTING=OFF 整体关测，
  未暴露本缺陷；本条目提供保留测试并正确归因的路径。

## 验证

tinycbor 0.6.0 R03 实测：`conan install --requires=qt/5.15.19 --build=never` 成功
（package 01d92cf3…，46.7MB）；qmake→make 构建 3 个 Qt Test 目标并运行：
parser 2331 pass/0 fail、encoder 1467 pass/0 fail/6 skip、tojson 2 pass/699 fail；
纯 libc 最小复现 open_memstream fclose=-9 + SIGTRAP 证实环境缺陷。
全量台账: archives/t/tinycbor/0.6.0/reports/upstream-test-ledger.md（R03 修正版）。
