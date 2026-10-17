# Combat

Combat 是 Tcl 语言的 CORBA ORB（"CORBA Scripting with Tcl"），提供
`corba::init`、动态调用接口（DSI 除外）、`idl2tcl` IDL 编译器与 `iordump`
IOR 解码工具，可在 Tcl 脚本中直接定义和调用 CORBA 对象。

## 功能概述

- 纯 Tcl 实现的 CORBA 2.x ORB：CDR 编解码、GIOP/IIOP 传输、POA、codeset 协商
- `bin/idl2tcl`：将 IDL 编译为 Tcl 桩（`combat::ir add` 描述 + 访问 procs）
- `bin/iordump`：解码 IOR 字符串（IIOP profile、tagged components）
- `tclkill`：可选 kill 扩展（向进程发 SIGTERM），带纯 Tcl `exec kill` 回退
- 上游 0.8（2008）起退役 Combat/C++，0.8.1（2011-08-01）为最终版本

## OHOS 适配要点

- 无构建系统：orb/*.tcl 拷贝安装，打包为 `lib/combat/` 与 `lib/tclkill/`
- 脚本解释器：入口脚本硬编码 `tclsh8.5`，patch 插入 `tclsh8.6` 探测分支
- **Itcl 是事实上的硬依赖**：combat.tcl 的 tcl++ 回退物不在 0.8.1 归档中；
  设备 tcl/8.6.16 包的 `lib/itcl4.3.2/` 又缺 `itcl.tcl` 等库脚本（其打包
  只按 `*.so*`/`*.a` 通配拷贝），本包从同源 Tcl 源码提取库脚本补齐到
  `lib/combat/itcl/`，pkgIndex 在 load 前设置 `ITCL_LIBRARY`
- tclkill：用设备 clang 以 `-DUSE_TCL_STUBS` 链接 `libtclstub8.6.a` 编译
  通用 `kill.so`；包索引优先加载它，缺失时回退 `unixkill.tcl`
- 与 Linux 的差异：仅解释器名与 Itcl 分发方式，ORB 本体无系统调用

## 依赖关系

- 运行依赖：`tcl/8.6.16`（tclsh8.6、libtcl8.6、libtclstub8.6.a、libitcl4.3.2.so）
- 可选：http 包（Tcl 核心，仅 http: URL 功能）、Tk（仅 GUI demo，未打包）

## 消费者用法

```tcl
lappend auto_path $env(COMBAT_ROOT)/lib/combat $env(COMBAT_ROOT)/lib/tclkill
package require combat   ;# 自动加载 Itcl（随包 itcl/ 目录）
corba::init
```

## 参考资料

- 官网：http://www.fpx.de/Combat/
- 源码归档（本仓采用）：Debian 源码池 combat_0.8.1.orig.tar.gz（与 fpx.de
  发布包同内容，HTTPS 可达）
