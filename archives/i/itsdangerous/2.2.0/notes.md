# itsdangerous 2.2.0 适配笔记

## 概述

itsdangerous 是 Pallets 的数据签名/序列化库，提供 `Signer`、`TimestampSigner`、
`Serializer` 及 URL 安全/带时限的变体，是 **Flask 2.2+ 的必需依赖**。

- 上游：https://github.com/pallets/itsdangerous
- 版本：2.2.0
- 构建系统：无（纯 Python 包，直接拷贝到 site-packages）
- 许可：BSD-3-Clause
- 编译日期：2026-09-16
- 状态：built

## 依赖

**无运行时依赖**（sdist 的 `pyproject.toml` 未声明 `dependencies`，实测确认）。

上游 `[build-system]` 用 **flit_core**：

```toml
requires = ["flit_core<4"]
build-backend = "flit_core.buildapi"
```

**但本配方完全不调用 PEP 517 构建**——与仓内其他 Python 包
（markupsafe / requests / docopt）一致，只把可导入的 `itsdangerous/` 目录
拷贝进 `site-packages`。因此**不需要 `build_requires`**，也就避开了
`flit_core` / `setuptools`（ohpcd 均未发布）是否可用的前置问题。

## 交付形态

纯 Python，交付 8 个文件：

```
__init__.py  _json.py  encoding.py  exc.py  py.typed
serializer.py  signer.py  timed.py  url_safe.py
```

## 关于 `__version__`（消费者测试刻意不断言）

上游 `__init__.py` 用模块级 `__getattr__` **懒解析** `__version__`：

```python
def __getattr__(name: str) -> t.Any:
    if name == "__version__":
        import importlib.metadata
        warnings.warn("The '__version__' attribute is deprecated ...", DeprecationWarning)
        return importlib.metadata.version("itsdangerous")
    raise AttributeError(name)
```

`importlib.metadata.version()` 会遍历 `sys.path` 找 `itsdangerous-*.dist-info`
目录——**本打包只交付可导入的包目录、不含 `.dist-info`**，故该调用会抛
`PackageNotFoundError`。

这是**打包形态的事实**，不是 API 契约缺陷（`.dist-info` 属 wheel 安装产物，
源码包直拷模式本就不带）。因此消费者测试**刻意不碰 `__version__`**，
改为断言真正的公开 API 行为。同理，markupsafe 3.0.3 的 `__version__` 虽可用，
也是走同一弃用路径（已在其测试中用 `warnings.catch_warnings` 静默）。

## 上游测试

`tests/test_itsdangerous/` 随 sdist 提供，5 个测试文件：

| 文件 | test 数 |
|---|---|
| `test_encoding.py` | 4 |
| `test_serializer.py` | 13 |
| `test_signer.py` | 11 |
| `test_timed.py` | 9 |
| `test_url_safe.py` | 0（辅助，用例复用 serializer 的）|

纯 Python 包、无 C 扩展，故**无 skipif 平台分支**（对照 markupsafe 需跳过
`_speedups` 组）。

`build()` 内以 `subprocess` 调 pytest 并回填真实通过率（R51），环境处理沿用
既有结论：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`（宿主 pytest 插件与 py3.12
不兼容）+ `--assert=plain`（断言重写钩子与 py3.12 字节码不兼容）。

## 消费者测试（test_package）

`test_package/test_itsdangerous.py`，全部为真实 API 断言（R34）：

| 组 | 断言 |
|---|---|
| Signer 往返 | `sign` / `unsign` 往返值正确；token 恰含 1 个 `.` 分隔符 |
| **篡改检测** | 追加字符 → `BadSignature`；**换密钥** → `BadSignature`（两条独立路径）|
| 过期 | `TimestampSigner.unsign(max_age=-1)` → `SignatureExpired` |
| 序列化往返 | `Serializer`（dict / list）、`URLSafeSerializer`、`TimedSerializer`、`URLSafeTimedSerializer` |
| URL 安全性 | 输出字符集 ⊆ base64url + `.`/`=`（证明 URL 安全变体名副其实）|
| 坏输入 | 垃圾 token → `BadData`/`BadSignature` |
| 编码助手 | `base64_encode`/`base64_decode` 往返、`want_bytes` 的 bytes/str 两分支 |

## 验证结果

```
conan create archives/i/itsdangerous/2.2.0 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
→ exit=0
```

| 项 | 实测结果 |
|---|---|
| `conan create` | **exit=0**，Package created |
| 上游 pytest | **297 passed in 1.37s**（**0 skipped、0 failed**）|
| skip 说明 | 纯 Python 包无 C 扩展，不存在 markupsafe 那样的 `_speedups` 平台分支，故无跳过 |
| 消费者测试 | `itsdangerous consumer API: PASS`（7 组断言全过）|

## 注意事项

1. **不要为 flit_core 加 `build_requires`**——本配方不走 PEP 517 构建；
2. **不要在测试里断言 `__version__`**——需要 `.dist-info`，本打包形态不含；
3. `--assert=plain` 必需（本机 pytest 5.4.3 的断言重写与 py3.12 不兼容）。
