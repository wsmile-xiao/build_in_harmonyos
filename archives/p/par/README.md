# par

## 简介

par（Paragraph reflow）是一个智能段落重排版工具，专为电子邮件格式化设计。它能将段落文本按照指定的宽度重新排版，同时智能处理前缀（如引用标记 `>`）、缩进、悬挂缩进等复杂排版场景。

## 功能概述

- 段落宽度重排（默认 72 字符宽度）
- 智能前缀保留（支持多层引用嵌套）
- 悬挂缩进处理
- 大小写智能识别
- 对齐模式（左对齐/两端对齐）
- 多语言字符集支持（Unicode/locale）
- fit 模式（自动选择最佳宽度）

## OHOS 适配

### 适配要点

- par 使用 `protoMakefile` 构建系统（非标准 autotools/cmake），需要通过变量覆盖指定编译器：
  ```bash
  make -f protoMakefile CC='clang -fPIC -O2 -c' LINK1=clang LINK2=-o
  ```
- 无 `make install` 目标，需手动安装二进制和 man 页面：
  ```bash
  cp par $DEFAULT_PREFIX/bin/par
  cp par.1 $DEFAULT_PREFIX/share/man/man1/par.1
  ```
- 版本查询使用布尔选项格式：`echo "" | par version`（不支持 `--version`）
- G0 干净构建验证需 `hints/clean-verify-hints.yaml` 自定义构建/安装命令

### 已知问题

- locale 相关测试（en_US/he_IL）在 musl 系统上会失败，因 musl locale 支持有限
- `/tmp` 目录只读（E002），locale 测试初始化受限
- 核心功能 36/36 测试全部通过，locale 问题不影响正常使用

### 与 Linux 的差异

- 构建系统为 protoMakefile（Linux 上通常也是），在 HarmonyOS 上需要 clang 编译器变量覆盖
- musl libc 的 locale 支持比 glibc 更有限，影响 Unicode 字符分类测试

## 依赖

### 编译依赖
- 无外部依赖，纯 ANSI C 实现
- 编译器：clang

### 运行依赖
- 无（单文件可执行程序）

## 功能验证

```bash
# 版本验证
echo "" | par version
# 输出: par 1.53.0

# 基本段落重排
echo "This is a long paragraph that needs to be reformatted to fit within a specific width." | par 40
# 输出: 自动重排为40字符宽度

# 引用段落重排
echo "> This is a quoted paragraph that should be reformatted while preserving the quote prefix." | par 60
# 输出: 保留 > 前缀的重排结果
```

## 参考

- 官方仓库：https://bitbucket.org/amc-nicemice/par
- 手册页：par.1（随源码附带）
- 详细文档：par.doc（随源码附带）