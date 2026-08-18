# gitdb 4.0.12 适配笔记

## 基本信息

- **名称**: gitdb
- **版本**: 4.0.12
- **许可证**: BSD-3-Clause
- **上游**: https://github.com/gitpython-developers/gitdb
- **类型**: 纯 Python 包（Git 对象数据库）

## 依赖关系

- **上游依赖**: `smmap>=3.0.1,<6`（声明为 Conan requirement: `smmap/5.0.3`）
- **下游消费者**: GitPython（GitPython 要求 `gitdb>=4.0.1,<5`）

## 构建方式

采用 `pip install --target --no-deps` 方式构建纯 Python 包：

```bash
python -m pip install --no-deps --target="{install_target}" "{source_folder}"
```

- `--no-deps`: smmap 由 Conan 依赖管理，不通过 pip 安装
- `--target`: 安装到构建目录的 install 子目录
- 使用 `sys.executable` 确保调用正确的 Python 解释器

## 包信息暴露

通过 `runenv_info.prepend_path("PYTHONPATH", python_path)` 将包路径注入运行时环境。
下游包（如 GitPython）可通过 PYTHONPATH 找到 gitdb，同时 gitdb 的 Conan 依赖声明
确保 smmap 的 PYTHONPATH 也被正确传递。

## 验证

- `conan create` 成功构建
- test_package 验证 `import gitdb` 和版本号
