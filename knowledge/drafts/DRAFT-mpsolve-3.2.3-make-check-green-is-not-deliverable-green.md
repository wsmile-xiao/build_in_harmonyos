# `make check` 全绿 ≠ 交付物可用：只链私有库的 check 套件，与"把 SKIP 算进 TOTAL"的退出码

## 场景一：check 套件里没有"交付物"，只有"构建树里的私有库"

看 `src/tests/Makefile.am` 的一句：

```make
COMMON_LDADD = ${top_builddir}/src/libmps/libmpsprivate.la
```

16 个 `check_PROGRAMS` **全部**用这一行链接。`libmpsprivate.la` 是构建树内的
convenience 库——**不安装、不对消费者暴露**。于是：

| 上游测试覆盖 | 交付物 |
|---|---|
| `libmps` 内部 C API | 安装树里的 `bin/mpsolve` CLI ← **零覆盖** |
| 求根算法的数值行为 | 安装出来的 `libmps.so` 的对外符号与 soname ← **零覆盖** |
| 单进程内的库调用 | CLI 的版本握手、输入格式解析、输出格式旋钮 ← **零覆盖** |
| | 无桌面栈 / 无 tty / 只读临时目录下能否跑 ← **零覆盖** |

**上游 check 越绿，越容易让人以为 CLI 已经被验证过。** 判定的第一步就是
`grep -n 'lib.*private\.la' src/tests/Makefile.am` —— 一行就够。

还有一个更隐蔽的：**`START_TEST` 声明数 ≠ 执行数**。本包 `src/tests/` 里
`START_TEST` 命中 90 处，但只有 88 处经 `tcase_add_test` 注册进 Suite
（`check_convex.c::hypograph_creation` 只声明未注册；`check_secsolve.c` 34 处
声明中 1 处未注册）。这 2 条要如实计入**未执行**，不能计进通过数：

```sh
grep -rn 'START_TEST' src/tests/*.c src/tests/*.cpp | wc -l          # 90 声明
grep -rn 'tcase_add_test\|tcase_add_loop_test' src/tests/*.c src/tests/*.cpp | wc -l  # 88 注册
```

## 场景二：automake 把 `SKIP` 计入 `TOTAL`，退出码分不出"全跑"与"大半跳过"

```
$ make -C src check ; echo $?
0
$ sed -n '/^# TOTAL/,/^# ERROR/p' src/tests/test-suite.log
# TOTAL: 16
# PASS:  16
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
```

`make check` 退出 0 **不蕴含** `SKIP: 0` —— 并行测试框架把 `SKIP` 计进 `TOTAL`。
同类机制在各家框架里都有：check(3) 的 `SKIP` 关键字、Catch2 的
`SKIP("...")`、gtest 的 `GTEST_SKIP()`、ctest 的 `WILL_FAIL`/`DISABLED_`。

**对策：不吃退出码，回读汇总块，并把条数钉死。** 配方里把
`src/tests/Makefile.am` 的 `check_PROGRAMS` 条数（本包 16）数出来写成常量，
`TOTAL` 取不到或 `TOTAL < 16` 一律抛异常：

```python
MIN_UPSTREAM_TESTS = 16          # src/tests/Makefile.am 的 check_PROGRAMS 条数

def _parse_suite_summary(text):
    return {m.group(1): int(m.group(2))
            for m in re.finditer(r"^#\s*(TOTAL|PASS|SKIP|XFAIL|FAIL|XPASS|ERROR):\s*(\d+)\s*$",
                                 text, re.MULTILINE)}

bad = {k: summary.get(k, 0) for k in ("FAIL", "ERROR", "SKIP", "XPASS") if summary.get(k, 0)}
if bad:
    raise ConanException("upstream suite not clean: %r" % (bad,))
if summary["TOTAL"] < MIN_UPSTREAM_TESTS:
    raise ConanException("ran only %d of %d programs" % (summary["TOTAL"], MIN_UPSTREAM_TESTS))
```

**顺带一个 CI 细节**：CI 只保留约 4000 字符的日志**尾部**。如果直接让
`make check` 失败往外抛，断言原文落在套件日志里、不在保留区内，排障时只剩一句
"make check failed"。所以捕获异常后**先主动**把 `test-suite.log` 尾部打成 error，
再抛。

## 场景三：把"安装树里的二进制"当被测对象，并给正向断言配反向验证

缺口既然在 CLI，就在 `test_package` 里把 CLI 当被测对象。这里有两个具体的坑：

