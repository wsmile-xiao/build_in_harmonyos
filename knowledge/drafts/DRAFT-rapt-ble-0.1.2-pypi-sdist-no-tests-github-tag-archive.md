# DRAFT: PyPI sdist 不含 tests/ → 改用 GitHub 官方 tag archive（sha256 固定）接入上游 pytest

- **条目主题**：上游 PyPI sdist 未打包 `tests/` 时，source 改用 GitHub 官方 tag archive
  （tag 名带 `v` 前缀，sha256 固定），否则 test_package 无法接入上游测试套件。
- **状态**：草稿（待知识库主编审核，拟提升编号 Exxx）
- **关联**：rapt-ble 0.1.2 适配（archives/r/rapt-ble/0.1.2，PR 待提）
- **同型/相邻条目**：E466（init-build 嵌套源码提升误判 `docs/`，同属"Python 源码包布局陷阱"）、
  DRAFT-tinydb-4.8.2-pypi-sdist-test-inventory（wheel vs sdist 测试清点）、
  DRAFT-python-sdist-missing-test-helper（sdist 缺测试辅助文件 → 固定 tag raw 取回）

## 适用场景

纯 Python 包适配（`package_type = "python-require"` / pip staging 配方），想在
`test_package` 里跑**上游自带测试套件**作为行为基线时。典型信号：

- `python3 -m pytest tests/` → `ERROR: file or directory not found: tests`。
- sdist 列表里只有 `LICENSE / README / pyproject.toml / src/...`，没有 `tests/`。
- 直接拼 `.../archive/refs/tags/<ver>.tar.gz` 得到 404（上游 tag 名带 `v`）。

## 诊断步骤

```bash
# 1) PyPI sdist 到底有没有 tests/
python3 -m pip download rapt-ble==0.1.2 --no-deps --no-binary :all: -d $HOME/tmp/sdist-check
tar tzf $HOME/tmp/sdist-check/rapt_ble-0.1.2.tar.gz
#   rapt_ble-0.1.2/LICENSE  README.md  pyproject.toml  src/rapt_ble/{__init__,parser}.py
#   src/rapt_ble/py.typed  PKG-INFO        ← 无 tests/
# 2) GitHub tag archive 里有没有
tar tzf <build>/rapt-ble-0.1.2.tar.gz | grep '/tests/'
#   rapt-ble-0.1.2/tests/__init__.py  rapt-ble-0.1.2/tests/test_parser.py
```

## 真实证据（rapt-ble 0.1.2）

| 制品 | 文件 | sha256 | 含 tests/ |
| --- | --- | --- | --- |
| PyPI sdist（镜像 `pypi.cnb.cool`） | `rapt_ble-0.1.2.tar.gz` | `7c73bf4813ba902209e9e428d5df52a08edbe28400529ad32238b12023e9562c` | ❌ 0 条 |
| GitHub 官方 tag archive（`v0.1.2`） | `rapt-ble-0.1.2.tar.gz` | `a5910820d3a2b6aab0cd01d306d442793977f61f11f7e5e276edfd0d6d7ebb28` | ✅ `tests/__init__.py`、`tests/test_parser.py` |

- 配方 `conandata.yml` 采用后者：`https://github.com/sairon/rapt-ble/archive/refs/tags/v0.1.2.tar.gz`
  （tag 名带 `v`；按 `0.1.2` 拼 URL 不命中任何 ref）。
- `test_package/tests/` 为上游 `tests/` 的**逐字节副本**
  （`test_parser.py` sha256 `e3e4cf587eb244b18dcd9d045ff555be606d615da396368eab3ea403e0680f7e`）。
- W3 本地 CI 实测：上游 pytest **7 passed**，与自写消费者断言 27/27 并存。

## 修复

```yaml
# conandata.yml
sources:
  "0.1.2":
    url: "https://github.com/sairon/rapt-ble/archive/refs/tags/v0.1.2.tar.gz"
    sha256: "a5910820d3a2b6aab0cd01d306d442793977f61f11f7e5e276edfd0d6d7ebb28"
```

```python
# conanfile.py
def source(self):
    self.get(self.conan_data["sources"][self.version]["url"], strip_root=True)
```

## 注意事项

- **tag 名要逐字核对**：本项目 tag 是 `v0.1.2`；有的项目却是 `0.1.2` 或 `rel-0.1.2`。
- GitHub archive 的根目录名是 `<repo>-<ver>`（连字符），`strip_root=True` 后与标准仓库根一致；
  与 E466 的"init-build 把 `docs/` 提升为源码根"是相邻但不同的问题（后者是本地工具启发式误判，
  建议手工 `tar --strip-components=1` 重建 `.orig/.work`）。
- sdist 与 tag archive 的 sha256 必然不同，conandata 必须写实际使用的那份。

## 推广价值

- 所有"上游测试只在 Git 仓库、不在 PyPI 制品"的纯 Python 包。
- 通用检查项：**先把 source 归档解开数一遍 `tests/`**，再决定能否接入上游套件。

## 查重关键词

PyPI sdist、sdist 不含 tests、MANIFEST.in、GitHub tag archive、`refs/tags`、tag `v` 前缀、
sha256 固定、上游 pytest、test_package/tests、`file or directory not found: tests`、
poetry/PEP 517 打包差异、E466
