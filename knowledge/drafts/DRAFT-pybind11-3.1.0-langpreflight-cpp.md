# DRAFT-pybind11-3.1.0-langpreflight-cpp — lang-preflight 对 pybind11 判 python 误判

## 问题（错误签名）
`ohc-run.py lang-preflight pybind11 3.1.0` 输出 `detected_language=python`、
`status=env_unsupported`（EXIT=2），错误摘要 "任务标记 cpp，实测源码为 python
（setuptools）"。与 SKILL R47 边界规则明文 "pybind11 绑定包判 cpp"、历史归档
pybind11 2.10.1（published，header-only cpp 库）及 DRAFT-onnx 官方裁定
（"C++ 库 + Python 打包" 仓库判 python 为误判）全部矛盾。

## 根因
`lang_detect.py` 判定链条：
1. `_manifest_scan` 全文件集合（rglob）检索 `pyproject.toml/setup.py/setup.cfg`，
   优先级高于仅看顶层 `CMakeLists.txt` 的 c/cpp 分支 → pybind11 根级
   `pyproject.toml` 使 `manifest=python(setuptools)`。
2. `_detect_binding` 已命中 "pybind11" 绑定标记（本库即绑定框架本体），但
   `binding_override` 要求 `dominant==cpp 且 share>=0.70`；本仓库源文件
   cpp:python = 100:97（tests/ 的 .py 测试驱动抬高 python 计数）→ cpp 占比 51%
   < 70% → 绑定覆盖不触发。
3. 结果 `detected=python`，与任务语言 cpp 冲突 → 协议 §4.7/R47 自动写
   `env_unsupported` 终态。

## 交付物证据（判 cpp 依据）
- `CMakeLists.txt:38 project(pybind11 LANGUAGES CXX)`
- `CMakeLists.txt:368 install(TARGETS pybind11_headers EXPORT ...)` →
  `pybind11::pybind11` find_package 目标
- `include/pybind11/*.h` 28 个公开头文件构成对外 API（header-only）
- `pyproject.toml` 仅承载可选 Python 打包（scikit-build-core），非主交付物
- 绑定框架本体：pybind11 的"绑定包"身份正是 R47 判 cpp 的边界规则对象

## 方案（rec_approach: deliverable-language-evidence-escalation）
1. 收到 detected=python/env_unsupported 时，先核验交付物语言三条证据（C/C++
   安装目标、绑定开关/打包为可选、头文件 API），证据齐 → 按 R47 边界规则
   "pybind11 绑定包判 cpp" 继续 cpp 适配，不停止。
2. 将误判作为知识候选记录，随本库归档同 PR 交付（本次已落 DRAFT 对）。
3. 平台/主编侧可选：将绑定覆盖阈值从 "cpp 占比≥70%" 放宽为 "绑定标记命中 +
   存在 C/C++ 安装目标即判对应语言"（D.4-2 意图），并同步 R47 规则文本。

## 验证（本任务真实日志）
- lang-preflight EXIT=2 detected=python（工具误判快照）。
- 按 cpp 继续：conan-verify G0-G4 全 PASS（conan create 干净构建 + test_package
  消费者编译/运行 "pybind11 3.1.0 (hex 0x030100F0) CXX17=yes"）。
- 上游 pytest 全量实跑：1151 passed / 1 failed（上游 Android 家族已知跨模块
  翻译器问题，xfail 平台同族）/ 51 skipped（clang15 libc++ 头缺口）/ 2 xfailed
  / 1 xpassed → 全量通过率 1151/1206 = 95.44%。

## 适用边界与反例
- 适用：C++ 头文件/源码库 + 根级 pyproject.toml（可选 Python 绑定/打包）的三方库。
- 反例：纯 Python 交付物（无 C/C++ 安装目标）——python 判定正确，不得硬适配。

## 查重差异（vs 既有草稿）
与 DRAFT-onnx-1.20.0（nanobind 未入绑定标记、cpp 占比 5 倍差距）、
DRAFT-libuninameslist（C 库绑定目录 setup.py 判 mixed）、DRAFT-libcec
（绑定子目录 misdetect）同属 `_manifest_scan` 全树扫描缺陷家族；本条新增签名：
**绑定标记已命中（pybind11 本体）但 cpp 占比不足 70% 仍判 python**——onnx 草稿
未覆盖"标记命中但占比不足"的触发细节，且 R47 规则文本明文 "pybind11 绑定包
判 cpp" 与实现阈值的冲突在本条得到官方口径记录。

## 关系
- similar_to: DRAFT-onnx-1.20.0-lang-preflight-pyproject-priority-cpp-deliverable-misdetect,
  DRAFT-libuninameslist-langpreflight-setuptools-binding-misdetect,
  DRAFT-libcec-8.1.7-langpreflight-binding-subdir-misdetect
- caused_by: lang_detect.py::_manifest_scan 优先级 + binding_override 70% 阈值
- prerequisite_of: （无）
- conflicts_with: （无）
