# beniget 0.5.0 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（无编译；实测 `beniget/` 下仅 4 个 `.py`：
  `__init__.py` / `__main__.py` / `beniget.py` / `ordered_set.py` / `version.py`）
- **编译日期**: 2026-09-30
- **目标**: HarmonyOS PC（OHOS aarch64 / Python 3.12.9）

## 为什么需要这个包
`beniget` 是 **pythran 的硬依赖**（`pythran` 要 `beniget~=0.5.0`），
而 `pythran` 是 **scipy / scikit-learn** 的构建期依赖。
即：本包是 imbalanced-learn 依赖栈中
`beniget → pythran → scipy → scikit-learn → sklearn-compat → imbalanced-learn`
这条关键路径上的一环。

## 依赖声明（重要）
上游 `requirements.txt` 只有一个依赖：
```
gast >= 0.7.0
```
`gast/0.7.0` **已在 ohpcd 制品仓**，故 `requirements()` 直接 `self.requires("gast/0.7.0")`。

## 包结构
```
beniget/
  __init__.py
  __main__.py
  beniget.py
  ordered_set.py
  version.py
```
无 C/C++ 扩展 → `package_type = "python-require"`。

## 编译步骤（conan create 全流程）

### 1. 源码获取（source()）
```yaml
url: https://files.pythonhosted.org/packages/31/a9/cf7c2317da1f5034fdebe84555e14a474b3297ef2d03ad148ff02fef2e3a/beniget-0.5.0.tar.gz
sha256: e7af11fa8ec7de3d3eb3d98b1e722d15d44017d8b35d8aa11d54f6719b312f22
size: 37097
```
实测下载并校验 sha256 一致。解包后 `cp -a beniget-0.5.0/. .`。

> `--no-same-owner`：hmdfs 上归档属主与构建 UID 不一致（同 packaging 教训）。

### 2. 打包（package()）
纯 Python noarch——`shutil.copytree` 拷贝 `beniget/` 到
`lib/python3.12/site-packages/beniget`；以
**`runenv_info.append_path("PYTHONPATH", …)`** 暴露导入路径
（**不是** `env_info`——后者是 Conan 1.x 遗留，2.x 下只告警不生效）。

### 3. 上游测试（build() 集成——R51 实测回填）
sdist 自带 `tests/`（6 个测试文件），pytest 风格：

```bash
PYTHONPATH=<src>:<gast site-packages> python3 -m pytest tests -q \
  --no-header -p no:cacheprovider --assert=plain -rs --basetemp=<可写目录>
```

**实测结果（2026-09-30，OHOS Python 3.12.9 / pytest 9.1.1）**：
```
562 passed in 1.88s
```
**562/562 = 100%**（采集 562，0 failed / 0 skipped / 0 error）。

测试文件构成：
| 文件 | 内容 |
|---|---|
| `tests/test_attributes.py` | 属性访问分析 |
| `tests/test_capture.py` | 闭包捕获分析 |
| `tests/test_chains.py` | def-use 链 |
| `tests/test_definitions.py` | 定义提取 |
| `tests/test_doc.py` | **doctest**（README/文档示例） |
| `tests/test_ordereed_set.py` | OrderedSet（注意上游文件名拼写 "ordereed"） |

## 注意事项
1. 纯 Python 包不需要 `commands.json`（R38：库包误加反而会被拦）。
2. **必须**在 `PYTHONPATH` 中包含 `gast` 的 site-packages——beniget 运行期
   `import gast`，缺它即 `ModuleNotFoundError`（`package_info()` 也已一并
   追加 gast 路径，保证消费侧可用）。
3. `tests/test_doc.py` 是 **doctest** 套件——若上游 README 中示例变更，
   该文件用例数会随之变化，回填时需重新采集。
4. 上游版本文件叫 `version.py`（非 `_version.py`），`setup.py` 从中读
   `__version__`；本配方不执行 `setup.py`（直拷贝），故与此无关。
