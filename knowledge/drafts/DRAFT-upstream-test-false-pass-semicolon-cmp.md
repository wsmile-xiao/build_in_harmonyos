# DRAFT-upstream-test-false-pass-semicolon-cmp — 上游测试目标的假通过

> 配对的 kv：`knowledge/drafts/DRAFT-upstream-test-false-pass-semicolon-cmp.kv`
> 来源：pcc（Portable C Compiler）1.2.0-devel-20220331 适配，PR !14348
> 分类：testing / conan

## 错误特征

上游测试目标**返回 0**，但用例实际失败：

```
破坏 res5 后期望输出 → make -C cc/cpp test 仍返回 0
```

## 根因分析

pcc 的 `cc/cpp/Makefile.in` 的 `test` 目标：

```make
test: $(DEST)
	@for n in 1 2 3 ... 18 ; do				\
		echo -n "test$${n} " ;				\
		./$(DEST) < tests/test$${n} > tests/run$${n} &&	\
		cmp tests/run$${n} tests/res$${n} && echo ;	\
		if test -f tests/res$${n}C ; then		\
			echo -n "test$${n}C " ;			\
			./$(DEST) -C < tests/test$${n} > tests/run$${n}C && \
			cmp tests/run$${n}C tests/res$${n}C && echo ; \
		fi ;						\
	done
```

每个比较用 `;` 串联，`&&` 只影响该条命令自身的显示分支；**整条 for 循环的退出状态
不反映任何一次 `cmp` 的失败**，`make` 恒返回 0。

**因此「上游测试通过」在退出码意义上毫无信息量。**
本机实测：人为破坏 `res5` 后 `make -C cc/cpp test` **仍返回 0**。

## 推荐方案

**方法**: `re-compare-and-raise-in-recipe`

1. `build()` 中**先原样执行上游 `test` 目标**（保留上游语义，让上游语料真正跑起来）；
2. 再**自行逐项比较** `run<N>` / `run<N>C` 与 `res<N>` / `res<N>C`，不一致即 `raise`：

```python
for n in range(1, 19):
    for tag, expected_name, produced_name in (
        ("",     f"res{n}",  f"run{n}"),
        ("-C",   f"res{n}C", f"run{n}C"),
    ):
        expected = os.path.join(tests_build, expected_name)
        if not os.path.isfile(expected):
            continue                       # test19/20/21 只有输入，不计入
        produced = os.path.join(tests_build, produced_name)
        checked += 1
        if not os.path.isfile(produced):
            failed.append(f"test{n}{tag}: no output")
        elif open(produced, "rb").read() != open(expected, "rb").read():
            failed.append(f"test{n}{tag}: output differs from {expected_name}")
if failed:
    raise ConanException(
        "upstream preprocessor tests failed: " + ", ".join(failed))
```

3. **用负测试证明该判定真的会失败**（否则只是「声称更强」）：

   破坏 `res5` 后再跑 →

   ```
   ConanException: upstream preprocessor tests failed: test5: output differs from res5
   ```

## 实测结果（pcc）

| 口径 | 结果 |
|---|---|
| 上游 `test` 目标退出码 | 0（**不可信**） |
| 独立逐项比较 | **20 次比较 / 0 失败** |
| 按编号用例 | 18/18（另有 `res15C` / `res16C` 两个 `-C` 变体） |
| 负验证（破坏 res5） | 上游目标仍 rc=0；独立判定报 `test5: output differs from res5` |

> 清点依据：上游顶层 `Makefile` 与 `cc/Makefile` **均无 `check`/`test` 目标**；
> 唯一套件在 `cc/cpp/tests/`，由 `cc/cpp/Makefile.in` 的 `test` 目标驱动。
> 目录内 `test19` / `test20` / `test21` **只有输入、无期望输出**，上游不遍历，不计入。

## 陷阱

**禁止**仅凭 `make test` 退出码为 0 就申报「上游测试通过」——
触碰 **R51（上游测试三步法）** 的如实申报要求。

## 与现有知识库的关系

既有库无「Makefile 手写 `test` 目标用 `;` 串联导致退出码无意义」的条目；
**E526** 讲的是 patch 语义（strip=0）的假通过，属不同层面，故各立一条。
