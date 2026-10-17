# DRAFT — R47 语言预检对 pybind11 绑定库的误判：应判 cpp

> 状态: 草稿（基于 pybind11 2.10.1 R01 真实证据，待查重/提升）。
> 来源: pybind11 2.10.1 全量适配（pc1-13, 2026-09-05），lang-preflight 对本库误写 env_unsupported 终态，按 R47 边界规则纠正为 cpp 后完成全部门禁。

## 真实问题（场景）

pybind11（C++ 头文件绑定库）R01 适配时，`ohc-run.py lang-preflight`（scripts/ohc/lang_detect.py）
按"manifest > 构建系统 > 源码统计"三级判定，把本库判为 **python/setuptools** 并自动
写终态 `env_unsupported`：

```
detected_language: python
language_evidence: manifest=pyproject.toml 存在（python 打包 manifest）
                   source_stats: 源文件 109 个（python:60, cpp:49, bash:1），主体占比 55%
```

`_source_stats` 对 `.h` 中立头文件**不计数**，因此仓库内 include/pybind11/（27 个
C++ 头文件，主交付物）完全不入统计；60 个 `.py` 中 48 个位于 tests/（pytest 驱动），
其余为 setup.py/pyproject.toml/pybind11/*.py 打包与 shim。cpp 与 python 实源接近
（49 vs 60），无法触发 `binding_override`（要求 C++ 占比 ≥70%）。

## 根因

1. pybind11 是**头文件型 C++ 库**：交付物为 include/pybind11/*.h（C++ API），
   `.py` 文件几乎全部是测试驱动与打包脚本——按 R47"辅助脚本不算主体"应不计主体。
2. 工具实现要求 `dominant == "cpp" and share >= 0.70` 才触发绑定覆盖，而 pybind11
   自身仓库恰好 python 实源略多（tests 驱动），导致 D.4-2 规则未生效。
3. lang_detect.py 文档字符串明确"pybind11 包装 C++ → 判 cpp"（协议附录 D.4-2），
   但实现阈值把 pybind11 本体排除在外。

## 修复/方案

按 R47 边界规则纠正判定：pybind11 绑定包判 **cpp**，忽略工具误写的 env_unsupported
终态，继续正常 C++ 适配流程（lang-preflight 的正确语义是"任务标记 cpp 且源码主体
为 C++ 绑定库 → cpp 兼容"）。适配完成后用真实终态 result 覆盖误写草稿。

## 验证

- lang-preflight 误判输出：`detected_language=python`、`language_evidence` 三项如
  上，写 $HOME/ohpcd-ai-worker-result.json（draft:false）。
- 人工纠正后按 cpp 走全程门禁：conan-verify G1/G0/G2/G3/G4 PASS（G2 conan create
  零 Python 依赖，PYBIND11_NOPYTHON=ON）、W3 build_and_test.sh L0/L1 PASS、
  test_package 消费者探测在真实 OHOS aarch64 设备运行 exit 0。

## 适用边界 / 反例 / 限制

- 适用：上游仓库混有较多 python 测试/打包文件的**头文件型 C++ 绑定库**
  （pybind11、nanobind 类、boost::python 包装库）。
- 反例：真正以 python 为主体的项目（如纯 setuptools 应用仓库 manifest 明确 python、
  源码 ≥70% python）不适用，仍走 env_unsupported 迁移。
- 限制：本经验不改变 lang_detect.py 工具代码（框架只读），仅记录执行端判定口径；
  工具后续若调低绑定覆盖阈值或对 pybind11 加显式白名单，本条可归档。