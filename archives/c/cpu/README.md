# cpu

**Change Password Utility** —— 面向 LDAP 的账户管理工具（用户/组的增删改），带本地 passwd/shadow/group 后端框架。

`cpu` 是唯一的驱动程序，本身不实现任何后端：它按 `-M <方法名>` 用 `dlopen()` 加载
`libcpu_<方法名>.so` 插件，由插件完成实际的账户操作。仓库中的 1.4.3 版本附带两个插件：

| 插件 | 说明 |
|------|------|
| `libcpu_ldap.so` | LDAP 后端（本版本唯一可用后端），依赖 OpenLDAP 客户端库 |
| `libcpu_passwd.so` | 本地文件后端，上游明确标注为未完成的桩实现（`Do not use me. I don't work!`），本配方不启用 |

## 用法

```bash
cpu [-M method] [-C config] <command> [options] [login]

# 示例（LDAP 后端）
cpu -M ldap -C /etc/cpu.conf useradd alice
cpu -M ldap -C /etc/cpu.conf userdel alice
cat /etc/cpu.conf

# 通用选项
-M, --method=name     选择后端插件（默认 ldap）
-C, --config=file     配置文件
-y, --yes             免交互确认
-h, --help            帮助
-V, --version         版本信息
```

插件在运行时按 `libcpu_<方法名>.so` 的名称查找（`src/util/dll.c`），因此 **LD_LIBRARY_PATH
必须包含安装前缀的 lib 目录**（例如 `$CONAN_PKG/lib`），否则只会得到
`CPU_loadLibrary: dlopen(libcpu_ldap.so, RTLD_NOW) failed.`

## 构建

- 构建系统：GNU Autotools（`configure` + `make`），生成物为 `sbin/cpu`、`lib/libcputil.so` 与插件模块 `lib/libcpu_*.so`
- 版本：1.4.3
- 许可证：GPL-2.0-or-later（见 COPYING）
- 源码：https://deb.debian.org/debian/pool/main/c/cpu/cpu_1.4.3.orig.tar.gz
- 依赖：`openldap/2.6.7`（制品仓 ohpcd）

## OHOS 适配

- `config.guess` / `config.sub` 换用支持 `aarch64-*-ohos` 的版本（E007）
- `configure`：临时目录 `umask 077` → `022`（HMDFS 上 chmod 不生效，E046）；仅对上游代码在
  clang 15 下触发的告警类别降级 `-Werror`（E063）；libtool 1.4.3 平台表新增 `linux-ohos*`
  并设 `deplibs_check_method="pass_all"`（否则共享库判定失败、插件退化为静态模块）
- 插件链接修复：上游把依赖写在 `LDADD`（libtool 模块忽略）并用未替换的 `@LBFLAGS@`，
  改为 `LIBADD` + `-module -avoid-version`，插件才带正确的 `DT_NEEDED`
- 源码缺陷修复：`conf.h` 私有 `typedef int bool` 与 `<stdbool.h>` 冲突；`ldap.h` 的
  `globalLdap` 缺 `extern`（`-fno-common` 下重复符号）；`hash.c` 的 crypt 守卫恒假；
  `cat.c` / `commandline.c` 的非法 C 写法
- OpenLDAP 依赖通过**构建目录内的私有 prefix**（`.la` 无关的符号链接树）接入，不使用共享
  `/usr/local`（R49 / E236 / E522 / E544）；`malloc(0)` 的 autoconf 探测用 cache 变量覆盖，
  不改源码
