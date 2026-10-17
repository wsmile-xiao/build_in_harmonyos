# 纯 Python 包安装成功不等于目标解释器可用 SQLite

## 错误特征

```text
ModuleNotFoundError: No module named '_sqlite3'
ModuleNotFoundError: No module named 'sqlite3'
sqlite3.OperationalError: unable to open database file
```

这些是需要识别的运行期错误特征，并非本次真机已经观测到的日志。本条说明一个可验证的边界：复制或安装纯 Python 模块不会构建 CPython 的 `_sqlite3` 扩展，也不会证明消费者 Python 能创建 SQLite 连接。

## 触发条件

目标使用裁剪版或自行构建的 CPython，构建时未提供 SQLite 扩展，或 `_sqlite3` 的运行时动态依赖不可用。Conan 包安装成功本身不能证明消费者解释器包含并能加载可选标准库扩展。本次 OHOS PC 的目标 Python 3.14.7 实际可用；上述缺失错误是待识别的通用故障特征，不是本次已观测到的故障。

minidb 2.0.8 的 `minidb.py` 在模块导入时执行 `import sqlite3`。因此适配检查应使用 Conan 消费者最终调用的同一 `sys.executable`，分别验证模块导入、建立连接、执行 SQL 和被测包 API。

## 根因分析

`pip install` 或 Conan `package()` 成功只说明 `minidb.py` 被放入包路径，不会构建 CPython 的 `_sqlite3`，也不负责目标 Python 的 SQLite 动态依赖。导入 `sqlite3` 成功仍不足以证明数据库可用；应再建立连接并执行一次 SQL。仅测试内存数据库也不能覆盖文件系统上的创建、关闭和重开。

| 检查层 | 可证明的事实 | 不可据此推断 |
|---|---|---|
| 文件已安装 | `minidb.py` 位于 Conan 包路径 | 目标解释器能导入 `sqlite3` |
| 标准库可导入 | 当前解释器可加载 `sqlite3` | SQLite 连接与 SQL 往返成功 |
| 内存连接与 SQL 往返 | 当前解释器的 SQLite 后端可用 | 文件数据库权限及重开流程正确 |
| 消费者持久化测试 | 被测包可按实际 API 写入并重新读回 | 其他 CPython 构建或设备也必然具备相同运行时 |

## 解决方案

先用消费者运行时执行导入、连接和 SQL 往返：

```sh
python3 -c 'import sys,sqlite3; print(sys.executable, sqlite3.__file__, sqlite3.sqlite_version); c=sqlite3.connect(":memory:"); assert c.execute("select 1").fetchone()==(1,)'
python3 -c 'import minidb; d=minidb.Store(); d.close()'
```

消费者测试还应创建文件数据库、保存记录、关闭 store，再用同一解释器重新打开并读回。minidb 的 `Store.close()` 会对数据库执行 `VACUUM`，因此该流程同时检查文件数据库生命周期。本次 `test_package/test_minidb.py` 的 3 个 unittest 用例共 10 条断言，均在目标 HarmonyOS PC 通过；测试另断言实际导入模块位于 Conan 包的 `lib/python3/site-packages`，避免宿主或源码目录中的同名模块造成假通过。

若目标解释器确实缺少 `_sqlite3`，应提供启用该扩展且运行依赖闭合的目标 Python。不要把宿主解释器结果当作设备证据，不要放置占位扩展、mock SQLite 或跳过真实连接测试。

## 通用性证据

该运行时边界适用于直接或间接依赖 CPython `sqlite3` 标准库的 Python 包。除 minidb 自身测试外，在同一 HarmonyOS PC 的 Python 3.14.7 上运行了 CPython 随发行版提供的独立 `Lib/test/test_sqlite3` 上游语料：共发现 510 项，506 项通过、4 项因上游内存门槛跳过、0 失败、0 错误。4 项分别要求 4.0、6.0 或 8.0 GiB 内存；当前设备不满足这些大内存测试的前置条件。此语料独立验证目标解释器的 SQLite 连接、事务、类型转换、回调和其他 DB-API 行为，不计入 minidb PR 的上游 N=42 或消费者 N=3。

