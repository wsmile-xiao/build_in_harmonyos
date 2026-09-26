# ksh93u-m — KornShell 93u+m 的 HarmonyOS 编译档案

## 软件简介
ksh93u+m 是 AT&T Research 的 KornShell 93（ksh93）社区维护版本，
POSIX 兼容的 shell，提供命令行交互、脚本编程、协程、作业控制、C 风格算术等特性。

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.0.10 | published | 2026-09-20 |

## 功能概述
- 命令行交互（emacs/vi 行编辑）
- 脚本编程（变量、函数、数组、算术运算、字符串操作）
- 管道、重定向、命令替换、进程替换
- coprocess（协程）与作业控制
- `shcomp` — ksh 脚本预编译器

## OHOS 适配要点
- 使用自定义 AST Mamfile 构建体系：`CC=clang bash bin/package quiet make`
- 唯一源码补丁：`env_init()` 跳过对 `A__z` 属性标记变量的普通变量导入（防重复导出，纯逻辑修复，无 `__OHOS__` 宏）
- 交付 flat 静态版 `bin/ksh`、`bin/shcomp`（仅依赖 libc.so），自包含无需额外 lib
- 上游 shtests 56 脚本 × 3 变体通过率 99.36%（14515 断言 / 93 错误，全部为平台限制或真实 ksh 行为差异）

## 依赖关系
- 无外部依赖（`requirements()` 为空）；libast/libcmd/libdll/libshell 随源码自带
- 构建期需: bash（POSIX shell）+ clang + ar/nm/ranlib

## 参考资料
- 上游项目: https://github.com/ksh93/ksh
- 许可证: EPL-2.0

## conan 安装
```bash
conan install --requires=ksh93u-m/1.0.10 -r=ohpcd
```
