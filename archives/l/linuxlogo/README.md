# linuxlogo

Linux Logo（上游 Linux_Logo，作者 Vince Weaver）在终端打印发行版 Logo，
并在 Logo 上叠加 CPU 型号与数量、内存、负载、运行时间、主机名等系统信息。
Logo 位图由打包进去的 parse_logos 工具从 logos/ 目录生成。

- 上游主页：http://www.deater.net/weave/vmwprod/linux_logo/
- 上游仓库：https://github.com/deater/linux_logo
- 许可：GPL-2.0-or-later
- 构建系统：手写 configure + 裸 Makefile（非 autoconf），内附 libsysinfo-0.3.0 后端
- 产物：单个可执行文件 bin/linux_logo（命令行工具，故本目录提供 commands.json）

## 版本
- 6.01
