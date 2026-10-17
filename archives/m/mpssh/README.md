# mpssh

Mass parallel ssh — 对主机列表批量并行执行同一命令的 CLI 工具。

- **主页**: https://github.com/ndenev/mpssh
- **许可证**: BSD-3-Clause
- **构建系统**: Makefile（纯 C，无 configure，install 目标不可用于鸿蒙）
- **功能**: 并行 spawn ssh 进程，按 hosts 文件（`user@host:port` + `%label` 分组）批量执行命令
- **特性**: 可调并行度（-p，默认 100）、盲模式（-b）、输出目录（-o，按 `user@host.out/.err` 落盘）、连接超时（-t）
- **依赖**: 无（仅 libc；运行时 exec 外部 ssh/scp，路径编译期烘焙为 /usr/bin/ssh、/usr/bin/scp）
