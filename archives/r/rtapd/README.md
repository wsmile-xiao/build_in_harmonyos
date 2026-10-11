# rtapd — TAP/TNPP 寻呼守护进程

`rtapd` 是 rtnppd 套件中的 TAP/TNPP 寻呼守护进程：它从 rtnppd 接收到 TNPP
寻呼包（通过 AF_UNIX 数据报「外部队列」socket），重组其中的 TAP 页面块，按路由表
把寻呼投递到串口调制解调器、文件、过滤程序，或转投给另一个 TNPP 地址。
同一个源码包还会构建 `vsnppd`（一个小型 SNPP/TNPP 网关）。

## 功能概述

- 外部队列：`ExtSocketIn`（rtnppd → rtapd）/ `ExtSocketOut`（rtapd → rtnppd）
- TNPP 包解析与 TAP 1.8 块重组（`A` CAP 页面、扩展 CAP、`B`/`C`/`F` 块、ETE 请求）
- 路由表（`RoutingTable`）按 `FROM TO DEST` 投递，支持区间、`PAGER:` 改址、`TNPP:` 转投、`NONE` 丢弃
- 设备类型：串口调制解调器、`>文件`（含按目录一页一文件）、`|过滤程序`
- 可选 SQL 后端（mSQL/PostgreSQL/MySQL）—— **本配方保持上游默认，全部关闭**
- `-d` 前台、`-s` 输出到 stderr、`-x 0..5` 日志级别、`-p FILE` 转储解析后的配置、`-S SECTION` 配置分段

## OHOS 适配要点

- 纯 Makefile，无 configure；上游 Makefile 不写死编译器，配方用 `CC=<ohos clang> CFLAGS='-O2 -pipe -g'` 构建
- **零外部依赖**：上游 Makefile 里 mSQL/PostgreSQL/MySQL 三组 `CFLAGS`/`LIBS` 全部是注释，`LIBS` 为空，默认构建只链 libc
- 补丁 `0001-rtapd.c.patch`
  - `send_tnpp_packet()` 在 `int` 函数里裸 `return`，clang 15 默认把 `-Wreturn-type` 判为 error
  - `strtoq` 是 glibc/BSD 扩展，musl 无此符号：aarch64-linux-ohos 链接期 `undefined symbol: strtoq` → 改 `strtoll`
  - `"%qX"` 不是 musl printf 支持的转换符：实测 `sprintf(id, "!%qX", pagenum)` 返回 `-1` 且 `id` 只剩 `"!"`，
    CAP 页面 ID 完全丢失 → 改 `"%llX"` + `(long long)` 转换（`quad_t` 在 OHOS `sys/types.h` 中即 `long long`）
- 补丁 `0002-vsnppd.c.patch`：`vsnppd.c` 的 `send_tnpp_packet()` 有同一处裸 `return`
- 上游 `make install` 会 `mkdir /var/spool/psheduler`（需 root），配方在 `package()` 中直接复制两个可执行文件
- 两个补丁都不含平台宏，是纯可移植性修复（Linux/OHOS 通用）

## 上游测试

上游无任何自动化测试入口（Makefile 无 `check`/`test` 目标，源码包内无 `tests/` 与测试源码，
Alpine aports 亦显式声明 `options="!check"`）。功能验证由 `test_package/` 的鸿蒙消费者用例承担：
在沙箱内启动守护进程，并用一个按 rtapd 自身 TNPP 线上格式（含 CRC-16/ARC）发包的消费者
C 客户端完成「socket → TNPP 解析 → CAP 页面 → 路由 → 文件设备落盘」的端到端验证。
