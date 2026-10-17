# 上游 pg_regress 入口依赖 ruby + 必须连既有 TCP 集群：用 Python 复刻 schedule，别顺手剪用例

> DRAFT-pgroonga-4.0.8-pg-regress-without-ruby-on-live-tcp-cluster
> （知识库扩展草稿，路径 B）与 pgroonga 4.0.8 归档同 PR 交付。

把这个可重定位的扩展装好之后（见「可重定位的 PG 扩展」那篇），还剩最后一件事：
**怎么让上游那 1600 条回归真的跑起来**（钉版 1600，实跑 1598）。pgroonga 的
上游套件不是 `make test`，
而是一套自己要启动 PostgreSQL 的 `pg_regress` 流程——在 OHOS 上它有三个地方
同时坏掉。

## 三个问题，任何一个处理错都会得到假结果

### (a) 入口依赖 ruby

`meson.build:585-586`：

```meson
if get_option('test')
  ruby = find_program('ruby')
endforeach
```

`-Dtest=true` 时它会 `find_program('ruby')`，再用 `test/prepare.rb` 生成
pg_regress 的 schedule。OHOS 上没有 ruby，构建期只能 `-Dtest=false`。

**但这意味着上游回归根本不会在 `build()` 里跑。** 于是"配方能编过"与"扩展真的
能用"之间那段空白，必须由 test_package 自己补上。

### (b) 不能用 `--temp-instance`

仓库打包的 PostgreSQL 定义了 `HAVE_NO_UNIX_SOCKETS`。pg_regress 的
`--temp-instance` 依赖 Unix domain socket 做启动探测，在这个 PG 上必然失败。

只能**自己起一个 TCP 集群**：`initdb` → `pg_ctl start`，`listen_addresses` 和
显式 `port` 写进 `postgresql.auto.conf`，然后让 pg_regress 用
`--host/--port/--user/--dbname` 接上去。

自证这条前提只要一行：

```bash
strings "$PG_PKG/bin/postgres" | grep HAVE_NO_UNIX_SOCKETS
```

### (c) oracle 对环境极其敏感

`expected/*.out` 是逐字节比对。计划类用例（全套件含 4 条
`EXPLAIN (COSTS OFF)` 形状断言）的**计划形状**由 `random_page_cost`、
`enable_partitionwise_join`、`max_prepared_transactions` 这些参数决定。

不照抄上游 CI（`.github/workflows/linux.yml`）往 `postgresql.conf` 里追加的那
几项，结果必然是一片 diff——而 diffs 会被误读成"适配失败"，实际只是环境没对齐。

## 复刻 schedule，而不是复刻测试

`test/prepare.rb` 只有 38 行，行为就三件事：

```ruby
Dir.glob("sql/**/*.sql").each do |sql|
  dir = File.dirname(sql.sub("sql/", ""))
  FileUtils.mkdir_p("results/#{dir}")
  puts "test: #{sql.sub("sql/", "").sub(/\.sql\z/, "")}"
end
```

——递归遍历 `sql/`、为每个目录预建 `results/<dir>`、每个 `*.sql` 写一行
`test: <相对路径去扩展名>`。Python 十几行等价实现即可。

### 关键纪律：不在这里做任何"顺手过滤"

最容易顺手写下去的一行是：

```python
if not os.path.isfile(oracle):
    continue          # ← 不要这样
```

看起来是"没有 oracle 就没法比对，跳过很合理"，实际后果是**用例集合静默缩水**：
pg_regress 仍然报全绿，rule4 里声明的上游用例数与实际执行集脱节。oracle 缺失
这类问题应该由 pg_regress 自己报 `FAILED`，而不是在生成 schedule 的阶段消失。

要排除就写进一份**逐条注明原因**的清单（本包是 `regress-skip.txt`，2 条），
让人一眼能看到减了多少、为什么减。

本包那 2 条是仅有的**插件依赖**用例，而 groonga 包不含对应插件：

