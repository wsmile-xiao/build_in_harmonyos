# uucp

GNU Taylor UUCP 是 UUCP（Unix-to-Unix Copy Protocol）协议的 GNU 实现，提供
文件传输、远程命令执行与串行连接能力。

## 简介

uucp/1.07 打包 13 个命令行工具：传输守护进程 `uucico`、远程执行 `uuxqt`、
配置校验 `uuchk`、配置转换 `uuconv`、文件传输 `uucp`、远程命令 `uux`、
队列查询 `uustat`、系统名查询 `uuname`、日志查看 `uulog`、文件收取
`uupick`、串行连接 `cu`，以及调度脚本 `uusched`/`uuto`。

## OHOS 适配

- **构建系统**: autotools（autoconf 2.13/automake 1.4 预生成 configure，
  in-source 构建，无 autoreconf）。
- **零第三方依赖**: `configure.in` 无任何 pkg-config/AM_PATH 宏，链接面为
  包内三个 `noinst` 静态库；socket 系函数由 musl libc 提供。
- **交叉探测**: 本机构建时 conftest 可直接执行，6 处 `AC_TRY_RUN` 全部真实
  运行（ftime/statvfs 等均命中 OHOS musl 能力）。
- **安装方式**: 不使用上游 `make install`——其 `install-exec-hook` 会执行
  `chown $(OWNER)`（`OWNER = uucp`）与 `chown root`，非 root 构建用户必然 EPERM；
  改由配方显式复制产物并 chmod 0755。
- **手册**: 保留 6 个 man 页与 `share/info/uucp.info`。

## 依赖

无第三方 Conan 依赖。仅使用目标平台 libc（含 socket/poll/ftw 等 POSIX 接口）。

## References

- Homepage: https://www.gnu.org/software/uucp/
- Source: https://ftp.gnu.org/gnu/uucp/uucp-1.07.tar.gz
  (sha256 `060c15bfba6cfd1171ad81f782789032113e199a5aded8f8e0c1c5bd1385b62c`)
