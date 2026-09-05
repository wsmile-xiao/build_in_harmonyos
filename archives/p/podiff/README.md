# podiff

**GNU gettext PO 文件智能比对工具**（作者 Sergey Poznyakoff，GNU puszcza 项目）

podiff 比较两个 PO 文件（或同一文件的两个版本）之间可翻译字符串与译文的真实差异：比对前自动剔除注释与多余空行、按 msgid 排序、统一字符串排版格式，再调用 `diff(1)` 输出差异——避免翻译者被注释/行号/折行噪音干扰，只看到"译文变没变"。专为翻译工作流设计，可作为 git 的外部 diff 驱动。

## 用法

```bash
podiff [OPTIONS] FILE1 FILE2                # 独立比对模式
podiff [OPTIONS] PATH OLD-FILE OLD-HEX OLD-MODE NEW-FILE NEW-HEX NEW-MODE   # git 外部 diff 模式
podiff -t [OPTIONS] FILE                    # 测试模式：输出规范化后的 PO
podiff -v | --version                       # 版本信息
podiff -h | --help                          # 帮助
```

| 选项 | 说明 |
|------|------|
| `-d CMD` | 指定 diff 命令（默认 `diff`） |
| `-D OPTION` | 传递选项给 diff 命令 |
| `-f` | 忽略 fuzzy 翻译条目 |
| `-k` | 保留用户注释 |
| `-L` | 外部 diff 支持 `-L` 标签（配合 git 使用） |
| `-w NUM` | 限制输出宽度（按字节） |
| `-t` | 测试模式（规范化单文件输出到 stdout） |
| `--version` / `--help` | GNU 长选项（适配补丁添加） |

**退出码**（实测）：

| 场景 | 码 |
|------|----|
| 两文件等价 | 0 |
| 两文件有差异 | 1 |
| 无效命令行选项/参数个数 | 2 |
| PO 语法/解析错误 | 3 |

## 作为 git diff 驱动使用

```ini
# .git/config
[diff "podiff"]
    command = /usr/bin/podiff -D-u -L
```

```gitattributes
# 仓库中 PO 文件所在目录的 .gitattributes
*.po diff=podiff
```

之后 `git diff`/`git log -p` 对 .po 文件自动显示译文级智能差异。

## 构建

- 构建系统：平铺 Makefile（无 configure），产物单二进制 `podiff` + 手册页
- 版本：1.4（2022-10-21 发布，上游最新）
- 许可证：GPL-3.0-or-later
- 依赖：纯 C，零第三方依赖（仅 libc；运行时比对调用系统 `diff`）
- 官方源码：https://download.gnu.org.ua/pub/releases/podiff/podiff-1.4.tar.gz
- 上游官网：https://puszcza.gnu.org.ua/software/podiff/

## OHOS 适配（1.4）

- **TMPDIR 支持**：上游临时目录硬编码 `/tmp`（OHOS 只读，E002），比对模式必崩；适配为优先读 `TMPDIR` 环境变量
- **上游 UB 修复**：`int ignore_rc` 未初始化导致"有差异"退出码恒 0（文档承诺 1）；初始化修复
- **GNU 长选项**：新增 `--version`/`--help`（getopt_long），满足冒烟测试惯例
- **Makefile 可移植性**：硬编码 `cc` 改为 `$(CC)`（`CC ?= cc` / `CFLAGS ?= -ggdb`），Conan 工具链 CC/CFLAGS 可注入
