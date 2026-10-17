# CDE 1.0.0 - Static Bundler

## 适配说明

- 本库从原版 CDEpack（动态 ptrace 引擎）改为交付 CDE 1.0.0 静态/离线辅助 CLI
  `cde-static-bundler`。
- 构建：`clang -Wall -Wextra -O2 -static`（单文件编译，无外部依赖）。
- 产物：静态 AArch64 ELF，903104 B，无 PT_INTERP，0 DT_NEEDED。
- 测试：R29 69/69 测试闭环通过；R32 Conan 包消费者 3/3 通过。
- 源码为本地归档内嵌组件（`tools/cde-static-bundler/cde-static-bundler.c`），
  无外部上游 tarball。原始 CDEpack 上游归档仅用于参考，不用于本构建。
---

**编译结束**: 2026-08-22 22:15
**最终状态**: built
