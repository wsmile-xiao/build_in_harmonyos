# torsocks

透明 socksification 包装器：通过 LD_PRELOAD 拦截应用的 socket 相关系统调用，
把流量转发到 Tor SOCKS5 代理（默认 127.0.0.1:9050）。

## 功能概述
- `bin/torsocks` 包装脚本（用法：`torsocks <程序> [参数...]`，支持 on/off 会话切换）
- `libtorsocks.so`：拦截 connect/socket/getaddrinfo/gethostbyname/close 等调用的预加载库
- 支持 DNS 解析劫持、.onion 地址路由、SOCKS5 用户名/密码认证、IPv6（实验性）

## OHOS 适配
- 上游 git 归档不带 configure：build() 先 `autoreconf -fi` 自举
  （tool_requires automake/1.18 + libtool/2.5.4）
- E114：生成的 configure 去除 `umask 077`（HMDFS 下 0700 临时目录不可写）
- E007：显式 `--build/--host=aarch64-unknown-linux-ohos`（config.guess 不识别 HarmonyOS）
- LIBC_NAME 探测回退改为 `libc.so`（OHOS musl 无 libc.so.6，运行期 dlopen 依赖）
- tests 链接去掉 `-lpthread`（OHOS musl 把 pthread 并入 libc）
- `make -j1`（HMDFS jobserver fifo EPERM）
- 上游测试：`make check`（automake TAP 套件：tests/ 5 例 + tests/unit/ 6 例）

## 依赖关系
- 编译依赖：automake/1.18、libtool/2.5.4（tool_requires，仅用于 autoreconf 自举）
- 运行依赖：无（纯 libc）

## 参考资料
- 官网：https://gitlab.torproject.org/tpo/core/torsocks
- 发布公告：https://forum.torproject.org/t/torsocks-v2-5-0/18104
