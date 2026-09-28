# DRAFT：meson 的 `not_installed` 不是「不执行」，`meson test` 退出码 0 也不是覆盖率

> 状态：草稿（待知识库主编 promote）
> 来源：libgmobile 0.7.2 适配，`archives/l/libgmobile/0.7.2`
> 类别：testing / meson / false-pass / counting-semantics

## 一、读错 `not_installed` 会少报上游 N

libgmobile 0.7.2 的 `tests/meson.build`：

```meson
tests = ['cutout', 'display-panel', 'mcc-mnc', 'svg-path', 'timeout', 'utils', 'device-tree']
# These need data not available on the installed system:
not_installed = ['test-device-tree']

foreach test : tests
  test_name = 'test-@0@'.format(test)
  test_conf = configuration_data()
  ...
  if get_option('installed_tests') and test_name not in not_installed
    configure_file(
      input: files('template.test.in'),
      output: test_name + '.test',
      install_dir: installed_tests_metadir,      # ← not_installed 唯一的作用
      configuration: test_conf,
    )
  endif

  t = executable(test_name, ['test-@0@.c'.format(test)], ...)   # ← 一律构建
  test(test, t, env: test_env)                                 # ← 一律注册执行
endforeach
```

`not_installed` 出现的**唯一**位置是 `configure_file()` 的那个 `install_dir:`。
它的语义是「这个程序即使装了包，也不要有 `.test` 元数据被
`gnome-desktop-testing-runner` 之类的工具发现」——因为该用例依赖
`tests/data/` 里的夹具，装到系统上之后夹具不在了。

它**不**从 `tests` 里剔除、也不影响 `executable()` / `test()`。所以

- 上游测试程序数 = **7**（含 `device-tree`）；
- 把 `not_installed` 读成「这些不跑」→ 数成 6，**少报 1 个程序**。

对照 automake 的同类概念也值得记一笔：`noinst_PROGRAMS` 与 `check_PROGRAMS`
是**真的**在「是否构建/是否纳入 check」上不同，而 meson 的 `not_installed`
不是。变量名的联想在这里会误导。

## 二、退出码 0 只说明「没有失败」，不说明「跑了多少」

`meson test` 的退出码语义是二值的：有任何失败/超时就非零，否则零。以下三种
情况**退出码都是 0**：

| 情况 | 退出码 | 汇总块 |
| --- | --- | --- |
| 7 个程序全绿 | 0 | `Ok: 7` |
| 7 个程序里 5 个被 SKIP、2 个通过 | 0 | `Ok: 2` / `Skipped: 5` |
| 条件分支让 `test()` 根本没被调用（空套件） | 0 | `Ok: 0` |
| 配置期 `-Dtests=false`，套件整个没生成 | 0 | 汇总块为空/不存在 |

这与 automake 并行测试框架把 `SKIP` 计入 `TOTAL` 是同一族问题，只是换了个
构建系统（参见 `similar_to` 的 mpsolve 条目）。判据应当放在
`<builddir>/meson-logs/testlog.txt` 末尾的汇总块：

```
Ok:                    7
Expected Fail:         0
Fail:                  0
Unexpected Pass:       0
Skipped:               0
Timeout:               0
```

`Ok:` 才是「真跑过并通过的程序数」。

## 三、程序数 ≠ 用例数，两个都要写清楚

meson 的 `test()` 注册的粒度是**程序**；一个程序内部可以有任意多个
`g_test_add_func` 用例。libgmobile 是：

| 口径 | 数 |
| --- | --- |
| meson `test()` 注册的测试程序 | 7 |
| `g_test_add_func` 注册的用例 | 14 |

（`cutout` 1 + `device-tree` 1 + `display-panel` 2 + `mcc-mnc` 1 +
`svg-path` 4 + `timeout` 2 + `utils` 3）

数用例数时按「可执行集」数，不能按函数定义数——本包里
`grep -c '^test_[a-z_0-9]* (void)'` 得到的正是 14，与 `g_test_add_func` 一致，
但两者一致只是巧合，遇到用 `g_test_add_data_func` 或条件注册的项目就会分叉。

上游默认分支 `main` 与本次钉版 tag `v0.7.2` 的 `tests/` 内容**一致**（同为
7 程序 / 14 用例），所以不存在「master 比 tag 多几个用例」的差额需要解释——
这一点要在 body 里主动写明，免得评估侧按 master 另一个口径去比。

