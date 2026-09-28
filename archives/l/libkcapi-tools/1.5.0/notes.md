# libkcapi-tools 1.5.0 — 构建笔记

## 环境

- 日期：2026-09-25；本机即目标机：aarch64-linux-ohos（OHOS PC，clang 15.0.4，OHOS SDK sysroot）
- conan 2.29.1（OHOS 适配版）；remote `ohpcd`；conan profile：ohos 默认
- `/tmp` 只读 → 一律 `$TMPDIR`/`$HOME/tmp`

## 与 base 包（libkcapi/1.5.0）的关系

- 同源：libkcapi-tools 与 libkcapi 使用同一个上游 tarball（GitHub v1.5.0 tag，sha256 `f1d827738bda03...`）。
- 内容差异：base 包发行静态库/头文件/pkgconfig（`--disable-*apps`），本包发行 `apps/` 四个工具
  （kcapi-dgst/kcapi-enc/kcapi-rng/kcapi-hasher），上游 Makefile.am 将每个工具**静态链接** in-tree
  `libkcapi.la`。实测二进制 DT_NEEDED 仅 `libc.so`（自包含）→ 配方不 `requires libkcapi`
  （先例：libfreeaptx-tools；避免 R36 双归属）。
- base 包 bin/ 中的 `.kcapi-hasher.hmac` 是构建机 openssl 探测污染（HAVE_OPENSSL 开启后 make install
  跑 CHECKSUM_CMD）。本包用 `ac_cv_path_OPENSSL=` 显式阻断，package() 也排除隐藏文件。

## 补丁（与 base 的差异：0001 无条件化）

1. `0001-lib-kcapi-kernel-if.c.patch`：E091 sockaddr_storage 冲突。
   - **偏离说明**：base 包 1.5.0 用 `#ifdef __OHOS__` 守卫。本包改写为**无条件**
     `#define sockaddr_storage __linux_sockaddr_storage`（仅包住 `#include <linux/netlink.h>`）。
     原因：仓库 R8/PF5 默认禁止补丁引入平台宏；glibc 系统的内核 UAPI 头不声明裸
     `sockaddr_storage`，重命名为无害 no-op，跨平台安全性经推理+本平台编译实证。
     机理确认：OHOS SDK `linux/socket.h:23` 定义 `struct sockaddr_storage {`，
     musl `sys/socket.h:377` 同名定义 → 冲突；`linux/netlink.h:22` include `<linux/socket.h>`。
   - 验证：patch -p1 干净应用 + conan create 全量编译通过 + 四工具运行正常。
2. `0002-ohos-stdbool-compat.patch`：与 base 共用（musl 严格模式 bool 冲突，
   改 `apps/app-internal.h`（工具直接相关）+ `lib/internal.h`），无平台宏，原文复用。

## 构建要点

- GitHub tag 包无 configure → 自举链（勿用 autoreconf，OHOS HMDFS 下 autoconf.m4f 宏冲突）：
  aclocal --force → libtoolize --copy --force --install → autoconf → automake --add-missing --copy --foreign；
  `tool_requires automake/1.18 + libtool/2.5.4`（与 base 相同）。
- configure 的 `mktemp -d` 在 HMDFS 下恒 0700 → config.status EPERM（DRAFT-6507 同型）：
  配方内替换 configure 中该行为 `umask 000 && mkdir`（与 base 相同）。
- configure 参数：`--enable-kcapi-harser...`（4 个工具全开）+ `--disable-kcapi-test
  --disable-kcapi-speed`（测试程序/cryptoperf 不属于发行内容）+ `--disable-werror`
  （musl 下 CMSG_NXTHDR sign-compare 噪声，见 base 1.5.0-r1 note）。
- kcapi-hasher 的 install-exec-hook 用 `ln -srf` 在 pkglibexecdir 建 sha256sum 等 14 个符号链接，
  toybox 支持 `-srf`；package() 白名单裁剪掉 pkglibexec/静态库/头文件/man3。

## 运行时结论（真机）

- AF_ALG 运行时被 SELinux 全面封锁（bind EPERM）——与 base 包结论一致（平台层限制，非适配缺陷）。
- 工具的 `--version`/`-v`/`--help` 均走用户态 kcapi_versionstring() API，正常工作。
- 上游工具测试（hasher-test.sh 23 例、kcapi-dgst-test.sh 16 例、kcapi-enc-test.sh 19 例、
  主套件 test.sh 225 例）全部依赖 AF_ALG，真机 0% 可运行（原因见上）。
- test_package 断言集：版本契约 ×5、--help 契约 ×3、自包含 ×4、反例 ×1、.codesign 加载性 ×4（见 MANIFEST.yml）。

## ELF 段

- 本机 OHOS SDK clang/lld 链接产物自动携带 `.codesign` 段（readelf 实证），无需配方内签名步骤
  （对比：libfreeaptx-tools 在配方内补签，因当时工具链未自动签）。

## 构建状态

- 首次 conan create：✅ 全绿（2026-09-25，本机 W3 同源验证，共 6 轮迭代），All tests passed。

### 构建过程追加记录（2026-09-25）

本地 `conan create`（-pr:h=b 同 profile，--build=missing）经 6 轮迭代通过，日志
`~/tmp/ohc-logs/libkcapi-tools-1.5.0-create-{1..6}.log`。关键修正与实证：

