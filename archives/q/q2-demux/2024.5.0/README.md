# q2-demux 2024.5.0

> QIIME 2 插件，用于对测序 reads 进行 demultiplexing（样本解复用）。
> 上游：https://github.com/qiime2/q2-demux

## 本仓库归档说明

- **类型**：纯 Python QIIME 2 插件（无编译步骤）。
- **归档方式**：将 `q2_demux` 源码复制进
  `lib/pythonX.Y/site-packages/q2_demux`，构建自包含、可独立通过 CI。
- **消费方式**：将 `lib/pythonX.Y/site-packages` 加入 `PYTHONPATH` 即可 `import`
  包内子模块（如 `q2_demux._ecc`）。

## 运行时依赖

完整使用 q2-demux 需要 QIIME 2 运行时（`qiime2 / q2-types / q2templates / pandas /
numpy / scikit-bio`）。其中 QIIME 2 核心包仅经 conda 分发（PyPI 404），尚未作为
Conan 包发布到本仓库制品仓，故运行时消费需待依赖补齐。

## 测试

| 项目 | 数量 | 说明 |
| --- | --- | --- |
| 上游测试（实测） | 88 | `q2_demux/tests/` 下 5 个文件 |
| 适配后已执行 | 14 | 新增鸿蒙/消费者测试 1 + 上游 test_ecc 13（仅 numpy） |
| 上游待执行 | 75 | 依赖 conda-only 的 QIIME 2 运行时（PyPI 404），跟踪中 |

适配测试入口：`test_package/test_q2_demux.py`
（含 `ArchiveIntegrity` 与 `UpstreamECC` 两个 R34 合规测试类）。
