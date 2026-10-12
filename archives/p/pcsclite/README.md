# pcsclite (pcsc-lite)

## 是什么

pcsc-lite 是 PC/SC 智能卡中间件的参考实现（Ludovic Rousseau 维护，Muscle
SmartCard Development 延续项目）：提供 Windows 兼容的 `SCard*` 客户端 API
（winscard.h），配合 pcscd 资源管理守护进程与 ifdhandler 驱动接口，构成
Linux/Unix 上智能卡访问的标准栈。openjdk、opensc、gnupg-scdaemon、pcscd-ccid
等大量上层软件经此库访问智能卡。

## 功能概述

- `SCardEstablishContext/SCardReleaseContext/SCardConnect/SCardTransmit/...`
  全套 PC/SC 客户端 API
- `pcsc_stringify_error` 错误码转字符串
- `SCARD_PCI_T0/T1/RAW` 协议控制信息全局
- `ifdhandler.h` 读卡器驱动接口（驱动开发者消费）
- libpcscspy：API 调用 spy 垫片（调试用）

## OHOS 适配要点

- 上游 2.5.2 起构建系统为 **Meson**（无 configure.ac）
- **pcscd 守护进程未交付**：OHOS musl libc 无 `pthread_cancel(3)`（守护进程
  eventhandler.c 依赖），且 udev/systemd/polkit 集成在 OHOS 均无组件；
  经 meson 选项 `-Dpcscd=false` 裁剪（补丁选项化，上游默认行为不变）
- 交付面：`libpcsclite.so`（facade，dlopen 委托 `libpcsclite_real.so.1`）+
  `libpcsclite_real.so`（真实客户端实现）+ `libpcscspy.so` + 7 个
  `include/PCSC/*.h` 头文件 + `libpcsclite.pc`
- 头文件安装于 `include/PCSC/`，消费者 `#include <winscard.h>`
- 无 daemon 环境 API 契约（可作测试断言）：`SCardEstablishContext` →
  `SCARD_E_NO_SERVICE`；bogus handle → `SCARD_E_INVALID_HANDLE`

## 依赖关系

- 编译/运行：零外部依赖（libc + pthread + dl，musl 下内建）
- 构建期工具：flex（生成 configfile.c/tokenparser.c）、pod2man（manpage）

## 参考资料

- 官网：https://pcsc-lite.apdu.fr/
- 源码仓库：https://github.com/LudovicRousseau/PCSC
- Debian 镜像仓：https://salsa.debian.org/rousseau/PCSC
- 驱动接口文档：ifdhandler.h（随包安装）
