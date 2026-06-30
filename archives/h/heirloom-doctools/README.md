# heirloom-doctools

Heirloom Documentation Tools - 传统 Unix 文档处理工具集，包含 troff/nroff 文档排版系统。

## 描述

heirloom-doctools 是从 OpenSolaris 源码衍生出的文档处理工具，包含：

- **troff**: 文档排版系统
- **nroff**: 终端输出排版
- **tbl**: 表格预处理器
- **pic**: 图片预处理器
- **eqn/neqn**: 数学公式预处理器
- **grap**: 图形预处理器
- **refer**: 文献引用处理
- **vgrind**: 程序美化打印
- **checknr**: nroff 检查工具

## 编译版本

- **191015**: 2019-10-15 发布版本

## 依赖

- flex (lex 替代)
- 无外部库依赖

## 安装路径

- 二进制: ~/usr/local/ucb/
- 库/数据: ~/usr/local/ucblib/
- 手册页: ~/usr/local/share/heirloom-doctools/man/

## 使用示例

```bash
# 使用 nroff 格式化文本
echo ".TL Test Document" | nroff -Tutf8

# 使用 tbl 处理表格
tbl table.ms | troff -ms | dpost > output.ps
```

## 注意事项

1. 此项目不支持 DESTDIR 安装模式
2. 二进制需要 ELF 签名才能在 OpenHarmony 上执行
3. troff/nroff 不支持 --version 参数

## 来源

- 项目主页: http://n-t-roff.github.io/heirloom/doctools.html
- 源码仓库: https://github.com/n-t-roff/heirloom-doctools