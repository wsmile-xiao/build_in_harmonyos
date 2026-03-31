# 鸿蒙平台开源软件编译兼容性总览

> 最后更新：2026-03-30
> 已收录软件：26 款 / 29 个版本

## 📊 总体统计

| 指标 | 数量 |
|------|------|
| 收录软件 | **26** 款 |
| 软件版本 | **29** 个 |
| ✅ 完全成功 | 19 |
| ⚠️ 部分成功 | 9 |
| ❌ 编译失败 | 0 |

| 构建系统 | 数量 |
|----------|------|
| Autotools | 25 |
| CMake | 1 |
| Makefile | 1 |
| Custom Perl | 1 |
| Script | 1 |

## 📋 软件兼容性一览

| 软件 | 版本 | 状态 | 兼容性 | 构建系统 | 补丁数 | 依赖 | 详情 |
|------|------|------|--------|----------|--------|------|------|
| **automake** | 1.16.5 | ✅ 完全成功 | 🟢 高 | Autotools | 1 |  | [📄](archives/a/automake/1.16.5/) |
| **bash** | 5.3 | ✅ 完全成功 | 🟢 高 | Autotools | 1 |  | [📄](archives/b/bash/5.3/) |
| **bzip2** | 1.0.8 | ✅ 完全成功 | 🟢 高 | Makefile | 0 |  | [📄](archives/b/bzip2/1.0.8/) |
| **coreutils** | 9.10 | ⚠️ 部分成功 | 🟡 中 | Autotools | 2 |  | [📄](archives/c/coreutils/9.10/) |
| **file** | 5.45 | ✅ 完全成功 | 🟢 高 | Autotools | 0 |  | [📄](archives/f/file/5.45/) |
| **gawk** | 5.3.0 | ✅ 完全成功 | 🟢 高 | Autotools | 1 |  | [📄](archives/g/gawk/5.3.0/) |
| **gdbm** | 1.23 | ✅ 完全成功 | 🟢 高 | Autotools | 2 |  | [📄](archives/g/gdbm/1.23/) |
| **help2man** | 1.49.3 | ✅ 完全成功 | 🟢 高 | Script | 0 |  | [📄](archives/h/help2man/1.49.3/) |
| **htop** | 3.4.1 | ⚠️ 部分成功 |  | Autotools | 3 |  | [📄](archives/h/htop/3.4.1/) |
| **jq** | 1.7.1 | ✅ 完全成功 | 🟢 高 | Autotools | 2 |  | [📄](archives/j/jq/1.7.1/) |
| **libffi** | 3.4.4、3.5.2 | ✅ 完全成功 | 🟢 高 | Autotools | 2 |  | [📄](archives/l/libffi/3.5.2/) |
| **libpipeline** | 1.5.8 | ✅ 完全成功 | 🟢 高 | Autotools | 2 |  | [📄](archives/l/libpipeline/1.5.8/) |
| **libtool** | 2.4.7 | ✅ 完全成功 | 🟢 高 | Autotools | 1 |  | [📄](archives/l/libtool/2.4.7/) |
| **lzma** | 5.6.2 | ✅ 完全成功 | 🟢 高 | Autotools | 1 |  | [📄](archives/l/lzma/5.6.2/) |
| **man-db** | 2.13.1 | ✅ 完全成功 | 🟡 中 | Autotools | 4 |  | [📄](archives/m/man-db/2.13.1/) |
| **ncurses** | 6.4 | ✅ 完全成功 | 🟢 高 | Autotools | 1 |  | [📄](archives/n/ncurses/6.4/) |
| **openssl** | 1.1.1w | ✅ 完全成功 | 🟢 高 | Custom Perl | 1 |  | [📄](archives/o/openssl/1.1.1w/) |
| **patch** | 2.7.6 | ⚠️ 部分成功 |  | Autotools | 1 |  | [📄](archives/p/patch/2.7.6/) |
| **python** | 3.9.0、3.9.25、3.12.9 | ⚠️ 部分成功 |  | Autotools | 21 |  | [📄](archives/p/python/3.12.9/) |
| **readline** | 8.2 | ✅ 完全成功 | 🟢 高 | Autotools | 1 |  | [📄](archives/r/readline/8.2/) |
| **rsync** | 3.3.0 | ⚠️ 部分成功 |  | Autotools | 2 |  | [📄](archives/r/rsync/3.3.0/) |
| **sed** | 4.9 | ✅ 完全成功 | 🟢 高 | Autotools | 1 |  | [📄](archives/s/sed/4.9/) |
| **strace** | 6.19 | ⚠️ 部分成功 | 🔴 低 | Autotools | 3 |  | [📄](archives/s/strace/6.19/) |
| **tar** | 1.35 | ✅ 完全成功 | 🟢 高 | Autotools | 1 |  | [📄](archives/t/tar/1.35/) |
| **wget** | 1.19.1 | ⚠️ 部分成功 |  | Autotools | 2 |  | [📄](archives/w/wget/1.19.1/) |
| **zlib** | 1.3.1 | ✅ 完全成功 | 🟢 高 | CMake | 0 |  | [📄](archives/z/zlib/1.3.1/) |

---

*本文档由 `scripts/gen_summary.py` 从编译档案自动生成，请勿手动编辑。*

Copyright (c) 2024-2026 OpenHarmony PC Developer社区