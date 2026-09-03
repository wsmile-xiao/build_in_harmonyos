# E429 — 子串匹配的单元测试过滤器会让逐用例断言数重复计数

## 错误特征

上游用「字符串子串匹配」选择测试用例的 C 单元测试框架（Cesanta 系 `unit_test`
即 `RUN_TEST(x)` + `strstr(#test, filter)`），逐用例跑完再把每个 run 报告的断言数
直接相加，得到的总数明显高于真实值：

```
$ ./unit_test test_http
# strstr(#test, "test_http") 同时命中 test_http, test_http_errors, test_http_index,
# test_http_parse_header, test_http_rewrites, test_http_dav, test_http_range,
# test_http_multipart, test_http_chunk, test_http_chunk2 —— 共 10 条用例
PASS, run 109 in <elapsed>s
# 该 run 报告的 109 是整族的断言数，而 test_http 自己只有 14 条
# （真机逐条测得：14+5+6+21+7+14+14+9+4+15 = 109）

把每个过滤器的 run 值直接相加 = 789     真实断言总数 = 669
```

同一框架的 `RUN_TEST` 宏体在首个失败处 `return msg`，全量跑一次只会得到
`FAIL, run 247 in 10.692s` 就退出，既给不出矩阵也解释不了总数。

## 触发条件

- 构建系统: makefile（上游自带 `test/Makefile`，`TEST_FILTER` 为 argv[1]）
- 阶段: testing（在 CI 中如实上报「用例数 / 断言数」时）

## 根因分析

两个独立缺陷叠加：

1. `RUN_TEST` 用 `strstr(#test, filter)` 选测，**一个短名字过滤器会连带命中所有以它
   为前缀/子串的长名字用例**，因此「逐过滤器求和」把超串用例重复计入。
2. 首个失败即中断进程，所以**一次全量跑无法产出逐用例判定矩阵**，也就无法用「减去
   重复项」的朴素办法核对。

结论：这类框架的日志数字不能直接照抄，必须设计度量方案本身可自证一致。

## 解决方案

### 推荐方案：按名字长度降序 + 超串断言归减法（desc-length-substring-subtraction）

1. 从测试源文件解析注册的用例名列表（`RUN_TEST\((test_[a-z0-9_]+)\)` 去重）。
2. **按名字长度降序**遍历，把每个用例名当作过滤器单独运行一次。
3. 长度为降序保证：某次 run 中除自己以外被跑到的用例，一定是**已先行计量过的**长名字
   超串。于是本用例真实断言数
   `own = 该 run 报告总数 - Σ(超串已计量断言数)`。
4. 逐用例真实值求和即无重复的断言总数；同时得到真实的判定矩阵
   （PASS/FAIL/skipped 各自独立）。
5. 三处自证一致，任一不满足立即报错而不是给出失真数字：
   - 用例未出现在自身过滤结果中 ⇒ 被更早失败截断 ⇒ 报错；
   - 超串尚未计量 ⇒ 归因失败 ⇒ 报错；
   - `own < 0` ⇒ 归因不自洽 ⇒ 报错。
6. 未编入二进制的用例（`RUN_TEST` 在特性宏 `#ifdef` 内）单独记为 `skipped`，
   不记为通过。

### 回退方案：不相交分组贪心（disjoint-greedy-groups）

按长度升序贪心：已被前面分组覆盖过的用例名不再当过滤器，未跑到的用例如实标注未执行。
代价是粒度较粗，且需要额外说明哪些用例未被单独判定。

### 禁止做法

- ❌ 直接把各过滤器 run 的断言数相加当作用例总数 —— 会虚高（实测 789 vs 真实 669）。
- ❌ 只跑一次全量就把 `run N` 当作总用例数 —— 首失败即中断，`N` 只是中断点之前的计数。
- ❌ 用「跳过失败用例」的方式让数字看起来整齐 —— 环境受限的失败必须逐条归因并保留在
  矩阵里，否则真实回归会被掩盖。

## 验证

先确认过滤器集合是否存在掩码对（无掩码对时子串匹配才天然安全）：

```bash
python3 - <<'PY'
import re, itertools
names = set(re.findall(r'RUN_TEST\((test_[a-z0-9_]+)\)', open('test/unit_test.c').read()))
pairs = [(a, b) for a in names for b in names if a != b and a in b]
print('mask pairs:', len(pairs), pairs[:6])
PY
```

再用与降序法无关的独立口径交叉核对总数：把矩阵行按 `case=N` 展开后逐项求和，
与 `conan create` 日志标记行 `HMBS_UPSTREAM_TEST_RESULT` 的 `assertions` 比对；
两者相等且矩阵无重复项，才算数。

## 关联条目

- 相关: E410（需按上游文件展开完整测试并做语义消费者验证）、E265（已确立
  「替代检查须单独统计通过率、不得伪造通过」—— 本条的增量是如何从一个子串匹配的
  runner 里取得**无重复**的逐用例断言数）、E479（同批 fossa 草稿：
  用上游自带的文件系统可靠性开关替代跳过测试）、E544（同批：环境语义前提导致的失败须逐条归因）
- 适用铁律: R9（质量门禁 FAIL 禁止标 success）、R34（test 必须实质依赖被测包）。
  本条解决的是「如实上报度量」：仓库通行约定是在 `conan create` 日志中输出单行
  `HMBS_UPSTREAM_TEST_RESULT={json}` 标记（`archives/` 下已有 279 个文件包含该约定），
  评审按该标记机读用例数与断言数，因此标记里的数字必须是无重复的真实值。

## 来源

- 软件/版本: fossa/2.1（`archives/f/fossa/2.1`）
- 上游: https://github.com/cesanta/fossa `test/unit_test.c`
- 实测: 鸿蒙真机 aarch64，58 用例 / 669 断言，朴素求和 789
