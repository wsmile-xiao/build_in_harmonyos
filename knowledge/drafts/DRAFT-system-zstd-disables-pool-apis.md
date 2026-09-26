# DRAFT — 用 `--system-zstd` 链系统 libzstd 时，python-zstandard 会按**上游设计**关闭 pool API（`HAVE_ZSTD_POOL_APIS` 仅定义于捆绑构建）→ 上游 `test_features` 必失败

> 触发事件：zstandard 0.25.0 HarmonyOS PC 适配（PR #12210）。上游 292 个用例中
> **恰好只失败一条**，且看起来像功能缺失（2026-09-23 真机实测）。

## 相关既有条目（同族差异化定位）

全库查重（`knowledge/graph/index.tsv` + `knowledge/graph/E*.kv` + `knowledge/drafts/`）：对 `HAVE_ZSTD_POOL_APIS` / `system-zstd` / `ZSTD_SINGLE_FILE` / `multi_compress_to_buffer` **0 命中**。

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| （无同族条目） | — | — | **真增量**：上游「替换默认依赖来源 → 编译期宏变化 → 运行期 feature 集变化」的明示取舍，本仓此前未收录 |

## 错误特征

```
FAILED tests/test_module_attributes.py::TestModuleAttributes::test_features
AssertionError: Items in the second set but not the first:
  'multi_compress_to_buffer'
  'multi_decompress_to_buffer'
```

`zstd.backend_features` 少了两个 pool API（其余 232 项全过）。

## 根因分析

### 要点 1：这是上游**明示取舍**，不是缺陷

`c-ext/python-zstandard.h`：

```c
#ifdef ZSTD_SINGLE_FILE
#include <zstd.c>

/* We use private APIs from pool.h. We can't rely on availability
   of this header or symbols when linking against the system libzstd.
   But we know it works when using the bundled single file library. */
#define HAVE_ZSTD_POOL_APIS
#else
#include <zdict.h>
#include <zstd.h>
#endif
```

而 `setup_zstd.py`：

```python
if system_zstd:
    extra_args.append("-DZSTD_MULTITHREAD")
else:
    extra_args.append("-DZSTD_SINGLE_FILE")      # ← 只有捆绑构建才有
    ...
```

即 `HAVE_ZSTD_POOL_APIS` **只在 `ZSTD_SINGLE_FILE`（捆绑上游 zstd 源码）时定义**；
`--system-zstd` 分支不定义它 → `backend_c.c` 里 `#ifdef HAVE_ZSTD_POOL_APIS`
包住的 `multi_*_to_buffer` 两个 feature 不会注册。而上游 `test_features` 的期望集
是按**捆绑构建**写的。

### 要点 2：`--system-zstd` 是 setup.py 的 argv 开关，pip 无法透传

`sys.argv.remove("--system-zstd")` —— pip 的 PEP517 构建路径无法传自定义 argv。
必须**先出 wheel** 再装：

```bash
setup.py bdist_wheel --system-zstd -d <wheels>   # 开关在此生效
pip install --target=<staging> <wheels>/*.whl    # 不再重建，开关不会丢
```

否则 `pip install <src>` 会静默退回**捆绑构建**（既慢又与配方声明不符）。

## 推荐方案

1. **接受并据实申报**：把 `test_features` 列入允许清单，并在 notes/MANIFEST/PR 正文里
   **引用上游注释**说明「链接系统 libzstd 无法依赖 pool.h 私有 API」—— 而非静默放行。
2. 若确实需要 pool API → 改回上游默认的**捆绑构建**（不传 `--system-zstd`），
   代价是把 zstd 源码随包分发（PyPI 的 zstandard wheel 也是静态链 zstd）。

## 禁止做法

- ❌ **不要**把 `test_features` 当「库缺陷」上报或试图用补丁「修」上游的
  `#ifdef`：那是上游有意的可移植性设计。
- ❌ **不要**为了让它过而静默删除/跳过该用例而不在日志与 PR 正文中申报。
- ❌ **不要**用 `pip install <src>` 代替「先 wheel 再装」：argv 开关丢失后会静默
  变成捆绑构建，产物与声明不一致。

## 验证证据

- **主证据**：zstandard 0.25.0（PR #12210）真机实测。
  - `--system-zstd` 构建 → 232 passed / 1 failed / 59 skipped，唯一失败即
    `test_features`（缺上述两个 feature）。
  - 构建日志显式告警：`上游套件有 1 项失败（system-zstd 构建缺 pool API，
    上游有意为之，已在允许清单内）: ['test_features']`。
  - 产物检查：`ZSTD_VERSION == (1, 5, 7)`（链到 conan `zstd/1.5.7`）。
- **环境**：HarmonyOS PC / aarch64 / CPython 3.12.9 / conan 2.29.1。

## 查重结论

- 对 `HAVE_ZSTD_POOL_APIS` / `system-zstd` / `system_zstd` 检索：**0 命中**。
- 对「换掉上游默认依赖来源 → 编译期宏变化 → 运行期 feature 集变化」这一**通用模式**
  检索：无同主题条目（本仓既有条目多为具体 ABI/RUNPATH 处置）。
- **盲区声明**：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人
  提交过同主题草稿。
