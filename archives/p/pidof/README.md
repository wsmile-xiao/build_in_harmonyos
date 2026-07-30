# pidof

查找正在运行程序的进程 ID。

这是一个从 sysvinit 套件中剥离出来的独立 pidof 实现，仅保留 pidof 功能
（去掉了 killall5 部分）。通过读取 `/proc` 文件系统来查找进程。

- 上游：https://github.com/drmrboy/pidof
- 许可：GPL-2.0-only
- 构建系统：makefile
