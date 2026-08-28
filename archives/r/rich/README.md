# rich

## 软件描述
rich 是一个纯 Python 的终端富文本库，用于在终端输出颜色、表格、进度条、Markdown 等美化内容。

## 功能概述
- **富文本输出**：颜色、样式、对齐的终端文本
- **表格**：`rich.table.Table` 生成美观表格
- **进度条**：`rich.progress.Progress` 任务进度显示
- **Markdown 渲染**：`rich.markdown.Markdown`（需 markdown-it-py，可选）
- **语法高亮**：`rich.syntax.Syntax`（基于 pygments）
- **树/面板/日志**：`rich.tree`/`rich.panel`/`rich.logging`

## OHOS 适配

### 构建方式
- **纯 Python noarch**：无 C/C++ 编译
- 直接拷贝源码 `rich/` 模块（含 `_unicode_data/` 子包）到 `lib/pythonX.Y/site-packages`——绕过 pip 构建（同 python-magic：环境 setuptools egg_info 报 pbr 缺失实测）

### 关键攻坚点
1. **运行时依赖 pygments**：`pygments/2.19.3`（ohpcd 已发布）——语法高亮/代码着色核心
2. **markdown-it-py 可选**：仅 `rich.markdown` 渲染用——本配方最小依赖集未纳入（消费时按需补）
3. **PYTHONPATH 注入**：`package_info()` 把 site-packages 注入 `env_info.PYTHONPATH`——消费者 `import rich` 可用

### 与 Linux 的差异
- 无差异——纯 Python 库，全平台行为一致（终端特性由运行时终端决定）

## 依赖关系
| 依赖 | 版本 | 用途 |
|------|------|------|
| pygments | 2.19.3 | 语法高亮/代码着色（必填） |

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 15.0.0 | built | 2026-08-28 | 纯 Python noarch 适配 |

## 参考资料
- 上游仓库: https://github.com/Textualize/rich
- PyPI: https://pypi.org/project/rich/
