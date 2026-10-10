# minidb 2.0.8（HarmonyOS PC）

minidb 是纯 Python 单模块对象存储，使用 Python `sqlite3` 标准库连接 SQLite 3。此 Conan 包只安装上游的 `minidb.py`，不构建扩展，也不把 SQLite 作为独立 Conan 依赖；运行时由消费者使用的 Python 提供 `sqlite3`。

- 上游：<https://github.com/thp/minidb>，固定 PyPI sdist `minidb-2.0.8.tar.gz`。
- Conan `package_type` 使用 `unknown`，将纯 Python 模块作为可安装的运行时包；不能使用 `python-require`，该类型只导出配方代码，不创建运行时包，也不会执行 `build()`。
- 运行时无 Conan 依赖；`pytest/9.1.1` 仅为配方 `tool_requires` 构建工具，版本级 manifest 的 `build.tool_requires` 与实际配方一致。
- HarmonyOS PC 真机：OHOS aarch64，Conan 2.29.1，Python 3.14.7；配方通过 `tool_requires = "pytest/9.1.1"` 固定上游测试运行器，从 Conan 构建依赖包目录发现 pytest 及其依赖的 `site-packages`，不依赖构建机预装 pytest。
- 修复检视指出的宿主环境隐式依赖后，使用隔离 `CONAN_HOME=~/work/psj/ch-minidb`、关闭 conancenter 并启用 ohpcd 远端，且未设置外部 `PYTHONPATH`，重新执行 `conan create ... --build='minidb/*'`：退出码 0。`build()` 对原始 `test/test_minidb.py` 先校验 pytest 收集数，再跑完整上游套件：收集 42/42，42 passed、0 failed、0 errors、0 skipped。
- `test_package` 由 Conan `test()` 使用 `sys.executable` 并加载 `conanrun` 环境，在 Python 3.14.7 中确认导入的是 Conan 安装路径里的 `minidb.py`，再验证 `sqlite3.connect(":memory:")` 的真实 SQL 往返、minidb 内存对象往返及文件数据库重开：3/3 测试、10 条断言全部通过。MANIFEST 命令和配方入口保持一致。
- Pytest 依赖路径通过遍历每个 Conan 构建依赖的 `lib/` 查找全部 `site-packages` 目录，不假定 Python 版本目录固定在单层结构；上游跳过项仍按未通过处理，保持声明的 42 项全部实跑通过这一门槛。
- 独立通用性验证运行 CPython 3.14.7 自带 `Lib/test/test_sqlite3`：510 项中 506 通过、4 项因上游声明的 4–8 GiB 内存门槛跳过、0 失败、0 错误；此独立语料不计入 minidb 的上游/消费者测试统计。
