# 内核模块交付物的分层适配：内核态判定清单（§1–§3 仍成立）+ 用户态分层交付模式（§4 结论修订）

> 草稿来源：jool-modules-lts 6.18.39 适配任务（平台任务 `contrib-12671`；上游 Jool v4.1.14）
> 状态：DRAFT（待评审转正式 E 条目）
> 日期：2026-09-20 初版 / **2026-09-21 结论修订**　实测环境：DevEco Studio HarmonyOS 26 SDK native clang 15.0.4，target `aarch64-linux-ohos`，sysroot `os=OHOS 6.0 / arch=armv8`
> 同类先例：`DRAFT-lenovolegionlinux-0.0.20-kernel-module-not-deliverable`（sysfs 路径硬编码型子集依赖）；本条补充 **netlink 客户端型**子集依赖、**内核态测试设施**、**多模块 Kbuild** 与 **bionic UAPI 导出规模化判据**。
>
> **⚠ 结论修订（2026-09-21，必读）**：初版结论「整体无法适配、不建包、走 issue 申报」经 MR #11362 管理员审查被判定
> **rule4 FAIL（编译失败 + 上游测试 0/36 且无真实执行证据）+ rule12 FAIL（鸿蒙特有测试 N=0）**。同日同构任务
> lenovolegionlinux 0.0.20（MR #11320）以**「用户态制品真实构建 + 内核模块源码快照随包交付 + fail-closed 契约测试 +
> 上游 0/N 以用例形态归因 + 可安全执行的脚本真实执行」**结构通过 CI（构建 #52755）。故本条结论修订为：
> **内核模块不可交付的判定（§1–§3、§5）全部保留；但处置从「不建包」改为「分层交付」——上游自建为独立
> `bin_PROGRAMS` 的用户态组件真实构建交付，内核态部分以源码快照 + fail-closed 契约承载，禁止伪造/桩化不变。**
> 初版「不得只交付用户态 CLI 子集」的绝对禁令对应修正为条件禁令：仅当用户态子集**无上游设计内的独立价值/降级契约**
> 时才禁止（本例 CLI 是上游 DKMS 发行版的常驻配置面，模块未加载时按上游 `-ESRCH` 契约优雅降级，非裁剪）。

## 1. 适用场景（什么时候该想起这条知识）

任务里的三方库，其**交付物本身位于内核空间**，且配套的用户态组件（CLI/守护进程）是内核模块的**纯控制面客户端**。本例 Jool：三个 `obj-m` 模块 + 经 generic netlink 配置模块的 CLI：

```make
# src/mod/common/Kbuild:4 / src/mod/nat64/Makefile:8 / src/mod/siit/Makefile:8
obj-m += jool_common.o        # obj-m += jool.o        # obj-m += jool_siit.o
```

```bash
# dkms.conf
MAKE[0]="make -C ${kernel_source_dir} M=.../src/mod/{common,nat64,siit} modules"
BUILT_MODULE_NAME[0..2]="jool_common"/"jool"/"jool_siit"   AUTOINSTALL="yes"
```

判别特征（任一命中即入本判）：`obj-m`/`MODULES_DIR ?= /lib/modules/$(shell uname -r)`/`dkms.conf`；CLI 侧出现 `genl_connect`/`nl_socket_alloc`/`<X>nl_setup`/`genl_ctrl_resolve`；测试脚本出现 `sudo insmod`/`sudo dmesg`/`modprobe`。

## 2. 判定清单（全部为可复现命令）

