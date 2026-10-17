# jgraph

Jim Plank 的 jgraph 是一个绘图过滤器：从标准输入（或命令行给出的文件）读取
图形描述语言，向标准输出写出一份 PostScript 文件。它支持散点图、折线图、
柱状图、多图分页、自定义坐标轴/图例/标题、EPS 图形标记等，常用于 LaTeX
文档与报告插图（上游主页附有大量示例输入与输出）。

- 上游：https://web.eecs.utk.edu/~jplank/plank/jgraph/jgraph.html
- 许可：GPL-2.0-or-later（作者 1994 年邮件确认按 GPL 分发）
- 构建系统：POSIX makefile（1997 年 K&R C 源码，无第三方依赖）
- 适配版本：83（HarmonyOS PC / aarch64，ohos-sdk clang 15）

## 命令

```bash
jgraph [ -p | -P | -L | -comments ] [ file ... ]
```

| 选项 | 作用 |
|------|------|
| （无） | 输出紧贴图形的 EPS（仅 `%%BoundingBox` 定位） |
| `-P` | 输出整页 PostScript（平移图形到 8.5x11 页面中央，含 `showpage`） |
| `-L` | 横向（landscape）页面 |
| `-p` | 不绘图，回显解析后的图形描述（show 模式，调试用） |
| `-comments` | 在输出中写入 `%` 注释行 |

不给出文件名时从标准输入读取；`shell:`、`include`、`newpage`、`newcurve eps`
等语言特性见 `man jgraph`。

## OHOS 适配

- 上游 tarball 为 1992–1997 年的 K&R C 源码，clang 15 默认方言下有三类问题，
  均已用最小补丁修复（共 10 个补丁，详见版本目录 `notes.md`）：
  1. 隐式 `int` 函数里的裸 `return;` 被判为错误 → 按上游 8.5 的做法改为
     `void` 过程；
  2. `malloc`/`get_node`/`make_list`/`atof`/`sin` 等未声明函数在 aarch64 上
     按 `int` 截断指针/浮点 → 无条件包含标准头 + 为返回指针的链表原语补声明；
  3. EPS `%%BoundingBox` 的 EOF 检测（`fscanf(...) == NULL`）与 landscape
     平移的 `%f` 传 `int`（64 位可变参数 ABI 下未定义）两处真实缺陷。
- 上游无测试套件（N=0），本适配新增 `test_package/` 消费者测试（25 断言）。
- 平台无差异项：jgraph 只做文本解析与 PS 文本输出，不涉及图形栈、外设或
  系统调用；`-L` 未加 `-P` 时的整页平移在 aarch64 上依赖上述补丁 3。

## 依赖

- 编译：无第三方依赖（libc + libm）。
- 运行：无。

## 参考资料

- 上游主页（含示例、讲义与 man 页）：见上
- Debian 源码包（83-26，orig tarball 与上游 83 内容一致）：
  https://tracker.debian.org/pkg/jgraph
