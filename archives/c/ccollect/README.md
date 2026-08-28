# ccollect

ccollect —（伪）增量备份工具，使用硬链接和 rsync 实现不同排除列表的增量备份。
由 Nico Schottelius 开发，纯 POSIX sh 编写。

- 上游: https://www.nico.schottelius.org/software/ccollect/
- 仓库: https://code.ungleich.ch/ungleich-public/ccollect
- 纯 POSIX sh 脚本（无 C/C++ 编译，无构建系统）
- 运行时依赖: rsync, ssh, hostname, coreutils（系统命令，非 Conan 管理）
- 许可证: GPL-3.0-or-later

> 注意：ccollect 是 rsync 包装器，核心备份功能由 rsync 提供。本包仅适配
> 脚本本身，使其在 OHOS PC 上可安装和运行（ccollect -V / -h），实际备份
> 功能需 rsync 支持。