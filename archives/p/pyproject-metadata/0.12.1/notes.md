# pyproject-metadata 0.12.1 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（无编译）
- **编译日期**: 2026-09-29
- **Python**: 3.12（OHOS 环境）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 为什么需要这个包
`pyproject-metadata` 是 **meson-python** 的运行时依赖
（`meson-python` 的 `requires_dist` 实测含 `pyproject-metadata>=0.9.0`）。
而 meson-python 是 `scipy` / `scikit-learn` 的构建后端（两者均
`build-backend = 'mesonpy'`）。故本包是 sklearn 栈的关键路径一环。

## 包结构
sdist `pyproject_metadata-0.12.1.tar.gz`（48,457 bytes）解包后含：
`pyproject_metadata/`（包本体：`__init__.py`、`_dispatch.py`、
`constants.py`、`errors.py`、`project_table.py`、`pyproject.py`、`py.typed`）、
`tests/`、`docs/`、`pyproject.toml`、`LICENSE`、`README.md`。

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/pyproject-metadata/0.12.1 --build=missing
```

### 1. 源码获取（source()）
`download()` 下载 PyPI sdist，`tar -xzf --no-same-owner` 解包后
`cp -a` 把内容提到 source_folder 根。

**关键**：必须带 `--no-same-owner`（hmdfs 属主与构建 UID 不一致，
同 packaging/ply/inn2 教训）。

### 2. 打包（package()）
纯 Python noarch——`shutil.copytree` 拷贝 `pyproject_metadata/`
（含 `py.typed`）到 `lib/python3.12/site-packages/`；
`env_info.PYTHONPATH` 暴露导入路径。

### 3. 上游测试（build() 集成——R51 实测回填）
sdist 自带 `tests/`（pytest 风格，`testpaths = ["tests"]`），实跑：

```bash
PYTHONPATH=<src> python3 -m pytest tests -q --no-header \
  -p no:cacheprovider --basetemp=<可写目录>
```

**实测结果（2026-09-29，OHOS Python 3.12.9）**：
```
318 passed, 88 skipped in 1.31s
```

**跳过项根因（环境差异，非配方缺陷）**：88 个 skipped 全部来自
`tests/test_standard_metadata.py` 的 4 处 SKIP 入口（行 51 / 918 /
1106 / 1541），原因均为
`exceptiongroup is not installed`——该测试辅助依赖未安装。
上游把相关用例标为可跳过（`pytest.importorskip` 语义），属**设计内的
条件跳过**，不是失败。如需 100% 覆盖，可在本地 pip 安装 `exceptiongroup`；
CI 上配方内不额外装测试辅助依赖（同 packaging 处理口径），如实记录。

## 依赖
- 运行时/构建期：`packaging`（本包 `requires("packaging/26.3")`；
  上游 `pyproject.toml` 实测 `dependencies` 含 packaging 约束）

## 注意事项
1. 纯 Python 包不需要 `commands.json`（R38：库包误加反而会被拦）。
2. 上游构建后端是 `flit-core`，但**无需为它建 Conan 包**——
   本包走「直接拷贝模块到 site-packages」路线（同 packaging 先例），
   不触发后端构建（该路线已验证，见 packaging/26.3）。
3. 目录名用连字符 `pyproject-metadata`（PyPI 分发名），导入名是下划线
   `pyproject_metadata`——两者不同，写测试时不要混。
