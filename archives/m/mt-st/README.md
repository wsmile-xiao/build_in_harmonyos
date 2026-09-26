# mt-st — Linux SCSI 磁带控制工具集

`mt-st` 提供两个面向 Linux SCSI 磁带驱动的命令行工具：

- **`mt`**：磁带控制程序（GNU `mt` 的替代品），除标准磁带操作外，还可发送 SCSI 磁带驱动专有的 ioctl，例如设置磁带分区、密度、驱动缓冲等。
- **`stinit`**：在系统启动或磁带驱动初始化时，根据磁带机返回的 inquiry 信息（厂商/型号）从文本数据库 `stinit.def` 中读取并设置磁带驱动的默认模式（块大小、压缩、缓冲、超时等）。

## 主要功能

- `mt`：`rewind`/`eof`/`fsf`/`bsf`/`status`/`stshowoptions`/`densities` 等磁带命令，支持命令缩写与参数解析。
- `stinit`：解析磁带定义数据库（`stinit.def`），按设备名或磁带编号批量初始化磁带机模式。
- 自带示例数据库 `stinit.def.examples`、man 手册与 bash 补全脚本。

## OHOS 适配要点

- **纯 Makefile 构建**：无 `configure`，直接 `make CC=<clang> CFLAGS="-Wall -O2" -j1`。
- **无三方依赖**：OHOS SDK sysroot 已包含 `<linux/major.h>`、`<scsi/sg.h>`、`<sys/sysmacros.h>`、`<sys/utsname.h>`、`<libgen.h>` 等源码所需头文件，源码零改动。
- **上游测试运行器替换**：上游 `make check` 使用 shelltestrunner（`shelltest`，Haskell 实现），OHOS 与 CI worker 均不可用；本配方内嵌一个零依赖的 **shelltestrunner format-1 兼容运行器**，直接解析并执行上游同一批 `tests/*.test`（31 例），并复现上游 Makefile 的 `-DVERSION=1.8` 宏替换语义。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/mt` | 磁带控制程序 |
| `bin/stinit` | 磁带模式初始化程序 |
| `share/man/man1/mt.1` | mt 手册 |
| `share/man/man8/stinit.8` | stinit 手册 |
| `share/mt-st/stinit.def.examples` | 示例磁带定义数据库 |
| `share/mt-st/mt-st.bash_completion` | bash 补全脚本 |

## 参考资料

- 上游仓库：<https://github.com/iustin/mt-st>
- 许可证：GPL-2.0-only