| 步骤 | 命令 | 判据 |
|---|---|---|
| ① 交付物是否内核态（多模块同判） | `grep -rn "obj-m\|MODULES_DIR\|/lib/modules" src/mod --include=Kbuild --include=Makefile*`；`grep -n "kernel_source_dir\|BUILT_MODULE_NAME\|AUTOINSTALL" dkms.conf` | 命中 `obj-m` / `dkms.conf` 关键字 ⇒ 内核态 |
| ② 头文件核验 | `grep -rhE '^[[:space:]]*#[[:space:]]*include[[:space:]]*<[^>]+>' src/mod \| sed -E 's/.*<([^>]+)>.*/\1/' \| sort -u \| while read -r h; do test -e "$SYSROOT/usr/include/$h" && echo present $h \|\| echo MISSING $h; done` | 统计「缺失」与「bionic UAPI 导出」；**头名勿用 `tr -d "#include<>"` 提取**（`tr -d` 删字符集合，会把 `linux/module.h` 变成 ` x/mo.h`，令所有头恒报 MISSING） |
| ③ 现存头是否内核 API | `grep -c 'automatically generated' $SYSROOT/usr/include/<h>`；`grep -cE 'MODULE_LICENSE\|module_init\|struct module\|THIS_MODULE' $SYSROOT/usr/include/<h>` | 横幅=1 且模块 API 命中=0 ⇒ bionic 用户态 UAPI 导出；**行数大（249 行的 linux/tcp.h）不代表是内核头** |
| ④ 内核构建树 | `for p in usr/src usr/include/linux/kconfig.h usr/include/config usr/include/generated; do test -e $SYSROOT/$p; done`（SDK 与 NDK sysroot 都查） | 四项全缺 ⇒ 无构建树 |
| ⑤ 用户态子集是否 netlink 客户端（不得裁剪论证） | 模块侧 `grep -rn "genl_register_family\|_FAMILY \"" src/mod src/common`；CLI 侧 `grep -rn "nl_socket_alloc\|genl_connect\|joolnl_setup\|genl_ctrl_resolve" src/usr` | CLI 每命令与 genl family 握手、模块未加载即 `-ESRCH`、错误文案指向 kernel module ⇒ 子集零功能，交付即裁剪 |
| ⑥ 测试设施是否内核态 | `grep -rn "insmod\|rmmod\|dmesg\|modprobe" test --include='*.sh'`；`find test -name Kbuild \| xargs grep -l obj-m` | 测试目标编译为 `.ko` / 框架自带 obj-m 模块 / 要求 recompile+reinstall 模块 ⇒ 上游测试用户态可运行数为 0 |
| ⑦ 实测编译 | `clang --target=aarch64-linux-ohos --sysroot=$SYSROOT -I src -fsyntax-only src/mod/siit/*.c` | 应失败于第一个内核内部头（含传递引入者，如本例 `net/net_namespace.h` 经 `mod/common/init.h` 引入） |

## 3. 实测证据（jool-modules-lts 6.18.39 / Jool v4.1.14）

**交付物**：三个内核模块（`jool_common`/`jool`/`jool_siit`）+ netlink CLI；`Makefile.am:12-13 SUBDIRS = src/common src/usr`（发行版包只构建用户态）、`DIST_SUBDIRS` 携带 `src/mod` 源码交 DKMS 重编译。

**头文件核验**：41 个唯一 include（28 `linux/*`、12 `net/*`、1 `crypto/*`）——**28 缺失**（含 `linux/skbuff.h`、`linux/list.h`、`linux/mutex.h`、`net/ip.h`、`net/netfilter/...`）；**13 现存全部为用户态 UAPI 导出**：

| 结果 | 头文件 |
|---|---|
| 严格桩（3） | `linux/module.h`（**23 行，仅 2 常量**）、`linux/string.h`(22)、`linux/types.h`(39) |
| 临界小桩（2） | `linux/errno.h`(19)、`linux/stddef.h`(22) |
| bionic UAPI 导出（8） | `linux/genetlink.h`(92)、`linux/icmp.h`(97)、`linux/icmpv6.h`(125)、`linux/ip.h`(152)、`linux/ipv6.h`(148)、`linux/sched.h`(85)、`linux/tcp.h`(249)、`net/route.h`(124，musl 风格无横幅) |

全部 13 个对 `MODULE_LICENSE`/`module_init`/`struct module`/`THIS_MODULE` 命中为 **0**；12/13 含 bionic 横幅 "This header was automatically generated from a Linux kernel header..."。

**内核构建树**：SDK sysroot 与 NDK sysroot 的 `usr/src`、`usr/include/linux/kconfig.h`、`usr/include/config`、`usr/include/generated` **四项全部不存在**；无 `asm/` 目录。

**实测日志**：

```text
# ① 任务原样命令（-I src/mod/common）
src/mod/siit/jool_siit.c:1:10: fatal error: 'mod/common/init.h' file not found   # exit 1
# ② 补齐上游 Kbuild 等价路径（-I src）后，失败于传递引入的内核内部头
src/mod/common/init.h:4:10: fatal error: 'net/net_namespace.h' file not found    # exit 1
# ③ 上游 Kbuild/DKMS 方式（kernel_source_dir 指向 sysroot）
make: *** No rule to make target 'modules'.  Stop.                               # exit 2
```

**netlink 客户端依赖**：`src/common/config.h:17 #define JOOLNL_FAMILY "Jool"`；模块侧 `src/mod/common/nl/nl_handler.c:235-237 strcpy(jool_family.name, JOOLNL_FAMILY); genl_register_family(&jool_family)`；CLI 侧 `src/usr/nl/core.c:288 nl_socket_alloc()`、`:307 genl_connect()`，每个子命令（`src/usr/argp/wargp/*.c`）`joolnl_setup()`→`joolnl_teardown()`；版本握手报 "Version mismatch. The kernel module's version is ..."（`core.c:90-97`）；模块未加载 `-ESRCH`（`core.c:277`）；响应处理全部为 "The kernel module's response ..."（`attribute.c:18`、`common.c:27`、`core.c:154/165/190/268`、`global.c:45`）。

