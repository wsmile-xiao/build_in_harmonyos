# CWEBx — 文学编程文档系统（ANSI C 分支）

## 简介

CWEBx 是 Marc van Leeuwen 维护的 CWEB 分支，基于 Levy/Knuth 的 CWEB 2.1 与 Frank Jensen
的 ANSI C 版本发展而来，完整支持 ANSI/ISO C，并对 C++ 提供合理支持。它与仓库里的 `cweb`
（Levy/Knuth 分支，包名 `cweb`）是**同源但不同的两个分支**，可执行文件名也不同：CWEBx 用
`ctanglex` 与 `cweavex`，以避免与系统里可能同时存在的 `ctangle`/`cweave` 冲突。

文学编程把文档（TeX）与代码（C）写在同一个 `.w` 源文件中：

- **ctanglex**：从 `.w` 提取可编译的 `.c`
- **cweavex**：从 `.w` 提取可排版的 `.tex`

CWEBx 相对 cweb 的额外能力包括 `@d`/`@f` 等记号处理、变更文件（change file）机制，以及
用 `-l` 控制是否输出 `#line` 与 `/*:N*/` 段号标记。

## 依赖

无第三方依赖，只需要一个 ANSI C 编译器与 libc。CWEBx 自身用 CWEB 写成，因此发行包附带
`common.c`/`common.h`/`ctangle.c` 作为自举产物；`cweave.c` 不随包提供，必须由构建出的
`./ctanglex` 从 `cweave.w` 生成。

## OHOS 适配要点

- **构建系统**：raw Makefile。发行包里的 `./configure` 只是一句「不需要配置，直接 make」的
  提示脚本（82 字节），按 autotools 处理会在 configure 阶段走偏。
- **自举与签名**：`make cweb` 先编出 `ctanglex`，再用它生成 `cweave.c` 并编出 `cweavex`。
  OHOS 要求可执行 ELF 带 `.codesign` 段，实测 SDK clang 在链接阶段已经写入，因此不需要
  额外的 `binary-sign-tool` 步骤（早期 cweb 归档里的手工签名记录属于旧工具链，已不适用）。
- **构建目标**：默认 `all` 目标包含 `doc` 与 `listings`，会对 `manual.tex` 调用 TeX，平台无
  TeX，因此配方只构建 `cweb` 目标。
- **安装**：`prefix` 与 `CC` 都可以用命令行变量覆盖，`install` 目标自己创建 `bin` 目录，
  无需补丁即可完成 staging 安装。
- **上游测试**：`make check` 只有一行 echo；`make cautiously` 是真正的自举自检，但其 recipe
  调用 `./ctanglex` 时未传 `-l`，与随包生成物的产生参数不一致，在 x3.52 上必然失败。详见
  `3.52/notes.md`。

## 安装文件

| 文件 | 说明 |
|------|------|
| bin/ctanglex | 从 .w 提取 C 源码 |
| bin/cweavex | 从 .w 提取 TeX 文档 |
| share/texmf/tex/generic/cwebxmac.tex | CWEAVE 输出所需的 TeX 宏 |
| share/texmf/tex/generic/cwebcmac.tex | 兼容模式附加 TeX 宏 |
| share/texmf/tex/generic/cwebhmac.tex | 生成超链接的可选 TeX 宏 |
| share/man/man1/cweb.1 | 手册页 |

## 已知限制

- 平台无 TeX 发行版，`cweavex` 产出的 `.tex` 无法在本机直接排版成 dvi/PDF。
- 上游 README 自称「version 3.51 at the time of writing」是过期文字；真实版本由 `intro.inc`
  的 `\def\currentCWEBxversion{x3.52}` 定义，并由 `ctanglex --version` 确证为 x3.52。
