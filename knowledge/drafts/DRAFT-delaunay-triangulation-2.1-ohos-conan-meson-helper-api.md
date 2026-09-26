# draft-delaunay-triangulation-2.1-ohos-conan-meson-helper-api

## 症状

delaunay-triangulation 2.1 在 OHOS 适配版 conan（2.29.1）下 `conan-verify` G2 连续两阶段失败：

1. **import 期**：
   ```
   ImportError: cannot import name 'meson_layout' from 'conan.tools.meson'
   (/storage/Users/currentUser/usr/local/lib/python3.12/site-packages/conan/tools/meson/__init__.py)
   ```
2. **build 期**（把 layout 换成 basic_layout 后）：
   ```
   AttributeError: 'Meson' object has no attribute 'compile'
   ```

## 根因

OHOS 社区适配版 conan（基线 2.29.1，来自私有 PyPI `pypi.cnb.cool`）的
`conan.tools.meson` 模块面与官方 conan 文档不一致：

```python
>>> import conan.tools.meson as m
>>> [x for x in dir(m) if not x.startswith('_')]
['Meson', 'MesonToolchain', 'helpers', 'meson', 'toolchain']   # 无 meson_layout

>>> from conan.tools.meson import Meson
>>> [x for x in dir(Meson) if not x.startswith('_')]
['build', 'configure', 'install', 'test']                      # 无 compile
```

官方 conan 标准配方模板 `from conan.tools.meson import MesonToolchain, meson_layout`
与 `meson.compile()` 在此环境不可用——这是**版本库 API 面差异**，不是配方写错。

## 修复

conanfile.py：

```python
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout   # 替代 meson_layout

def layout(self):
    basic_layout(self)

def build(self):
    apply_conandata_patches(self)
    meson = Meson(self)
    meson.configure()
    meson.build()          # 替代 meson.compile()
```

## 验证

`python3 scripts/ohc-run.py conan-verify delaunay-triangulation 2.1` → G2 PASS
（conan create：source→generate→build→install→test_package ctest 全过），
G1/G3/G4/L2/L4/L5 全过，`.ci-result.json` exit_code=0。
见 `archives/d/delaunay-triangulation/2.1/reports/conan-verify-report.md` 与
`reports/conan-create.log`（补丁 0001-meson.build.patch 已应用）。

## 适用范围与边界

- **适用**：所有在 OHOS 适配版 conan 环境编写 Meson 配方的库；遇到官方模板
  `meson_layout`/`Meson.compile` 报 ImportError/AttributeError 时，统一替换为
  `basic_layout` + `meson.build()`。
- **边界/反例**：官方 conan（非 OHOS 适配版）有 `meson_layout` 与 `compile()`，
  不可套用本方案硬改；若错误发生在 `meson setup` 平台检测（host_machine.system()
  返回 harmonyos），那是 E355 的领域；若是 Windows host 交叉文件问题，那是 E296。

## 关系

- `similar_to`：E355（OHOS meson 平台映射三步法）、E296（OHOS Meson cross file
  补全）——同在 OHOS+meson+conan 域，但均不涉及 helper API 面差异。
- 无既有条目覆盖 `meson_layout` / `Meson.compile` API 差异。

## 查重

按 `meson_layout` / `Meson.compile` / `conan.tools.meson` / `AttributeError.*compile`
检索 `knowledge/graph/index.tsv`、`knowledge/doc/`、`knowledge/graph/*.kv`、
`knowledge/drafts/`：

- index.tsv 与 .kv/doc 均**零命中**（E296/E355/E370 关键词不重合）；
- `knowledge/drafts/` 无同主题条目；
- 结论：**新增草稿**，无 exact/causal duplicate。