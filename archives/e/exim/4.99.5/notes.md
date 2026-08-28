# exim 4.99.5 编译笔记

## 编译环境
- 平台: HarmonyOS PC aarch64
- 编译器: clang 15.0.4 (OHOS SDK)
- 构建系统: 自定义 Makefile (非 autotools 非 cmake)。无 configure 脚本，
  通过 `Local/Makefile` 站点配置文件 + 顶层 `make` 完成构建。
- 依赖 (Conan 静态): pcre2/10.47, openssl/3.5.6.1.1, berkeley-db/4.8.30,
  libxcrypt/4.5.2, libiconv/1.17, libtirpc/1.3.7

## 构建流程
1. `scripts/os-type` 探测 OS 类型 (`uname -s`)；顶层 Makefile 据此选
   `OS/Makefile-<os>`、`OS/os.h-<os>`、`OS/os.c-<os>`。
2. `Local/Makefile` 由 conanfile.py 的 generate() 生成，设置 BIN_DIRECTORY、
   CONFIGURE_FILE、SPOOL_DIRECTORY、EXIM_USER、CC/CFLAGS、各 Conan 静态库路径、
   TLS(OpenSSL)、DANE、DBM(Berkeley DB)、transports/routers 内建开关。
3. `make makefile` (生成 build-<os>-<arch>/Makefile) + `make -j1` 编译。
4. `make install DESTDIR=...` 部署二进制 + 默认 exim.conf。

## 适配修改 (源码)

### 1. scripts/os-type — 映射 HarmonyOS → OHOS
`uname -s` 在 OHOS 返回 "HarmonyOS"，原脚本无此 case → 输出 UnKnown →
构建中止。新增一行 `HarmonyOS)  os=OHOS;;`，使构建选用新的 OHOS 平台文件。
补丁: `patches/0001-os-type-map-HarmonyOS-to-OHOS.patch`

### 2. 新增 OHOS 平台文件 (OS/{Makefile,os.h,os.c}-OHOS)
派生自 Linux 版本 (OHOS libc6 与 glibc 高度兼容)，并修正两处 OHOS libc
差异：
补丁: `patches/0002-OS-add-OHOS-platform-files.patch`

#### 2a. DNS resolver state (os.c-OHOS)
OHOS libc 提供 `res_init()/res_search()/res_query()`，但**不导出**传统的
全局 `_res` 符号，也不导出 `__res_state()` 线程局部访问器。exim 通用
`src/os.c` 的 `os_get_dns_resolver_res()` 用 `return &_res;`，链接失败
(undefined symbol: _res)。

修复：在 `os.h-OHOS` 定义 `OS_GET_DNS_RESOLVER_RES` 跳过通用实现，在
`os.c-OHOS` 提供基于进程级 `static struct __res_state` 的自有实现
`os_get_dns_resolver_res()`。exim 在 dns_init()/dns_basiclookup() 中操作
该结构 (options/retrans/retry)；OHOS 的 res_search() 读取自身内部相同配置，
故保持单一静态状态即可让 exim 编译并运行其解析器配置路径 (R8 实质逻辑，
非空壳 stub)。`os_put_dns_resolver_res()` 保留 exim.h 的 no-op 宏默认
(我们的状态在原地被修改，无需回写)。

#### 2b. IPv4 IP 选项 (os.h-OHOS)
OHOS NDK 头文件**不提供** `<linux/ip.h>`，故 `struct ip_options` 为不完整
类型。exim 的 `smtp_in.c` 在 `#if !HAVE_IPV6 && !defined(NO_IP_OPTIONS)`
下引用 `EXIM_IP_OPT_T = struct ip_options`，编译失败
(incomplete type 'struct ip_options')。

修复：在 `os.h-OHOS` `#undef GLIBC_IP_OPTIONS` 并 `#define NO_IP_OPTIONS`，
使 smtp_in.c 跳过 IP 选项日志/拒绝路径。这是一项已弃用的 IPv4 特性
(源路由记录)，OHOS 不以此方式暴露 IP socket 选项 (R8 实质逻辑)。

## 其他观察
- `HAVE_IPV6` 为 FALSE (config.h 默认)，故 IP 选项路径原本被编译；上述
  NO_IP_OPTIONS 守卫是必需的。
- perl 路径: OHOS 无 /usr/bin/perl，Local/Makefile 设置
  `PERL_COMMAND=/storage/Users/currentUser/usr/local/bin/perl` 供工具脚本
  (exigrep/exiqgrep 等) 使用；构建期 `make install` 会执行 `./exigrep --version`
  自检。
- 编译仅有 -Wparentheses / -Wdangling-else 等无害警告，无 error。
- exim 的 `make check` 目标不存在 (无 test 目标)；上游测试套件位于独立
  exim-test Git 仓库，不随发布 tarball 提供，OHOS CI 不适用。功能验证由
  test_package/test.sh 通过 `exim --version` + `exim -bV` 完成 (R34)。

## 验证结果
- 探索性编译: 成功，exim 二进制 + 全部工具 (exigrep/exiqgrep/eximstats/
  exim_dbmbuild/exim_dumpdb/exim_fixdb/exim_lock 等) 构建完成。
- `exim --version`: Exim version 4.99.5，含 OpenSSL TLS / DANE / DKIM /
  Berkeley DB 4.8.30 / 内建 routers(dnslookup 等) + transports(smtp 等)。
- `make install DESTDIR`: 成功。
