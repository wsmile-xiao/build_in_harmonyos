# speg

**speg** — avakar 开发的带记忆化的 PEG 解析器解释器（pure Python，MIT License）。
通过 `speg.peg(text, rule)` 把文本按规则函数解析为结构化结果；解析失败抛 `speg.ParseError`。

## 功能概述

- 纯 Python 实现，无任何 C/C++ 扩展、无第三方运行时依赖（Python 2.7/3.x 兼容）
- 规则即函数：`p(regex)` 消费 token、`p.opt(...)` 可选、`p.not_(...)` 负向前瞻、`p.eof` 结尾判断
- 带记忆化（memoization）的 PEG 解析，支持语义动作回调与变量（`p.set/get`）

## OHOS 适配

- 纯 Python 库——**无编译**。Conan 配方 `build()` 为 no-op，`package()` 把 `speg/` 目录
  拷贝到 `lib/python3/`，`package_info()` 无 libs（s3transfer 纯 Python 范式）
- `package_type = "python-require"`（避免 L0k/R38 误判为 CLI 工具；speg 无任何可执行文件，
  **不需要 commands.json**）
- 消费者通过 `PYTHONPATH=<pkg>/lib/python3` 后 `import speg` 使用
- 上游 v0.3 **无测试文件**（git tag v0.3 树 + PyPI sdist 双路核验）；其 CI 仅 `import speg` 冒烟

## 依赖关系

- 编译依赖：无（无编译）
- 运行依赖：无（纯 Python，标准库 `re`/`sys`）

## 参考资料

- 上游仓库：https://github.com/avakar/speg
- PyPI：https://pypi.org/project/speg/
