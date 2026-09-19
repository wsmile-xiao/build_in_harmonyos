# DRAFT-fir1-1.8.0-langpreflight-swig-root-setup-misdetect

> Contributor: pc2-14 | Status: Draft | Updated: 2026-09-19
> Source: 任务 fir1-1.8.0-r01-pc2-14-20260919T044434Z（fir1 1.8.0 语言预检误判）

## 背景

fir1 1.8.0 是 CMake 构建的 C++11 FIR 滤波器库（根目录 `CMakeLists.txt`
`project(fir VERSION 1.8.0 LANGUAGES CXX)`，主体 10 个 `.cpp` + `Fir1.h`，
test/ 注册 6 个 ctest 用例，无第三方依赖）。源码树另含根目录 `setup.py` +
`fir1.i`/`numpy.i`（SWIG Python 绑定包装）和 `docs/`（Doxygen 预生成 API 文档，
22 个 `.js`）。`ohc-run.py lang-preflight` 输出：

```json
"detected_language": "python",
"language_evidence": {
  "build_system": "setuptools",
  "manifest": "setup.py 存在（python 打包 manifest）",
  "source_stats": "源文件 35 个（nodejs:22, cpp:10, python:3, bash:1），主体占比 63%"
}
```

并按 R47 自动写终态 `env_unsupported`（任务语言 cpp ≠ python）。

## 根因

`scripts/ohc/lang_detect.py` 两个判定路径叠加：

1. `_manifest_scan` 用全文件集合 `names = {p.name for p in files}`（rglob 任意层级）
   检索 `setup.py`，命中返回 `("python", "setuptools", ...)`；而根目录
   `CMakeLists.txt` 的检查也在同一函数中，但 `setup.py` 分支在其之前 →
   **根级 setup.py（SWIG 绑定包装）优先于根级 CMakeLists.txt**，manifest 直接判 python。
2. `_source_stats` 的 `_SKIP_DIRS` 不含 `docs`，把 Doxygen 生成的 22 个 `.js`
   计入 nodejs 统计（nodejs:22 / 35 = 63% < 70%）。

两者叠加 → manifest=python 且无 ≥70% 主体冲突 → `detected=python` →
cpp 任务报 env_unsupported。与既有草稿的区别见"查重差异"。

## 复核与修复（流程侧）

按协议 §D.4 / R47 边界规则人工复核：

- 根构建系统为权威：根目录 `CMakeLists.txt`（project CXX）→ c/cpp 族；
- 辅助脚本/绑定不算主体：`setup.py`/`fir1.i`/`numpy.i` 为 SWIG 绑定包装（非库主体），
  `docs/` 为 Doxygen 生成文档（非源码）；
- 主体源码 10 个 `.cpp` + 6 个 ctest → C++ 主体，c↔cpp 兼容族不迁移。

复核判定 `cpp`，与任务语言匹配，继续完整适配（编译、6/6 上游测试、test_package
消费者、conan-verify G0-G4、finish W2/W3/W5 全部通过），证明复核正确。

## 验证

- 按 cpp 族完成 fir1 1.8.0 全流程：CMake 编译 + ctest 6/6 PASS + HarmonyOS 专项
  测试 PASS + 消费者验证 PASS + conan-verify 全门禁 PASS + W3 本地 CI PASS。
- 误判证据（文件构成 + 统计）留存于最终回报 `language_evidence` 与 notes.md 问题 #1。

## 适用边界

- 适用：根目录同时存在 `setup.py`（SWIG/ctypes Python 绑定包装）与
  `CMakeLists.txt`，且 `docs/` 含 Doxygen 生成 `.js` 的 C/C++ 库（SWIG 绑定系
  fir1/fftw 等）。也适用于仅含其一者（根级 setup.py 或 docs/ js 单独也可触发）。
- 反例：真实 python 主体（根 setup.py + py 主体源码 ≥70%）仍判 python；
  绑定子目录 setup.py（如 py/ 内）见 DRAFT-libuninameslist，不适用本条。

## 查重差异

| 既有条目 | 覆盖部分 | 本条新增 |
|---|---|---|
| DRAFT-lwip-2.2.1-lang-preflight-doxygen-js-misdetect | docs/ Doxygen .js 计入 nodejs 统计污染 | 根级 setup.py 优先于根级 CMakeLists 的 manifest 路径；判 python（非 mixed）的出口 |
| DRAFT-libuninameslist-langpreflight-setuptools-binding-misdetect | 绑定目录 setup.py 判 mixed | setup.py 在**根目录**（非子目录），其"仅顶层检索"修复对本签名无效；判 python 而非 mixed |
| DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect | 测试目录辅助 Cargo.toml | setup.py 签名 + 根级遮蔽组合 |
| DRAFT-libcec-8.1.7-langpreflight-binding-subdir-misdetect | 绑定子目录 Cargo.toml | SWIG 绑定 + docs 组合 |
| DRAFT-debugbreak-1.0-langpreflight-gnumakefile-misdetect | GNUmakefile 不识别 | 根级 setup.py 遮蔽 |

## 关系

- similar_to: DRAFT-lwip-2.2.1-lang-preflight-doxygen-js-misdetect、
  DRAFT-libuninameslist-langpreflight-setuptools-binding-misdetect、
  DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect
- caused_by: lang_detect.py _manifest_scan 根级 setup.py 优先级高于根级 CMakeLists.txt +
  _SKIP_DIRS 缺 docs
- prerequisite_of: 无
- conflicts_with: 无
