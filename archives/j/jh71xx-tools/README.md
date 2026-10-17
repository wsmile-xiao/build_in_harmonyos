# JH71xx-tools

JH71xx-tools is a command-line utility that recovers and updates the StarFive JH7100 bootloader over a serial UART connection using XMODEM.

## 功能

- 通过 UART 向 JH7100 BootROM 发送恢复固件。
- 更新第二阶段 bootloader 和 DRAM 初始化固件。
- 提供 `jh7100-recover --help` 查看设备路径和固件参数。

## HarmonyOS 适配

程序使用 POSIX 串口、终端和内存映射接口，由 HarmonyOS PC 原生 C 工具链构建。消费者测试会运行真实打包程序的帮助输出，并查询 `const.ohos.fullname` 确认运行环境。实际固件传输需要兼容的 JH7100 UART 设备和相应设备访问权限，不属于自动化测试范围。

## 依赖

- 编译依赖：HarmonyOS C/Clang 工具链。
- 运行依赖：HarmonyOS 系统 C 库；Conan 配方不声明第三方库依赖。

版本配方直接调用 Conan profile 指定的 C 编译器，按上游 Makefile 的单文件默认编译规则生成程序。

## 参考资料

- [上游源码仓库](https://github.com/xypron/JH71xx-tools)
- [固定源码提交](https://github.com/xypron/JH71xx-tools/tree/43be3329)