**坑 1：版本握手入口可能是短选项，不一定是 `--version`。**

```
$ mpsolve --version
mpsolve [-a alg] [-b] -c [-G goal] [-o digits] [-i digits] [-j n] [-t type] [-S set]
  ...（一大段 usage）
$ mpsolve -v
MPSolve 3.2.3
```

`--version` 落进了 usage 分支（打印用法、但**并不以非零码退出**）。断言一旦写成
`grep -q '3.2.3' <(mpsolve --version)`，会因为 usage 里恰好有版本串而**永真**。
真正的入口是 `-v`，输出恰好一行 —— 断言就写"**恒等于** `MPSolve 3.2.3`"：

```sh
V=$("$BIN" -v 2>"$TMP/err.txt"); [ $? -eq 0 ] || fail "-v exited $?"
[ "$V" = "MPSolve 3.2.3" ] || fail "-v printed '$V'"
```

**坑 2：`-O f`（打印几位）与 `-o digits`（保证几位）是两个正交的旋钮。**
实测：`-O f` 把有效数字从 14 位抬到 21 位、并给每个根加一行 `Status:`；
`-o 50` 则把 `Status: Approximated` 变成 `Status: Isolated`（要求 50 位保证精度
会逼算法把根证明分离）。**断言 `-o 50` 会改变输出前，先证"默认不满足"**，否则
很可能写出一条永真断言：

```sh
# 反向验证：默认输出既无 16 位以上有效数字，也无 Status 行
grep -qE '\(0\.1414213562373095' out.txt && fail "默认已带 16 位以上，正向断言将永真"
grep -q 'Status:'                 out.txt && fail "默认已带 Status:，正向断言将永真"
# 正向断言
grep -qE '\(0\.1414213562373095' full.txt || fail "-O f 没抬到 16 位以上"
grep -q 'Status:'                 full.txt || fail "-O f 没输出 Status 行"
```

**注意别写的断言**：`grep <二进制>` 取编译期字符串。OHOS 上"字符串在不在"与
"运行期能不能跑起来"是两件事，且 toybox/bionic 的 `grep` 按行读并以 NUL 截断、
`tr`/`strings` 未必存在。断言要落在**可观测的运行时行为**上。

## 场景四（鸿蒙特有）：把"退化环境"做成一条真断言

上游 check 框架的 IPC 临时文件按 `TEMP → P_tmpdir(/tmp) → TMPDIR → .` 取路径,
**反过来要求一个可写的 TEMP** —— 在 OHOS 的 HMFS 只读 `/tmp` 上会失败。所以
"CLI 在不可写临时目录下还能不能跑"这条路径，上游既**没覆盖**、也**不等价**。

断言写法（只用 POSIX sh 内建，避免假设 `env`/`tr`/`awk` 存在）：

```sh
(
    unset DISPLAY HOME
    TMPDIR="$TMP/no-such-tmpdir" TEMP="$TMP/no-such-tmpdir" \
        "$BIN" "$TMP/poly.txt" < /dev/null > "$TMP/deg.txt" 2>"$TMP/err.txt"
)
[ $? -eq 0 ] || fail "degraded-env run exited $?"
grep -qE '\(0\.1414213[0-9]*e1'  "$TMP/deg.txt" || fail "丢失正根"
grep -qE '\(-0\.1414213[0-9]*e1' "$TMP/deg.txt" || fail "丢失负根"
```

无 tty（stdin/stdout 皆管道）+ 无 `DISPLAY` + `HOME` 未设 + `TEMP`/`TMPDIR`
指向不存在的目录，四件事一起上 —— 这正好是 OHOS PC（无桌面栈、HMFS 只读、
$HOME 未必有）的运行形态。

## 推广

`make check` 是**上游的**测试，不是**你的**测试。三句话：

1. **退出码不是判据**，汇总块才是 —— 任何把"跳过"实现成正常退出路径的框架
   （autotools/check 的 `SKIP`、Catch2 `SKIP`、gtest `GTEST_SKIP`、ctest 空套件），
   都要去读汇总行，并把条数从上游 Makefile.am 数出来钉死。
2. **先查测试链的是什么库**：`grep 'lib.*private\.la' <test>/Makefile.am` 命中
   ⇒ 交付物（安装树里的 CLI/共享库）在上游测试里零覆盖，必须自己补消费者测试。
3. **正向断言配反向验证**：任何"打开某个开关行为就变了"的断言，先写一条
   "默认值不满足它"的反向验证 —— 这是把"永真断言"挡在门外的唯一廉价手段。
