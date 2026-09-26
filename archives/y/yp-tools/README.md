# yp-tools

## 简介

yp-tools 是 Linux-NIS（YP）的客户端工具集（Thorsten Kukuk 维护），提供 ypcat/ymatch/ypwhich/yppasswd/yppoll/ypset/yp_dump_binding/yptest/domainname 以及 ypchsh/ypchfn/ypdomainname/nisdomainname 别名，用于查询 NIS map、显示绑定服务器、修改 NIS 口令等。

- 上游：https://github.com/thkukuk/yp-tools （GPL-2.0）
- 本仓库版本：4.2.3
- 包类型：application（无库产物，CLI 工具集）

## OHOS 适配

- **构建系统**：Autotools；上游 tag archive 不含 `configure`，构建时先运行 `autogen.sh`（automake/libtool/autoconf/gettext-autopoint 由 tool_requires 提供）。
- **依赖**：libnsl/2.0.1 + libtirpc/1.3.7（NIS/TI-RPC，OHOS sysroot 无 rpcsvc//rpc/ 头文件）、gettext/0.22.5.1（libintl，静态链接）、libxcrypt/4.5.2（crypt.h + libcrypt.a）。四者均静态链接，产物运行时仅依赖 musl `libc.so`。
- **平台补丁**（patches/，全部为可移植特性探测，无平台宏）：getpass() 可用性探测与自备实现、config.guess 不识别 HarmonyOS 时显式 `--build` 三元组、HMDFS 不支持硬链接 → 别名改软链、上游测试注册与失败跳过。
- **运行前提**：查询类工具需要可达的 ypbind/NIS 服务器，且 libtirpc 需要 `/etc/netconfig`（OHOS 上通常缺失，`/etc` 只读）；本包保证可执行与优雅报错。
