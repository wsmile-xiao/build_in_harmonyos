# comgt

**3G/GSM 调制解调器控制与脚本工具**（来自 Martin Gregorie / Paul Hardwick，SourceForge）

comgt 是一个命令行工具，用于控制、配置和交互 Option Wireless 3G/2G（HSDPA、UMTS、EDGE、GPRS、GSM）数据设备。它使用自带的类 shell 脚本语言发送 AT 命令、读取 SIM/PIN 状态、设置 PIN 码、切换模式等。支持 `-V`/`-h`（版本/用法）、`-d 设备`、`-s`（跳过默认脚本）、`-t`（行终止符）、`-e`（回显）、`-v`（冗余输出）、`-x`（高速覆写）、`-b`（波特率）等选项。

## 用法

```bash
comgt -V                  # 打印版本横幅
comgt -d /dev/ttyUSB0 -s script.gcom   # 对指定设备运行脚本
```

## 上游

- 主页: https://sourceforge.net/projects/comgt/
- 许可证: GPL-2.0-or-later
- 构建: 纯 makefile（无 configure）
- 说明: 上游无自动化测试套件；makefile 的 install 目标硬编码 /usr/local 与 /etc/comgt，包内直接拷贝产物
