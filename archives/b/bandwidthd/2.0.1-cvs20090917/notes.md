# bandwidthd 2.0.1-cvs20090917 适配笔记

## 编译环境

- 构建系统：Autotools（`configure.in` + `Makefile.in`，上游 tarball 不含 `configure`）
- 编译日期：2026-08-26
- host-side 验证：macOS arm64、Apple clang 21、GNU make 3.81、Autoconf 2.73、Automake 1.18
- WSL 交叉验证：Ubuntu 24.04 x86_64、OHOS SDK clang 15、系统 bison 3.8.2、系统 flex 2.6.4
- 目标环境：OpenHarmony PC arm64，Conan profile `ci/conan/profiles/ohos-aarch64`
- 当前状态：`built`；已在真实 OHOS Worker `hm` 完成 Conan `conan create` 和 `test_package`，2/2 通过。本地 WSL/QEMU 仍不能替代 Worker 运行验证，QEMU 运行 `--help` 与 `-l` 均因 loader/runtime 不可用退出 139

## 源码与依赖

- 源码：Debian 官方镜像中的 upstream orig tarball
- SHA256：`9e91e59a64d98c4f2ae11530e8bd8e360ad4df9168ae77fa5896ffc5953fbffb`
- 编译依赖：`gd/2.3.3.2`、`libpcap/1.10.6`、`libpng/1.6.58.2`
- 构建工具：`bison/3.8.2`、`flex/2.6.4`；`configure`/`config.h.in`/Autoconf 辅助脚本由主机侧一次性生成并随补丁提供
- PostgreSQL 支持是源码中的可选 `HAVE_LIBPQ` 分支，本配方不引入 PostgreSQL 依赖，默认构建静态 HTML/PNG 模式。

## 实际编译过程

主机侧使用 Homebrew 提供的 gd/libpcap/libpng 和 Autotools 生成可复现的 bootstrap 补丁：

```bash
autoreconf -fi                         # 仅用于生成 0002-0005 补丁，不在 OHOS Conan build 中执行
CPPFLAGS='-I/opt/homebrew/opt/gd/include -I/opt/homebrew/opt/libpcap/include -I/opt/homebrew/opt/libpng/include' \
LDFLAGS='-L/opt/homebrew/opt/gd/lib -L/opt/homebrew/opt/libpcap/lib -L/opt/homebrew/opt/libpng/lib' \
CFLAGS='-O2 -fgnu89-inline' \
./configure --prefix=/Users/awstme/usr/local
make -j1
```

