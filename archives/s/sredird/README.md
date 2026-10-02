# sredird

## 是什么

sredird 是符合 RFC 2217（Telnet Com Port Control Option）的**串口重定向服务端**：把本机的串口设备通过网络共享出去。
它设计为由 inetd 类超级服务器启动，连接的标准输入/输出就是网络套接字；客户端（C-Kermit、DialOut/IP、pyserial 的
`rfc2217://` 等）通过 RFC 2217 子协商设置波特率、数据位、校验、停止位和流控，sredird 用 `termios` 应用到串口设备。

```
sredird [-i] <log-level> <device> <lock-file> [poll-interval-ms]
```

| 参数 | 含义 |
|------|------|
| `-i` | 兼容 Cisco IOS 的入站流控实现缺陷 |
| `log-level` | 0（不记日志）到 7（debug），经 `syslog` 输出 |
| `device` | 串口设备，如 `/dev/ttyS0` |
| `lock-file` | HDB 风格（ASCII）锁文件，需与其他串口程序一致，如 `/var/lock/LCK..ttyS0` |
| `poll-interval-ms` | 调制解调器状态轮询间隔，默认 100，0 为关闭 |

无参数（少于 4 个参数）时打印版本与用法，退出码 1；程序本身没有 `--version` 选项。

## OHOS 适配

- 上游 Makefile 写死 `CC=gcc`：配方把 `AutotoolsToolchain` 给出的编译器与标志放在 make 命令行上覆盖（R33）。
- `patches/0001-sredird.c.patch`（无平台宏，可上游化）：
  1. 删除未使用的 `#include <termio.h>`：OHOS musl 没有该头文件；源码只使用 `<termios.h>`；
  2. RFC 2217 波特率字段由 `unsigned long` 改为 `uint32_t`：LP64（aarch64）上 `unsigned long` 是 8 字节，
     应答帧 `IAC SB 44 101 <值> IAC SE` 中值被展开成 8 字节，客户端解析错位。
- 上游没有 `install` 目标，配方 `package()` 把二进制复制到 `bin/`、man 页到 `share/man/man8/`、`COPYING` 到 `licenses/`。
- 上游无测试套件；test_package 补全一个 C 消费者用例（7 项检查）。

## 依赖关系

- 编译依赖：无（仅 libc：termios / socket / syslog）
- 运行依赖：无

## 参考资料

- 上游发布归档：https://www.ibiblio.org/pub/linux/system/serial/sredird-2.2.2.tar.gz（Debian `copyright` 的 Source 与 `watch` 所指）；
  构建取自其 GWDG 学术镜像 https://ftp.gwdg.de/pub/linux/metalab/system/serial/（字节与 ibiblio 发布文件一致，
  ibiblio 对 `.tar.gz` 带 `Content-Encoding`，Conan 下载后 sha256 不符）
- Debian 维护仓库：https://salsa.debian.org/debian/sredird（`upstream/2.2.2` 标签的 6 个文件与上述发布包逐文件 sha256 相同；`debian/2.2.2-2` 的 `0004-rm-termio-h.patch` 与本适配补丁 1 相同）
- RFC 2217：https://www.rfc-editor.org/rfc/rfc2217
