# DRAFT-multipledispatch-python-require-conan-staging

## 问题

`multipledispatch` 是纯 Python 包，没有 native 扩展和运行时依赖。目标
Conan Python 只提供解释器和 Conan 自身能力，不提供
`setuptools.build_meta`。直接执行 pip 或 setuptools 构建会在
`BackendUnavailable: Cannot import 'setuptools.build_meta'` 处失败。

## 诊断

上游 `setup.py` 的作用是生成安装元数据，运行时真正需要的是
`multipledispatch/` 下的 Python 源文件。该包没有编译步骤，强行引入
完整 Python 构建链会扩大依赖闭包，也不能改善 OHOS 运行时能力。

## Conan 方案

配方声明：

```python
package_type = "python-require"
requirements()  # no runtime requirements
```

构建阶段：

1. 校验 sdist 中的 `multipledispatch/`；
2. 将包目录复制到 build 私有的 `python-stage/multipledispatch`；
3. 若存在则同时复制 `multipledispatch.egg-info`；
4. 用目标 Python 执行 API smoke；
5. 执行官方上游功能测试。

打包阶段将 staging 复制到：

```text
lib/python3.12/site-packages/
```

`package_info()` 通过 `runenv_info.prepend_path("PYTHONPATH", site)`
把安装位置发布给下游消费者。版本目录和 staging 都属于配方私有路径，
不污染系统 Python。

## 为什么不调用 pip

- 目标解释器缺失 setuptools build backend；
- 纯 Python 包无需编译 wheel；
- pip 可能把构建依赖误带入运行时；
- 直接复制可以精确控制最终包内容；
- 消费者测试仍能验证真实导入和分派行为。

## 验证

本机 `conan create` 在 Linux host 设置下完成 source、build、package。
构建日志包含上游功能测试结果：

```text
upstream functional tests: 62 passed, 0 failed
```

之后用生成包的 `site-packages` 运行消费者测试，验证 Conan 环境变量和
实际导入路径都有效。

## 适用边界

该方案仅适用于没有 native 扩展、没有需要执行安装脚本的纯 Python 包。
若包含 Cython、Rust/PyO3、平台动态库或 install-time code generation，
必须重新分析 ABI、工具链和 wheel/源码构建边界。

## 查重结论

本草稿聚焦目标 Conan Python 缺少 setuptools backend 时的纯 Python
`python-require` 打包和消费者路径；不替代 Python 包的一般依赖检查。

## 关联文件

- `archives/m/multipledispatch/1.0.0/conanfile.py`
- `archives/m/multipledispatch/1.0.0/test_package/conanfile.py`
