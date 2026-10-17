# catkin-pkg 1.1.0 适配笔记

## 构建

该版本是纯 Python setuptools 软件包。源码通过 `conandata.yml` 下载并校验 SHA-256；源码包包含 `setup.py` 而不包含 `pyproject.toml`，因此以当前 Python 执行：

```bash
python -m pip install --no-deps --target <build>/site-packages <source>
```

配方复制生成的 site-packages，并在 pip 生成 console scripts 时将其复制到包的 `bin`。未添加 C/C++ 依赖。

## 依赖

- docutils/0.23
- packaging/26.3
- python-dateutil/2.9.0.post0
- pyparsing/3.1.4

## 验证

上游完整测试套件使用官方 `ros-infrastructure/catkin_pkg` 1.1.0 标签源码执行，结果为 60 passed、11 warnings；PyPI sdist 遗漏 `test/util.py` 和 `test/data/`，因此报告中明确记录了测试源码来源。消费者测试直接运行当前 Python，导入 `catkin_pkg.package.parse_package_string`，解析 package XML 并校验名称和版本，以覆盖安装与 API 集成路径。

## 源码修改

无补丁。
---

**编译结束**: 2026-09-13 14:49
**最终状态**: published
