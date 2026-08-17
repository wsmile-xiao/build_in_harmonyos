# pandoc

通用文档转换器（universal markup converter），支持 Markdown、HTML、LaTeX、
PDF、docx、epub 等数十种标记格式互转，广泛用于文档处理流水线。

- 官网: https://pandoc.org
- 源码: https://github.com/jgm/pandoc
- 许可: GPL-2.0-or-later

## 鸿蒙适配说明

pandoc 为 Haskell 项目（cabal/ghc 构建）。鸿蒙 PC 为纯 musl 环境，
GHC 官方 bindist 均为 glibc 动态链接（缺少 /lib/ld-linux-aarch64.so.1），
无可用 GHC 工具链（知识图谱 E105/E172 平台限制）。

本适配按 use-binary-release 回退路径交付 pandoc 官方 **linux-arm64 静态
musl 二进制**（纯静态 ELF，无解释器），经 ELF 签名后在鸿蒙 aarch64 上直接运行。

## 版本

- 3.10.1（当前）
