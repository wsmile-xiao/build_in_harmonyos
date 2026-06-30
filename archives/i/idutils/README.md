# idutils

ID database and query tools — 一个用于标识符数据库管理和查询的工具集。

## 简介

idutils 是 GNU 项目中的一组工具，用于创建和维护标识符数据库，并在其中快速查找标识符。它可以从多种编程语言的源代码中提取标识符，建立索引数据库，然后通过多种方式查询。

## 核心命令

| 命令 | 功能 |
|------|------|
| mkid | 创建标识符数据库 |
| lid | 查询标识符（支持进制和范围查询） |
| fid | 通过文件名查找标识符 |
| gid | 通过 grep 模式查找标识符 |
| eid | 通过正则表达式查找标识符 |
| aid | 通过近似匹配查找标识符 |
| fnid | 通过文件名模式查找标识符 |
| xtokid | 显示标识符的词法分析结果 |
| defid | 查找标识符的定义位置 |

## 编译信息

- 版本: 4.6
- 许可证: GPL-3.0-or-later
- 构建系统: autotools
- 官方源码: https://ftpmirror.gnu.org/gnu/idutils/

## 鸿蒙适配

该软件已在 HarmonyOS aarch64 平台成功编译适配，详见对应版本目录中的 notes.md 和 manifest.yaml。
