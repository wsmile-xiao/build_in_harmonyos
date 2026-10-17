# cpu 1.4.3 — 构建报告

## 1. 环境

| 项 | 值 |
|----|----|
| 平台 | HarmonyOS PC / aarch64-unknown-linux-ohos |
| 编译器 | clang（OHOS SDK 26.0.0.18） |
| conan | 2.29.1（OHOS 适配版）+ 制品仓 ohpcd |
| profile | ci/conan/profiles/ohos-aarch64 |
| 依赖 | openldap/2.6.7（`conan download openldap/2.6.7 --only-recipe` 与制品探测均通过） |
| 源码 | cpu_1.4.3.orig.tar.gz，sha256 `ef52a91dc5438de5978daf7dadabded3f7adacc765c8840eabc970868dfc67dd` |

## 2. 构建步骤与结果

| 步骤 | 结果 | 关键输出 |
|------|------|----------|
| configure | rc=0 | `host_os='linux-ohos'`；`deplibs_check_method="pass_all"`；`checking if libtool supports shared libraries... yes` |
| make | rc=0，errors=0 | `-j1`（HMDFS jobserver fifo EPERM，E074） |
| make check | rc=0 | `Nothing to be done for 'check-am'.`（上游无用例） |
| make install（DESTDIR→staging） | rc=0 | `bin/cpu`、`lib/libcputil.so.0.0.0`、`lib/libcpu_ldap.so` |
| conan create（W3/G2） | rc=0 | 8 道门禁 + test_package 11 项用例通过 |

插件形态（决定运行时能否被主程序 dlopen）：

```
libcpu_ldap.so:
  DT_NEEDED  libcputil.so.0
  DT_NEEDED  libldap.so.2
  DT_NEEDED  liblber.so.2
```

## 3. 适配要点（问题 → 处理）

### 3.1 平台类

| 问题 | 处理 | 知识 |
|------|------|------|
| config.guess/sub 不识别 OHOS triplet | 换用仓库事实标准 OHOS-aware 版本（12 包复用），得到 `aarch64-unknown-linux-ohos` | E007 |
| HMDFS 上 chmod 不生效，configure 内 `umask 077 && mktemp -d` 的临时目录非 owner 不可写 | 直接 patch 生成的 configure：umask 077→022（仓库 581 处先例） | E046 |
| 上游代码在 clang 15 下新告警被 `-Werror` 放大 | 仅对触发的告警类别降级（configure 与 configure.ac 同步，避免重生成回退） | E063 |
| 并行 make 触发 jobserver fifo EPERM | `make -j1` | E074 |

### 3.2 依赖（OpenLDAP）

|cpu| 通过 `--with-ldap` 使用 OpenLDAP；制品仓中的 openldap 包带 libtool `.la`，
其 `libdir='//lib'`、`dependency_libs` 指向构建期路径，而 libtool 优先于 `.so` 使用 `.la`
→ 链接必然失败。处理：`generate()` 在构建目录内建立**私有、无 .la 的 prefix**
（`include` 与 `lib/lib{ldap,lber}.so` 全部是指向制品的符号链接），libtool 于是
`-L<priv>/lib -lldap` 直链共享库并记录 SONAME；同时 `-DLDAP_DEPRECATED` 让
`ldap_get_values()` 家族有声明。不写共享 `/usr/local`（R49）。知识：E236/E522（E544 同题草稿）。

### 3.3 上游缺陷 / 构建系统缺陷

| 文件 | 问题 | 处理 |
|------|------|------|
| `src/include/util/conf.h` | 自造 `typedef int bool` 与 `<stdbool.h>`（经 `<dlfcn.h>` 间接引入）冲突，`-fno-common` 下编译失败 | 统一为编译器 bool（插件与主程序共享结构体，ABI 必须一致） |
| `src/include/plugins/ldap/ldap.h` | `globalLdap` 试探性定义缺 `extern`，与 `commandline.c:423` 的定义构成重复符号 | 补 `extern`，定义保留在 commandline.c |
| `src/util/hash.c` | `#ifndef crypt` 守卫恒真（`crypt` 不是宏） | 改 `#ifdef HAVE_CRYPT_H` |
| `src/plugins/ldap/cat.c` | `ldap_get_values` 无声明；指针与字符串字面量比较 | 修声明；比较改为 `?:` 打印 |
| `src/plugins/ldap/commandline.c` | 对转型表达式赋值（clang 拒绝） | 引入临时变量 |
| `src/util/cgetpwent.c` | 缺 `<stdlib.h>`（malloc 隐式声明在 64 位截断指针） | 补头文件 |
| `src/plugins/*/Makefile.{am,in}` | 插件依赖写在 `LDADD`（libtool 模块忽略）→ 插件缺 `libcputil` 的 DT_NEEDED；`@LBFLAGS@` 从未被替换 | 改 `libcpu_*_la_LIBADD`；`@LBFLAGS@` → `-module -avoid-version` |
| `configure`（libtool 1.4.3 平台表） | 只认 `linux-gnu*`，`linux-ohos` 落到静态分支 → 插件被构建成 `.a` 而非 `.so` | 平台表新增 `linux-ohos*` 并 `deplibs_check_method="pass_all"` |

### 3.4 autoconf 探测

| 问题 | 处理 |
|------|------|
| `AC_FUNC_MALLOC` 在 OHOS libc 上误判（`malloc(0)` 返回 NULL 属 POSIX 合法，探测要求非 NULL）→ 会 `#define malloc rpl_malloc`，而本包无该实现 | 用标准 autoconf cache 覆盖 `ac_cv_func_malloc_0_nonnull=yes`（不改源码） |

## 4. 补丁（12 个，`patches/`）

0001 config.guess、0002 config.sub、0003 configure、0004 src/include/conf.h、
0005 src/include/plugins/ldap/ldap.h、0006/0007 src/plugins/ldap/Makefile.{am,in}、
0008 src/plugins/ldap/cat.c、0009 src/plugins/ldap/commandline.c、
0010/0011 src/plugins/passwd/Makefile.{am,in}、0012 src/util/hash.c

- 生成方式：`refresh-patch --auto`（per-file difflib，源树干净重建）
- 补丁内不新增平台宏（R8）；0003 的 `-Werror` 处理按类别降级，不做全局 `-Wno-error`
- 0006/0007 与 0010/0011 同时改 `.am` 与生成物 `.in`，未重跑 automake

## 5. 制品内容（package_type = application）

```
bin/cpu                      # 唯一的命令行工具（commands.json 已声明）
lib/libcputil.so.0.0.0       # 主程序与插件共用的工具库
lib/libcpu_ldap.so           # LDAP 方法插件（dlopen 加载）
licenses/COPYING
```

`--enable-developer` / `--with-flatfile` 未启用：该开关才会构建的 `libcpu_passwd.so`
在上游是桩实现（`"Do not use me. I don't work!"`，操作函数为空），且需要额外依赖，
不属于本平台需要发布的制品（R1：参数最少化）。

## 6. 已知限制

- `doc/test.ldif` 需要真实 LDAP 服务器才能作为端到端数据；本环境无服务器，
  测试改为"插件加载 + 进入 libldap 调用"的离线断言（见 test-report.md）
- `libcpu_ldap.so` 为共享模块（无 SONAME，由 dlopen 加载），主程序 `bin/cpu`
  内嵌 `$ORIGIN` 不参与；运行时依赖由主程序自身与插件的 DT_NEEDED 决定，
  与 conan 运行环境（conanrun）配合工作
