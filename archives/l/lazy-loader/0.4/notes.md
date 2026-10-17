# lazy-loader 0.4 适配笔记（HarmonyOS PC / OHOS armv8）

## 一、软件定位与选型理由

`lazy_loader` 是 scientific-python 的**按需加载**工具库（SPEC 1，基于 PEP 562
模块级 `__getattr__`），让包可以推迟子模块/函数的导入时机。它是 scikit-image
的运行时依赖，也是 spclean 等科学计算包的构建期辅助，属于科学计算栈的
基础件。本仓库引入它补齐 Python 科学计算依赖链（matplotlib/numpy 已在库，
scikit-image 链条的缺口之一）。

纯 Python、无 C 扩展、无 ELF 产物，不涉及 OHOS 签名要求。

## 二、源码与校验

| 项 | 值 |
|---|---|
| 上游 | https://github.com/scientific-python/lazy_loader |
| 版本 | 0.4 |
| sdist | `lazy_loader-0.4.tar.gz` |
| URL | `https://files.pythonhosted.org/packages/6f/6b/c875b30a1ba490860c93da4cabf479e03f584eba06fe5963f6f6644653d8/lazy_loader-0.4.tar.gz` |
| sha256 | `47c75182589b91a4e1a85a136c074285a5ad4d9f39c63e0d7fb76391c4574cd1` |
| 许可 | BSD-3-Clause |

sha256 取自 PyPI JSON API，并在本机下载后复算比对一致。

## 三、构建方式

采用 `python-require` 包型 + **直接铺模块树**（同 packaging/26.3、
iniconfig/2.3.0、attrs/26.1.0 的既有范式）：

1. `source()`：解压官方 sdist（`strip_root=True`）。
2. `build()`：把顶层 `lazy_loader/`（sdist 为平铺布局，无 src/）复制到
   `staging/lib/python3.12/site-packages/lazy_loader/`，并生成
   `lazy_loader-0.4.dist-info/{METADATA,top_level.txt}`。
3. `package()`：整树复制进 `package_folder/lib/python3.12/site-packages/`。
4. `package_info()`：同时经 `buildenv_info` 与 `runenv_info` 注入
   `PYTHONPATH`。

### 为什么不走 setuptools 构建

上游 `pyproject.toml` 声明 `setuptools>=61.2`。sdist 中版本号已烘焙进
`lazy_loader/__init__.py`（`__version__ = "0.4"`），不依赖构建期现场推断，
直接铺模块树即可得到与 `pip install` 等价的产物，同时把构建依赖降到零。
wheel 内容比对确认：官方 wheel 装出来就是 `lazy_loader/` 模块树 +
dist-info，与 staging 产物一致（wheel 还把 `lazy_loader/tests/` 一并带入，
本配方照做，上游测试资源随包分发）。

### 运行时依赖

`Requires-Dist: packaging`——`packaging.requirements` 在 `_check_requirement()`
内**惰性导入**（`load(..., require=...)` / `attach_stub()` 的规格校验路径），
模块顶层导入不需要它。配方以 `requires("packaging/26.3", run=True)` 声明，
保证消费方 PYTHONPATH 链完整（run=True 的传播语义见 pytest/9.1.1 配方
的实测注释：不加则依赖进 "Skipped binaries"，runenv 到不了消费方）。

## 四、上游测试的真实执行

`build()` 中调用 `_run_upstream_tests()`：

1. 用 `sys.executable -m pip install --target=<build>/test-deps pytest==9.1.1`
   自举构建期 pytest（同 iniconfig/2.3.0 的做法）——不能在
   `build_requirements()` 里声明 pytest，否则形成循环依赖
   （pytest → … → lazy-loader → pytest 的潜在环路）。
2. 以 `PYTHONPATH = staging:test-deps:packaging包site` 执行
   `pytest lazy_loader/tests/ -q --no-header -p no:cacheprovider --basetemp=...`。
   staging 置前，确保测的是将要打包的那份（测试就在模块树内部）。
3. 若自举失败，输出具名 warning 说明"上游套件未执行、这是覆盖率下降而非
   通过"，而不是静默跳过。

上游用例规模：`lazy_loader/tests/test_lazy_loader.py` 共 11 个 `def test_`。
其中 numpy 相关用例（test_lazy_import_impact_on_sys_modules、
test_lazy_import_nonbuiltins、test_parallel_load）走 `pytest.importorskip`
或软路径，numpy 缺席时为 skip 而非 fail。

### 平台环境注意（HMDFS）

pytest 套件的 `tmp_path` fixture 在用户 home（HMDFS）上会因目录属主问题
报错、`/tmp` 只读——`--basetemp` 优先选 `TMPDIR`（排除 home 下路径）、
`/data/storage/el2/base/cache`、build 目录兜底（同 pytest/9.1.1 配方的
`_suite_tmpdir` 顺序）。

## 五、test_package 消费者断言

`test_package/test_lazy_loader.py` 共 26 项断言：来源校验（防 user-site
副本假通过）+ 模块完整性（0.4 版本/__all__/tests 资源/dist-info）+
load() 真加载与 sys.modules 登记 + DelayedImportErrorModule 延迟报错语义
+ attach() 的 PEP 562 惰性装配 + attach_stub() 的 .pyi AST 解析。
脚本以 `env="conanrun"` 运行，消费方视角的 PYTHONPATH 即打包树。

## 六、运行期要求

- 消费方 Python 版本需与打包时的 `X.Y` 一致（本包铺在
  `lib/python3.12/site-packages`）。
- 依赖经 `PYTHONPATH` 供给（Conan 的 `buildenv_info`/`runenv_info`）；
  纯 Python 无动态库，不涉及 OHOS loader 的 DT_RUNPATH 限制。
