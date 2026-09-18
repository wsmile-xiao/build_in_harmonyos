# 语言预检误判：C 库绑定目录内 setup.py 使 lang-preflight 错判 mixed(setuptools)

## 问题

libuninameslist 20250714（纯 C 库，autotools 构建）首次运行
`ohc-run.py lang-preflight` 时输出 `detected_language=mixed`、
`build_system=setuptools`、`manifest: setup.py 存在（python 打包 manifest）`，
与任务语言 cpp 不匹配，工具自动写终态 `env_unsupported`。

## 根因

`scripts/ohc/lang_detect.py::_manifest_scan` 用**全文件集合** `names = {p.name for p in files}`
（rglob 任意层级）检索 `setup.py`，其判定优先级高于同一集合中的顶层
`configure.ac/Makefile.am`（autotools → c/cpp 族）。本库源码树含 `py/` 绑定目录：
`py/uninameslist.py`（ctypes 包装）+ `py/setup.py`（注释明确"Users will first need to
install C library libuninameslist"）。manifest=python(setuptools) 与主体统计
（c:12 python:2 bash:1，C 占 86%）矛盾 → §4.7 冲突规则判 mixed → 自动 env_unsupported。

## 方案

按协议 §D.4 边界规则（辅助脚本/绑定包不算主体、C/C++ 混编按主体判）人工复核：
1. 顶层构建系统为 autotools（configure.ac/Makefile.am/libuninameslist.pc.in）
2. 主体源码 12 个 .c（nameslist.c 约 5.9 万行、nameslist-fr.c 约 5.8 万行等），C 占 86%
3. py/ 是 ctypes 绑定包装，需先装 C 库，属辅助目录不计主体

复核判定为 C（与任务 cpp 属兼容族，不迁移），继续适配主流程。

## 验证

按 C 判定继续完成全流程：configure/make/make install DESTDIR/make check 4/4 通过、
conan-verify 8 道门禁 PASS、OHOS 专项测试 7/7 断言 PASS。证明正确判定为 C 后适配完全可行。

## 适用边界

- 适用：含 py/ 等绑定目录且目录内存在 setup.py/pyproject.toml 的 C/C++ 库
  （ctypes/cffi 包装库、fontforge 系等）；依赖绑定目录打包的库。
- 反例：真正混合语言（主体即 python/c++ 混合、无 ≥70% 单语言主体）项目不得强行按 cpp 适配，
  应如实上报 detected_language 迁移。

## 查重差异

| 既有条目 | 覆盖部分 | 本条新增 |
|---|---|---|
| DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect | _manifest_scan 全树扫描 Cargo.toml 误判 mixed | setup.py(setuptools) 签名；绑定目录 + 顶层 autotools 组合 |
| DRAFT-debugbreak-1.0-langpreflight-gnumakefile-misdetect | GNUmakefile 不被识别为构建系统 | 绑定目录 setup.py 优先级高于顶层 configure.ac 的签名 |

## 关系

- similar_to: DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect、DRAFT-debugbreak-1.0-langpreflight-gnumakefile-misdetect
- caused_by: lang_detect.py _manifest_scan 对 setup.py/pyproject.toml 未限定顶层
- prerequisite_of: 无
- conflicts_with: 无
