# astap

ASTAP（Astrometric STAcking Program）是一个天文图像测量与 plate solving 工具。本归档适配其无 GUI 的命令行求解器 `astap_cli`。

## HarmonyOS PC 适配

- 使用官方 AArch64 Free Pascal Compiler 3.2.2 静态发行包构建。
- 直接编译上游 `command-line_version/astap_command_line.lpr`，不依赖 Lazarus LCL、GTK 或 Qt。
- 对 FPC 构建工具及最终 ELF 添加 HarmonyOS 签名。
- Conan 制品不包含 GUI 和大型外部星表数据库。

## 版本

| 版本 | 状态 | 测试 |
|---|---|---|
| 2026.07.16 | built | 9/9 消费者断言通过（含真实 FITS 分析） |

## 上游

- 项目主页：https://www.hnsky.org/astap.htm
- 源码镜像：https://github.com/CanardConfit/ASTAP
- 许可证：MPL-2.0
