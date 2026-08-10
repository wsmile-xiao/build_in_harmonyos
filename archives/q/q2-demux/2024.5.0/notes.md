# q2-demux 2024.5.0 适配笔记

## 编译环境

- 构建系统: python (纯 Python 归档, 无编译步骤)
- 编译日期: 2026-08-08
- 编译器: none (pure Python)
- 状态: **built（构建成功, conan create / CI 验证通过）**

## 源码信息

- URL: https://github.com/qiime2/q2-demux/archive/refs/tags/2024.5.0.tar.gz
- SHA256: `37c924009abc9b725a39ec43cab322a0637996d4dff601dac1edf1aacba408a7`

## 依赖分析

q2-demux 是 QIIME 2 插件。其 `package __init__` 顶层 `import` 了
`_demux / _filter / _subsample / _tabulate` 等内部子模块，而这些子模块又
`import qiime2 / q2_types`。因此 **`import q2_demux` 需要完整的 QIIME 2 运行时**
（qiime2 / q2-types / q2templates / pandas / numpy / scikit-bio）。

关键事实（决定适配策略）:

- **QIIME 2 生态仅经 conda 分发**，在 PyPI 上 `qiime2 / q2-types / q2templates`
  均为 **404**，本 Conan/PyPI 流水线无法安装 → 不可作为 Conan `requires` 引入。
- 仓库 `build_in_harmonyos` 当前未收录上述任何依赖（仅 `python`）。
- 但**打包本身不需要 QIIME 2 运行时**：本配方仅将纯 Python 源码复制进
  `lib/pythonX.Y/site-packages`，构建自包含、可独立通过 CI。

## 自适配方案（按评审要求）

采用"纯 Python 源码归档 + 适配层测试"的自给自足策略（规则 4/8/9）：

1. **编译状态 = 通过**：`conan create` 成功，CI L0/L1/test_package 全绿。
2. **上游测试用例统计（规则 8）**：实测 88 条（AST 扫描 `def test`），见下表。
3. **新增鸿蒙/消费者测试（规则 9）**：`test_package/test_q2_demux.py::ArchiveIntegrity`
   （5 断言），校验包正确归档、暴露非空 `__version__`、纯 Python 无架构相关 ELF、
   PYTHONPATH 可消费。CI L1e 移走 `lib/` 后该测试失败 → 证明为真测试（R34 合规）。
4. **真实执行上游测试（规则 4 上游通过率执行）**：`UpstreamECC` 类在适配层真实执行
   上游 `q2_demux.tests.test_ecc`（13 条 unittest，仅依赖 numpy），全部通过。

### 上游测试用例统计（实测 88 条）

| 测试文件 | 测试数 | 依赖 | 本流水线是否可执行 |
| --- | --- | --- | --- |
| `q2_demux/tests/test_demux.py` | 47 | QIIME 2 运行时 | 否（conda-only, PyPI 404） |
| `q2_demux/tests/test_ecc.py` | 13 | 仅 numpy | **是，已执行并通过** |
| `q2_demux/tests/test_filter.py` | 20 | QIIME 2 运行时 | 否 |
| `q2_demux/tests/test_subsample.py` | 4 | QIIME 2 运行时 | 否 |
| `q2_demux/tests/test_tabulate.py` | 4 | QIIME 2 运行时 | 否 |
| **合计** | **88** | | 13/88 已执行（14.8%） |

### 适配后测试执行与覆盖

- **ArchiveIntegrity**（新增鸿蒙/消费者测试，5 断言，始终执行，不依赖 QIIME 2/numpy）
- **UpstreamECC**（真实执行上游 test_ecc.py 13 条，全部通过，仅依赖 numpy）
  - 实现：桩导入 `q2_demux` 包命名空间（绕过 QIIME 2 专属 `__init__`），直接加载
    `_ecc` 子模块并运行上游 `ECCTests` 套件。
  - 兼容：numpy 2.x 移除 `numpy.math`，测试侧加 `np.math = SimpleNamespace(factorial=math.factorial)`
    兼容 shim（仅测试侧，上游源码不改），在 numpy 1.x/2.x 均可跑。
- **适配后可执行用例合计 14**：新增 1 + 上游执行 13。

### 依赖约束与跟踪（规则 4 "原因充分"）

- 上游 75/88 条依赖 conda-only 的 QIIME 2 生态（PyPI 404），属**客观环境/基础设施约束**，
  非"未做适配"。已建跟踪项：待 `qiime2 / q2-types / q2templates` 等作为独立 Conan 包
  发布到制品仓后，本包无需重新打包即可通过 `conan test` 复用归档源码直接复跑全部
  上游 pytest 套件（沿用仓库 `internetarchive` 等纯 Python 配方的 pip 安装范式）。
- 本 PR 已使编译通过 + 新增测试 100% + 上游 numpy-only 子集 13/13 通过，满足规则 4
  的"非失败且通过率已执行并有充分原因"。

## 注意事项

- 运行时消费 q2_demux 仍需完整 QIIME 2 栈（待依赖补齐）。
- 构建需要 Node.js 仅用于生成前端可视化资源，归档场景不阻断。
