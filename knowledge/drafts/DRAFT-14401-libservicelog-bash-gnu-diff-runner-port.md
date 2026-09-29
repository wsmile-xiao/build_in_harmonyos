# DRAFT-14401-libservicelog-bash-gnu-diff-runner-port

## 摘要

上游测试执行器是 bash 脚本且依赖 GNU coreutils 特性（`diff -a -y
--suppress-common-line`、`[[ ]]`、bash 数组），OHOS 设备 toybox 的 diff 不支持
`-y`，执行器整体不可用。解法：**POSIX 移植驱动 + python 行级容差比较器**，
复刻上游比较语义——测试内容（场景脚本、期望输出、C 驱动）零改动。

libservicelog/1.1.19 真机实测：6 场景 SUITE PASS 6/6（conan-verify 迭代 11，
Verdict PASS）。

## 上游语义（run_tests 的 diff_with_result_without_timestamp）

```bash
diff -a -y --suppress-common-line EXPECTED ACTUAL | cut -d ' ' -f1,2
# 每行只留下"差异行的行首字段名"，与 5 个易变字段名比较：
#   Log Timestamp: / Event Timestamp: / Update Timestamp: / Platform: / Node Name:
# 命中 → 忽略；未命中 → register_fail（exit 1）
```

## 关键陷阱：cut -f1,2 的字段名语义

`cut -d ' ' -f1,2` 对**单词字段名**（`Platform:`）后接多空格时，第二字段是空串，
产物是 `"Platform: "`（带尾随空格）。移植时若写成"取前两个词拼接再比集合"，
会拿 `"Platform: ppc64le"` 去比 → 平台差异（ppc64le→aarch64）被误报为功能失败。
真机迭代 10 实测踩中：scenario 004/005 误 FAIL，单行
`expected='Platform:           ppc64le' actual='Platform:           aarch64'`。

**正确语义：行首字段名前缀匹配**（`line.lstrip().startswith(易变字段名)`）——
忽略字段名命中行的值差异，其余差异行任一出现即失败，行数不等也失败。

## 推荐解法（rec_approach: posix-port-plus-tolerant-comparator）

1. POSIX sh 重写执行器最小驱动循环：逐场景调驱动二进制（上游 C 驱动原样编译
   为消费者），输出落临时目录；
2. python 行级比较器复刻上游 diff 语义（逐行字节比对 + 行首字段名前缀匹配
   易变集合）；
3. 比较器随 test_package 提交进包，场景脚本/期望输出用上游原文件。

```bash
sh run_upstream_tests.sh ./test_libservicelog \
  <pkg>/share/libservicelog/upstream-tests/tests-results cmp_tolerant.py
# → 每场景 "comparison OK (timestamp/platform/node tolerant)" → SUITE PASS 6/6
```

## 兜底解法（fallback: tool-dep-diffutils）

制品仓有 diffutils/busybox 完整版时，`test_requires` 引入并前置 PATH，直接跑
上游 bash 执行器；需 bash 亦可用，工具包体积/可用性不定，移植驱动仍是首选。

## 禁止项

- 禁止直接跑上游执行器硬刚 toybox（`diff: invalid option -- 'y'`）并反复改库
  代码追不存在的问题；
- 禁止扩大容差比较器的忽略范围（如忽略 description/refcode/severity 差异）——
  只忽略上游明确豁免的易变字段，否则测试放水，审查员按 rule12 否决；
- 禁止用 sed 伪造 GNU diff 输出糊弄比较——语义必须逐条复刻。
