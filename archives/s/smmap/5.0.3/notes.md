# smmap 5.0.3 适配笔记

## 基本信息

- **名称**: smmap
- **版本**: 5.0.3
- **许可证**: BSD-3-Clause
- **上游**: https://github.com/gitpython-developers/smmap
- **类型**: 纯 Python 包（滑动窗口内存映射管理器）

## 依赖关系

- **上游依赖**: 无（零运行时依赖）
- **下游消费者**: gitdb（gitdb 要求 `smmap>=3.0.1,<6`）

## 构建方式

采用 `pip install --target` 方式构建纯 Python 包：

```bash
python -m pip install --no-deps --target="{install_target}" "{source_folder}"
```

- `--no-deps`: smmap 零依赖，无需安装额外包
- `--target`: 安装到构建目录的 install 子目录
- 使用 `sys.executable` 确保调用正确的 Python 解释器

## 包信息暴露

通过 `runenv_info.prepend_path("PYTHONPATH", python_path)` 将包路径注入运行时环境，下游包（如 gitdb）可通过 PYTHONPATH 找到 smmap。

## 验证

- `conan create` 成功构建
- test_package 验证 `import smmap` 和版本号
