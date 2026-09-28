# jool-modules-lts 6.18.39 适配笔记（上游 Jool v4.1.14）

## 1. 上游形态与本包交付边界

Jool 是 SIIT/NAT64 双栈翻译器，上游交付物分两层：

- **内核层**（`src/mod/`）：`jool` / `jool_siit` 两个 Linux 内核模块
  （`obj-m += jool.o` / `obj-m += jool_siit.o` / 公共库 `obj-m += jool_common.o`，
  DKMS 打包见 `dkms.conf`）——在内核里做报文翻译；
- **用户层**（`src/usr/`）：`jool` / `jool_siit` 两个 netlink CLI
  （实例/表项/统计的配置面）与 `joold` 会话代理守护进程。

**本包交付用户层三件套**（`bin/jool`、`bin/jool_siit`、`bin/joold`）+ **上游
源码快照**（`share/jool-modules-lts/upstream/`，任务指定 tarball 原样再解压）。
内核层在 OHOS PC 侧不可构建（无内核构建树 `/lib/modules/*/build`、无 root、
无 insmod/modprobe 途径），**不交付 .ko、不伪造内核态通过**；源码快照供
fail-closed 契约测试逐文件校验，并在平台未来提供内核构建树时可复用
（同 lenovolegionlinux 0.0.20 的「内核模块源码快照交付模式」）。

内核模块缺失时 CLI 的运行时契约（上游源码注释原文，`src/usr/nl/core.c:277`）：

> Contract: The result will contain 0 on success, -ESRCH on module likely not
> loaded.

即 OHOS 上运行 CLI 是**设计内的降级路径**：`jool instance display` 打印
"Jool's socket family doesn't seem to exist. (This probably means Jool hasn't
been modprobed.)" 并非零退出——本包测试对这一行为做了显式断言。

## 2. 构建要点（全部经本机 OHOS clang 交叉验证）

| 环节 | 处置 | 依据 |
|---|---|---|
| 源码无 `configure` | `Autotools.autoreconf()` 自举；`tool_requires automake/1.18 + libtool/2.5.4`（CI 沙箱 USER=100 看不到手工安装的 autotools） | argp-standalone / abiword-plugin-eml 先例 |
| `PKG_CHECK_MODULES(LIBNLGENL3, libnl-genl-3.0 >= 3.2.22)` | `PkgConfigDeps` 生成组件 .pc（libnl 配方的 `pkg_config_name` 恰为 `libnl-genl-3.0`），`PKG_CONFIG_PATH` 指向 generators 目录 | abiword-plugin-eml 先例 |
| `AC_CHECK_LIB(argp, argp_parse)` + `<argp.h>` | argp-standalone/1.5.0 静态库；`-L`/`-I` 经 LDFLAGS/CPPFLAGS 显式注入（cpp_info 相对路径用 package_folder 归一化） | abiword-plugin-eml 先例（AutotoolsDeps 不可靠） |
| E119：sysroot `linux/netlink.h` 用未定义的 `__kernel_sa_family_t`；`linux/socket.h` 的无前缀 `sockaddr_storage` 与 musl `sys/socket.h` 冲突 | `CPPFLAGS` 预定义 `-D_UAPI_LINUX_SOCKET_H -D__kernel_sa_family_t=ushort` | libnl/3.11.0 MANIFEST「消费者须知」的既定处置 |
| xtables / bash-completion 可选依赖 | `--with-xtables=no`（上游 Makefile.am 自动加 `-DXTABLES_DISABLED` 并裁掉 `src/usr/iptables/`）、`--with-bash-completion-dir=no` | 上游 configure.ac 原生开关，无源码补丁 |
| E114：HMDFS 拦 autoconf 临时目录子进程写入 | autoreconf 后修补 configure：`ac_tmp=$tmp` 重定向到预建目录 + 退出 trap 不删 + `umask 077`→`022` | abiword-plugin-eml / argp-standalone 先例 |
| E074 并行 make 竞态 | `make -j1` | 仓库先例 |
| R15 config.guess 不识别 OHOS | 显式 `--build=aarch64-linux --host=aarch64-linux` | abiword-plugin-eml 先例 |
| make install 会写系统目录 | package() 用 glob+copy 收集 `src/usr/{nat64,siit,joold}` 产物 + chmod 755 | abiword-plugin-eml 先例 |

**零源码补丁**：全部适配经由上游 configure 开关与编译器预定义宏完成；
`conandata.yml` 的 `patches: {}` 为空。

本机交叉验证记录（OHOS clang 15，`--target=aarch64-linux-ohos` + OHOS sysroot，
链接制品仓 libnl/3.11.0 + argp-standalone/1.5.0 静态库）：

- 50/50 用户态源文件 `-fsyntax-only` 通过（排除 `src/usr/iptables/`，因
  `--with-xtables=no` 不参与构建）；
- 三个二进制真实链接成功：`jool`（356KB）、`jool_siit`（356KB）、`joold`（359KB），
  ELF/aarch64。

## 3. 测试策略（rule4 / rule12 / rule8 / rule9 的合规表达）

上游 36 个测试脚本**全部以 Linux 内核模块为被测对象**（17 个单元测试工程编译
为 `.ko` 后 `sudo insmod`+`sudo dmesg`；graybox 套件 `insmod graybox.ko` + netns
报文注入；regression/fragmentation/compilation 需要 root / modprobe / 预编译
内核树 / GRUB 多内核）。OHOS 非特权用户态沙箱（USER=100）原理上不满足任何一项
——**上游用例形态问题**，非缺依赖/非环境配置。

如实分层（详见 `reports/upstream-test-evidence.md` 与 `test_package/MANIFEST.yml`）：

- **上游通过率 0/36**，逐条具体技术原因；
- 其中 **2 个脚本在 CI 真实执行**并以预期方式阻塞（client-test.sh 与 graybox
  run.sh 的首语句是非 root 门禁 → 退出码 1 + "Please start the script as root
  or sudo."）——第一手执行证据；
- 其余 34 个经 **fail-closed 前置审计**（每脚本必须仍命中阻塞模式串，未命中
  即 CI 失败强制重评）；
- **新增 118 断言全部通过**：CLI 行为契约 28（`--help/--usage/--version=4.1.14.0`、
  joold 无参退出码 22=EINVAL、`-ESRCH` 优雅降级不崩溃）+ 鸿蒙平台 19（bin 交付
  契约、commands.json 入口、整包无 .ko、快照纯净与完整）+ 内核模块源码契约 30
  （obj-m×3、MODULE_LICENSE、module_init/exit、/lib/modules 依赖、dkms.conf、
  src/common 混合源码）+ 阻塞前置审计 41；
- 未声明通过：内核模块构建/加载、NAT64/SIIT 转发、graybox 报文注入。

## 4. 版本口径

- 平台包名/版本：`jool-modules-lts/6.18.39`（任务指定，目录/分支/commands.json
  一致）；
- 上游软件版本：Jool **v4.1.14**（`AC_INIT([Jool], [4.1.14])`，`xlat.h`
  `JOOL_VERSION_STR "4.1.14.0"`，`jool --version` 实测输出）；
- 源码 URL 与 sha256 按任务指定（codeload GitHub 归档）。
