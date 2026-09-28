# qcontrol

qcontrol 是运行在嵌入式 NAS 设备上的守护进程 + 命令行工具，用来驱动这类机器上的
串口/GPIO 外设：指示灯、风扇、LCD 面板与看门狗，并把面板按键事件回调给配置脚本。
主要面向 QNAP TS 系列，模块化为便于扩展到其他机型。上游主页
<https://www.hellion.org.uk/qcontrol/>。

支持机型（上游 README）：QNAP TS-109/109 II/209/209 II（ts209）、TS-409/409U（ts409）、
TS-11x/12x/HS-210/TS-21x/TS-22x（ts219）、TS-41x/TS-42x（ts41x）、Synology
Diskstation / Rackstation（synology）。

## 名字提示

包名容易被误读成"终端会话/多路复用工具"。它**不使用 pty，也没有 ioctl**：
终端相关代码只有串口 termios（`tcgetattr` 存旧参数 → `B1200/B9600/B19200 | CS8 | CLOCAL | CREAD`
+ `cfsetispeed/cfsetospeed` → `tcsetattr`），操作对象是 `/dev/ttyS0` / `/dev/ttyS1`。
详见 `0.5.7/notes.md` §1 与 §5。

## HarmonyOS PC 适配版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 0.5.7 | built（conan create / conan-verify 通过） | 裸 Makefile，唯一库依赖 lua/5.1.5（静态 liblua.a） |

鸿蒙上可运行的部分：CLI、内嵌 Lua 配置解释器（`-c PATH`、`confdir()` 的 glob 递归载入）、
命令表与 `--direct` 执行路径。本机无 `/dev/ttyS*`、`/dev/input/event*` 不可开、
AF_UNIX 在实测挂载点均不可 bind 且 `/var/run` 不存在，因此 NAS 外设动作与守护模式的
socket 监听在平台上没有承载物（实测数据在 `0.5.7/notes.md` §5）。
