# bmt 0.6 适配笔记

## 编译环境
- 构建系统: custom（纯脚本，无编译）
- 编译日期: 2026-09-05
- 状态: built
- 上游: https://github.com/tautschnig/bmt tag 0.6 (edff895e25180555cacb8f161b70288d22db73b7)

## 适配概述
bmt（Benchmarking Toolkit）是面向软件分析与验证的基准管理与评测工具集，由 Michael Tautschnig 维护。项目为纯 Shell/Perl 脚本集合，主入口 `cpbm` 通过子命令（unpack/update/init/run/csv/table/graph 等）完成 patch 集管理、并行评测与 LaTeX/HTML 报表生成。无 C/C++ 编译过程。

## 适配方案
- `package_type = application`，仅声明 `os`/`arch`（无需 compiler）。
- `source()` 通过 `conan.tools.files.get` 获取 GitHub 归档，`strip_root=True`。
- `package()` 将 `scripts/cpbm` 安装至 `bin/cpbm`（chmod 755），其余脚本（*.sh、*.pl、VERSION、rules.*）安装至 `share/cpbm/`，与 Debian `debian/install` 布局一致。
- `package_info()` 声明 `bindirs = ["bin"]`、`resdirs = ["share"]`，消费者可通过 `bin/cpbm` 与 `share/cpbm/` 访问完整工具集。
- 无需 OH 平台宏与编译器注入（R33 不适用，纯脚本无需 CC/CXX）。

## 上游测试
- 上游无独立测试套件（仅 `cprover/rules` 驱动的基准执行流程，依赖外部验证工具与基准数据）。已在 `test_package/MANIFEST.yml` 声明 `upstream_tests_exist: false` 并附审计说明。

## 验证
- `cpbm --version` 输出 `0.6`
- `cpbm help` 列出全部子命令
- `share/cpbm/` 下 30+ 脚本与解析器完整安装
- `bash -n` 对主脚本做语法检查