1. **HMDFS 脚本 exec 限制与自举链（attempt-1/2）**：本机 python3（app sandbox）后代进程
   execve hmdfs 上的 shebang 脚本（autoconf/autom4te/aclocal/libtoolize 为 perl/sh 脚本）
   报 EACCES；ELF 二进制 exec 不受限。解法与知识库既有条目同型
   （libuio-0.3.0-hmdfs-autotools-toolchain-interpreter-bootstrap、
   libdisasm-0.23-hmdfs-script-exec-denied-sh-configure）：把 bootstrap 工具改为
   **解释器读取式调用**（`PERL5LIB=... perl <abs>/aclocal`、`AUTOMAKE_LIBDIR=... perl
   <abs>/automake`、`/bin/sh <abs>/libtoolize`），CI 常规 Linux 上行为中性。conan 缓存中
   automake 的 `Automake::Config` 硬编码 `//share/automake-1.18`，需 AUTOMAKE_LIBDIR +
   PERL5LIB 双覆盖；libtool 的 conan 包装 libtoolize 期望 `_lt_pkgdatadir` 指向
   `share/libtool-conan`（缓存回填 build-aux/libltdl 与 m4 宏）。最终自举链
   aclocal → libtoolize → autoconf → automake 全通，compile/missing/depcomp 就位。
2. **basic_layout 目录结构（attempt-3）**：configure/make 必须显式 `cwd=self.source_folder`
   （源码树在包 build 目录根，`build-release/` 仅含 generators）；package() 同理改手动
   `make install DESTDIR=...`。
3. **--disable-shared 关键性（attempt-5→6，重要发现）**：上游 Makefile.am 将 4 个工具链到
   in-tree libkcapi.la；libtool 共享构建默认链接 `.so`，导致工具携带
   `DT_NEEDED libkcapi.so.1` 而本包不发布库 → 运行报 symbol not found（exit 127）。
   加 `--disable-shared` 强制静态链接后每个工具 `DT_NEEDED` 仅 `libc.so`，与 openEuler
   libkcapi-tools 的自包含形态一致。此为**配方实质修正**，非平台规避。
4. **install-exec-hook 的 ln -srf（attempt-4）**：hasher 安装钩子在 DESTDIR 包缓存里
   `ln -srf` 建 14 个别名链接，HMDFS 对 conan 缓存目录的 symlink() 拒绝
   （Permission denied；与包提取时软链丢失同源）。配方在 configure 后对生成的 Makefile
   将 `$(LN) -srf ` 重写为 `cp -f `（参数序相同；staging 的 pkglibexec 链接本就被
   package() 白名单裁剪，语义等价；常规 Linux CI 上 cp 同样成立）。
5. **configure mktemp**：`umask 000 && mkdir` 替换（DRAFT-6507 同型）照常生效。
6. **包内容终检**（readelf/find 实证）：包仅含 `bin/kcapi-{dgst,enc,rng,hasher}`（NEEDED
   仅 libc.so）+ `share/man/man1/` 4 页；无 lib/libexec/include/pkgconfig/.hmac 残留。
7. **test_package 运行结果（attempt-6，真机实测）**：15 项断言全绿——4 工具 PATH 可寻、
   --version ×3 与 hasher -v/--version（退出码 0，输出 "libkcapi 1.5.0" 契约）、
   --help 退出码 1 契约 ×3、自包含（无 libkcapi DT_NEEDED）×4、未知选项非 0 ×1、
   .codesign 段 ×4。AF_ALG 加密功能断言因平台 SELinux 限制未纳入（见上）。

> 注：工具 `--help` 退出码为 1 是上游 usage() 的既定契约（exit(1) 收尾），非缺陷；
> `--version` 退出码 0。与命令声明（commands.json type=tool, binary=true）一致。
## 上游测试真机实跑记录（2026-09-26，rule4 复审回应）

以 `--enable-kcapi-test` 完整构建上游测试程序（bin/kcapi 等，构建自举链全通），
用上游 test/ 目录脚本**原样驱动**全部 5 个脚本（未修改任何上游测试文件）：

| 脚本 | 实跑标记 | PASS | FAIL |
|------|---------|------|------|
| test.sh | 225 | 0 | 225 |
| hasher-test.sh | 182 | 18 | 164 |
| kcapi-dgst-test.sh | 384 | 64 | 320 |
| kcapi-enc-test.sh | 483 | 120 | 363 |
| kcapi-enc-test-large.sh | — | 上游 DEACTIVATED（wordsize 检测缺陷） |
| **合计** | **1275** | **202** | **1072** |

- 202 个 PASS 逐条核对后**全部为退化通过**（负路径用例或期望/实际输出同时为空），
  正向密码学功能用例 0 通过；全部正向用例失败于同一处
  `AF_ALG: bind failed (errno: -13)`。
- 本机复验（2026-09-26）：bind hash/skcipher/rng/aead 四类均 EACCES；
  `/proc/crypto` 不存在；域 `u:r:hishell_hap:s0`，param selinux.enforce 读写均被拒
  （errNum 106/114）；无 root；无 /dev/kvm、qemu、docker——环境内不存在
  可提供 AF_ALG 的替代内核。
- 完整逐条日志与 sha256：reports/upstream-test-execution.md 及同目录 5 份 .log；
  平台根因基线（2026-09-16 strace 鉴别）见 archives/l/libkcapi/1.5.0/notes.md。

---

**编译结束**: 2026-09-25 10:34（2026-09-26 补上游套件真机实跑，见上）
**最终状态**: built
