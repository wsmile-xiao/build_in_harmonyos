# liblksctp 1.0.17 适配笔记（HarmonyOS PC）

lksctp-tools — Linux 内核 SCTP（流控制传输协议）的用户空间库与工具集（C，LGPL-2.1，
autotools）。本配方交付 `libsctp.so.1.0.17`（`sctp_sendmsg`/`sctp_recvmsg`/
`sctp_getladdrs` … 封装，版本脚本 `Versions.map` 导出到 VERS_1..VERS_3）、
三个 bin 工具（`sctp_darn`/`sctp_test`/`sctp_status`）以及 `checksctp`/`withsctp` 与
`libwithsctp.so.1.0.17`。

## 本版改了什么

原始归档只有 manifest/notes/patches（ASCII 预编译包），无 conanfile。本版补齐
完整 conan 配方，按 ohpcd 制品仓规范从源码重建：

1. **平台三元组（E007）**。`bin/config.guess` 是 2015 旧版，HarmonyOS 上
   `uname -s` 返回 `HarmonyOS` → `cannot guess build type`。两条措施并用：
   (a) 打上归档自带 `0001-bin-config.guess.patch`（加 HarmonyOS 分支）+
   `0002-bin-config.sub.patch`（加 `linux-ohos*`）；(b) `generate()` 显式传
   `--build=aarch64-unknown-linux-gnu`、`--host=aarch64-unknown-linux-ohos`
   （build 侧 gnu、host 侧 ohos；两侧都写 ohos 会被 `config.sub` 误判，
   同 remctl 3.18 口径）。框架的 `patch-autotools-ohos.pl` 在 CI worker 上取不到，
   故不依赖它。两个补丁只改 autotools 辅助脚本，不动产品源码。
2. **OHOS ELF 签名（E077）**。`package()` 对 `libsctp.so*`、`libwithsctp.so*` 与
   三个 bin 工具统一「`llvm-objcopy --remove-section .codesign` 剥旧段 →
   `binary-sign-tool sign -selfSign 1` 重签 → 恢复 0755」。
3. **上游测试（§10）**。`src/func_tests` 的 v4 用例是 `noinst_PROGRAMS`，上游
   **未注册 `TESTS=`**，`make check` 因此静默零执行；真正驱动是自定义目标
   `v4test`/`v6test`，且均为**内核实时（live-kernel）用例**——每条都要
   `socket(AF_INET, SOCK_STREAM, IPPROTO_SCTP)` 起真实关联。本配方
   `--enable-tests` 全量编译这些用例；`build()` 内先用上游自带 `checksctp` 探针
   判定内核是否启用 SCTP：启用则逐条实跑 v4 用例并汇总通过/失败；未启用则逐条
   标记「资源未执行（内核未启用 SCTP）」，不静默删用例、不缩分母。
4. **HMFS `config.status` 临时目录（umask）**。`configure` 的安全临时目录惯用法
   `(umask 077 && mktemp -d "./confXXXXXX")` 在 HMFS 上建出 0700 目录后，往里写
   `subs*.awk` 被拒 → `Permission denied` / `could not setup config files
   machinery`。`TMPDIR` 重定向无效（目录名硬编码 `./confXXXXXX`，且子 shell 显式
   `umask 077` 不受 ambient umask 影响）。打 `0003-configure-umask-022.patch`
   把 `configure` 全文 `umask 077` → `umask 022`（生成的 `config.status` 从
   here-doc 继承同文本，一次替换同步修复）；只改 autotools 生成脚本，不动产品源码。
   先例：a52dec 0.7.4 同名补丁。
5. **musl uapi 头冲突（R8，配方层 shim）**。`src/func_tests/*.c` 同时 `#include`
   内核 uapi 头 `<linux/socket.h>` 与用户态头 `<sys/socket.h>`
   （`test_1_to_1_rtoinfo.c` 另含 `<linux/in.h>`/`<linux/in6.h>`）。musl 上
   `<sys/socket.h>` 已定义 `struct sockaddr_storage`、`<netinet/in.h>` 已定义
   `sockaddr_in`/`in6_addr`，uapi 头再定义一次 → `error: redefinition of
   'sockaddr_storage'`，func_tests 编译失败。规则 **R8 禁止把平台宏写进补丁**，
   故新增配方层 shim：`shim/linux/{socket,in,in6}.h`——`#ifndef __GLIBC__` 时
   `#include <sys/socket.h>`/`<netinet/in.h>`（用用户态定义），glibc 时经
   `#include_next` 落回真 uapi 头（shim 在 glibc 上自动失效）。经 `exports = 
   ["shim/linux/*.h"]` 随配方入缓存，并在 `generate()` 里
   `-I <recipe_folder>/shim` 前置到包含路径 shadow 掉 SDK uapi 头。上游源码零改动
   （先例 kbd/2.9.0 的 progname shim）。

## 测试用例

- **上游测试**：`src/func_tests` v4 用例 32 条（+ v6 9 条，共 41 条），内核实时用例。
- **鸿蒙特有测试**：`test_package/test.c`（L1）——链接 `-lsctp` 并调用公开 API
  `sctp_getaddrlen(AF_INET/AF_INET6/AF_UNSPEC)`，断言返回值等于
  `sizeof(struct sockaddr_in)` / `sizeof(struct sockaddr_in6)` / 0。该函数是库内
  纯用户态逻辑（`addrs.c:135`），不依赖内核 SCTP、不依赖 socket，因此在任意 worker
  上确定性通过；它同时验证头闭包、`-lsctp` 链接、以及运行期 `.so` 可加载
  （即 `.codesign` 签名有效）。

## 验证结果

- `conan create`: ✅ 通过（CI conan-build-test 为准）
- `test_package`（链接 + 运行 `sctp_getaddrlen` 断言）: ✅
- 上游 v4 内核实时用例: 取决于 worker 内核是否启用 SCTP（`checksctp` 判定），
  未启用时逐条标记「资源未执行」，详见构建日志 §10 汇总行

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libsctp.so.1.0.17（+ .so.1 / .so 符号链接） | SCTP 用户态库（已签名） |
| lib/lksctp-tools/libwithsctp.so.1.0.17 | LD_PRELOAD 包装库（已签名） |
| lib/pkgconfig/libsctp.pc | pkg-config 描述（Name: sctp） |
| include/netinet/sctp.h | 公开头 |
| bin/sctp_darn, sctp_test, sctp_status | 诊断/测试工具（已签名） |
| bin/checksctp, bin/withsctp | 内核 SCTP 探测 + LD_PRELOAD 包装脚本 |

## 注意事项

- 库本身不依赖内核 SCTP 即可编译、安装、被链接；只有 func_tests 的实时用例需要
  内核启用 `CONFIG_IP_SCTP`。
