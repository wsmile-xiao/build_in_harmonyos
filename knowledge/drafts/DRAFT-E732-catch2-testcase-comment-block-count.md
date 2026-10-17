# DRAFT-E732 — Catch2 TEST_CASE 注释块计数陷阱（rule4 少报误判）

- **任务**: libnpy 1.0.1（2026-09-25）
- **号段**: DRAFT-E732（`knowledge_id.py --claim` 三面扫描取号）
- **状态**: DRAFT — 待维护方审入 graph

## 现象

libnpy `tests/test-read.cpp` 清点用例数，两个口径对不上：

| 口径 | 数值 | 取数 |
|------|------|------|
| 源码宏 `grep -c TEST_CASE` | **16** | `tests/test-read.cpp` |
| 框架注册 `--list-test-names-only \| wc -l` | **15** | Catch2 实际注册 |
| 源码断言 `grep -c REQUIRE` | **93** | 同文件 |
| 实跑断言（Catch2 汇总） | **87** | `All tests passed (87 assertions in 15 test cases)` |

若按注册数声明 N=15，审方独立克隆 grep 得 16 → 「实测 N > 声明 N」= **rule4 少报
直接不通过**（外部审查第二大失败项，2026-09-11 审计 5/20）。

## 根因

`test-read.cpp:194-210` 有上游块注释：

```cpp
/*
 * bool not supported
TEST_CASE( "Load bool data", "[read]" ) { ... 6 条 REQUIRE ... }
*/
```

grep 按行匹配不解析块注释 → 16 = 15（注册）+ 1（注释块）；93 = 87（实跑）+ 6（注释块）。
差额**全部**归因于这一处，可逐行验证。

## 处置口径（N 候选数法）

1. **声明 N = 源码宏最大候选 = 16**，N′ = 实跑 15；
2. 四分项恒等：`TOTAL = PASS 15 + FAIL 0 + SKIP 0 + NOT_RUN 1 = 16`；
   NOT_RUN 1 = 块注释内 `Load bool data`（上游自注释 "bool not supported"，不可编译）；
3. **断言口径另列不混用**：源码 93 / 实跑 87（注释块 6 条归因）；
4. meson/ctest 层注册数（本例 2：test read + test write）单独披露——`test write`
   是 0 断言冒烟，在任何"用例"口径下都计 0，不并入 N；
5. notes.md 申报表 + PR 正文 + 审计主张三处同源。

## 复现命令（设备可直接执行）

```bash
SRC="$HOME/ws/tmp/builds/libnpy-1.0.1.work/tests"
echo "src_macros=$(grep -c TEST_CASE "$SRC/test-read.cpp")"
grep -n "bool not supported" "$SRC/test-read.cpp"     # 命中 = 注释块证据
echo "registered=$("$SRC/builddir/test-read" --list-test-names-only | wc -l)"
"$SRC/builddir/test-read" 2>&1 | grep "assertions in"  # 87 assertions in 15 test cases
```

日志证据：`$HOME/tmp/libnpy-1.0.1/native-test.log`（meson 汇总 `Ok: 2 / Fail: 0`）。