交付配方使用 `AutotoolsToolchain` 注入依赖路径、真实 build/host 三元组和 `-fgnu89-inline`，通过 0002-0005 补丁直接提供 `configure`、`config.h.in` 及最新 `config.guess/config.sub`，避免 OHOS Conan build 加载 HMDFS 中的 Perl XS 模块；同时固定 `make -j1`。WSL 使用 OHOS SDK clang 和 Conan 缓存中的目标库完成了 `aarch64` 交叉编译，最终产物为带 `/lib/ld-musl-aarch64.so.1` 解释器的 ARM64 ELF。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make -j2` 报 `conf.tab.h: file not found` | `conf.l.o` 规则没有声明对 bison 生成的 `conf.tab.h` 的依赖，并行构建发生竞态 | 配方使用 `make -j1`，不改上游生成文件 |
| 2 | 链接缺少 `Credit`、`FindIp`、`HostIp2CharIp` | 2009 年源码使用 GNU89 外部 inline 语义，现代 clang 默认 C99/C23 语义不发出外部定义 | 在 Conan toolchain 中追加 `-fgnu89-inline`，保持源码语义 |
| 3 | OHOS Conan build 执行 `autoreconf` 时 `Cwd.so` 被拒绝加载 | CI 同时使用 OHOS profile 作为 build/host，Perl XS 位于 `/storage` HMDFS，hmmac 禁止从该路径 dlopen | 主机侧生成并通过 0002-0005 补丁固化 `configure`、`config.h.in`、`config.guess/config.sub`；配方移除 `autoconf/automake` tool requirements，构建阶段不再执行 `autoreconf` |
| 4 | 交叉 configure 在 `/sw/lib` 等路径检查处中止 | 上游 `AC_CHECK_FILE` 不能在 cross compiling 时检查构建机文件系统 | 补丁仅在非交叉构建时保留这些可选主机路径检查 |
| 5 | OHOS 包只有 `libpng16`，上游只检查 `-lpng` | Conan libpng 配方导出的库名与旧 Autotools 检查不一致 | 补丁优先检查 `-lpng16`，保留 `-lpng` 回退 |
| 6 | 部分 libc 的 `resolv.h` 没有公开 `_res` 对象 | `graph.c` 直接访问可选的 resolver 内部状态 | 用 `AC_CHECK_DECLS([_res])` 进行特性探测；未声明时跳过非必要调优，不使用平台宏 |
| 7 | 现代 clang 链接时报 `SubnetTable`/`IpTable` 重复定义 | 旧头文件在每个翻译单元定义全局数组 | 补丁将头文件声明改为 `extern`，由 `bandwidthd.c` 提供唯一实体定义 |
| 8 | 上游没有 `make check` 目标 | `Makefile.in` 只定义 all/clean/install/distclean/real-clean | 不伪造上游测试通过；test_package 真实执行安装后的 `bandwidthd --help` 与 `bandwidthd -l` |
| 9 | 旧 `config.sub` 不识别 `aarch64-unknown-linux-ohos` | 源码快照内置 2001 年版 GNU config.sub | 通过 0002/0004 刷新 `config.guess/config.sub`，配方显式传入动态 build/host triplet |
| 10 | Conan 源码外构建时无法确定 `tcphdr` 源端口字段 | `AC_CHECK_MEMBER` 测试包含源码目录下的 `bandwidthd.h`，而构建目录不在源码目录；musl 还需要系统扩展声明 | 使用 `AC_USE_SYSTEM_EXTENSIONS`，并直接从 `<netinet/tcp.h>` 探测 `source/dest` 或 `th_sport/th_dport` |
| 11 | `config.status` 报 `could not setup config files machinery` | Autoconf 生成的 CR 规范化 `sed` 管道在 OHOS shell 环境中失败 | 固化的 `configure` 对 Unix 行尾直接复制 `subs1.awk`，保留 config.status 的后续 awk 替换流程 |
| 12 | `./config.status: line 579: ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 对 `umask 077` 创建的 Autotools 临时目录施加特殊权限，目录创建成功但当前进程无法写入 | 固化的 `configure` 将生成 `config.status` 的 `umask 077` 改为 `umask 022`，覆盖 `mktemp` 和回退 `mkdir` 两条路径（E129） |
| 13 | `make: No rule to make target 'bandwidthd.o'` | Conan `basic_layout` 默认在独立 `build-release` 中执行 make；遗留 `Makefile.in` 没有 `VPATH`，无法从源码目录解析对象文件 | `layout()` 保留 `basic_layout` 的生成器配置，但将 `self.folders.build` 设为 `self.folders.source`，让 configure、make、install 使用同一源码目录 |
| 14 | OHOS `checking whether the C compiler works... no` / `C compiler cannot create executables` | CI profile 提供通用 `/data/service/hnp/bin/clang`；首个链接探测既可能缺少显式 `aarch64-unknown-linux-ohos` 目标，也可能因 SDK `ld.lld` 找不到其 `llvm/lib/libxml2.so.16` 运行库而失败（摘要未包含 `config.log` 的第一条 linker stderr） | 在 `AutotoolsToolchain` 的 C/C++ 编译及链接 flags 中显式加入目标三元组，并自动发现 OHOS SDK `llvm/lib` 加入 `LD_LIBRARY_PATH`；先验证裸 clang 参数再决定链接模式 |
| 15 | `graph.o` 只显示 10 个 warning 和 2 个被截断的 error | 日志尾部的 `gdImageString` 指针符号 warning、未使用变量 warning 在主机构建中也存在且不会阻断编译；结合源码位置，缺失的两条 error 很可能是 OHOS libc 声明 `_res` 但 `struct __res_state` 没有 `retrans`/`retry` 成员 | 在 `configure.in` 增加 `AC_CHECK_MEMBERS`，并让 `graph.c` 同时检查 `_res` 声明及两个成员；若下一次 CI 仍失败，需要补充被截断的两条原始 `error:` 行确认 |
| 16 | `-all-static` / `-static` 导致 `ld.lld: unable to find library -lpng16` | bandwidthd 通过裸 clang 直接链接，且已发布的 `libpng/1.6.58.2` OHOS binary 只有 `libpng16.so`、没有 `libpng16.a`；`-all-static` 不是裸 clang 参数，`-static` 又要求静态归档 | 移除静态链接参数，仅保留 `--target=aarch64-unknown-linux-ohos`；其余 gd/libpcap 静态库仍由 Conan 依赖提供 |
| 17 | WSL Conan create 执行 OHOS `bison` 报 `/lib/ld-musl-aarch64.so.1` 缺失 | WSL 使用 OHOS profile 作为 build/host 时，build requirement 也解析为 OHOS/aarch64；WSL 没有可用的 OpenHarmony runtime loader | 真实 CI Worker 继续使用原生 OHOS build/host profile；WSL 仅以系统 bison/flex 做额外交叉编译实验，不将其结果标记为 W3 |
| 18 | OHOS worker 的 HNP bash 在 HMDFS 构建目录中执行 `pwd` 失败 | Autoconf 通过 profile 的 `CONFIG_SHELL` 重新执行 configure，HNP bash 对 HMDFS 当前目录的 `getcwd()` 支持不可靠 | OHOS 配方在生成的 Conan 环境加载后，调用 configure 时显式设置 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`；其余构建环境保持 profile 配置 |
| 19 | `make install` 报 `install: -m755 does not exist` | 上游 `Makefile.in` 使用 `./install-sh -m755/-m644`，归档内旧 `install-sh` 只解析分离参数 `-m 755/-m 644` | 新增 `0008-install-sh.patch`，支持紧凑 mode 参数，并在真实 OHOS worker 的 Conan install 阶段验证通过 |
| 20 | OHOS worker 直接执行 HMDFS 中的包内 ELF 报 `Operation not permitted` | Worker 的执行策略要求用户编译 ELF 具有有效 code signature，文件权限为 0755 仍不足 | `test_package` 将已安装 `bandwidthd` 复制到 `/data/storage/el1/base`，移除旧 `.codesign` 后调用 `binary-sign-tool sign -selfSign 1`，再执行真实测试 |

## 源码修改

通过 `refresh-patch --auto` 生成 8 个可复现补丁：

1. `0001-bandwidthd.h.patch`：修复现代 clang 的全局数组重复定义。
2. `0002-config.guess.patch`：更新 Autoconf 主机识别脚本。
3. `0003-config.h.in.patch`：提供无 autoreconf 构建所需的 autoheader 输出。
4. `0004-config.sub.patch`：识别 `aarch64-unknown-linux-ohos`。
5. `0005-configure.patch`：提供主机侧生成的 configure，避免 CI 在 HMDFS 中运行 Perl XS，绕过 OHOS config.status 的 CR 规范化 sed 兼容性问题，并修复 HMDFS 临时目录权限。
6. `0006-configure.in.patch`：启用系统扩展，支持源码外构建的 `tcphdr` 特性探测、跨编译和 `libpng16` 库名，并探测 `_res` 及其 resolver 成员。
7. `0007-graph.c.patch`：仅在 configure 探测到 `_res`、`retrans` 和 `retry` 时使用 resolver 调优。
8. `0008-install-sh.patch`：让遗留 `install-sh` 接受 `-m755` 和 `-m644` 紧凑 mode 参数。

## 验证结果

应用原始 tarball + 7 个补丁后的主机侧构建及 CLI 验证通过：

```text
patch sequence                         PASS
./configure ...                         PASS
make -j1                                PASS
make check                              FAIL: upstream has no check target (not a test failure)
./bandwidthd --help                    PASS
./bandwidthd -l                        PASS
```

test_package 包含 2 个测试组：帮助文本包含 Usage/--help，设备枚举命令成功返回。真实 OHOS worker `hm` 已完成 Conan W3：安装后的 ELF 先按 worker 规则 self-sign，再从 `/data/storage/el1/base` 执行，两个测试均通过（2/2）。

真实 OHOS worker 验证命令：

```bash
conan create archives/b/bandwidthd/2.0.1-cvs20090917 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

结果：`conan create` 返回 0，Conan package build/install 通过；`test_package` 返回 0，输出 `bandwidthd CLI checks passed`。验证日志保存在 `reports/conan-create.log`，配方门禁报告保存在 `reports/conan-verify-report.md`。

WSL 交叉复现命令（验证编译链接，不等价于 Conan W3）：

```bash
./configure --build=x86_64-pc-linux-gnu --host=aarch64-unknown-linux-ohos \
  --prefix=/ --sysconfdir=/etc --localstatedir=/var \
  --with-htdocs-dir=/var/bandwidthd/htdocs --with-log-dir=/var/bandwidthd \
  --with-extension-dir=/var/bandwidthd/extensions
make -j1
file bandwidthd
```

结果：`bandwidthd` 为 ARM aarch64 PIE ELF，动态依赖 `libpng16.so.16` 与 OHOS `libc.so`，链接通过；使用系统 bison/flex 完成了源码树的 `make -j1`。WSL 临时 QEMU runtime 执行 `--help` 与 `-l` 均因 loader/runtime 不可用退出 139；该限制不影响真实 OHOS worker 已完成的 2/2 运行验证。
