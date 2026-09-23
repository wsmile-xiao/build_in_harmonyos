# socat

socat 是**多用途双向数据中继工具**，可在 socket / 文件 / 管道 / 命令等任意两种「地址」之间建立双向或单向的数据通道，常用于端口转发、调试代理、协议测试与网络服务联调。

## 功能概述

- **地址类型丰富**：`TCP`/`TCP-LISTEN`/`UDP`/`UNIX-CONNECT`/`UNIX-LISTEN`/`EXEC`/`SYSTEM`/`OPEN`/`CREATE`/`FILE`/`PIPE` 等
- **双向与单向中继**：默认双向；`-u` 单向（左→右）、`-U` 单向（右→左）
- **数据转换**：`-x` 十六进制转储、`-v` 流量打印，便于调试
- **辅助工具**：`filan`（文件描述符分析）、`procan`（进程/地址分析）

### 典型用途

- **作为测试基础设施的中继组件**：swtpm 的测试套件即通过
  `socat -x -t50 "FILE:...,rdonly" "UNIX-CONNECT:..."` 从 TPM 模拟器的
  控制通道读取交换数据。
- 端口转发、TCP/UDP 代理、串口与网络互通。

## OHOS 适配

### 构建期

- **源码形态**：上游 release dist tarball，**自带 `configure` 与 `Makefile.in`**，
  无需 `autoreconf`。因此**不涉及** `config.guess` 的 OHOS 三元组补丁 ——
  `configure.ac` 内 `AC_CANONICAL_*` 命中为 0，configure 不调用 `config.guess`。
  这与 swtpm / tpm2-tss（git archive 快照，须 autoreconf 并补 `config.guess`）不同。

- **`_res` 缺失（坑一）**：OHOS sysroot **有** `<resolv.h>`，但 libc **不导出**传统全局
  `_res`（也无 `__res_state()` 访问器）。socat 的 `configure.ac:79` 用
  `AC_HEADER_RESOLV()`，**只判断头文件是否存在** → `HAVE_RESOLV_H=1`，随后
  `xio-ip.c` 在 `#if HAVE_RESOLV_H` 下直接使用 `_res.options`，编译失败：

  ```
  xio-ip.c:119:11: error: use of undeclared identifier '_res'
  ```

  修法：`ac_cv_header_resolv_h=no` → `HAVE_RESOLV_H` 不定义 → 跳过整段。
  该段只提供 `res-debug`/`res-recurse` 等**已废弃**的 resolver 调优选项，
  域名解析本身仍由 `getaddrinfo()` 正常提供。
  > 同族知识条目：**E516**（OHOS libc omits `_res`/`__res_state`）。

  > 对照：`--disable-res-deprecated` **无效**（只关 `WITH_RES_DEPRECATED`，不关 `HAVE_RESOLV_H`）。

- **`isastream()` 缺失（坑二）**：OHOS sysroot **有** `<sys/stropts.h>`
  （内容仅 `#include <stropts.h>`），而 `<stropts.h>` **定义了 `I_LIST`**，
  使 `filan.c:452` 的 `#ifdef I_LIST` 块激活并调用 `isastream()`；
  但 libc **不声明也不导出**该函数，链接期报：

  ```
  ld.lld: error: undefined symbol: isastream
  >>> referenced by filan.c  >>> filan.o:(filan_stat) in archive libxio.a
  ```

  修法：`ac_cv_header_sys_stropts_h=no` → 不引入该头 → `I_LIST` 未定义 → 整段跳过。
  该块为 SunOS STREAMS 遗留，与核心中继功能无关。

- **`umask 077`（E114 同族）**：`configure` 生成 `config.status` 时以
  `(umask 077 && mktemp -d)` 建临时目录，HMDFS 强制目录 setgid 下 077 会失败：

  ```
  ./config.status[692]: can't create ./confXXXXXX/subs1.awk: Permission denied
  config.status: error: could not setup config files machinery
  ```

  由补丁 `0001-configure-drop-umask-077.patch` 移除两处 `umask 077`。

- **`-j1`**：E074 —— HMDFS 上 jobserver fifo `EPERM`，并行 `make` 失败。

### 运行期

- 核心中继功能（TCP / UDP / UNIX socket / 文件 / 管道）实测可用；
  `test_package` 以 TCP 双向建立与内容到达作为判据。
- OHOS 对 AF_UNIX 路径名 socket 有域限制，如需 UNIX 域可用
  `/data/storage/el1/base` 下路径。

## 依赖关系

- **编译期**：无库依赖（仅 libc）；无需额外构建工具（自带 `configure`）
- **运行期**：无第三方运行依赖

> **下游消费方**：swtpm 的测试套件将本包列为 `--enable-tests` 的**五项硬门禁**之一
> （`AC_PATH_PROG([SOCAT], socat)`，只做可执行性探测、不链接符号）。
> 依赖链：`socat` → `swtpm tests/` → `gnupg tests/tpm2dtests`。

## 可用版本

| 版本 | 状态 | 说明 |
|------|------|------|
| `1.7.4.4.1` | ✅ built | 当前版本。基于上游 1.7.4.4 的 OHOS 适配轮次（本仓 `.1` 惯例，如 gnupg `2.4.9.1`）；源码 URL 与产物自报版本均为 1.7.4.4 |
| `1.7.4.4` | built | 早期手工适配记录；`conandata.yml` 缺失，conan 侧无法直接构建 |
| `1.8.0.3` | failed | 不完整：无 `conanfile.py`，其补丁为自动生成的空转 diff（仅改 autoconf 版本注释） |

## 参考资料

- 官网：http://www.dest-unreach.org/socat/
- 源码下载：http://www.dest-unreach.org/socat/download/
- 知识条目：**E516**（OHOS libc omits `_res`/`__res_state`）、**E114**（umask 077 临时目录）