| 用例 | 需要 | 为什么排不掉 |
|------|------|--------------|
| `function/tokenize/metadata` | TokenMecab | 需要 mecab 词典，包里没有 |
| `full-text-search/text/options/token-filters/custom` | TokenFilterStem | `token_filters/stem.so` 未随包提供 |

它们**没有备用 oracle**（不像其 50 条 `_1/_2.out`），所以既不能靠环境变量兜底，
也不能伪装成通过。

> 反过来说，语言模型类用例（`PGRN_*_TEST` 开关）**不要**去设那些环境变量：
> 让它们走自带的 `\quit` 提前退出分支，由 `_1.out` 备用 oracle 兜底——这才是
> 上游 CI 的行为。

## 把 pg_regress 接到活集群上

`--inputdir` **必须可写**：pg_regress 会往 `<inputdir>/results/` 写实际输出。
Conan cache 只读，所以先把 vendored 的 `sql/` + `expected/` 复制到 build 目录
再指过去。

参数逐条对齐上游 `meson.build:628-636`：

```bash
pg_regress --bindir <pg>/bin --dlpath <pkg>/lib \
           --inputdir <build>/upstream --outputdir <build>/regress \
           --launcher <upstream>/test/short-pgappname \
           --load-extension pgroonga \
           --host localhost --port <port> --user hmbstest --dbname regression \
           --schedule <build>/regress/schedule.txt
```

唯一比上游多出来的是 `--host/--port/--user/--dbname`，而它们是被
`HAVE_NO_UNIX_SOCKETS` 逼出来的。`--launcher test/short-pgappname` 要保留
（它只是个 `PGAPPNAME=pg_regress "$@"` 的壳；本套件没有用例读
`application_name`/`pg_stat_activity`，所以它不是 oracle 敏感项，但要跟上游一致）。

## 失败时怎么归因

pg_regress 的**退出码**与**逐用例结果**是两套信息；而失败时真正有用的东西在
`regression.diffs` 里——它默认只写到 `<outputdir>/regression.diffs`，CI 日志里
看不到。不主动打印就永远只能看到 "1 of 1600 tests failed"，无从下手。

所以：

```python
for m in re.finditer(r"^\s*test\s+(\S+)\s+\.\.\.\s+(ok|FAILED)\s*$",
                     output, re.M):
    ...                       # 逐条统计，不要只解析 "N% tests passed"
if failed:
    # 把 regression.diffs 尾部打到控制台（CI 只保留日志尾部）
    raise ConanException(...)
```

## 判定信号

```bash
grep -n "find_program\|get_option('test')" meson.build          # 入口依赖什么
strings "$PG_PKG/bin/postgres" | grep HAVE_NO_UNIX_SOCKETS      # 有没有 unix socket
find expected -name '*.out' | wc -l                             # oracle 总数
find expected -name '*_1.out' -o -name '*_2.out' | wc -l        # 备用 oracle 数
grep -n -A8 'random_page_cost\|enable_partitionwise_join' .github/workflows/*.yml
```

## 反模式

- **在生成 schedule 时过滤用例**：得到"全绿但用例集缩水"的假绿，比直接失败更糟
  （rule 2/9 的欺骗性行为区间）。
- **用 `--temp-instance` 或 `unix_socket_directories`**：报错出现在 "could not
  connect"，与"测试内容"完全无关，容易误判成"扩展没装好"。
- **只看退出码 / 只解析汇总百分比**：失败不可归因，下一轮只能盲改。

## 相关

- `DRAFT-pgroonga-4.0.8-pg-extension-relocatable-install-and-discovery`
  —— 扩展**怎么被 PG 找到**；本篇是它之后"怎么把上游回归跑起来"。
- `DRAFT-pgroonga-4.0.8-groonga-dep-baked-build-prefix-pc-and-plugins-dir`
  —— `GRN_PLUGINS_DIR` 没设时，症状正是本篇那 2 条被排除的用例报
  `unsupported tokenizer` / `unsupported token_filter`。
