# pdftoipe

把 PDF 文件转换成 Ipe 绘图编辑器可编辑的 XML 文档的命令行工具。

## 项目信息

- **主页**: https://github.com/otfried/ipe-tools
- **源码**: https://github.com/otfried/ipe-tools（`pdftoipe/` 子目录，无独立仓库）
- **许可证**: GPL-2.0-or-later
- **上游依赖**: poppler >= 0.86（含 C++ 私有头）

## 描述

pdftoipe 读取任意 PDF 文件，把其中的矢量图形与文字转换为 Ipe 7 格式的 XML
（`.ipe`），转换后的文件可直接在 Ipe 中打开与编辑。图形部分转换质量很高；
文字部分受 Ipe 文本模型所限，只做近似还原（上游作者的原始表述）。

## 主要功能

- PDF → Ipe 7 XML 转换（`<ipe version="70000">`）
- 页面范围选择（`-f` / `-l`）
- 文字处理策略：`-math`（全部文字转数学公式）、`-literal`、`-notext`（丢弃文字）、
  `-notextsize`、`-merge`（相邻文字合并力度）、`-unicode`（Unicode 处理级别）
- 加密 PDF 口令（`-opw` / `-upw`）
- `-q` 静默模式

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁 | 说明 |
|------|------|---------|------|------|
| 7.2.29.2 | built | 2026-09-21 | 0 | ipe-tools tag `v7.2.29.2`；源码零补丁，仅注入 clang++ 与 poppler/freetype 路径 |

## 依赖

- poppler/25.12.0@ohpcd/stable（Conan；提供 `include/poppler` 私有头与 `libpoppler.so`）
  - 传递依赖：freetype/2.14.3、zlib/1.3.1.1

## 编译环境

- Clang 15.0.4 / GNU Make 4.4.1 / Conan 2.29.1
- Profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, compiler=clang/15, libcxx=libc++, build_type=Release）
- 构建系统：上游 Makefile（`make -j1`），源码零补丁

## 使用说明

```bash
# 转换（默认输出同目录同名 .ipe）
pdftoipe input.pdf

# 指定输出文件
pdftoipe input.pdf output.ipe

# 只转第 2~5 页，且丢弃所有文字
pdftoipe -f 2 -l 5 -notext input.pdf out.ipe
```

运行期需要 `libpoppler.so` 与 `libfreetype.so.6`：通过 Conan 的 `conanrun` 环境
（`source conanrun.sh`）或自行设置 `LD_LIBRARY_PATH` 指向依赖包 `lib/` 目录。

## CI 合规

- L0: PASS | L1: PASS | L2: SKIP（上游 `-h/--help` 以退出码 1 结束，无 `--version`；非阻塞） | L4: PASS | L5: PASS
- JC（杂项/原子性）: PASS
- 总体: SUCCESS

## 测试

上游 pdftoipe 组件无测试目标（实测 `make -n check` 为 `No rule to make target`），
适配后补全 11 项断言：消费者用例 7、鸿蒙特有测试 2、PC 特有测试 2（详见
`7.2.29.2/notes.md` 与 `7.2.29.2/test_package/MANIFEST.yml`）。
