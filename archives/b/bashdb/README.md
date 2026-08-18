# bashdb — OpenHarmony 编译档案

## 软件简介
bashdb 是 GNU bash 调试器（GNU bash debugger），提供类似 gdb 的交互式调试能力，
用于调试 bash 脚本：设置断点、单步执行、查看/修改变量、显示调用栈等。

## 功能概述
- 交互式调试 bash 脚本
- 断点（break）、条件断点
- 单步（step/next）、继续（continue）、运行到行（tbreak）
- 变量查看（info variables）、表达式求值（eval）
- 调用栈回溯（backtrace）
- 源码查看（list）、搜索（search）
- watchpoint（watch）

## OHOS 适配要点
- configure.ac 的 bash 版本检查扩展支持 5.2/5.3（制品仓 bash 为 5.3）
- HarmonyOS 拒绝通过 shebang 直接 exec 脚本文件 → bashdb 需 `bash bashdb` 显式执行
- `/dev/fd` 不可访问 → `info variables` 的进程替换改为 here-string
- `/tmp` 只读 → 调试器临时目录默认使用 `$TMPDIR`
- config.status 的 `mktemp -d` 权限异常 → mktemp wrapper 强制 mkdir fallback
- 测试框架 shunit2 phantom 文件去掉 shebang；集成测试 LOG_COMPILER=bash

## 依赖关系
- 运行时依赖: bash（支持 --debugger，制品仓 bash/5.3 已编译）
- 构建期依赖: autoconf/automake（autogen.sh 生成 configure）

## 参考资料
- [bashdb 官方仓库](https://github.com/Trepan-Debuggers/bashdb)
- [bashdb 官网](https://bashdb.sourceforge.net/)

## 版本历史
- 5.2-1.2.0（2026-08-14）: 首次适配 OpenHarmony PC，published
