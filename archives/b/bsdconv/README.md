# bsdconv — OpenHarmony 编译档案

## 软件简介
bsdconv 是一个字符编码转换工具，纯 C 实现，无外部依赖。提供基于 `from:inter:to` 流水线语法的编码/过滤/转换 DSL，支持 UTF-8/BIG5/GB2312 等数百种字符集与过滤器模块。

## OHOS 适配要点
- 纯 Make 构建（无 configure 脚本），使用 `make CC=clang` 直接编译
- **上游 VLA off-by-one 修复**（`bsdconv_unpack`）：`phase_off[i+1]` 数组越界写导致 3 阶段转换（如 `ASCII:COUNT:ASCII`）在 clang 15 下 EINVAL，需 `phase_off[i+2]`（补丁 0002）
- **SONAME 修复**：上游 Makefile 链接 libbsdconv 时未加 `-Wl,-soname`，补丁 0001 补齐，满足 CI L5a 门禁
- OHOS `uname -s` 返回 `HarmonyOS`（非 Linux），Makefile 的 `-ldl` 分支不触发；OHOS libc 原生提供 dlopen/dlsym/dlclose，无需 -ldl
- 运行时通过 `BSDCONV_PATH` 环境变量或编译宏定位 `share/bsdconv` 模块目录

## 依赖关系
- 无编译依赖（纯 C）
- 产物：libbsdconv.so.11 + bsdconv/bsdconv-man/bsdconv-mktable/bsdconv-completion + filter/scorer/from/inter/to 模块

## 参考资料
- [bsdconv 上游仓库](https://github.com/buganini/bsdconv)
