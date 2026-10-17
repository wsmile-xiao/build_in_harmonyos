# joystick (linuxconsoletools)

Linux 输入子系统用户态工具集（上游项目 linuxconsole，Debian 包名
joystick）。交付 8 个 ELF 工具 + 2 个运维脚本：

| 工具 | 用途 |
|---|---|
| jstest | joystick 设备测试/观察 |
| jscal | joystick 校准 |
| jscal-restore / jscal-store | 校准持久化运维脚本（依赖 udevadm） |
| evdev-joystick | evdev 轴/按钮属性调整 |
| inputattach | 串口设备连接为输入内核子系统（termios 面） |
| fftest / ffset / ffcfstress / ffmvforce | Linux 力反馈接口测试（ffmvforce 用 SDL2 可视化） |

- 上游：https://sourceforge.net/projects/linuxconsole/
- 许可：GPL-2.0-or-later
- 构建系统：裸 Makefile（utils/）
- 依赖：sdl2/2.32.10（仅 ffmvforce，静态）

鸿蒙 PC 适配：内核 UAPI 头由 OHOS clang sysroot 自带（无需头文件注入）；随包补丁 1 枚＝K0 命令行契约（`0001-k0-help-version-exit0.patch`，7 个源文件），除此源码零修改；
交付 ELF 已 selfSign 签名。设备级功能需 /dev/input 节点，无设备环境
以 --help/退出码契约为消费者断言。
