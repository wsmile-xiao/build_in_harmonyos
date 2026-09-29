# gast 0.7.0 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（无编译）
- **编译日期**: 2026-09-29
- **Python**: 3.12（OHOS 环境）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 为什么需要这个包
`gast` 是 **pythran** 的运行时/构建期依赖（pythran 的 `requires_dist`
实测含 `gast~=0.7.0`），而 pythran 是 **scipy** 的构建期依赖
（scipy `pyproject.toml` 的 `requires` 含 `pythran>=0.14.0`）。
故本包是 sklearn 依赖栈关键路径的一环（scipy → pythran → gast）。

同时 `beniget`（pythran 的另一个前置）也依赖 `gast>=0.7.0`——
本包可被两者共用。

## 包结构
sdist `gast-0.7.0.tar.gz`（33,630 bytes）解包后含：
`gast/`（包本体：`__init__.py`、`ast2.py`、`ast3.py`、`astn.py`、
`gast.py`、`unparser.py`、`version.py`）、`tests/`（含 fuzz）、
`setup.py`、`setup.cfg`、`LICENSE`、`README.rst`。

## 编译步骤（conan create 全流程）

```bash
conan create archives/g/gast/0.7.0 --build=missing
```

### 1. 源码获取（source()）
`download()` 下载 PyPI sdist，`tar -xzf --no-same-owner` 解包后
`cp -a` 把内容提到 source_folder 根。

**关键**：必须带 `--no-same-owner`（hmdfs 属主与构建 UID 不一致，
同 packaging/ply/cython 教训）。

### 2. 打包（package()）
纯 Python noarch——`shutil.copytree` 拷贝 `gast/` 到
`lib/python3.12/site-packages/gast`；`env_info.PYTHONPATH` 暴露导入路径。

### 3. 上游测试（build() 集成——R51 实测回填）
sdist 自带 `tests/`（pytest 风格），实跑：

```bash
PYTHONPATH=<src> python3 -m pytest tests -q --no-header \
  -p no:cacheprovider --basetemp=<可写目录>
```

**实测结果（2026-09-29，OHOS Python 3.12.9）**：
```
64 passed in 1.33s
```

全部通过，无跳过、无失败。

## 版本说明
`gast 0.7.0` 的 `setup.py` 声明 `python_requires='>=2.7, !=3.0.*, ...'`
（历史遗留的宽范围声明），实际在 Python 3.12 上功能正常
（上游测试 64 passed 实测）。

## 注意事项
1. 纯 Python 包不需要 `commands.json`（R38：库包误加反而会被拦）。
2. 上游构建后端是 `setuptools`（`setup.py`）——**无需为它建 Conan 包**，
   本包走「直接拷贝模块到 site-packages」路线（同 packaging 先例）。
3. 导入名与包名一致（都是 `gast`），无连字符/下划线转换问题。
