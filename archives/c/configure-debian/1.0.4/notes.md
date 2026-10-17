# configure-debian 1.0.4 — HarmonyOS PC 适配说明

configure-debian 是 Debian 的 debconf 集中配置程序：**单个 337 行 Perl 脚本**
（`configure-debian`，shebang `#!/usr/bin/perl -w`）+ 1 个 debconf helper 脚本 +
桌面图标/菜单元数据。上游 Debian native 3.0 源码（`configure-debian_1.0.4.tar.xz`），
Makefile 纯 install（无编译段），**上游 0 测试用例**。纯脚本包，`build_system: none`。

## OHOS 适配点

### 1. `use Locale::gettext` —— XS 模块在 OHOS 无法构建（L32 编译期硬依赖）

`Locale::gettext` 1.07 是 XS 模块（`gettext.xs`，DynaLoader bootstrap）。
`Makefile.PL` 的 conftest 用 dlopen 探测 libintl 的 C 符号——musl libc 自带
`gettext()` 符号（C 链接本身可行，已实测 trivial C + perl 头链接 OK），
但 conftest 需要 `<libintl.h>` 头文件，**OHOS musl 无此头**
（`Makefile.PL` 实测失败：`gettext function not found. Please install libintl`）。

而本包是纯脚本消费方：**不带 .mo catalog，C 区域恒等语义（`gettext($m) == $m`）
就是正确行为**。故 conanfile `package()` 期生成同名 namespace 的最小纯 Perl
shim（`lib/perl5/Locale/gettext.pm`，`@ISA = Exporter` + `@EXPORT` 导出裸函数：
`gettext/dgettext/dcgettext` 恒等返回、`ngettext/dngettext` 按 `$n` 选单复数、
`textdomain/bindtextdomain/bind_textdomain_codeset` 空操作），经 `runenv` 的
`PERL5LIB` 暴露——包自包含，不依赖系统 Perl 树。

实测（shim + 真实脚本）：`perl -c` → syntax OK（RC=0）；非 root 实跑
`perl configure-debian foo` → 过编译/模块加载/常量表构建，命中 L139 root 门禁
exit 1 + `must be run as root`。

### 2. shebang 适配

`#!/usr/bin/perl -w` → `#!/usr/bin/env perl -w`（OHOS 无 `/usr/bin/perl`，
perl 由 hnp 提供 `/data/service/hnp/bin/perl`，house perl shebang 先例）。

### 3. 布局映射（house 归档惯例）

| 上游（Debian） | 归档包 |
|---|---|
| `/usr/sbin/configure-debian` | `bin/configure-debian`（0755） |
| `/usr/share/configure-debian/configure-debian-debconf` | `share/configure-debian/`（0755） |
| `/usr/share/pixmaps/*.xpm/png` | `share/pixmaps/` |
| `/usr/share/applications/*.desktop` | `share/applications/` |
| （无）Locale::gettext 1.07 | `lib/perl5/Locale/gettext.pm`（vendored shim） |
| `debian/copyright` | `licenses/` |

`cpp_info.libs = []`（纯脚本包）；`bindirs = ["bin"]`、`resdirs = ["share"]`；
`runenv` 定义 `PERL5LIB=<pkg>/lib/perl5`。

## 依赖

**无 conan `requires`**（acme.sh 纯脚本包先例）。核实依据：

- 编译期唯一外部依赖 `Locale::gettext`（L32 `use`）由本包 vendored 纯 Perl
  shim 满足（`lib/perl5/Locale/gettext.pm` + `runenv` PERL5LIB），自包含。
- root 交互路径的外部命令归属（脚本 `system()`/backtick 全文核对，勿凭命令名
  前缀猜包）：
  - `dpkg-reconfigure`（L149/L292）→ **debconf 包**（`work/dpkg-reconfigure`，
    已发布 dpkg 包全树 find 无此二进制）；
  - `apt-cache`（L168）→ apt 包；
  - `tempfile`（L118/L224/…）→ miscfiles 包。
  三者均为 Debian 用户态工具，本归档环境无对应可用配方 → 不硬拉无关依赖，
  如实记为环境边界（非 root 冒烟不触达该路径）。

## 测试

上游 0 测试 → 自写冒烟 `test_package/test_configure_debian.sh`（7 项，断言点
全部来自脚本全文核对）：PATH 注入 / 可执行 / 非 root 实跑命中 root 门禁
（exit 1 + `must be run as root`——证明编译期依赖全部可解析）/ `--help` 分支
同行为 / shim 落位且可加载 / debconf helper 落位（`share/configure-debian/`）
/ shebang 适配。

环境适配（实测）：非 root 判定用 HOME 存在性（toybox `id -u` 对大 uid 报
`bad uid` RC=2）；本环境 VirtualRunEnv 未把 PERL5LIB 传播到 test 子进程——
测试内从包路径自举 export（配方 runenv PERL5LIB 保留给下游消费方）。

## 边界

- root 交互路径外部命令（`dpkg-reconfigure`/`apt-cache`/`tempfile`，分属
  debconf/apt/miscfiles 包）本归档环境无可用配方——非 root 冒烟断言不触达该
  路径，如实记录不宣称已适配。
- Locale::gettext shim 为恒等语义：对不带 catalog 的本包是精确行为，不是降级。
