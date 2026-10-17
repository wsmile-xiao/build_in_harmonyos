# ktls-utils 1.4.0 · 适配笔记

## 上游

- 仓库：https://github.com/oracle/ktls-utils
- Tag：`ktls-utils-1.4.0`（GitHub release 资产 `ktls-utils-1.4.0.tar.gz`）
- 大小 / sha256：232203 B / `acd9e1851e492e7e16b879b30fc800f4a98d4214fa534ebb7e24d379f5984770`（本机 2026-09-22 实算；conan 会二次校验）
- 许可：GPL-2.0-only
- 语言：C，纯 Autotools（`AM_INIT_AUTOMAKE`，无 libtool，无 `AC_CANONICAL_HOST`）
- 产物：`sbin/tlshd` 单一守护进程 + `/etc/tlshd/config` 配置样例 + man pages

## 依赖与内核 UAPI

- 构建依赖：gnutls ≥ 3.3.0、libkeyutils、glib-2.0 ≥ 2.6、libnl-3.0 ≥ 3.1、libnl-genl-3.0 ≥ 3.1
- 会话标签（可选，`--enable-session-tags`）额外需要 libyaml；本配方保持默认关闭，因此不引入 libyaml
- 唯一需要的内核头：`<linux/tls.h>`；OHOS SDK native sysroot `ohos-sdk@26.0.0.18` 已提供：
  - `TLS_TX=1`、`TLS_RX=2`
  - `TLS_1_2_VERSION` / `TLS_1_3_VERSION`
  - `TLS_CIPHER_AES_GCM_128=51` 及其尺寸常量
  - `struct tls_crypto_info` / `struct tls12_crypto_info_aes_gcm_128` 等
  - **不含** `TLS_TX_MAX_PAYLOAD_LEN` → `configure` 的 `AC_COMPILE_IFELSE` 自动把 `HAVE_TLS_TX_MAX_PAYLOAD_LEN` 置 no，无需干预
- `<linux/handshake.h>`（Linux 6.5+ UAPI）**上游不需要**：`HANDSHAKE_FAMILY_NAME`、`HANDSHAKE_A_*`、`HANDSHAKE_CMD_*` 全部在 `src/tlshd/netlink.h` 内以 `_UAPI_LINUX_HANDSHAKE_H` 守卫自带一份

## 制品仓命中情况（预检）

- `keyword=gnutls` → `gnutls/3.8.10` (pulls=146)
- `keyword=keyutils` → `libkeyutils/1.6.3` (pulls=89)，`pkg_config_name="keyutils"`
- `keyword=libnl` → `libnl/3.7.0` / `libnl/3.11.0`，通过 `components` 暴露 `libnl-3.0` / `libnl-genl-3.0`
- `keyword=glib` → `glib/2.84.0.2`，`pkg_config_name="glib-2.0"`
- `keyword=libyaml` → `libyaml/0.2.5`（本 PR 未使用）
- `keyword=nettle` → `nettle/3.10.2` 等（gnutls 传递依赖）
- `keyword=pkgconf` → `pkgconf/3.0.5`（tool_requires）

## 唯一需要动配方的错配：`libkeyutils`

`configure.ac` 里 `PKG_CHECK_MODULES([LIBKEYUTILS], [libkeyutils])` 找模块名 `libkeyutils`；而 conan 的 `libkeyutils/1.6.3` 把 `pkg_config_name` 定义为 `keyutils`，`PkgConfigDeps` 因此生成 `keyutils.pc`（不是 `libkeyutils.pc`）。

**最小处理**：在 `build()` 里，紧接 `apply_conandata_patches` 之后、`configure` 之前，把 `PkgConfigDeps` 生成的 `keyutils.pc` **原样复制**一份为 `libkeyutils.pc`（`pkg-config` 以文件名解析模块名，字段不需要改）。零补丁、零上游源码改动。

## 真机构建与验证（2026-09-22）

