# DRAFT-E592-libyal-root-pep517-langpreflight-mixed-misdetect

> Contributor: libpff 任务 | Status: Draft | Updated: 2026-09-20
> Source: 任务 feat/libpff-20231205（libpff 20231205 语言预检误判 mixed，第 5 次家族复现）

## 背景

libpff 20231205 是 libyal 家族的 PFF/OST 邮件存储格式库（autotools，纯 C，随库发布
pffinfo/pffexport 工具）。`ohc-run.py lang-preflight` 对其判定：

```json
{
  "expected": "cpp",
  "detected_language": "mixed",
  "language_evidence": {
    "build_system": "setuptools",
    "manifest": "pyproject.toml 存在（python 打包 manifest）",
    "source_stats": "源文件 348 个（c:340, bash:9, python:3, cpp:3），主体占比 98%"
  },
  "notes": ["冲突: manifest=python 但统计 c 占 98% → mixed"]
}
```

并按 R47 自动写终态 `env_unsupported`（协议 exit 2）。

## 根因

libyal 自 2023 起把 Python 绑定打包清单上移到仓库根（PEP517 迁移布局）：

- 根级 `pyproject.toml` 仅有 `[build-system]`（setuptools 引导），不含项目元数据；
- 根级 `setup.py` 首行自述 `Script to build and install Python-bindings`，只打包
  SWIG 生成物 `pypff/`（pypff.c 等由 pypff.h.in 生成，本质是 C 库的绑定壳）；
- `.py` 全部 3 个文件 = 该 setup.py + `tests/pypff_test_file.py` +
  `tests/pypff_test_support.py`（tests/ 属绑定测试目录）。

`lang_detect.py` 的排除面（`_AUX_MANIFEST_DIRS` 的 bindings/binding/docs/test 等
目录名 + `_SKIP_DIRS` 的 `py_ext/`）覆盖不了「manifest 在根级、绑定源码目录名不带
binding 字样」的形态：manifest 判 python(setuptools)，而源码统计 c=340/348≈97.7% ≥70%，
两路信号撞进 §4.7 冲突规则 → 判 mixed → 与任务语言 cpp 不匹配 → exit 2 +
env_unsupported 终态。绑定在配方里以 `--disable-python`（`--enable-python` default=no）
显式排除，与构建交付完全无关。

与既有条目的差异（查重结论）：

| 既有条目 | 布局 | 出口 | 与本条差异 |
|---|---|---|---|
| DRAFT-fir1-1.8.0 | 根级 setup.py(SWIG) + 根级 CMakeLists | manifest 胜出 → python | 本条为 autotools、§4.7 冲突 → mixed |
| DRAFT-libuninameslist | 绑定目录内的 setup.py | — | 本条 manifest 在根级 |
| DRAFT-emio-0.9.0 | 辅助 Cargo.toml | — | 语言不同 |
| DRAFT-debugbreak-1.0 | GNUmakefile 未命中 manifest | none | 本条是命中错误的 manifest |

## 家族复现记录（5 次）

| 任务 | 绑定 | 处置 |
|---|---|---|
| libfsapfs-20240429 | pyfsapfs | lang-preflight rc=2 → 跳过留痕 → 已完成 |
| libfsxfs-20240501 | pyfsxfs | 同上 → 已完成 |
| libvslvm-20240504 | pyvslvm | 任务进行中，同一 rc=2 现场 |
| libpff-20231205 | pypff | 本条（mixed 出口首次留证） |
| （fir1 1.8.0 非 libyal 但同根级 setup.py 形态） | fir1 python 绑定 | 已有独立条目 |

## 处置（对 libpff 的落地）

1. 逐个归因工具证据里的 python 文件（3 个均为绑定清单/绑定测试）；
2. 确认 configure 入口有 `--enable-python`（default=no），配方显式 `--disable-python`
   后绑定不进构建与交付；
3. 主体占比 97.7% C，与任务语言 cpp 属 c↔cpp 兼容族 → 判定主体语言 C，继续适配；
4. 编排里按「未执行≠通过」以 `--skip-step lang-preflight` + `--start-note` 留痕，
   readiness 记 skip；本节即 notes.md「语言预检处置记录」的证据源；
5. 工具缺陷另记 workflow 反馈（feedback/pending/），不在软件 PR 内改框架。

## 修复建议（框架侧，另开任务）

`lang_detect` 命中 python manifest 时回查 manifest 内容：`pyproject.toml` 仅
`[build-system]`、或 `setup.py` 首行/`packages=` 仅声明绑定模块时，按辅助清单跳过；
§4.7 冲突出口在「manifest=辅助绑定清单」情形下不应判 mixed。

## 禁止

- 禁止因根级 pyproject.toml/setup.py 对 autotools C 库直接接受 env_unsupported 终态；
- 禁止为通过预检删除或改写上游绑定文件；
- 禁止对真正 python 主体的项目强行按 cpp 适配（应如实上报迁移）。
