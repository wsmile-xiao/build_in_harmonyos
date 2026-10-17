# E543 — ctest --output-on-failure 在用例通过时不回显被测进程 stdout，导致解析其统计行的硬闸误判为回归

> 状态：DRAFT（contributor NGS1，2026-09-16，实测于 ngs 0.2.17 适配）

## 错误特征

构建明明全绿，却被配方自己的质量闸判为失败：

```
ngs/0.2.17: UPSTREAM CTEST: 0 assertions executed, 0 skipped as platform gaps
ERROR: ngs/0.2.17: Error in build() method ...
       upstream ctest regressed: only 0 assertions executed, ...
```

而同时 ctest 日志里清楚写着成功：

```
1/1 Test #1: all ..............................   Passed    5.95 sec
100% tests passed, 0 tests failed out of 1
```

## 触发条件

- 构建系统：cmake（注册了 `add_test()`，配方用 `ctest` 驱动）
- 阶段：`build()` 里以"解析 ctest 输出"的方式设测试质量硬闸的配方
- 症状触发点恰好是**测试通过**的时候；测试失败时反而一切正常

## 根因分析

`ctest --output-on-failure` 的语义是"仅在用例失败时回显该用例子进程的 stdout"。
用例通过时子进程输出被 ctest 吞掉。

若配方用正则去抓被测程序自己打印的统计行（例如 `OK. Tests: 754`）来设闸，
在通过路径上这行根本不出现在 ctest 输出里 → 解析结果为 0 → 闸误判回归。

同一根因还有两个变体，都会踩：
1. 改用数"逐条用例前缀行"（如 `^+ Test: `）来统计 —— 同样只在失败回显时才有；
2. 被测套件在中间异常中止（未跑到统计行）—— 此时若只判"条数达标"就会被
   部分输出蒙混过关，覆盖量被静默削减。

## 解决方案

### 推荐方案
用 `ctest -V`（verbose，逐行加 `<num>: ` 前缀）采集被测进程完整输出，
并且**优先解析被测程序自报的统计行**，同时把"统计行缺失"本身当作失败信号：

```python
log = os.path.join(self.build_folder, "upstream-ctest.log")
self.run(f'ctest -V --timeout 1800 > "{log}" 2>&1',
         cwd=self.build_folder, env="conanbuild", ignore_errors=True)
out = load(self, log) or ""
m = re.search(r"OK\. Tests: (\d+)(?: Skipped\(platform\): (\d+))?", out)
if not m:
    raise ConanException("... did not report its assertion count; the suite "
                         "most likely aborted early")          # fail-closed
executed, skipped = int(m.group(1)), int(m.group(2) or 0)
if "100% tests passed" not in out:      raise ConanException("ctest not green")
if executed + skipped <= 540:           raise ConanException("below upstream's own bound")
if skipped > 8:                         raise ConanException("undocumented new skips")
```

三道闸各自守住的失效模式：`100% tests passed` 守"用例失败"；总数下限守"覆盖缩水"；
`skipped > 上限` 守"新增跳过被静默放行"。`ignore_errors=True` 只用于把日志落盘后自解析，
**不能**用来吞掉失败 —— 失败判定必须显式写在解析逻辑里。

### 禁止做法
- ❌ 直接 `self.run("ctest ...")` 不带 `-V`，再解析输出（通过时无输出）
- ❌ 用 `ignore_errors=True` 且不做任何解析（等于取消测试闸）
- ❌ 把统计行缺失当成 0 条然后继续（应 fail-closed，因为套件可能中途 abort）

## 验证

```bash
# 1) 日志同时含被测程序统计行与 ctest 汇总行
grep -E "100% tests passed" <build_folder>/Release/upstream-ctest.log
grep -E "OK\. Tests: [0-9]+" <build_folder>/Release/upstream-ctest.log
# 2) 反向验证闸门真的会拦：临时把阈值调高，conan create 必须失败
sed -i 's/<= 540/<= 99999/' conanfile.py && conan create . --build=missing; echo "应非 0"
git checkout conanfile.py
```

## 关联条目

- 无强关联。`draft-review` 查重：最近邻 E535（相似度 0.35，不同问题）。
- 互相 link：与本批次 E544（同为"配方自身写法导致 conan create 误判/失败"类）建议标 similar_to。
