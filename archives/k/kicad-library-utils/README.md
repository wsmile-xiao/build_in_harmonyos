# kicad-library-utils

KiCad 官方的库维护工具集：一组纯 Python 命令行工具，用于对 KiCad 官方符号库、封装库执行 KLC（KiCad Library Convention）规则检查、库表一致性校验、跨版本对比与符号生成，是 KiCad 官方库仓库 GitLab CI 的质量门禁程序。

## 功能概述

- `klc-check/`：KLC 规则检查器主体
  - `check_symbol.py` / `check_footprint.py`：符号/封装逐规则检查（`--unittest` 驱动上游自带测试用例）
  - `check_lib_table.py`：库表（sym-lib-table / fp-lib-table）与库文件集合一致性
  - `comparelibs.py`：与上一版本的规则结果对比（CI 门禁用）
- `common/`：s-expression 解析、符号/封装数据模型、规则基类与着色输出（被上述工具以相对路径 `../common` 引用）
- `tools/`：库打包、格式转换等辅助工具（部分依赖可选第三方库）
- `symbol-generators/`：从 CSV 批量生成符号
- `html-diff/`：检查结果的 HTML 差异视图
- `scripts/`：仓库维护脚本

## OHOS 适配

- 本包为纯 Python 工具集：无 C/C++ 编译单元、无 CMake、非 pip 包，因此配方没有任何构建步骤，安装语义是**整体保留上游源码树布局**（脚本以 `os.path.dirname(__file__)/../common` 相对引用公共模块，不能拆散安装）。
- 核心检查路径（`common/` + `klc-check/`）仅依赖 Python 标准库；`tools/`、`symbol-generators/`、`html-diff/`、`scripts/` 中的部分脚本按需引用 bs4/click/requests/Pillow 等可选第三方库，这些不在本包的依赖闭包内（使用对应子目录时需自行准备）。
- 在 OHOS PC 上建议统一以 `python3 -B` 调用（关闭字节码写入，保持已安装包目录卫生：不在包内遗留 `__pycache__`）。上游测试体系为标准库 `unittest`，不需要 pytest。
- 与 Linux 的差异：无平台相关代码路径；真机（aarch64，Python 3.12.9）已实测上游符号/封装 unittest 全部通过。

## 依赖关系

- 运行依赖：python3（>= 3.8；OHOS PC 3.12.9 实测）；核心路径仅标准库
- 可选依赖：colorama（彩色输出，缺失时自动降级）、以及 tools/ 等子目录的可选第三方库（见上）
- 编译依赖：无

## 参考资料

- 上游仓库：<https://gitlab.com/kicad/libraries/kicad-library-utils>
- KiCad 官方库：<https://gitlab.com/kicad/libraries/kicad-symbols> / <https://gitlab.com/kicad/libraries/kicad-footprints>
- KLC 规则文档：<https://dev-docs.kicad.org/en/python-library-conventions/>
