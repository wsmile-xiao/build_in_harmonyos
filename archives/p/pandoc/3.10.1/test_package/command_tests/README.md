# command_tests — 上游命令测试精选用例（AI 补充设计）

为回应审查意见「能否用别的测试 / 让 AI 补充设计测试用例」，将 pandoc 上游
命令测试套件（`test/command/`，共 1177 个用例，由 `test/Tests/Command.hs`
通过 hspec 驱动）中的 **51 个代表性用例**移植为可独立执行的测试套件，
随 `test_package` 在鸿蒙 CI 环境实跑，逐用例与上游期望输出做字节级比对。

## 目录结构

```
command_tests/
├── run_command_tests.sh   # 解析器 + 执行器
└── cases/                 # 51 个上游命令测试文件
```

## 用例格式（与上游 Command.hs 一致）

每个 `cases/*.md` 文件结构：

    % pandoc <args>          ← 命令行
    <输入行...>
    ^D                       ← 输入结束分隔符
    <期望输出行...>          ← 上游期望输出

## 执行方式

```bash
# 直接运行（pandoc 需在 PATH 中，conanrun 环境已注入）
bash run_command_tests.sh

# 或指定 pandoc 二进制
PANDOC=/path/to/pandoc bash run_command_tests.sh
```

通过 `test_package/test.sh` 接入 `conan create`（L1 测试执行验证）。

## 精选标准

- 单命令块（每文件恰好 1 个 `% pandoc` 命令）且结构完整（恰好 1 个 `^D`）
- 文本输出格式（排除 docx/epub/opendocument/slides 等二进制/复合输出）
- 无外部资源依赖（不引用 `command/*.csl`、图片、docx 模板等外部文件）
- 不依赖 `--citeproc`（交付静态二进制 Features 为 `+server +lua`，无 `+citeproc`）
- 期望输出不含 stderr 行（`2>` 前缀），避免环境相关警告干扰字节比对

## 覆盖范围

51 个用例覆盖 30+ 种 reader/writer 组合：markdown、latex、html、rst、org、
mediawiki、docbook、man、typst、jats、texinfo、ms、textile、dokuwiki、
bibtex、biblatex、csljson、gfm、native、asciidoc、markdown_strict、
markdown_mmd 等，含表格、引文、YAML 元数据、代码块语法高亮等典型转换路径。

## 实跑结果（鸿蒙，交付二进制）

```
结果: PASS=51 FAIL=0 SKIP=51 - 51
✅ 命令测试套件全部通过
```

用例文件版权归上游 pandoc 项目（GPL-2.0-or-later，与交付二进制同源），
仅作测试用途随配方分发。
