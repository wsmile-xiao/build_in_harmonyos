# catkin-pkg 1.1.0 测试报告

## 上游测试

- 命令：`PYTHONPATH=src:. python3 -m pytest -q`
- 测试源码：官方 `ros-infrastructure/catkin_pkg` 1.1.0 标签源码（含 sdist 遗漏的 `test/util.py` 与 `test/data/`）
- 结果：`60 passed, 11 warnings`
- 覆盖：上游 13 个测试文件全部执行，无失败。

## Conan 消费者测试

- 文件：`test_package/test_consumer.py`
- 命令：Conan `conan create` 自动调用 Python subprocess
- 结果：通过
- 内容：从打包 site-packages 导入 `catkin_pkg.package.parse_package_string`，解析 package XML 并断言名称与版本。

## 结果

上游完整 pytest 套件与真实消费者导入/API 集成测试均通过。
