# pps-tools — LinuxPPS 用户态工具集与 PPSAPI 头

`pps-tools` 是 LinuxPPS 子系统的用户态配套工具集，随包提供 PPSAPI 头
`sys/timepps.h`，以及 5 个命令行程序：

| 程序 | 说明 |
|------|------|
| `ppstest`  | 打开 PPS 设备并打印 assert/clear 时间戳序列，验证 PPSAPI 接口 |
| `ppsctl`   | PPS 设备管理：绑定/解绑内核消费者、设置/清除内核 NTP PPS 标志 |
| `ppswatch` | 连续打印 PPS 时间戳并统计抖动/均值/标准差 |
| `ppsldisc` | 在 RS232 串口上设置 PPS line discipline（`N_PPS`） |
| `ppsfind`  | 按名称在 `/sys/class/pps` 里查找 PPS 设备（POSIX sh） |

公共头 `sys/timepps.h` 提供 `time_pps_create`/`time_pps_getparams`/`time_pps_fetch`
等 `static inline` 封装，直接通过 `ioctl(PPS_*)` 访问 LinuxPPS 内核接口。

## 主要功能

- 通过 PPSAPI（RFC 2783）访问 Linux PPS 时钟源，采集 assert/clear 时间戳。
- `ppsctl` 管理内核 PPS 消费者与 NTP PPS 标志。
- 提供可被其它程序直接 `#include <sys/timepps.h>` 的用户态 API。

## OHOS 适配要点

- **纯 Makefile 构建**：无 `configure`，`make CC=<ohos-clang> CFLAGS="-Wall -O2 -D_GNU_SOURCE -fPIC"` 即可。
- **零三方依赖、零补丁**：OHOS SDK sysroot 已包含源码所需的全部内核 uapi 头
  （`<linux/pps.h>`、`<linux/types.h>`、`<linux/tty.h>`）。
- **链接器**：Conan OHOS profile 通过 `tools.build:compiler_executables` 指定
  `ohos-sdk/.../llvm/bin/clang`，并在 buildenv 注入 `LD=ld.lld`，无需额外配置。
- **运行期限制**：4 个程序都需要真实 `/dev/ppsN` 与 `/sys/class/pps`；OHOS 无 PPS
  时钟源，故验证覆盖编译、参数/用法错误路径与头文件消费（消费者测试 12 项）。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/ppstest`  | PPSAPI 接口测试程序 |
| `bin/ppsctl`   | PPS 设备管理器 |
| `bin/ppswatch` | PPS 时间戳监视/统计 |
| `bin/ppsldisc` | PPS line discipline 设置 |
| `bin/ppsfind`  | PPS 设备查找脚本 |
| `include/sys/timepps.h` | PPSAPI 公共头 |

## 参考资料

- 上游仓库：<https://github.com/redlab-i/pps-tools>
- 许可证：GPL-2.0-or-later
