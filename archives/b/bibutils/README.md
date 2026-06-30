# bibutils

Bibliography conversion utilities — 文献格式转换工具集。

## 简介

bibutils 是一组命令行工具，用于在各种参考文献格式之间进行转换。支持的目标格式包括 MODS XML 作为中间格式，可在 BibTeX、BibLaTeX、EndNote、RIS、NBIB、ISI、Word 2007 bibliography、COPAC、EBI 等格式之间互转。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 7.2 | built | 2026-06-25 |

## 工具列表（21 个二进制）

### 转入工具（→ MODS XML）
- `bib2xml` — BibTeX → MODS XML
- `biblatex2xml` — BibLaTeX → MODS XML
- `copac2xml` — COPAC → MODS XML
- `ebi2xml` — EBI → MODS XML
- `end2xml` — EndNote → MODS XML
- `endx2xml` — EndNote XML → MODS XML
- `isi2xml` — ISI → MODS XML
- `med2xml` — MEDLINE → MODS XML
- `nbib2xml` — NBIB → MODS XML
- `ris2xml` — RIS → MODS XML
- `wordbib2xml` — Word 2007 bibliography → MODS XML

### 转出工具（MODS XML →）
- `xml2ads` — MODS XML → ADS
- `xml2bib` — MODS XML → BibTeX
- `xml2biblatex` — MODS XML → BibLaTeX
- `xml2end` — MODS XML → EndNote
- `xml2isi` — MODS XML → ISI
- `xml2nbib` — MODS XML → NBIB
- `xml2ris` — MODS XML → RIS
- `xml2wordbib` — MODS XML → Word 2007 bibliography

### 其他工具
- `bibdiff` — 比较两个参考文献文件
- `modsclean` — 清理/规范化 MODS XML

## 主页

https://sourceforge.net/p/bibutils/home/Bibutils/

## 许可证

GPL-2.0-only

## 构建信息

- **构建系统**: 自定义 configure 脚本（非标准 autotools）
- **语言**: C
- **依赖**: 无
- **编译器**: clang 15.0.4
- **平台**: aarch64 OpenHarmony (HongMeng Kernel 1.12.0)
