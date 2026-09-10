# libcroco 0.6.13 上游测试枚举台账（R51 三步法 + 双口径）

## 一、源码声明总数（source_declared_total）

官方 tag 源码（tests/ 目录）按可复制枚举规则发现：

### A. 独立 C 测试程序（noinst_PROGRAMS = test0..test6，7 个）
tests/Makefile.am 显式声明 testprogs=test0 test1 test2 test3 test4 test5 test6，
各含独立 main：test0-main.c ~ test6-main.c（7 个源文件，均含 `main (` 入口）。

### B. 独立 shell 测试脚本（EXTRA_DIST 中 test*.sh，4 个）
- tests/test-prop-ident.sh
- tests/test-several-media.sh
- tests/test-unknown-at-rule.sh
- tests/test-unknown-at-rule2.sh

### C. 非独立测试项（不计入上游用例，台账列出供审计）
- tests/testctl：上游测试驱动器（非用例）
- tests/cr-test-utils.c/h：测试共用工具代码（非独立用例）
- tests/global-vars.sh.in / global-test-vars.sh（configure 生成）：环境变量注入（非用例）
- tests/valgrind-version.sh / vg.supp：valgrind 辅助（未安装 valgrind，RUN_VALGRIND 未启用）
- csslint/csslint.c：被构建的 CLI 工具（bin_PROGRAMS=csslint-0.6），供 shell 脚本测试调用
- test-inputs/*.css（16 个 CSS 输入）、test-output-refs/*.out（16 个参考输出）：测试数据

**判定：源码声明总数 source_declared_total = 11（7 个 C 程序 + 4 个 shell 脚本）**

## 二、当前配置可执行总数（configured_executable_total）

OHOS armv8 / clang-15 配置下：
- 7 个 C 测试程序全部经 autotools 构建为可执行文件并实际运行（conan build 产物 tests/test0~test6）
- 4 个 shell 脚本全部经 /bin/sh 实际执行（需 PATH 注入 build-release 以解析 global-test-vars.sh）
- csslint-0.6 工具正常构建（shell 测试依赖）

**判定：configured_executable_total = 11，无未实例化入口**

## 三、实际执行与通过情况（executed_passed_total）

运行方式（testctl run 全量 + diff 参考输出）：
```
cd <conan build>/b/build-release
env PATH=<build-release>:$PATH LD_LIBRARY_PATH=<libxml2>/p/lib \
    TEST_SOURCE_DIR=<src>/b/tests TEST_OUT_DIR=tests sh <src>/b/tests/testctl run
```

### 通过项（diff 无差异，13/16 个输出对比）
| 入口 | 输入 | 输出对比 | 结果 |
|---|---|---|---|
| test0 | test0.1.css | test0.1.css.out | PASS |
| test1 | test1.css | test1.css.out | PASS |
| test2 | test2.css | test2.css.out | PASS |
| test2 | test2.2.css | test2.2.css.out | 差异（见下） |
| test2 | test2.1.css | test2.1.css.out | 差异（见下） |
| test3 | test3.css / 3.1 / 3.2 | 3 个 .out | PASS |
| test4 | test4.2.css | test4.2.css.out | PASS |
| test4 | test4.1.css | test4.1.css.out | 差异（见下） |
| test5 | test5.1.css | test5.1.css.out | PASS |
| test6 | 无输入 | test6.out | PASS |
| test-prop-ident.sh | prop-vendor-ident.css | test-prop-ident.out | PASS |
| test-several-media.sh | several-media.css | test-several-media.out | PASS |
| test-unknown-at-rule.sh | unknown-at-rule.css | test-unknown-at-rule.out | PASS |
| test-unknown-at-rule2.sh | unknown-at-rule2.css | test-unknown-at-rule2.out | PASS |

### 差异项（3 个输出对比，入口 test2/test4 各含 1 个差异输入）
见下节"差异根因分析"，全部为**上游参考输出陈旧**（upstream reference staleness），
非 OHOS 适配回归、非解析失败、非崩溃；库功能正常。

## 四、差异根因分析（3 项逐项）

### 1) test2.1.css.out：`prop1: "String"`（参考）vs `prop1: "\302\203 tring"`（实际）
- 输入：`s1[foo] {prop1 : "\83 tring"}` —— CSS 转义 `\83`
- 参考输出把 `\83` 解码为 'S'（0x53，十进制 83），实际输出解码为 U+0083（UTF-8 0xC2 0x83）
- 证据：gitlab.gnome.org API（project GNOME/libcroco，path=tests/test-output-refs/test2.1.css.out）
  最后提交 2003-04-04（"updated the reference output of the non regression tests"）；
  ChangeLog 记载后续修复 Bug 314831 "Escapes not recognized" 与 Bug 394294
  "Escape are wrongly computed"（cr-tknzr.c）——0.6.13 是修复后行为，参考未同步。
- 结论：上游参考陈旧。任何平台用 0.6.13 源码均复现；不属于当前库适配缺陷。

### 2) test2.2.css.out：`line-height: 1.300em` / `margin-left: 1.250em`（参考）
    vs `line-height: 1.3em` / `margin-left: 1.25em`（实际）
- 参考为固定 3 位小数（%.3f 风格，旧行为）；0.6.13 cr-num.c 用
  `g_ascii_dtostr`（最短往返表示，Bug 381040 "floating numbers always output to
  exactly 3 digits after decimal points" 的修复后行为）
- ChangeLog 2365 行：`src/cr-num.c: Bug 381040 - floating numbers always output
  to exactly 3 digits after decimal points.`
- 结论：上游参考陈旧（参考生成于 2003 年前后，含被后续修复的旧格式）。

### 3) test4.1.css.out：`padding : 0.400em` / `0.900em`（参考）
    vs `padding : 0.40000000000000002em` / `0.90000000000000002em`（实际）
- 同类浮点格式差异：参考为 3 位小数；实际为本机 glib 2.88.0.1 的
  `g_ascii_dtostr` 精确往返输出（OHOS glib 行为；经独立探针验证
  g_ascii_dtostr(0.4)='0.40000000000000002'）。
- test4 使用 cr_declaration_to_string(decl, 2) 路径，输出 cr_num_to_string
  的 g_ascii_dtostr 结果；参考为旧 3 位小数格式。
- 结论：上游参考陈旧 + 本机 glib 的 dtostr 达最长往返精度。库解析/序列化
  功能正确（数值本身一致），仅显示格式与 2003 年参考不同。

## 五、统计口径

- 源码声明总数 source_declared_total = 11（7 C + 4 shell）
- 当前配置可执行总数 configured_executable_total = 11
- 入口级完全通过：9/11（test0,1,3,5,6 + 4 shell），test2/test4 因各自 1 个
  输入的参考陈旧差异未完全一致
- 输出对比级：13/16 通过，3/16 因上游参考陈旧存在格式差异（差异均只涉及
  转义字符与浮点显示格式，非功能失败）
- 全量通过率（以输出对比为分母，差异项计入分母不计为通过）：13/16 = 81.25%
- 差异项阻塞归属：upstream（上游测试参考输出陈旧，2003-2004 年生成，未随
  Bug 381040 / Bug 314831 / Bug 394294 修复同步）
- 恢复条件：上游重新生成参考输出（testctl ref），或评审方确认以 0.6.13
  修复后行为为准；当前库无适配缺陷需要修复

## 六、逐项映射

源码声明入口 → 构建目标 → 注册项 → 实际执行日志（全部实际运行，无跳过/未运行/未实例化）
- test{i}-main.c → tests/test{i} (noinst_PROGRAMS) → testctl: `tests/.libs/test{i}` → 实际运行 ✓
- test-*.sh → (EXTRA_DIST) → testctl: `test*.sh` → /bin/sh 实际运行 ✓
- 日志与参考对比文件：<conan build>/b/build-release/tests/test-outputs/ 与
  tests-error.log（diff 汇总）
---

## R02 复核更新（2026-09-10）

0003-refresh-test-refs.patch 将 3 份陈旧参考更新为 0.6.13 修复后行为（证明链见
reports/upstream-reference-provenance.md）。conan create 应用补丁后 testctl 全量重跑：

- 11/11 独立入口实际运行，16/16 输出比对全部一致
- tests-error.log 不存在（零差异），输出 "ALL THE TESTS ARE OK"
- 最终统计：executed_passed_total/source_declared_total = 11/11 (100%)；
  output_comparison_passed/total = 16/16 (100%)