- 独立 `CONAN_HOME=/storage/Users/currentUser/work/psj/ch-ktls-utils`
- 设备 profile：`$HOME/.conan2/profiles/ohos-aarch64`（OHOS/armv8/clang-15/libc++/cppstd-17/Release）
- 命令：`conan create archives/k/ktls-utils/1.4.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
- 结果：见本文件末尾「CREATE 结果」段与 `reports/test-report.md`

## 上游测试（诚实声明）

- 上游 1.4.0 dist tarball **无任何测试**：`grep -rniE 'TESTS|check_PROGRAMS|noinst_PROGRAMS' --include=Makefile.am .` 输出为空；`find . -iname '*test*'` 亦为空
- 结论：上游用例数 **0**。按 §3.6 表格填 0，勾选「补全=是」，用 `test_package/test.sh` 补 7 条鸿蒙特有消费者断言（CLI 冒烟 + 负向控制），全部走用户态代码路径，不触碰内核 handshake netlink 派发

## 关于运行期内核支持（写清楚，不粉饰）

tlshd 的**存在意义**是把内核 `handshake` generic-netlink 家族的握手请求在用户态完成、再把会话密钥回灌到 socket（`SOL_TLS` setsockopt + `add_key()` 内核密钥环）。这条路径依赖 Linux ≥ 6.5 且开启 `CONFIG_TLS`+`CONFIG_KEYS`+`CONFIG_KEYS_REQUEST_CACHE`。鸿蒙 PC 的 HongMeng Kernel 1.12.0 侧的证据：

- `/usr/include/linux/handshake.h`：SDK sysroot 中 **不存在**（上游在源码里自带此 UAPI 副本，编译无碍，但内核是否注册该 genl 家族是运行期问题）
- 设备 `grep -RE 'SOL_TLS|TLS_TX|TLS_RX|TLS_CIPHER' /usr/include` 命中 **0** 条
- 设备 `grep -RE '__NR_(add_key|keyctl|request_key)' /usr/include` 命中 **0** 条
- 内核 syscalls：直接 `syscall(219)`（aarch64 `__NR_keyctl`）触发 `SIGSYS (Signal 31, core dumped)`——seccomp/内核层不允许
- 打开 `AF_NETLINK` 原始 socket（`NETLINK_GENERIC`）返回 `EACCES`

因此本包交付的是**上游用户态二进制在 OHOS aarch64 上的可构建、可安装、可执行**：`tlshd --version` / `-v` / `--help` 全部实跑通过，动态链接 gnutls/libkeyutils/libnl/glib 全部解析成功；真正的握手服务循环（`tlshd_genl_dispatch()`）需要内核 handshake 家族，属于**部署环境能力**，与 OpenSSL kTLS 后端在其它发行版上是否启用是同一类问题。配方与消费者测试**都未假装调用过内核 handshake**，避免以假绿欺骗 CI/AI 门禁。

## CREATE 结果（真机 2026-09-22，独立 CONAN_HOME=~/work/psj/ch-ktls-utils）

命令：`conan create archives/k/ktls-utils/1.4.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`

- **CREATE_EXIT:0**
- 包 `ktls-utils/1.4.0#c0abe878a8ec6118954c1c93b2efe12d:6e7b4b72428eaaa5b3bee0cdaadb0a9d9a12d521#65a8c5d4af59f5261eace755863faef2`
- 配方执行链（create 日志）：
  - `Calling source()` → `Source ...retrieved from local download cache`（本机用 curl 预置 `core.sources:download_cache`，sha256 仍按配方校验；CI 走真实 github URL）
  - 两个补丁均 `Apply patch (portability)`：0001 config.status umask、0002 config.h.in sockaddr_storage
  - configure：`checking for gcc ... clang` → `checking whether the C compiler works... yes` → `checking for TLS_TX_MAX_PAYLOAD_LEN in linux/tls.h... no`（SDK 头无此宏，configure 自动 `HAVE_TLS_TX_MAX_PAYLOAD_LEN=no`，代码有守卫）
  - `Calling build()`：`CC tlshd-*.o` × 全源文件 → `CCLD tlshd`（无 -Werror 失败，sockaddr_storage 冲突已由 config.h 抑制）
  - `Created package revision 65a8c5d4...` / `Package '6e7b4b...' created`
  - `Calling test()` → 消费者 `test.sh`：**ASSERTIONS: 7, FAILURES: 0**（tlshd 在 PATH、--version/-v/--help 通过、未知选项/缺失配置两条负向通过）
  - 产物：`bin/tlshd`(1108608 B) + `etc/tlshd/` + `licenses/` + `share/man/`
  - runner 直跑 `LD_LIBRARY_PATH=<cached lib dirs> bin/tlshd --version` → `tlshd, built from ktls-utils 1.4.0 on Sep 22 2026 05:13:17`，`DIRECT_VERSION_RC:0`

## 消费者测试为何要显式补 gnutls 的 LD_LIBRARY_PATH

`bin/tlshd` 无 RUNPATH，`DT_NEEDED` 含 `libgnutls.so.30 / libtasn1.so.6 / libgcrypt.so.20 / libgpg-error.so.0 / libkeyutils.so.1`（nettle 在本制品为静态，无 .so）。本 conan 的 `VirtualRunEnv` 把 libtasn1/libgcrypt/libgpg-error/libkeyutils 的 lib 目录放进了消费者 `LD_LIBRARY_PATH`，却漏了 gnutls 自身的 lib 目录（gnutls 包的 `cpp_info.libdirs` 为空），导致消费者测试里 `tlshd --version` 在动态链接阶段报 `Error relocating ...: gnutls_alert_send: symbol not found`。修法：在 ktls-utils 的 `package_info()` 里显式 `runenv_info.append_path("LD_LIBRARY_PATH", <gnutls.package_folder>/lib)`，把 gnutls 的运行时目录补给下游消费者（配方内已注释说明）。

## CI 链接失败复盘（2026-09-23）

PR #11881 首轮 CI 构建 #56165 在链接 `tlshd` 时找不到 `-l:ld-musl-aarch64.so.1`。该参数来自已发布 `glib/2.84.0` 的静态 pkg-config 元数据；在真机它解析到 `/lib/ld-musl-aarch64.so.1`，而 CI 构建沙箱没有 `/lib`。第一次候选修复尝试从生成的 `glib-2.0.pc` 删除 loader 参数，真机重跑随即暴露 `bindtextdomain`、`gettext`、`dgettext`、`dcgettext`、`dngettext` 等未定义符号：当前静态 GLib 正是借 musl loader 提供这些 gettext 符号，删除参数会改变链接语义。

最终修复使用制品仓已发布的 `glib/2.84.0.2`（pullCount 3147）。它是同一上游 GLib 2.84.0 的 Conan 修订版，默认为共享 GLib，并将 `proxy-libintl` 静态链接进库，pkg-config 不再引用绝对 `/lib` loader 路径，同时保留 gettext 实现。`conanfile.py` 与 manifest 均改为 `glib/2.84.0.2`；没有改上游 ktls-utils 源码或过滤链接参数。新版本真机构建/消费者结果见 `reports/test-report.md`。
