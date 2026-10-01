# xmill — XMill（XML 结构化压缩器）

## 软件简介

XMill 是 AT&T Labs Research 的 XML 压缩器（作者 Hartmut Liefke、Dan Suciu，1999）。
它不把 XML 当普通字节流压缩，而是用 SAX 解析器把文档拆开：

- 元素/属性名 → 结构容器（并对路径做字典/FSM 编码）
- 文本内容 → 按**路径表达式**分流到各自的容器（同类数据放在一起，压缩率显著提升）
- 空白字符与 DTD/PI/CDATA 等特殊段 → 独立容器

各容器再用 zlib 压缩。仓库同时提供两个命令行工具：

| 工具 | 作用 | 用法（来自 `Options.cpp:PrintUsage()`） |
|------|------|------------------------------------------|
| `xmill` | 压缩 | `xmill [-i file] [-v] [-p path] [-m num] [-1..9] [-c] [-d] [-f] [-w] file ...` |
| `xdemill` | 解压 | `xdemill [-i file] [-v] [-c] [-d] [-r] [-os num] [-ot] [-oz] file ...` |

- **上游（可达）**: https://github.com/jungsagacity/xmill （AT&T XMill 的镜像，唯一分支 `master`）
- **官方站点**: `www.research.att.com/sw/tools/xmill/` 已下线，存档通道不可达
- **许可证**: AT&T 专有（源码头声明仅供非商业研究使用）

> ⚠️ 版本口径：本目录版本号为请求值 `0.8`，但该快照源码自述版本是
> `XMill 0.7 (30 Nov 99)`（`xmill/src/Options.cpp:459`），上游不存在 0.8 的任何证据。
> 取证过程与结论见 [0.8/notes.md](0.8/notes.md)。

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 依赖 |
|------|------|---------|---------|------|
| 0.8 | built | 2026-10-01 | cmake（补丁新增） | zlib/1.3.2 |

产物（`aarch64` / `os=OHOS` / clang 15 / libc++ / cppstd 17）：

| 文件 | 大小 | sha256（前 16） |
|------|------|------------------|
| `bin/xmill` | 264,704 B | `8795bb2bf6b0be0…` |
| `bin/xdemill` | 260,608 B | `072d0395d111d9c…` |

## OpenHarmony 适配要点

| 补丁 | 说明 |
|------|------|
| `0001-CMakeLists.txt.patch` | **新增 CMakeLists.txt**：上游只有 MSVC 工程，没有任何可用的构建系统；本补丁提供 cmake 构建面并产出 `xmill` / `xdemill` 两个目标 |
| `0002` / `0008` | zlib 头文件由 `"../zlib/zlib.h"`（含 Windows 风格 `"..\zlib\zlib.h"`）改为 `<zlib.h>`，消费制品仓的 `zlib/1.3.2`，不再编译树内 vendored zlib 1.1.3 |
| `0003` | 删除手写 `extern int errno;`，改为 `#include <errno.h>`（musl 上 errno 是宏，手写声明会链接失败） |
| `0004` | `LabelDict::PrintLabel()` 不再解引用压缩器里为 NULL 的解压字典（否则 `xmill -v` 段错误） |
| `0005` | `WordAlignMemBlock()` 的 32 位掩码 `0xFFFFFFFC` 在 LP64 上截断指针 → `xdemill` 段错误；改为按指针宽度取掩码 |
| `0006` | `Output.hpp` 非 WIN32 分支补 `<stdio.h>` |
| `0007` | 移除 C++17 已删除的 `register` |
| `0009` | 还原命令行入口 `main()`（镜像把它改成了忽略 argv 的硬编码调试驱动）+ 两处三元表达式显式转 `char *` |

根因分析、首个错误与验证证据见 [0.8/notes.md](0.8/notes.md)；
上游测试执行结果见 [0.8/reports/test-report.md](0.8/reports/test-report.md)。

## 产物验证摘要

```
# 上游样例（唯一随包数据）
xmill   sprot1_2.xml  → sprot1_2.xmi   与上游自带 .xmi 逐字节一致 (sha256 f6e1a0ff…)
xdemill sprot1_2.xmi  → sprot1_2.xml   与原始 XML 逐字节一致    (sha256 b98e10f2…)

# 自建端到端矩阵：20/20 PASS（CLI 选项、压缩级别、往返、OHOS 二进制形态）
# test_package：7/7 PASS（含 2 项鸿蒙特有断言）
```
