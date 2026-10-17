# DRAFT — 纯 Python 包的 staging 目录必须放在**源码树之外**（否则被 setuptools flat-layout 自动发现当成顶层包）；装 **wheel** 时用 `pip --target` 而非 `--prefix`（后者实测装出空目录），装**源码目录**时 `--prefix` 可用但必须断言落点

> 触发事件：pybeam 0.8.1 HarmonyOS PC 适配（PR #13242）。
> 本地 `conan create` 的 `build()` 阶段失败（2026-09-23 真机实测）。

## 相关既有条目（同族差异化定位）

全库查重（`knowledge/graph/index.tsv` + `knowledge/graph/E*.kv` + `knowledge/drafts/`）：

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-vfit-2.1.0-legacy-poetry-copytree-wrapper`（`{.kv,.md}`） | 草稿 | poetry 旧版 `copytree` 包装导致的**构建脚本**兼容问题 | 同属「Python 打包布局」，但那条是**上游构建脚本**的写法问题；本条是**本仓 staging 目录落点**被 setuptools flat-layout 自动发现吞掉 + `pip --prefix` 装出空目录（属适配侧规范） |
| E 编号检索（`Multiple top-level packages` / `flat-layout` / `pip install --prefix`） | — | `graph/index.tsv` 与 `E*.kv` **0 命中** | 本条为**真增量** |

## 错误特征

两个**互相独立**的失败，都出在「把 wheel 装到一个 staging 目录」这一步：

**症状 A —— setuptools 自动发现报错**：

```
error: Multiple top-level packages discovered in a flat-layout: ['pybeam', 'staging'].
```

**症状 B —— 装完 staging 是空的**：

```
ConanException: zstandard site-packages not found under staging=.../_staging_zstandard
```

且 `find <staging> -maxdepth 4 -type d` 只列出 staging 自身，**没有任何子目录** ——
`pip install --prefix=<staging> <wheel>` 明明退出码为 0。

## 根因分析

### 要点 1：staging 落在源码树内 → 被 flat-layout 自动发现当成顶层包

- conan 里**未定义 `layout()`** 的配方，`self.build_folder == self.source_folder`；
- 于是 `staging = os.path.join(self.build_folder, "staging")` 落在**源码树里**；
- pybeam 用 `pyproject.toml` 且**未显式声明 packages** → setuptools 走 flat-layout
  自动发现，扫到同级的 `staging/`，与 `pybeam/` 一起构成两个顶层包 → 报错。
- 同理 `setup.cfg` 里写 `packages = find:` 的包（如 pyenchant）也有被纳入的风险。

### 要点 2：`--prefix` 装 **wheel** 时的落点与预期不符（装源码目录则可用）

- `pip install --prefix=<dir>` 依赖 `<dir>/lib/pythonX.Y/site-packages` 这套布局。
  实测在**本平台装 wheel**（zstandard 0.25.0）时 `<dir>` 装完仍为空。
- 但 `--prefix` **并非普遍失效**：pybeam 0.8.1 用
  `pip install --prefix=<staging> <源码目录>` 实测**正常装出**
  `<staging>/lib/python3.12/site-packages/pybeam`（conan-create.log 实证），
  故「改用 `--target`」的适用范围是**装 wheel**；装源码目录时 `--prefix` 可继续使用，
  但同样必须断言落点（见「推荐方案」）。
- `--target=<dir>` 语义明确：把内容**平铺**进该目录（含 `*.dist-info`），
  打包时整目录拷入 site-packages 即可，不依赖 `lib/pythonX.Y/` 布局推断。

### 要点 3：为什么纯 Python 的既有范式没踩到

本仓既有的 soupsieve / acronym / pyxdg / construct 用**显式 `setup.py` 包列表**，
不触发自动发现，故 `staging` 放在源码树内也不报错 —— 症状只在
`pyproject.toml`/`packages = find:` 形态的包上出现。

## 推荐方案

```python
# 1) staging 一律取 source_folder 的**父目录**，确保落在源码树之外
def _staging_dir(self):
    return os.path.join(
        os.path.dirname(os.path.normpath(self.source_folder)),
        "_staging_" + self.name)

# 2a) 装 wheel：用 --target（--prefix 实测装出空目录），装完**断言包目录存在**
self.run(f'{python_exe} -m pip install --break-system-packages --no-deps '
         f'--target="{staging}" "{wheel}"')
if not os.path.isdir(os.path.join(staging, self.name)):
    raise ConanException(f"wheel install produced no {self.name} under {staging}")

# 2b) 装源码目录：--prefix 可用（pybeam 0.8.1 实证），同样**断言落点存在**
self.run(f'{python_exe} -m pip install --break-system-packages --no-deps '
         f'--prefix="{staging}" "{src_dir}"')
# --prefix 的落点是 <staging>/lib/pythonX.Y/site-packages，
# 装完须断言该目录下有包，否则错误会推迟到 package() 才以误导性的
# "site-packages not found under staging" 文案爆出
```

共同要点：**装完立即断言**，把「空安装」提前变成显式失败，而不是留到 `package()`
才报找不到 site-packages。（pybeam 0.8.1 的 `package()` 用候选路径轮询兜底 `--prefix`
的落点差异，也是可行形态，但确定性不如安装后立即断言。）

## 禁止做法

- ❌ **不要**把 staging 放在 `self.build_folder` 下就以为安全：无 `layout()` 的配方里
  它等于源码树。
- ❌ **不要**在 `package()` 里用「多个候选路径轮询」来兜 `--prefix` 的落点差异 ——
  直接用 `--target` 更确定。
- ❌ **不要**只在 `package()` 里发现 staging 为空时才报错：应在**安装后立即**断言，
  否则错误会以「找不到 site-packages」这种误导性文案出现。

## 验证证据

- **主证据（症状 A）**：pybeam 0.8.1 真机实测。
  - staging 在源码树内 → `Multiple top-level packages discovered in a flat-layout:
    ['pybeam', 'staging']`。
  - staging 移到源码树外 → 该错误消失，构建推进。
- **主证据（症状 B，限定为装 wheel）**：zstandard 0.25.0 上以 `--prefix` 装 **wheel**
  → staging 为空；改 `--target` 后正常。
  - 边界反证：pybeam 0.8.1 以 `--prefix` 装**源码目录**实测**成功**，落点为
    `<staging>/lib/python3.12/site-packages/pybeam`（conan-create.log 实证，
    构建日志 `.ci_logs/conan_build_pybeam_0.8.1.log`）。
    → 故症状 B 的适用范围是**装 wheel**，不构成「`--prefix` 一律失效」的结论。
- **交叉佐证**：同批 pyxdg / construct（显式 setup.py 包列表）**未**出现症状 A，
  与「要点 3」一致。
- **环境**：HarmonyOS PC / aarch64 / CPython 3.12.9 / conan 2.29.1。

## 查重结论

- 对 `Multiple top-level packages discovered` / `flat-layout` 检索：**0 命中**。
- 对 `pip install --prefix` 与 `--target` 的落点差异检索：**0 命中**。
- 本仓既有纯 Python 配方文档只描述「staging 放 build_folder」的范式，**未**记录
  `pyproject.toml`/`packages = find:` 形态下的这一陷阱。
- **盲区声明**：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人
  提交过同主题草稿。