## 解决方案

配方侧三层：

1. **跑**：`build()` 内 `meson.test()`，让上游全部 7 个程序都执行。
2. **回读**：解析 `meson-logs/testlog.txt` 的汇总块，硬断言
   - `Fail` / `Timeout` / `Unexpected Pass` 必须为 0；
   - `Ok` 必须 >= `UPSTREAM_TEST_PROGRAMS`（模块级常量，本包 7）；
   - 汇总块读不到（文件缺失/格式变更）也抛异常——**「读不到结论」不等于
     「结论是好」**。
3. **报口径**：在 `notes.md`、`test_package/MANIFEST.yml` 与 PR body 里同时写
   出「7 个测试程序 / 14 个用例」，并注明 `not_installed` 只影响
   `.test` 元数据的安装、不影响执行。

对应代码（摘）：

```python
def _assert_suite_not_vacuous(self):
    log = os.path.join(self.build_folder, "meson-logs", "testlog.txt")
    if not os.path.isfile(log):
        raise ConanException(f"meson test log missing: {log}")
    content = open(log, encoding="utf-8", errors="replace").read()
    summary = {}
    for key in ("Ok", "Expected Fail", "Fail", "Unexpected Pass", "Skipped", "Timeout"):
        m = re.search(rf"^{re.escape(key)}:\s+(\d+)\s*$", content, re.MULTILINE)
        if m:
            summary[key] = int(m.group(1))
    for key in ("Fail", "Timeout", "Unexpected Pass"):
        if summary.get(key, 0):
            raise ConanException(f"upstream meson suite reports {key}={summary[key]}")
    if summary.get("Ok", 0) < UPSTREAM_TEST_PROGRAMS:
        raise ConanException(
            f"only {summary.get('Ok', 0)} of {UPSTREAM_TEST_PROGRAMS} test programs ran")
```

## 验证命令

```bash
# 1) 不要看退出码，回读汇总块
meson test -C <builddir>
sed -n '/^Ok:/,/^Timeout:/p' <builddir>/meson-logs/testlog.txt

# 2) 两个口径分别数
grep -n 'tests = \[' -A2 <src>/tests/meson.build          # → 7 个程序
grep -h 'g_test_add_func' <src>/tests/test-*.c | wc -l    # → 14 个用例

# 3) 确认 not_installed 只影响元数据
grep -n 'not_installed' -B4 -A12 <src>/tests/meson.build

# 4) 负向复现：关掉 tests，退出码照样 0，套件是空的
meson setup _b <src> -Dtests=false && meson test -C _b; echo "exit=$?"
#    → exit=0，但汇总块为空 → 只吃退出码就会把「空跑」判成全绿
```

## 禁止策略

| 禁止 | 原因 | 后果 |
| --- | --- | --- |
| 因为 `not_installed` 就把该程序从 `tests` 里删掉 | 它只门控 `.test` 元数据的安装，程序照样构建执行；删掉等于改上游测试注册表 | rule4 判少报，且真的丢掉一个用例的回归保护 |
| 只看 `meson test` 退出码 == 0 | 退出码不覆盖 SKIP 与「用例根本没注册」 | 把「只跑了 2/7」当「7/7 全绿」 |
| 用 `--suite` / `--no-suite` 过滤掉不想要的程序 | 适配目标是让库在 OHOS 上跑对，不是让报表好看 | 伪造通过率，评审判不实 |
| 汇总块读不到时静默放过 | 「读不到结论」不等于「结论是好」；格式变更/文件缺失本身就是要修的问题 | 断言退化成恒真，等于没有断言 |

## 关联

- `similar_to` **DRAFT-mpsolve-3.2.3-make-check-green-is-not-deliverable-green**：
  同一失效模式在 autotools 侧的实例——`make check` 退出 0 而 SKIP 计入 TOTAL，
  且 check 程序只链构建树内的私有库。本条是 meson 侧的对应物，额外多了一层
  「变量名 `not_installed` 误导统计口径」。
- `similar_to` **DRAFT-box2d-2.4.1-ctest-empty-suite-false-pass**：CMake/ctest
  侧的空套件假通过。三条合起来覆盖 autotools / meson / cmake 三大构建系统的
  同一族问题。
- `similar_to` **E265**：上游测试的注册表与执行集不是一回事。
