# DRAFT-multipledispatch-upstream-consumer-test-boundary

## 知识类型

这是 `multipledispatch 1.0.0` 的路径 B 测试证据草稿，专门记录
Python 纯包在发布 sdist 与官方 Git 仓库测试不一致时，如何分别给出
上游测试和 Conan 消费者测试证据。

## 现象

PyPI `multipledispatch-1.0.0.tar.gz` 包含运行时包和 setuptools 元数据，
但不包含 `multipledispatch/tests/`。如果只检查 sdist，容易把上游测试
误报为 0；官方 `1.0.0` 标签实际包含以下 6 个测试文件：

```text
multipledispatch/tests/test_benchmark.py
multipledispatch/tests/test_conflict.py
multipledispatch/tests/test_core.py
multipledispatch/tests/test_dispatcher.py
multipledispatch/tests/test_dispatcher_3only.py
multipledispatch/tests/test_variadic.py
```

## 根因与边界

发布物是面向安装的最小 sdist，Git 仓库标签则包含开发测试。两者都是
上游事实，但不能混成一个测试分母：

1. 上游测试分母取官方标签的测试文件和 pytest 收集结果。
2. 消费者测试分母取 Conan 生成包之后，独立消费者导入并调用 API 的断言。
3. benchmark 文件中的功能断言可以纳入功能回归，但目标环境不具备
   `pytest-benchmark` 时不能伪称完成性能基准。

## 适配方案

本配方把官方标签的 6 个测试文件放在版本目录的 `upstream_tests/` 下，
作为构建期测试源导出，不复制到最终 `site-packages`。构建阶段执行
`run_upstream_tests.py`：

- 保留官方测试函数和参数化数据；
- 用最小 pytest 装饰器替身支持 `pytest.mark.parametrize`；
- 用一次调用的 benchmark fixture 保留 benchmark 用例的功能断言；
- 按源文件定义顺序执行，避免 `test_core.py` 的共享命名空间受到
  非 pytest 执行顺序影响；
- 任意上游测试失败都使 `build()` 失败。

本机额外使用真实 pytest 运行官方测试，收集 62 项并全部通过。Conan
构建使用不依赖 pytest 的执行器，仍执行同一组 62 个功能用例。

## 消费者测试

`test_package/test_multipledispatch.py` 在生成的 Conan 包上独立运行，
覆盖：

- distribution metadata 版本为 `1.0.0`；
- 模块内上游 `__version__` 的事实值；
- `int` 和 `str` 的多分派；
- `Dispatcher.add` 注册和调用；
- 未注册签名抛出 `NotImplementedError`。

这组测试证明下游通过 Conan `PYTHONPATH` 能真正导入并使用打包产物，
不能由上游测试替代。

## 验证证据

```text
官方 pytest：62 passed
Conan build runner：upstream functional tests: 62 passed, 0 failed
消费者测试：7 项断言通过
```

## 适用边界

该方法适用于 Python 纯包、运行时不需要 pytest、但上游测试是 pytest
格式的场景。若上游测试依赖数据库、网络服务、真机能力或复杂 pytest
插件，必须分别记录未接入原因，不能用轻量执行器掩盖环境缺失。

## 查重结论

本草稿聚焦 `multipledispatch` 的 sdist/官方标签测试分母差异，以及同一
配方内上游测试和消费者测试的证据边界；不替代通用 Conan `test_package`
规则。

## 关联文件

- `archives/m/multipledispatch/1.0.0/conanfile.py`
- `archives/m/multipledispatch/1.0.0/upstream_tests/`
- `archives/m/multipledispatch/1.0.0/test_package/test_multipledispatch.py`