复现实验使用 CPython 自带测试树并保留包名以支持相对导入：

```python
import os, sys, unittest
base = os.path.join(os.path.dirname(os.__file__), "test", "test_sqlite3")
top = os.path.dirname(os.__file__)
suite = unittest.TestLoader().discover(base, pattern="test_*.py", top_level_dir=top)
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful()
```

## 查重反证

按 main tip `9b028fd5bd2887ead685d55a6a6a179e3e1c9683` 检索正式目录：正式条目 542 个。精确机制词 `_sqlite3`、`sqlite3.connect`、`CPython sqlite3 extension`、`import sqlite3` 在 `knowledge/graph/` 与 `knowledge/doc/` 中均为 0 命中；宽词 `sqlite3` 命中 E236、E280、E524 及 `index.tsv`，分别涉及 Libtool 链接、Tcl 静态包注册和 Autotools 构建期依赖。因宽词有命中，本条不宣称 SQLite 主题零命中；下面逐条给出机制边界与反证命令。


| 条目 | 已覆盖机制 | 本条边界与可执行反证 |
|---|---|---|
| E236 | 静态 Conan 依赖中的 Libtool `.la` 元数据导致链接路径或归档成员异常 | 该条发生在 Libtool/链接阶段；本条可用 Python `import sqlite3` 与 `sqlite3.connect(":memory:")` 独立验证，不经过 Libtool。 |
| E280 | OHOS 静态 Tcl 未注册 Thread 子解释器包 | 该条涉及 Tcl package registry；Python 检查命令不启动 Tcl，也不触达其 Thread 注册。 |
| E524 | Autotools 构建期共享 prefix 污染及 configure 所需 SQLite3 等依赖缺失 | 该条检查 C 构建期查找与 configure；本条检查运行期 CPython `_sqlite3` 扩展。即使 C 项目已找到 SQLite3，仍须用消费者 Python 执行 `import sqlite3` 与连接检查。 |

复核命令：

```sh
git ls-tree -r --name-only 9b028fd5bd2887ead685d55a6a6a179e3e1c9683 -- knowledge/graph | grep -cE 'knowledge/graph/E[0-9]{3}\.kv$'
git grep -il -e '_sqlite3' -e 'sqlite3.connect' -e 'CPython sqlite3 extension' -e 'import sqlite3' 9b028fd5bd2887ead685d55a6a6a179e3e1c9683 -- knowledge/graph knowledge/doc
git grep -il 'sqlite3' 9b028fd5bd2887ead685d55a6a6a179e3e1c9683 -- knowledge/graph knowledge/doc
git grep -il '_sqlite3' 9b028fd5bd2887ead685d55a6a6a179e3e1c9683 -- knowledge/graph knowledge/doc
python3 -c 'import sqlite3; c=sqlite3.connect(":memory:"); assert c.execute("select 1").fetchone()==(1,)'
```

## 证据

- 上游源码：<https://github.com/thp/minidb>；PyPI sdist `minidb-2.0.8.tar.gz`，SHA-256：`d985748753cc19c2bed83654b77dd0f2212cfa82de7b8fbc8fe5f6058c2c661c`。
- 任务：MAIN minidb 2.0.8，任务 #8883，分支 `feat/minidb-2.0.8`。
- HarmonyOS PC：`conan create` exit 0；上游 pytest 42/42；消费者 3/3（10 条断言，且确认模块来自 Conan 安装路径）。
- 独立语料：CPython 3.14.7 `Lib/test/test_sqlite3`，510 项中 506 pass、4 skip、0 fail/error；设备任务日志：`~/work/psj/minidb8883/cpython-sqlite3-unittest.log`。
- CI #67998 未进入 git clone 或 Conan：worker-prep 与 git-clone 日志都明确为 SSH bridge `Connection refused`。它不能证明上游源码 URL 不可达；不据此修改官方 PyPI sdist URL。

## 元信息

- 作者：iKalous_OscarP
- contributor_id：328
- 草稿标记：`draft: true`

