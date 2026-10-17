# tor

Tor（The Onion Router）匿名通信网络守护进程：通过多层加密的洋葱路由中继网络
隐藏用户 TCP 流量的来源与目的地，同时提供 .onion 隐藏服务（会合点）能力。

## 功能概述
- `bin/tor`：核心守护进程（客户端 / 中继 / 网桥等角色由配置决定），内置
  SOCKS5 代理（默认 127.0.0.1:9050）与控制端口
- `bin/tor-gencert`：中继身份密钥与签名证书生成工具
- `bin/tor-resolve`：经 Tor SOCKS 代理做主机名解析的小工具
- 洋葱路由目录协议、隐藏服务、流控与带宽统计

## OHOS 适配
- E007：config.guess 不识别 HarmonyOS（uname -s=HarmonyOS），显式
  `--build/--host=aarch64-unknown-linux-ohos`（上游 config.sub 经
  patches/0001-config.sub-ohos.patch 支持 *-linux-ohos）
- E114：上游自带 configure 去除 `umask 077`（HMDFS 下 0700 临时目录不可写）
- HMDFS getcwd 不可达：改写 configure 的 pwd 判定为失败时回退 `$PWD`
- E182/E188：HMFS 上带 `-c` 的 install 失败（Error 64），install shim 用
  cp/mkdir 替代（`INSTALL = sh <shim>` 经全树 os.walk 改写生成 Makefile）
- 真机沙箱禁止 execve shebang 脚本（ELF 不受影响）：configure 经
  `sh ./configure` 启动；生成 Makefile 中 `.sh` 集成测试规则加 `$(SHELL)`
  前缀，静态库归档合并脚本 `scripts/build/combine_libs`（libtor.a /
  libtor-testing.a 两条规则）同走 `$(SHELL)`（上游测试仍全量原样执行）
- automake 依赖跟踪关闭（`--disable-dependency-tracking`）：depfiles 引导
  会裸 execve 生成 Makefile 的 `MKDIR_P = ./install-sh`（脚本 exec 禁令），
  生成 Makefile 的 `MKDIR_P` 统一改写为 `$(SHELL)` 前缀
- E074：`make -j1`（HMDFS jobserver fifo EPERM）
- 可选特性全关：`--disable-seccomp/systemd/zstd/lzma/asciidoc`
  （OHOS 无对应环境；seccomp/systemd 为 Linux 专有）
- 依赖 openssl/libevent/zlib 由 Conan 管理（同 haproxy 3.2.0 先例）：
  `--with-*-dir=<依赖包前缀>` + CPPFLAGS/LDFLAGS 注入，TOR_SEARCH_LIBRARY 的
  link+RUN 探测（原生构建 build==host）与 make check 二进制另加
  LD_LIBRARY_PATH 前缀（3 依赖 libdir）

## 依赖关系
- 编译依赖：openssl/1.1.1w、libevent/2.1.12、zlib/1.3.1
- 运行依赖：同上（libevent 为共享库形态运行期加载；依赖 lib 目录经
  VirtualRunEnv 与 runenv_info 注入 LD_LIBRARY_PATH）

## 参考资料
- 官网：https://www.torproject.org/
- 源码镜像：https://sources.voidlinux.org/tor-0.4.9.11/
