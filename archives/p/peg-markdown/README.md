# peg-markdown

**PEG 语法实现的 Markdown → HTML/LaTeX/groff_mm/ODF 转换器**（John MacFarlane，`jgm/peg-markdown`）

peg-markdown 用 Ian Piumarta 的 PEG（Parsing Expression Grammar）解析器生成器 `leg` 描述
John Gruber 的 Markdown 语法，实现为可移植的 ANSI C。解析器由 `markdown_parser.leg` 在构建期
生成，运行时依赖 glib-2.0。

## 用法

```bash
markdown [options] [file ...]      # 不给 file 时从 stdin 读取
markdown README.md > readme.html
cat note.md | markdown --to latex
```

| 选项 | 说明 |
|------|------|
| `-v`, `--version` | 输出版本 |
| `-o FILE`, `--output=FILE` | 输出到文件（默认 stdout） |
| `-t FORMAT`, `--to=FORMAT` | 输出格式：`html`（默认）、`latex`、`groff`、`odf` |
| `-s`, `--smart` | 智能标点（straight quotes → curly） |
| `-n`, `--notes` | 支持脚注 |
| `-x`, `--extensions` | 启用扩展语法（fenced code blocks、tables、definition lists、math 等） |
| `--filter-html` | 过滤（转义）输入中的原始 HTML |
| `--standalone` | 输出完整文档（含头尾） |

注：0.4.14 不识别 `--help`，帮助文本由 `markdown` 在参数解析失败时输出（`markdown -h` 亦如此）。

## 构建与依赖

| 依赖 | 版本 | 类型 |
|------|------|------|
| glib | 2.84.0.2 | 编译期 + 运行期（`pkg-config glib-2.0`） |
| pcre2 / zlib / libffi | 10.45 / 1.3.1.1 / 3.4.4 | glib 的传递依赖 |
| peg/leg | 0.1.4（源码内嵌 `peg-0.1.4/`） | 构建期主机工具 |
| tidy-html5 | 5.8.0 | 仅上游测试 `--tidy` 归一化 |

```bash
conan install --requires=peg-markdown/0.4.14 -r=ohpcd
conan run     --requires=peg-markdown/0.4.14 -- markdown --version   # 需在 conanrun 环境内执行
```

## 鸿蒙 PC 适配要点

1. **`markdown.c` 的 `char` → `int` 修复**（`patches/0001-markdown.c.patch`）：上游用 `char`
   变量承接 `fgetc()`，AArch64 上 `char` 默认无符号，EOF(-1) 永不匹配，导致任何输入读取死循环。
2. **构建期内嵌 `peg/leg` 的编译器**：上游顶层 Makefile 硬编码 `CC=gcc`，鸿蒙 worker 只有 clang，
   配方先用 conan 的 C 编译器单独构建 `peg/leg` 再执行主 `make`。
3. **无 install 目标**：0.4.14 的 Makefile 不安装也不产出库文件，本包只交付 `bin/markdown`。
4. **glib 依赖经 `PkgConfigDeps` 注入**：制品自带的 `glib-2.0.pc` 里 `prefix=/`，直接使用会得到
   `-I/include/...` 废路径。
5. **运行期需要 glib**：设备上没有系统 glib，须在 conan 的 run 环境（或部署后的目录树）中运行。

## 上游测试

`MarkdownTest_1.0.3`（John Gruber 官方 1.0.3 用例集，22 个用例）：

```bash
cd MarkdownTest_1.0.3 && perl ./MarkdownTest.pl --script=markdown --tidy
```

实测 21 passed / 1 failed（`Ordered and unordered lists`，上游 README 与 issue #6 已文档化的预期失败）。

## 版本

| 上游版本 | 适配版本 | 状态 |
|---|---|---|
| 0.4.14 | 0.4.14 | built（待 CI 发布） |

## 许可

MIT 或 GPLv2+（双许可，见 `LICENSE`）。

- 上游主页：<https://github.com/jgm/peg-markdown>
- PEG 生成器：<http://piumarta.com/software/peg/>
