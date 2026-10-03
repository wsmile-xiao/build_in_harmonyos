# 上游测试数据仓"滚动 main"与发布 tarball 的版本错配：锁定发布日快照才算真验证

> Draft: DRAFT-14412（snowball）
> Stem: `DRAFT-14412-snowball-2.2.0-testdata-release-date-snapshot` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-14412
- **严重度**: 2
- **类别**: testing / test-data / version-skew / portability
- **触发工具**: make / conan
- **阶段**: testing

## 错误特征

```
Checking output of danish stemmer with UTF-8
--- /path/snowball-data/danish/output.txt
+++ tmp.txt
@@ -1524,7 +1524,7 @@
-bbc
+bbc's
 ...
@@ -3075,12 +3075,12 @@
-cd
+cd'en
make: *** [GNUmakefile:527: check_utf8_danish] Error 1
```

- 48 个数据驱动目标里 28 个失败，失败按**语言整组聚集**（同语言的 UTF-8/ISO-8859 变体一起挂）；
- 逐词 diff 形态与"算法移植 bug"完全同构，极易误导进入平台差异排查；
- 库本身编译全绿、自包含回归（check_stemtest）全过。

## 根因分析

snowball 上游 49 个测试目标中 48 个是数据驱动（check_utf8_×29 等），期望输出
存于独立仓 snowball-data（~500MB、**无任何 tag**）。main 分支随算法演进而
**重新生成全部期望文件**：danish 的撇号-s 规则（bbc's→bbc）是 v2.2.0 之后的
算法增强。对 v2.2.0 tarball 用 main HEAD 数据验证，等于拿新版答案对旧版算法
——系统性假失败，与平台无关。

诊断特征（区别于真移植 bug）：

1. 失败按**数据组/语言**整组聚集，而非按代码路径；
2. tarball 内算法源（algorithms/*.sbl）与数据期望语义对不上（v2.2.0 的
   danish.sbl 无撇号规则，main 数据期望却剥撇号）；
3. 库本体编译全绿、自包含回归全过、其他 11 语言全过。

## 解决方案（solution）

1. **锁定数据快照**：tarball 内 NEWS 取发布日（2021-11-10）→ GitHub HTML
   commits 页 `?until=` 过滤（API 限流时的可靠通道）→ 取"发布日前最后提交"
   `0703f1d6a21802c3ff00c2c8b31bd255b74b2aec`（"Update german2 test data"）；
2. **逐文件下载**（git clone/整包 tarball 在低速通道必断连 early EOF）：
   `raw.githubusercontent.com/<org>/<repo>/<SHA>/<lang>/<file>`，纯文本优先、
   仅 .gz 变体回退（Makefile 原生支持 gz 输入）；
3. **截断双校验**：voc 与 output **行数必须相等** + `gzip -t`——截断的期望
   文件产生"尾部整段缺失"型 diff 假失败（swedish 实锤：期望文件只下了
   14475/30623 行）；
4. **验证结果**：`STEMMING_DATA=<snapshot> make check` → 48/48 + stemtest
   全过，整体 exit 0。

## CI 形态与统计口径

- CI 内：自包含 `check_stemtest`（8 用例）进 conanfile.py build()，L1 可复现；
- 适配机：数据驱动 48 目标对快照实测全过，PR 统计表如实标注"数据仓不入库
  （~500MB）、CI 不复现、适配机实测"；
- test_package 消费者断言的词干期望值一律由"该快照实测输出"锚定，不手写。

## fallback

拿不到发布日快照时（数据仓不可达/无法定位历史提交）：退化为自包含目标
（check_stemtest 类）+ 消费者测试，统计表如实标注数据驱动目标未跑及原因
（环境限制：数据仓不可达）；禁用 main HEAD 数据冒充验证——假失败比不跑
更糟（会触发对正确代码的错误排查与无意义"平台差异"修复）。

## verify_builds

- 适配机实测：`STEMMING_DATA=<snowball-data@0703f1d6a218 快照> make check`
  exit 0（48 数据目标 + stemtest 全过）
- conan create（ohos-aarch64 profile）：build() 内 check_stemtest 通过 +
  test_package 41 checks 0 failures + CLI fixture 往返，一次通过
- CI 构建号：待 PR !14412 CI 绿后补录（前 5 轮 #68421/#68424/#68429/#68444/
  #68460 均为 Worker SSH bridge 基础设施毫秒级失败，非包问题）
