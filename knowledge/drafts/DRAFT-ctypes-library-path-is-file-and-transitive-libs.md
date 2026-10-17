# DRAFT — ctypes 型包的库路径环境变量语义是「库文件」而非目录；且 `LD_LIBRARY_PATH` 必须覆盖**整条依赖链**而非只有直接依赖

> 触发事件：pyenchant 3.3.0 HarmonyOS PC 适配（PR #12208）。本地 `conan create`
> 时上游 9 个测试文件中有 8 个在**加载期**即失败（2026-09-23 真机实测）。

## 相关既有条目（同族差异化定位）

全库查重（`knowledge/graph/index.tsv` + `knowledge/graph/E*.kv` + `knowledge/drafts/`）：

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| **E212** | 正式收录 | ctypes CDLL / dlopen 报 `Permission denied`（HNP 路径与安全标签） | 本条不是「装到哪」，而是**环境变量的语义**——`PYENCHANT_LIBRARY_PATH` 是**库文件**路径，传目录会 dlopen 目录；E212 未涉及该变量语义 |
| **E131** | 正式收录 | Perl XS `DynaLoader` 的 **LD 环境变量未设**导致加载失败 | 本条是「变量设了、但传的是目录」+「传递依赖 NEEDED 未覆盖」；触发工具（ctypes vs XS loader）与机制均不同 |
| **E502** | 正式收录 | **CI worker 拒绝 dlopen 用户目录下的 SO**（与 ELF 签名无关；exec 期 NEEDED 仍可） | 本条发生在**任意机器**且是「用法传错」；E502 讲「worker 哪里不许 dlopen」，本条讲「应当怎么传 / 搜索路径要覆盖到哪」 |
| `DRAFT-libnm-…-rejects-symlinked-dt-needed`、`DRAFT-qlibc-…-in-source-relative-dt-needed`、`DRAFT-kf6-relative-needed-musl-cwd-shim`、`DRAFT-libjpeg-turbo-…-slash-relative-NEEDED` | 草稿 | **相对路径 DT_NEEDED** 导致加载失败 | 同属「加载失败」，但成因是**被链接方**的 NEEDED 写成相对路径；本条是**调用方**未把整条依赖链的 lib 目录放进搜索路径 |

## 错误特征

**第一层（环境变量语义误用）**：

```
OSError: Error loading shared library <enchant-pkg>/lib: Permission denied
```

注意报错对象是**一个目录** —— 加载器被要求 dlopen 目录。

**第二层（依赖链不全）**：

```
OSError: Error loading shared library libgio-2.0.so.0:
       (needed by <enchant-pkg>/lib/libenchant-2.so)
```

即把**直接依赖**的 lib 目录加进 `LD_LIBRARY_PATH` **还不够**。

两层的共同点：报错都发生在测试**收集期**，表现为 8 个文件全数 `ERROR ... during collection`。

## 根因分析

### 要点 1：`PYENCHANT_LIBRARY_PATH` 是库**文件**路径，不是目录

`enchant/_enchant.py`：

```python
def from_env_var(library_path: str) -> str:
    assert os.path.exists(library_path), library_path + " does not exist"
    return library_path                      # ← 原样返回
...
e = ctypes.cdll.LoadLibrary(enchant_lib_path)
```

`from_env_var()` 只断言存在并**原样返回**，随后直接 `LoadLibrary`。传目录 →
`LoadLibrary(目录)` → `Permission denied`。

另一变量 `PYENCHANT_ENCHANT_PREFIX` 走 `from_prefix()`，但那是 **Windows** 布局
（`<prefix>/bin/libenchant-2.dll`），Linux 不适用 —— 别把它当「目录版」用。

### 要点 2：共享库的 NEEDED 是**整条链**，不是一层

`libenchant-2.so` 自身 NEEDED `libgio-2.0.so.0` / `libglib-2.0.so.0`（conan 侧
`enchant/2.8.2` 的 `conaninfo` 里 requires `glib/2.84.Z`）。只把 `enchant` 的
`lib/` 前置进 `LD_LIBRARY_PATH`，加载 `libenchant-2.so` 时它自己的 NEEDED
解析不到 → 报错。

## 推荐方案

```python
# 1) 库路径环境变量传**文件**（优先无版本后缀 .so，退到 libenchant-2.so*）
lib_dir  = os.path.join(self.dependencies["enchant"].package_folder, "lib")
lib_file = os.path.join(lib_dir, "libenchant-2.so")
env["PYENCHANT_LIBRARY_PATH"] = lib_file

# 2) LD_LIBRARY_PATH 用**整条依赖链**的 lib 目录
dirs = []
for dep in self.dependencies.values():
    for d in (getattr(dep.cpp_info, "libdirs", None) or []):
        if os.path.isdir(d) and d not in dirs:
            dirs.append(d)
env["LD_LIBRARY_PATH"] = os.pathsep.join(dirs + [existing])
```

同一套环境要**同时**给到 `build()`（跑上游测试）、`test_package`（消费者测试）
与 `package_info()` 的 `env_info`（让下游也能加载）。

## 禁止做法

- ❌ **不要**把目录传给 `PYENCHANT_LIBRARY_PATH`：它的契约是文件路径，传目录只会
  得到 `Permission denied`，而报错文本不会提示「你该传文件」。
- ❌ **不要**只把直接依赖的 `lib/` 放进 `LD_LIBRARY_PATH` 就以为够了 —— 传递依赖
  的 NEEDED 同样要解析得到。
- ❌ **不要**用 `PYENCHANT_ENCHANT_PREFIX` 代替（Windows 布局，Linux 上必然失败）。
- ❌ **不要**因为「本地能 import enchant」就判定环境齐备 —— 若 `LD_LIBRARY_PATH`
  恰好含某条宿主路径，本地会通过而 CI 复现失败。

## 验证证据

- **主证据**：pyenchant 3.3.0（PR #12208）真机实测。
  - 传目录 → `Error loading shared library <pkg>/lib: Permission denied`。
  - 改传文件后前移 → `Error loading shared library libgio-2.0.so.0: (needed by
    <pkg>/lib/libenchant-2.so)`。
  - 再把整条依赖链 lib 目录前置 → 8 个文件的收集期 ERROR 消失，进入正常测试执行。
  - 消费者测试最终输出：`OK: pyenchant real API ok (libenchant loaded via ctypes;
    Broker ok, tokenize ok, list_languages -> 0 langs)`。
- **环境**：HarmonyOS PC / aarch64 / CPython 3.12.9 / conan 2.29.1；
  `enchant/2.8.2`（ohpcd 已发布）。

## 查重结论

- 对 `PYENCHANT_LIBRARY_PATH` 检索：**0 命中**。
- 对 `dlopen` + 目录（`Permission denied` 且报错对象是目录）检索：无同机制条目。
- 对「传递依赖 NEEDED 未覆盖」检索：本仓既有条目多为**C 扩展包自身的 RUNPATH/
  SONAME** 处置（如 libzimg / audiocd 系列），与本条「Python 侧经 ctypes 加载
  系统库、且环境变量语义为文件路径」的路径不同，不重叠。
- **盲区声明**：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人
  提交过同主题草稿。
