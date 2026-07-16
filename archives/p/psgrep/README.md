# psgrep

psgrep is a small Bash utility that wraps the common `ps aux | grep` process-search workflow and filters out helper `psgrep`/`grep` processes from the result.

## 功能概述
- 使用 `ps` 输出作为数据源，通过 `grep` 搜索进程列表。
- 支持 BSD/Linux/custom `ps` 输出格式。
- 支持大小写忽略、扩展正则、Perl 正则和 PID-only 输出。
- 提供 `psgrep` 命令和 `psgrep(1)` man page。

## OHOS 适配
- 项目是纯 Bash 脚本，无 C/C++ 编译步骤。
- 上游 `psgrep` 与 `install.sh` 已使用 `#!/usr/bin/env bash`，适配 OHOS 无 `/bin/bash` 的环境。
- 打包时直接复制 `psgrep` 到 `bin/`，复制 `psgrep.1` 到 `share/man/man1/`。
- `psgrep -v` 输出版本信息后按上游语义返回退出码 2，测试中显式接受该退出码。

## 依赖关系
- 编译依赖：无。
- Conan 依赖：无。
- 运行时依赖：Bash，以及系统提供的 `ps`、`grep`、`awk`、`head`、`which`。

## 参考资料
- Homepage: https://jvz.github.io/psgrep/
- Source: https://github.com/jvz/psgrep
- Release: https://github.com/jvz/psgrep/archive/refs/tags/1.0.9.tar.gz
