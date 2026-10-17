# iniconfig 2.3.0 适配笔记（HarmonyOS PC / OHOS armv8）

## 一、软件定位与选型理由

`iniconfig` 是 pytest 的**运行时依赖**（`Requires-Dist: iniconfig>=1.0.1`），
负责解析 ini 风格配置。本仓库引入它的目的不是给终端用户用，而是补齐
pytest 的依赖闭包，使**依赖 pytest 驱动的上游测试套件**（如
`xkeyboard-config` 的 `tests/`）能在 CI 环境中真实执行，而不是因缺
pytest 被静默跳过。

纯 Python、无 C 扩展、无 ELF 产物，因此不涉及 OHOS 签名要求
（对比 Qt/rust 类包必须 `binary-sign-tool sign`）。

## 二、源码与校验

| 项 | 值 |
|---|---|
| 上游 | https://github.com/pytest-dev/iniconfig |
| 版本 | 2.3.0 |
| sdist | `iniconfig-2.3.0.tar.gz` |
| URL | `https://files.pythonhosted.org/packages/72/34/14ca021ce8e5dfedc35312d08ba8bf51fdd999c576889fc2c24cb97f4f10/iniconfig-2.3.0.tar.gz` |
| sha256 | `c76315c77db068650d49c5b56314774a7804df16fee4402c1f19d6d15d8c4730` |
| 许可 | MIT |

sha256 取自 PyPI JSON API（`https://pypi.org/pypi/iniconfig/2.3.0/json` 的
`digests.sha256`），并在本机下载后复算比对一致。

## 三、构建方式

采用 `python-require` 包型 + **直接铺模块树**（同 `python3-rdflib/7.1.4`
与 `packaging/26.3` 的既有范式）：

1. `source()`：解压官方 sdist（`strip_root=True`）。
2. `build()`：把 `src/iniconfig/` 复制到
   `staging/lib/pythonX.Y/site-packages/iniconfig/`，并生成
   `iniconfig-2.3.0.dist-info/{METADATA,top_level.txt}`。
3. `package()`：整树复制进 `package_folder/lib/pythonX.Y/site-packages/`。
4. `package_info()`：同时经 `buildenv_info` 与 `runenv_info` 注入
   `PYTHONPATH`。

### 为什么不走 setuptools 构建

上游 `pyproject.toml` 声明：

```toml
[build-system]
requires = ["setuptools>=77", "setuptools-scm>=8"]
```

本机 Python 3.12.8 自带 `setuptools 75.6.0`（< 77），且未安装
`setuptools_scm` / `wheel`；若在配方内 `pip install .`，pip 会联网拉取
build backend（在没有构建隔离或网络受限的环境下即失败）。而 sdist 中
**已烘焙** `src/iniconfig/_version.py`：

```python
__version__ = version = '2.3.0'
```

即版本号不依赖 setuptools-scm 现场推断，因此直接铺模块树即可得到与
`pip install` 等价的产物，同时把构建依赖降到零。

## 四、上游测试的真实执行

`build()` 中调用 `_run_upstream_tests()`：

1. 用 `sys.executable -m pip install --target=<build>/test-deps pytest==9.1.1`
   自举一个**构建期** pytest（同 `pluggy/1.6.0` 的做法）——不能在
   `build_requirements()` 里声明 pytest，否则形成循环依赖
   （pytest → iniconfig → pytest）。
2. 以 `PYTHONPATH = staging:src:test-deps` 执行
   `pytest testing/ -q --no-header -p no:cacheprovider --basetemp=...`。
   staging 置前，确保测的是**将要打包的那份**，而不是 pip 顺带拉进来的副本。
3. 若自举失败，输出具名 warning 说明"上游套件未执行、这是覆盖率下降而非
   通过"，而不是静默跳过。

上游用例规模：`testing/test_iniconfig.py` 共 31 个 `def test_`。

## 五、运行期要求

- 消费方 Python 版本需与打包时的 `X.Y` 一致（本包铺在
  `lib/python3.12/site-packages`）。
- 依赖经 `PYTHONPATH` 供给（Conan 的 `buildenv_info`/`runenv_info`）；
  OHOS loader 忽略 DT_RUNPATH 的限制在这里不适用，因为纯 Python 无动态库。
