# cpu 1.4.3 适配笔记

## 基本信息

| 项 | 值 |
|----|----|
| 软件 | cpu (Change Password Utility) 1.4.3 |
| 上游 | https://cpu.sourceforge.net/ |
| 源码 | https://deb.debian.org/debian/pool/main/c/cpu/cpu_1.4.3.orig.tar.gz |
| sha256 | ef52a91dc5438de5978daf7dadabded3f7adacc765c8840eabc970868dfc67dd |
| 构建系统 | GNU Autotools（发布包自带 configure/Makefile.in，无需 autoreconf） |
| 目标平台 | HarmonyOS PC / aarch64-unknown-linux-ohos |
| 编译器 | clang（OHOS SDK 26.0.0.18 自带） |
| 依赖 | openldap/2.6.7（制品仓已发布） |
| 许可证 | GPL-2.0-or-later |
| 补丁数 | 13 |
| 状态 | built（conan create + 测试全通过） |

## 软件结构

`cpu` 是唯一的驱动程序，本身不实现后端：它按 `-M <方法名>` 用
`dlopen("libcpu_<方法名>.so", RTLD_NOW)` 加载插件（`src/util/dll.c:78`，
`src/include/util/dll.h:36` `LIB_PREFIX "libcpu_"`）。1.4.3 附带两个插件：

- `libcpu_ldap.so`：功能后端（LDAP），本配方构建的即是它
- `libcpu_passwd.so`：本地文件后端，上游明确标注为未完成的桩实现
  （`"Do not use me. I don't work!"`，`src/plugins/passwd/passwd.c` 的 `CPU_init`/
  `passwdOperation` 为空），且需要 `--enable-developer` + `--with-flatfile` 才编译。
  为避免把非功能性插件打进制品，配方不传这两个开关（R1：参数最少化）

## 构建配置

```bash
# 依赖解析：openldap 制品仓中带有 .la，其 libdir/dependency_libs 不可迁移
# （libdir='//lib'，见 E236/E522），因此 generate() 在构建目录内搭一个私有 prefix：
#   <build>/prefix/include -> <openldap pkg>/include
#   <build>/prefix/lib/lib{ldap,lber}.so -> 制品内的真实共享库
#   （不复制/不生成 .la，libtool 于是走 -L<priv>/lib -lldap 直链 .so，记录 SONAME）
# 另：LDAP_DEPRECATED 声明 ldap_get_values()；LD_LIBRARY_PATH 供 configure 探针与插件运行时使用
python3 ohc-run.py conan-init cpu 1.4.3   # 生成配方骨架
python3 ohc-run.py conan-verify cpu 1.4.3 # 8 道门禁
```

关键 configure 选项：`--prefix=/`（conan 默认，install 用 DESTDIR 落到 package_folder）、
`--with-ldap=<build>/prefix`。autoconf cache 覆盖：`ac_cv_func_malloc_0_nonnull=yes`
（OHOS libc 的 `malloc(0)` 返回 NULL 属 POSIX 合法，`AC_FUNC_MALLOC` 却据此判定不兼容，
会定义 `malloc=rpl_malloc`，而本包没有 rpl_malloc 实现 → 不改源码，用标准 cache 变量覆盖）。

## 补丁清单

| # | 补丁 | 内容 | 类型 |
|---|------|------|------|
| 0001 | config.guess | 最小补丁（+3 行）：`case` 首插入 `aarch64:HarmonyOS:*:*`/`arm64`/`HongMeng` 命中分支，直接输出 `aarch64-unknown-linux-ohos`（不再整文件替换，E007/E572） | 平台 |
| 0002 | config.sub | 最小补丁（+4/-1 行）：`maybe_os` 白名单加 `linux-ohos*`；在通用 `-linux*)`（会把 linux 改写成 linux-gnu）之前插入 `-linux-ohos*)` 守卫（E007/E572） | 平台 |
| 0003 | configure | (a) sed 临时目录 umask 077→022（E046）；(b) 仅对上游代码在 clang 15 下触发的告警类别降级 `-Werror`（E063）；(c) libtool 平台表新增 `linux-ohos*` 并设 `deplibs_check_method="pass_all"` | 平台 |
| 0004 | doc/Makefile.in | `install-data-local` 缺 `$(DESTDIR)`（staging 时装到宿主 `/etc`，包内缺 `etc/cpu.conf`）且未用 `$(srcdir)`（out-of-tree 构建时找不到源文件）；可上游化（E571） | 缺陷 |
| 0005 | src/include/conf.h | 上游自造 `typedef int bool` 与 `<stdbool.h>`（经 `<dlfcn.h>` 引入）冲突 → 统一为编译器 bool | 平台/ABI |
| 0006 | src/include/plugins/ldap/ldap.h | `globalLdap` 试探性定义缺 `extern`，`-fno-common` 下与 `commandline.c:423` 的定义构成重复符号 | 缺陷 |
| 0007 | src/plugins/ldap/Makefile.am | 插件依赖写在 `LDADD`（libtool 模块忽略）→ `libcpu_ldap_la_LIBADD`；`@LBFLAGS@` 从未被替换 → `-module -avoid-version` | 构建 |
| 0008 | 同上 Makefile.in | 生成文件同步（不重跑 automake） | 构建 |
| 0009 | src/plugins/ldap/cat.c | `ldap_get_values` 无声明；指针与字符串字面量比较 | 缺陷 |
| 0010 | src/plugins/ldap/commandline.c | 对转型表达式赋值（clang 拒绝）；保留 `globalLdap` 唯一定义 | 缺陷 |
| 0011 | src/plugins/passwd/Makefile.am | 同 0007（该插件默认不构建，补丁保证开关打开时同样可编译） | 构建 |
| 0012 | 同上 Makefile.in | 生成文件同步 | 构建 |
| 0013 | src/util/hash.c | `#ifndef crypt` 守卫恒真（`crypt` 不是宏）→ 改 `#ifdef HAVE_CRYPT_H` | 缺陷 |