**内核态测试设施**（36 个 `.sh` 中 35 个实际用例全部内核态依赖）：
- `test/unit/`：`Makefile` 17 个 PROJECTS **编译为 .ko**；`test.sh:4 TESTS=`ls -r */*.ko``、`:15 sudo insmod $i && sudo rmmod $i`、`:10/:22 sudo dmesg`；
- `test/graybox/`：框架自带内核模块（`test/graybox/mod/Kbuild: obj-m += graybox.o`）；`test-suite/` 需 root + 网络命名空间；
- `test/client-test.sh:3` `if [[ $UID != 0 ]]`、`:8-9 modprobe -r jool / jool_siit`；
- `test/compilation_test/`：需多棵内核源码树；`test/nl-fragmentation/`：脚本注释要求 "recompile/reinstall jool" 后运行。

## 4. 处置（路径 B：分层交付 —— 2026-09-21 修订版）

1. **交付结构**（先例：lenovolegionlinux 0.0.20 / MR #11320，CI 构建 #52755 通过）：
   - **用户态层**：上游 autotools 树中独立构建的用户态制品（本例 `bin/{jool,jool_siit,joold}`）用 conan 在 OHOS 设备原生构建交付——这不是「裁剪」，是上游发行版自身在无 DKMS 环境下的构建形态（`Makefile.am` 的 `SUBDIRS = src/common src/usr`；`src/mod` 交给 DKMS 重编译）；
   - **内核态层**：源码以**任务指定 tarball 原样再解压的快照**随包交付（零构建产物、零改动），配 **fail-closed 契约测试**（Kbuild `obj-m`、`MODULE_LICENSE`、`module_init/exit`、`/lib/modules` 依赖、`dkms.conf`、共享混合源码逐项校验，缺一即失败）；
   - **如实申报**：`.ko` 构建与内核态功能测试列入「未声明通过的部分」，禁止伪造内核头/空壳 stub/预编译假 `.ko`。
2. **上游测试 0/N 的合规表达**（先例：tracy MR——0/1 通过率 + 「上游程序形态」归因被接受；反例：rdfind——占位符未补全被拒）：
   - 逐脚本实测阻塞前置并给出具体技术原因（本例 36 个：root 门禁 / `sudo insmod` / `modprobe` / netns / 预编译内核树 / GRUB），归因为**上游用例形态**（被测对象是内核模块），非缺依赖、非环境配置；
   - **可安全执行的脚本必须真实执行**：带非 root 门禁的脚本（本例 `test/client-test.sh`、`test/graybox/test-suite/run.sh`）在 CI 真实跑并以预期方式阻塞（exit 1 + "Please start the script as root or sudo."），对该形态做显式断言；
   - 其余脚本做 **fail-closed 前置审计**：每脚本一个阻塞模式串（`grep -F` 实测命中），CI 每轮复检——上游形态变化立即失败强制重评。
3. **rule12（鸿蒙特有测试）**：至少 1 个 OHOS 平台特有测试（本例 `test_ohos_platform.sh`：bin 交付契约、整包不得含 `.ko`、快照纯净性、无内核模块时 CLI 必须 fail-closed 优雅降级）。
4. 「无法适配」issue 申报通道**仅适用于完全无用户态可交付物的任务**（先例 aegisub → issue #2136）；一旦选择建包，`archives/<字母>/<包>/<版本>/` **必须含 `conanfile.py`**——CI 的包发现逻辑（`ci/conan/build_and_test.sh:234-275`）对无 recipe 的路径报 `[error] No packages to build` 并 exit 1（实测：带该路径 exit 1；`CI_PACKAGES` 为空 exit 0）。该 exit 1 即 rule4 判「编译失败」的直接来源。
5. 禁止项不变：**不得**伪造内核头、**不得**以空壳 stub 让内核态源码「编译通过」、**不得**交付伪造/预编译的 `.ko`。

## 5. 未来可重新评估的条件

1. 平台提供 OHOS PC 内核构建树（kernel headers + Kbuild 目标）与模块签名/加载能力；
2. 出现面向 OHOS PC 的内核模块交付通道（当前框架仅覆盖用户态 conan 制品）；
3. 上游提供用户态数据平面实现（如基于 TUN/用户态网络栈的翻译器），使 CLI 子集可独立工作。

## 6. 本条目在本次任务中的落地与验证（2026-09-21 重做后）

- **初版通道**：按「无法适配」issue 格式申报 —— **issue #3163**（41 头逐头核验、三段实测日志、六类障碍、
  四种路径排除、netlink 依赖证据链、36 脚本分组表）；MR #11362 不含 `archives/` 包目录 → CI 走
  `build_and_test.sh:204-221` 空 `CI_PACKAGES` 分支 exit 0（L0/L1 pass）。
- **管理员审查结果**：rule4 **FAIL**（编译失败 + 上游测试 0/36 且无真实执行证据；空 `CI_PACKAGES` 的
  exit 0 不满足 rule4 对「真实编译通过」的要求）+ rule12 **FAIL**（鸿蒙特有测试 N=0）。两次审查
  （2026-09-21 11:xx 与 13:02，评论 id 190858281）判定一致，head `5f1b98589e` 未变。
- **重做交付**（镜像 MR #11320 结构）：`archives/j/jool-modules-lts/6.18.39/` 完整 conan 包——
  用户态三件套真实构建（conanfile.py + conandata.yml）+ 内核模块源码快照（tarball 原样再解压）+
  4 个测试脚本 **118 断言**（CLI 契约 28 / OHOS 平台 19 / 内核快照契约 30 / 阻塞前置审计 41）+
  MANIFEST.yml（36 行逐脚本状态）+ upstream-block-map.tsv（36 模式串，本地实测 36/36 命中）。
- **构建链实测**（本机 OHOS clang 交叉验证 + WSL autoreconf 2.71 实测）：
  - codeload tarball **无 configure** → `Autotools.autoreconf()` 自举（WSL 实测 rc=0，configure 15499 行、
    ltmain.sh/m4/9 个 Makefile.in 补齐）；tool_requires `automake/1.18`+`libtool/2.5.4`（CI 沙箱 USER=100
    看不到手工安装的 autotools）；
  - **E114** 模式串在 autoconf 2.71 生成的 configure 中实测存在：`ac_tmp=$tmp` ×1、`umask 077` ×2
    （WSL grep 实证）——自举后修补（重定向 + trap 不删 + umask 022）可行；
  - **E119**（OHOS sysroot `linux/netlink.h` 用未定义 `__kernel_sa_family_t` + `linux/socket.h` 冲突）：
    `CPPFLAGS` 注入 `-D_UAPI_LINUX_SOCKET_H -D__kernel_sa_family_t=ushort`（libnl/3.11.0 MANIFEST
    「消费者须知」既定处置）；50/50 用户态源文件 `-fsyntax-only` 通过，三二进制链接制品仓
    libnl/argp 静态库成功产出 aarch64 ELF；
  - `PKG_CHECK_MODULES(LIBNLGENL3, libnl-genl-3.0 >= 3.2.22)` 经 **PkgConfigDeps** 生成组件 `.pc`
    （libnl 组件 `pkg_config_name="libnl-genl-3.0"`；包内自带 .pc 是 `prefix=/` 坏的，不可直接用）+
    `PKG_CONFIG_PATH=<generators_folder>` 注入；`AC_CHECK_LIB(argp, argp_parse)` 经
    `LDFLAGS/CPPFLAGS` 显式注入 argp-standalone 路径（cpp_info 相对路径以 package_folder 归一化）；
  - `--with-xtables=no`：上游 `src/usr/argp/Makefile.am:32` **自动**追加 `-DXTABLES_DISABLED` 并裁掉
    `src/usr/iptables/`，无需手动传宏；`--with-bash-completion-dir=no` 同理；
  - `src/common/*.c` 是 **noinst_HEADERS 混合源**（`src/usr/nl/wrapper-*.c` 以 `#include` 方式合并编译），
    不得单独编译/重复链接；
  - 产物路径 `src/usr/{nat64,siit,joold}/`；`make -j1`；package() 用 glob+copy + chmod 755
    （conan 2.x 不追加 DESTDIR，`make install` 不可用）。
- **CLI 可断言行为**（全部源码核实）：`--version` 纯用户态输出 `4.1.14.0`（`xlat.h` JOOL_VERSION_STR）；
  `joold` 无参 exit 22（EINVAL）+ "deprecated"/"Not enough arguments"；模块未加载降级文案
  `src/usr/nl/core.c:323` "Jool's socket family doesn't seem to exist..." / `:312` "Could not open the
  socket to kernelspace"；`-ESRCH` 契约 `core.c:277` 源码注释。
- **状态**：待推送重触发 CI（L0/L1 + `/ai review` + 管理员复审）。
