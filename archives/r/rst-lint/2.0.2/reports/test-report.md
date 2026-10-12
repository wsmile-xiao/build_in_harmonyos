# 测试报告 — rst-lint 2.0.2

> **项目**: rst-lint（PyPI: restructuredtext-lint）
> **测试日期**: 2026-10-02
> **测试环境**: HarmonyOS / OpenHarmony PC aarch64（os=OHOS / os.version=6.0 / arch=armv8 / clang 15）
> **测试类型**: 上游官方测试套件（`test.sh`）+ conan test_package

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游总测试数 | 16 | 100% |
| 通过 (PASS) | 16 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**上游核心功能通过率**: ✅ **100%**

| 指标 | 数值 | 说明 |
|:----:|:----:|:------|
| test_package 断言 | 8/8 | 消费者视角（含 1 个 OHOS 平台用例） |

---

## 二、测试结论

### 2.1 总体评价

✅ **全部通过**（上游 16/16、test_package 8/8）

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| `flake8-quotes==3.4.0` 镜像不可获取 | 仅上游 lint 插件（未启用相关选项） | 🟢 |

### 2.3 可用功能清单

```
✅ lint(content)            —— 字符串 reST 检查
✅ lint_file(filepath)      —— 文件 reST 检查
✅ cli `rst-lint <paths>`   —— 文件/目录检查（0=通过，2=存在错误，1=路径不存在）
✅ cli --version / --level / --format text|json / --rst-prolog
```

### 2.4 已知限制

1. 上游 `test.sh` 声明 `flake8-quotes==3.4.0`，该包在 pypi.cnb.cool / pypi.repo.openharmony.cn / pypi.org 均不可获取；上游 flake8 调用未启用 flake8-quotes 选项且 `setup.cfg` 无 flake8 配置段，lint 结果不受影响。
2. 目标为纯 Python，无 ELF 产物，"安全扫描（L4）/ 签名" 不适用。

---

## 三、测试详情

### 3.1 上游测试（`test.sh`：flake8 + nosetests）

命令（真实执行）：

```bash
# PYTHONPATH = <已安装 docutils 0.23> + <源码树>
flake8 --max-line-length=120 restructuredtext_lint     # FLAKE8_EXIT=0
nosetests --nocapture -v                               # Ran 16 tests ... OK (NOSETESTS_EXIT=0)
```

日志：`_task/logs/rstlint_upstream_test.log`

| # | 用例 | 结果 |
|---|------|------|
| 1 | `TestRestructuredtextLint.test_encoding_utf8` | ✅ PASS |
| 2 | `TestRestructuredtextLint.test_invalid_line_mismatch` | ✅ PASS |
| 3 | `TestRestructuredtextLint.test_invalid_link` | ✅ PASS |
| 4 | `TestRestructuredtextLint.test_invalid_target` | ✅ PASS |
| 5 | `TestRestructuredtextLint.test_passes_valid_rst` | ✅ PASS |
| 6 | `TestRestructuredtextLint.test_raises_on_invalid_rst` | ✅ PASS |
| 7 | `TestRestructuredtextLint.test_rst_prolog_basic` | ✅ PASS |
| 8 | `TestRestructuredtextLint.test_rst_prolog_line_offset` | ✅ PASS |
| 9 | `TestRestructuredtextLint.test_second_heading_short_line_number` | ✅ PASS |
| 10 | `TestRestructuredtextLintCLI.test_level_fail` | ✅ PASS |
| 11 | `TestRestructuredtextLintCLI.test_level_high` | ✅ PASS |
| 12 | `TestRestructuredtextLintCLI.test_rst_lint_correct_file` | ✅ PASS |
| 13 | `TestRestructuredtextLintCLI.test_rst_lint_filepaths_not_given` | ✅ PASS |
| 14 | `TestRestructuredtextLintCLI.test_rst_lint_folder` | ✅ PASS |
| 15 | `TestRestructuredtextLintCLI.test_rst_lint_many_files` | ✅ PASS |
| 16 | `TestRestructuredtextLintCLI.test_rst_lint_missing_file` | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 跳过的测试

无。

---

## 四、test_package（消费者视角，含 OHOS 平台用例）

`conan create` 内执行 `test_rst_lint.py`（日志：`reports/w3-local-ci.log`，`_task/logs/rstlint_conan_create.log`）：

| # | 断言 | 结果 |
|---|------|------|
| 1 | import `restructuredtext_lint` + `cli.VERSION == "2.0.2"` | ✅ PASS |
| 2 | `lint()` 干净→0 错误 / 破损→1 WARNING（经 docutils/0.23） | ✅ PASS |
| 3 | `lint_file()` 磁盘文件 | ✅ PASS |
| 4 | `bin/rst-lint --version == 2.0.2` | ✅ PASS |
| 5 | `bin/rst-lint` 干净文件 → exit 0，静默 | ✅ PASS |
| 6 | `bin/rst-lint` 破损文件 → exit 2 + WARNING | ✅ PASS |
| 7 | `bin/rst-lint` 目录输入聚合 `*.rst` | ✅ PASS |
| 8 | **[OHOS]** POSIX entry script（`#!/usr/bin/env python3` + 可执行位）在 OHOS `$TMPDIR` 路径下运行 | ✅ PASS |

---

## 五、测试环境

```
rst-lint 2.0.2 (restructuredtext_lint 2.0.2, VERSION=2.0.2)
Python 3.12.9 (cmd-pkgs)
conan 2.29.1 (OpenHarmony 适配版)
profile: ci/conan/profiles/ohos-aarch64  (os=OHOS/os.version=6.0/arch=armv8/compiler=clang-15/libc++/cppstd=17/Release)
运行时依赖: docutils/0.23 (conan)
测试期依赖: nose-py3==1.8.0 + flake8==7.3.0 (+ mccabe 0.7.0/pycodestyle 2.14.0/pyflakes 3.4.0)
```

---

*报告生成时间: 2026-10-02*
