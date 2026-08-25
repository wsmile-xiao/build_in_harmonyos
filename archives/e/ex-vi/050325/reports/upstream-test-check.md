# 上游测试用例检查 — ex-vi 050325

## 检查结论

ex-vi 050325 **没有上游测试套件**。

### 检查范围

| 检查项 | 结果 |
|--------|------|
| 源码中 `test/` / `tests/` 目录 | 不存在 |
| Makefile `test` / `check` 目标 | 不存在 |
| `.sh` 测试脚本 | 不存在 |
| `.expected` / `.golden` 输出文件 | 不存在 |
| README 中的测试说明 | 仅提到终端兼容性（xterm/rxvt），非测试套件 |
| SourceForge 独立测试包 | 不存在 |

### 原因分析

ex-vi 是 Gunnar Ritter 对传统 Unix vi/ex 的源码级移植，属于经典 Unix 工具移植项目。这类项目通常不附带自动化测试套件——原始 Unix vi（BSD/CSRG）本身就没有测试框架，移植者保留了这一传统。源码包仅包含编辑器本体和 man 手册，无任何测试基础设施。

## 替代方案：自建 Smoke Test 套件

由于上游无测试用例，按 SKILL L2 平台 smoke test 要求，自行设计并运行了一套覆盖 ex/vi 核心功能的测试套件（22 项测试，10 个类别），全部通过。

详细结果见 `smoke-test-report.md`。
