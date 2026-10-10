# YACPI

YACPI（Yet Another Configuration and Power Interface）是一个基于 ncurses 的终端系统状态监视工具，可显示电池、电源适配器、风扇、热区及 CPU 信息。

## 功能

- 交互式 ncurses 界面与纯文本输出
- 查询 ACPI 电池、适配器、风扇和热区信息
- 查询 CPU 频率和 governor

## HarmonyOS 适配

HarmonyOS PC 设备可能不提供 Linux ACPI 接口。适配后，缺少 ACPI 时工具仍会启动，并显示可访问的 CPU 频率；未提供的电池、适配器、风扇和热区数据会按“无信息”处理。CPU 频率读取优先使用 Linux `scaling_*` 节点，并回退到设备提供的 `cpuinfo_*` 节点。

## 依赖

- 编译与运行依赖：`libacpi/0.2`、`ncurses/6.5`
- 构建工具：HarmonyOS aarch64 clang、make

## 参考资料

- [YACPI 项目主页](http://www.ngolde.de/yacpi.html)
- 上游源码包：`https://download.tuxfamily.org/slitaz/sources/packages/y/yacpi-3.0.1.tar.gz`
