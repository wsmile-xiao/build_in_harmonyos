# light

light 是一个用 C 编写的命令行背光 / LED 亮度调节工具，直接读写 sysfs：

- `/sys/class/backlight/<ctrl>/brightness`、`max_brightness`
- `/sys/class/leds/<led>/brightness`、`max_brightness`

它枚举上述控制器，按名称/默认规则挑选一个作为目标，然后读取或设置亮度。
上游同时提供可选的 udev 规则（`90-backlight.rules`），用于把 `brightness`
节点的可写权限授予 `video` 组，从而替代把二进制装成 SUID root。

- 上游主页：<https://github.com/haikarainen/light>
- 许可证：GPL-3.0-or-later

## HarmonyOS PC 适配状态

本包在 HarmonyOS PC（aarch64）上**可构建、可安装、可执行**；背光调节这一功能面
依赖 sysfs，而实测 sysfs 目录枚举对本平台进程返回 `EACCES`，因此运行期表现为
「无可用控制器」并正常退出（非崩溃）。逐条一手 errno 读数见
`1.2.2/notes.md`。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.2.2 | built | autotools 自举构建，零外部依赖 |