`patches/` 内不新增任何平台宏（R8）；0001/0002 的平台判定完全走 `uname` 文本（`HarmonyOS`/`HongMeng`）与 triplet 解析，不含 `__OHOS__`；0003 的 `-Werror` 降级只针对具体告警类别
（如 `-Wno-error=implicit-function-declaration`），不做全局 `-Wno-error`。

## 平台识别改最小补丁（原整文件替换，2026-09-12 修订）

原 `0001-config.guess.patch` / `0002-config.sub.patch` 用仓库事实标准的 OHOS-aware 探针**整文件替换**
（config.guess +1235/-810、config.sub +1687/-1232，补丁文件合计 5841 行，占当时 PR 8420 行的 69%）。收到“变更过大”审查反馈后改为最小补丁：

| 文件 | 改动点 | 增量 |
|------|--------|------|
| config.guess | `case "${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}"` 首插入 `aarch64:HarmonyOS:*:* \| arm64:HarmonyOS:*:* \| aarch64:HongMeng:*:* \| arm64:HongMeng:*:*` → `echo aarch64-unknown-linux-ohos; exit 0` | +3 行 |
| config.sub | ① `maybe_os` 白名单加 `linux-ohos*`；② 通用 `-linux*)` 之前插入 `-linux-ohos*) os=-linux-ohos ;;`（通用分支会 `sed 's\|linux\|linux-gnu\|'`） | +4/-1 行 |

**为何必须两处都改**：`configure` 会用 `$ac_config_sub` 二次归一化 `config.guess` 的输出；只改 config.guess 时
`-linux-ohos` 仍会被通用分支改写成 `-linux-gnu`，OHOS 语义丢失（老式 libtool 平台表随之为假）。

**等价性验证**（与整文件替换方案逐项对齐）：

- `sh config.guess` → `aarch64-unknown-linux-ohos`；`sh config.sub "$(sh config.guess)"` → 同值
- 回归：`sh config.sub riscv64-unknown-linux-gnu` 等仍返回原值（未污染其它架构/OS 判定）
- 补丁 strict 可应用（无 fuzz 漂移）：`patch -p1 --dry-run < patches/000N-*.patch` 通过
- 构建日志 `checking build system type... aarch64-unknown-linux-ohos` / `checking host system type... aarch64-unknown-linux-ohos`（构建树 `.conan2/p/b/cpu59a506316f4af/b` 实测）
- `conan create` 11/11 通过，与替换方案一致；CI（build #44729）通过

**保留回退路径**：注入点若被上游大改而无法定位，再回退到整文件替换（12 包复用，sha256 `02a2b4483f0f6d9514f0b938eba95fb6`），并在 PR 说明中申报理由。

## 测试情况

**上游测试：1.4.3 没有自动化测试用例。**
- 顶层 `check` 目标存在但无 TESTS 条目：`make check` 实测输出
  `Nothing to be done for 'check-am'`（rc=0）——配方 `build()` 中仍调用
  `make check`，让 CI 侧也留下"上游检查目标已执行"的证据
- 唯一与测试相关的文件 `doc/test.ldif` 是 LDAP 目录数据（需真实服务器导入），
  不是自动化用例；`doc/cpu.conf` 是同目录的配置样例

**适配测试（test_package/，11 项，全部通过）**

