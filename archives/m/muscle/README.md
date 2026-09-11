# MUSCLE

MUSCLE (Multiple Sequence Comparison by Log-Expectation) is widely-used software for making multiple alignments of biological sequences.

Muscle achieves highest scores on Balibase, Bralibase and Balifam benchmark tests and scales to thousands of sequences or structures on a commodity desktop computer.

## 版本

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 5.3 | published | custom (vcxproj_make.py) | 2026-09-10 |

## 构建说明

MUSCLE 使用非标准构建系统：`vcxproj_make.py` 脚本将 Visual Studio `.vcxproj` 项目文件转换为 Makefile，然后使用 make 编译。

OHOS 适配要点：
- 编译器从 g++ 切换为 clang++（通过 `--cppcompiler` 参数）
- 使用 OpenMP（`--openmp` 标志）
- 无外部依赖（self-contained）

## 上游

- 仓库: https://github.com/rcedgar/muscle
- 许可证: GPL-3.0
