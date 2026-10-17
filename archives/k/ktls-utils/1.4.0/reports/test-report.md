# ktls-utils 1.4.0 · 真机构建与测试报告

- 日期：2026-09-23
- 设备：HarmonyOS PC（HongMeng Kernel 1.12.0，aarch64，Toybox）
- 编译器：OHOS SDK `ohos-sdk@26.0.0.18` clang，target `aarch64-unknown-linux-ohos`
- Profile：`~/.conan2/profiles/ohos-aarch64`（os=OHOS/6.0, arch=armv8, clang-15, libc++, cppstd=17, Release）
- 独立缓存：`CONAN_HOME=/storage/Users/currentUser/work/psj/ch-ktls-utils`

## 命令

```
conan create archives/k/ktls-utils/1.4.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

## 结果：CREATE_EXIT:0

依赖（全部命中制品仓 ohpcd 预编译二进制，无本地重编）：
gnutls/3.8.10, libkeyutils/1.6.3, libnl/3.11.0, glib/2.84.0.2（Conan revision `c030759d6798a3b0274ee05ac641b058`；OHPCD package ID `b55f7a483155972128ae18c9f9e8c67eba35e745`）；工具 pkgconf/3.0.5。其余传递依赖均命中 ohpcd 预编译包。

包标识：
```
ktls-utils/1.4.0#000be29832b7769c662ed5afdd21f3ab:436073c3978d5e3d730292fcd961ccdd1f3b105a#b77f271f2ef765dc9db9fb0c11838ec5
```

配方关键步骤（create 日志摘录）：
```
Calling source() ... Source https://github.com/oracle/ktls-utils/releases/download/ktls-utils-1.4.0/ktls-utils-1.4.0.tar.gz retrieved from local download cache
Apply patch (portability): Relax config.status tmp-dir umask 077 -> 022 ...
Apply patch (portability): OHOS/musl: suppress <linux/socket.h>'s sockaddr_storage ... via _UAPI_LINUX_SOCKET_H in config.h.in ...
configure: checking for gcc ... clang
configure: checking whether the C compiler works... yes
configure: checking for TLS_TX_MAX_PAYLOAD_LEN in linux/tls.h... no      # SDK 头无此宏，configure 自动置 HAVE_...=no，代码有守卫
Calling build()
  CC       tlshd-main.o
  GLIB_LIBS=-L<glib/2.84.0.2>/lib -lglib-2.0 -lm -lpthread -ldl  # 无 /lib/ld-musl-aarch64.so.1 绝对路径
  CCLD     tlshd
Created package revision b77f271f2ef765dc9db9fb0c11838ec5
Package '436073c3978d5e3d730292fcd961ccdd1f3b105a' created
Calling test()
```

## 上游测试

上游 ktls-utils 1.4.0 **无任何测试套件**（所有 Makefile.am 无 TESTS/check_PROGRAMS，无 tests/ 目录）→ 上游用例数 0（取数见 test_package/MANIFEST.yml）。按赛事 §3.6 补鸿蒙特有消费者测试。

## 消费者测试（test_package/test.sh，真机 conanrun 环境）

```
PASS: tlshd found on PATH and executable
PASS: tlshd --version exits 0
PASS: tlshd --version carries 'ktls-utils 1.4.0'
PASS: tlshd -v carries 'ktls-utils 1.4.0'
PASS: tlshd --help prints 'usage:'
PASS: tlshd rejects an unknown option
PASS: tlshd rejects a nonexistent explicit config
ASSERTIONS: 7, FAILURES: 0
```

runner 直跑（显式把缓存 lib 目录加入 LD_LIBRARY_PATH）：
```
tlshd, built from ktls-utils 1.4.0 on Sep 23 2026 16:41:34
DIRECT_VERSION_RC=0
```

## 产物布局

```
bin/tlshd        (191040 B ELF aarch64，DT_NEEDED: libgnutls.so.30 libtasn1.so.6 libgcrypt.so.20 libgpg-error.so.0 libkeyutils.so.1 libglib-2.0.so.0 libc.so)
etc/tlshd/       (config、tags.example)
licenses/COPYING, licenses/LICENSE.txt
share/man/man5, man7, man8
```

## 运行期能力说明（不粉饰）

tlshd 的内核握手服务循环 `tlshd_genl_dispatch()` 需要 Linux ≥ 6.5 且开启 CONFIG_TLS+CONFIG_KEYS+CONFIG_KEYS_REQUEST_CACHE 的 net/handshake generic-netlink 家族；HongMeng 内核未注册该家族（SOL_TLS/TLS_TX 常量与 add_key/keyctl 系统调用在设备上均不存在，原始 netlink 套接字需 CAP_NET_ADMIN）。本包交付的是上游用户态守护进程在 OHOS aarch64 上的可构建/可安装/可执行；消费者测试只覆盖 `--version/--help/参数与配置解析` 等用户态路径，未伪装执行过内核 handshake 派发。
