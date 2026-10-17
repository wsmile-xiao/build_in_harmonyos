# dot2tex

## 简介

dot2tex 是一个将 Graphviz DOT 文件转换为 LaTeX TikZ/PGF 格式的转换工具。它允许用户在 LaTeX 文档中使用 Graphviz 的布局算法生成高质量图形，同时利用 TikZ/PGF 的排版能力。

## 特性

- 将 Graphviz DOT 文件转换为 TikZ/PGF 格式
- 支持 dot, neato, twopi, circo, fdp 等布局算法
- 支持节点样式、边标签、颜色等属性转换
- 自动处理 LaTeX 数学符号转义
- 支持输出为 standalone TikZ 文件或可嵌入片段

## 安装

### 预编译包安装

```bash
# 下载安装脚本（先下载后执行，避免管道注入风险）
curl -fsSLO https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh
# 验证后执行（必须：检视脚本内容确认 SHA256 校验和）
# install.sh SHA256: 834c87a3c2e0d218205123f53323fd12ce03337b24780675700780973e2013fc
sh install.sh -- dot2tex 2.12.0
```

### 手动安装

```bash
# 安装依赖
pip3 install pyparsing

# 安装 dot2tex
pip3 install dot2tex --prefix=/path/to/install
```

## 使用方法

```bash
# 将 DOT 文件转换为 TikZ
dot2tex input.dot > output.tex

# 指定输出格式
dot2tex --format tikz input.dot > output.tex

# 使用 Graphviz 的 dot 布局
dot2tex --figonly --crop input.dot > output.tex
```

## 运行时依赖

- Python 3.8+
- pyparsing (>=2.0.0)
- Graphviz (可选，用于布局)

## 验证安装

```bash
dot2tex --version
# 或
python3 -c "import dot2tex; print(dot2tex.__version__)"
```

## 相关链接

- 上游仓库：https://github.com/sagemath/dot2tex
- 许可证：MIT

## 编译信息

- 版本：2.12.0
- 编译日期：2026-07-28
- 构建系统：setuptools（纯 Python）
- 平台：OpenHarmony aarch64
