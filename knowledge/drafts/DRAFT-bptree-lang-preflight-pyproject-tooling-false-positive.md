# DRAFT — lang-preflight 误判：dev-tooling pyproject.toml 把纯 C/C++ 库判成 mixed → env_unsupported

> Status: DRAFT (contributor pc2-20) | Source: bptree/0.5.0 adaptation, task bptree-0.5.0-r01-pc2-20-20260919T144325Z
> Environment: HarmonyOS PC aarch64, OHOS SDK clang 15.0.4, Conan 2.29.1 (OHOS), R47 语言预检

## 1. 问题现象

`ohc-run.py lang-preflight` 对 bptree 0.5.0（纯 C 单头文件库）判定
`detected_language="mixed"` 并自动写入终态 `env_unsupported`：

```json
"error_detail": "任务标记 cpp，实测源码为 mixed（setuptools），无法按 cpp 适配",
"language_evidence": {
  "build_system": "setuptools",
  "manifest": "pyproject.toml 存在（python 打包 manifest）",
  "source_stats": "源文件 6 个（c:6），主体占比 100%"
}
```

矛盾的证据一目了然：源码统计是 100% C，却因一个 pyproject.toml 被判为 python。

## 2. 根因

`scripts/ohc/lang_detect.py` 的 `_manifest_scan()` 对**任意** pyproject.toml 存在
即返回 `("python", "setuptools", ...)`，不校验：

- 是否存在 `[build-system]` 段（bptree 的 pyproject.toml 没有）；
- 同目录是否存在 setup.py / setup.cfg（都没有）；
- 仓库是否存在任何 `.py` 源文件（0 个）。

随后冲突规则（manifest=python vs 统计 c 100%）→ `mixed` → 与任务语言 cpp
不匹配 → 终态 `env_unsupported`（协议 v0.8 §4.5 语言迁移分支）。

bptree 的 pyproject.toml 实际是开发环境声明：

```toml
[project]
name = "bptree"
description = "The Python environment for the Bptree project"
dependencies = ["python-dotenv (>=1.1.0,<2.0.0)", "pre-commit (>=4.2.0,<5.0.0)"]
```

即给 pre-commit / dotenv 工具链用的依赖清单，与库本体（C 头文件）无关。

## 3. 判定与验证

| 检查 | 命令 | 结果 |
|---|---|---|
| Python 源文件 | `find . -name '*.py'` | 0 个 |
| build-system 段 | `grep -c 'build-system' pyproject.toml` | 0 |
| 移除 pyproject.toml 后检测 | 合成目录重跑 `detect_language` | `"c"`（make） |
| 兼容族 | `_COMPAT_FAMILY = {"c","cpp"}` | c↔cpp 兼容，任务 cpp 应通过 |

- 真实语言为 **C**（build_system=make，顶层 Makefile，单头文件库），属 cpp
  兼容族（R47：c↔cpp 不迁移）。
- 处置：记录为检测器误判，**继续适配主流程**；终态由最终 result 命令如实覆盖
  （不手写 JSON，不删除源文件）。

## 4. 修复建议（检测器侧）

`_manifest_scan()` 对 pyproject.toml 的判定应加守卫：

1. pyproject.toml 含 `[build-system]` 段 → 判 python（真打包清单）；
2. 同目录存在 setup.py / setup.cfg → 判 python；
3. 仓库存在 `.py` 源文件 → 判 python（统计兜底）；
4. 以上皆无 → 回落到 Makefile / CMakeLists.txt / configure.ac 等构建系统判定
   （c/cpp 族），不再因 dev-tooling pyproject.toml 翻转语言。

## 5. 适用边界与反例

- **适用**：纯 C/C++ 仓库附带 pre-commit/dotenv 等 dev 工具的 pyproject.toml。
- **反例**：确有 Python 主体（pybind11 绑定、setup.py 打包、.py 源 ≥ 主体）的
  仓库必须判 python/cpp 绑定，不得套用本方案。
- 不得通过删除/移动 pyproject.toml 绕过检测器（CI 仍是原仓库，误判照旧），
  也不得手写 result.json 覆盖终态（R46 协议红线）。

## 6. 查重差异

- 正式知识 / 图谱 / 草稿四范围检索 "pyproject / lang-preflight /
  detected_language"：**全库 0 命中**（E257/E321/E322/E470 均属 header-only
  配方类，主题不同）。
- 新增差异：R47 语言预检阶段的检测器误判处置 + 检测器改进守卫，无既有条目覆盖。
- 关系：`similar_to=E257`（同为门禁类误判处置方法论），无 conflicts/caused_by。
