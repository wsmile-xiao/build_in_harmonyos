# aa3d

**ASCII art 立体图生成器**（ASCII-3D-2000 技术演示，来自 AA-Project）

aa3d 将简单的文本文件 3D 深度图（由空格和数字组成）转换为随机点 ASCII 立体图（random dot stereogram）。使用"对眼"或"平行眼"观看即可看到立体效果。

## 用法

```bash
aa3d [options] < depth.txt > output.txt
```

| 选项 | 说明 |
|------|------|
| `-w width` | 图像宽度（默认 80） |
| `-s step` | 重复序列步长（默认 12） |
| `-t text` | 用于生成背景的文本 |
| `-r` | 关闭随机文本放置 |
| `-f file` | 从文件读取深度图 |
| `-d` | 使用数字代替字母生成背景 |
| `--version` | 输出版本信息（适配补丁添加） |
| `--help` | 输出帮助信息（适配补丁添加） |

示例：

```bash
aa3d -w 120 -d < pyramid
```

## 构建

- 构建系统：纯 Makefile（隐含规则 `aa3d: aa3d.c`），无 configure 脚本
- 版本：1.0（1998 年发布）
- 许可证：GPL-2.0-or-later（源自 XaoS，见 aa3d.c 头注释）
- 源码：https://sourceforge.net/projects/aa-project/files/aa3d/1.0/aa3d-1.0.tar.gz

## OHOS 适配

- 添加 `--version` / `--help` 选项（原程序无，用于通过 Conan L2 冒烟门禁）
- 补充 `#include <string.h>`（消除 strcmp/strlen 隐式声明告警）