| # | 用例 | 断言 |
|---|------|------|
| 1-3 | 制品内容 | `bin/cpu`、`lib/libcputil.so`、`lib/libcpu_ldap.so` 存在 |
| 4 | CLI 契约 | `cpu --version` 输出 1.4.3 |
| 5-6 | CLI 契约 | `cpu --help` 输出 `USAGE: cpu` 与 `--method=` |
| 7 | 插件加载（反向对照） | `-M bogus` 必须在 `CPU_loadLibrary` 处失败（证明断言 8/9 可失败） |
| 8-9 | 插件加载 | `-M ldap` 不得出现 `CPU_loadLibrary` 失败，也不得出现 `error loading the ldap library` |
| 10 | 消费者测试 | `consumer.c` 对 `libcputil.so` 编译链接成功 |
| 11 | 消费者测试 | `consumer.c` 运行通过（10 个断言：Strdup/Free、MD5("abc") 已知答案、SHA1("abc") 已知答案、`cgetpwent` 命中/未命中/uid 解析） |

说明：`cpu` 对操作失败也返回 0，因此用例断言的是输出内容而非退出码；`-M ldap`
用 `LDAP_URI=ldap://127.0.0.1:1`（必然拒绝连接）保持离线确定性——断言的是"加载器
让位给插件"，不是"服务器可达"。

## 复现命令

```bash
# 1) W3 本地验证（finish 内部做 W2 结构 + R36 依赖 + conan create）
python3 $SKILL_ROOT/scripts/ohc-run.py finish cpu 1.4.3 built

# 2) 单独复跑消费者测试（对 conan create 后的制品）
conan create . --build=missing -pr:b=default -pr:h=ci/conan/profiles/ohos-aarch64
```

## 验证结果

| 检查 | 结果 |
|------|------|
| configure | rc=0（`host_os='linux-ohos'`，`deplibs_check_method="pass_all"`） |
| make | rc=0，errors=0（`-j1`，E074） |
| 插件形态 | `libcpu_ldap.so` 为共享模块，`DT_NEEDED = libcputil.so.0 + libldap.so.2 + liblber.so.2` |
| make install | rc=0，产物 `bin/cpu` + `lib/libcputil.so.0.0.0` + `lib/libcpu_ldap.so`（`bin/`：老式 configure 的 bindir 解析随之走 OHOS 布局，测试按 `bin/cpu` 定位） |
| 运行时加载 | `cpu -M ldap` 插件加载成功并进入 libldap 调用（无 `CPU_loadLibrary` 失败） |
| 测试 | 11/11 通过 |
| CI 链接环境 | 测试脚本自备工具链 lib 目录（E573）：同名坏 `libxml2.so.16` 前置时仍 11/11 |

## CI 失败与修复（lld 载入 libxml2，E573）

第 2 轮 CI（run #44867）红在 test_package 阶段，包本身构建全部通过：

```
Error loading shared library libxml2.so.16: (needed by .../llvm/bin/lld)
Error relocating .../lld: xmlFreeDoc: symbol not found
```

根因：test 阶段用 `${CC:-clang}` 现场编译消费者程序，而 clang 驱动的链接器
lld 自身动态依赖 SDK `llvm/lib` 下的 `libxml2.so.16`；conan test 的 runenv
只导出包目录，lld 能否启动取决于调用它的 shell 环境（同一提交重跑因此时红时绿）。
musl 又规定：`LD_LIBRARY_PATH` 里命中同名但不可加载的条目即硬失败，不回退
RPATH/默认路径。

修复（`test_package/test.sh` + `test_package/conanfile.py`）：

- 用 `command -v` 解析 CC 真身，把 `dirname(readlink -f CC)/../lib` 前置进
  `LD_LIBRARY_PATH`——lld 的依赖由脚本自己保证，不再依赖调用方环境
- 若仍报 libxml2（lld 完全起不来），用 `clang -fuse-ld=bfd` 重链一次（GNU ld
  不依赖 libxml2）；测试依旧是"真实编译 + 真实执行消费者程序"，不做降级跳过
- 链接产物 `chmod +x`（HMDFS 不留可执行位，E046/E490）
- recipe 侧把 `cpp_info.libdirs/bindirs`（相对名字）拼成绝对包目录并过滤空条目

本地复现与验证：把同名坏 `libxml2.so.16` 放到搜索路径首位即可复现 CI 逐字报错；
修复后"干净环境 / 敌对环境 / 真实 conan test"三种场景均 11/11。经验已入草稿
**E573**（平台级，建议优先转正）。

## 备注

- `configure` 与 `configure.ac` 的相关改动保持同步（0003/0004 涉及的文件若被
  autoreconf 重生成也不会回退）；但配方不触发 autoreconf（发布包自带生成物）
- 补丁生成走 `refresh-patch --auto`（per-file difflib），源树不落 `.patch`
- 与 `archives/l/ldapvi` 的旧做法不同：本配方不使用共享 `/usr/local`（R49），
  依赖注入全部在构建目录内的私有 prefix 完成
- 遗留：`doc/test.ldif` 需要真实 LDAP 服务器才能作为端到端数据使用，本环境
  无服务器，故未纳入自动化用例（已在测试小节说明）
---

**编译结束**: 2026-09-12 12:03
**最终状态**: published
