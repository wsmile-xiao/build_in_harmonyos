# console-common 0.7.92 — HarmonyOS PC 适配说明

console-common 是 Debian 文本控制台配置基础设施（**DEPRECATED**，官方建议改用
console-setup）：`install-keymap(8)` 启动期键图安装工具（sh，约 150 行）+
`kbd-config`（sh 包装器，转调 dpkg-reconfigure console-data）+
`dh-consoledata`（debhelper 插件，perl）+ `getkmapchoice.pl` / `ps2-to-riscpc`
键图声明工具 + `common.pl` 共用子程序。上游 Debian native 3.0 源码
（`console-common_0.7.92.tar.xz`），Makefile 纯 install（**无编译段**，仅两处
sed 模板展开），**上游 0 测试用例**（tar 树核对：无 t/ 目录、无 make check 目标）。

## OHOS 适配点

### 1. 构建期：复刻上游 Makefile 的两处 sed（零 shell 依赖）

上游 `make all` 只有两个生成规则：

- `dh_consoledata.in` → 替换 `@DHDIR@`（`/usr/share/debhelper/dh-consoledata`）、
  `@KMAPDIR@`（`/usr/share/console/lists/keymaps`）、`@LCDDEP@`
  （`console-common (>= 版本)`，版本号上游经 `dpkg-parsechangelog` 取——
  Debian 构建工具链，OHOS 无配方）→ conanfile `package()` 用 python
  `str.replace` 等价实现，版本直接取 conanfile version。
- `getkmapchoice.pl.in` → `sed '/^#####COMMON####$/ r common.pl'` 在标记行后
  插入 common.pl（标记行保留）→ conanfile 行级插入等价实现。

`make install` 的目录映射（`debian/console-common.install` 装 sbin +
share/man/man8 + share/console）：

| 上游（Debian） | 归档包 |
|---|---|
| `/usr/sbin/install-keymap` | `bin/install-keymap`（0755） |
| `/usr/bin/kbd-config` | `bin/kbd-config`（0755） |
| `/usr/bin/dh_consoledata`（sed 生成） | `bin/dh_consoledata`（0755） |
| `/usr/share/console/getkmapchoice.pl`（sed 生成） | `share/console/`（0755） |
| `/usr/share/console/ps2-to-riscpc`（awk） | `share/console/`（0755） |
| `/usr/share/debhelper/dh-consoledata/{common.pl,config.in,templates}` | `share/debhelper/dh-consoledata/`（config.in 0755，debian/rules override_dh_fixperms 显式 chmod +x） |
| `/usr/share/debhelper/autoscripts/postinst-lcd-keymaps` | `share/debhelper/autoscripts/`（0644） |
| （man8 由 docbook-to-man/pod2man 生成） | 不生成（Debian 文档工具，OHOS 无配方） |
| `debian/copyright` | `licenses/` |

### 2. shebang 适配

`#!/usr/bin/perl`、`#!/usr/bin/perl -w` → `#!/usr/bin/env perl`、
`#!/usr/bin/env perl -w`（OHOS 无 `/usr/bin/perl`，perl 由 hnp 提供
`/data/service/hnp/bin/perl`，house perl shebang 先例）；
`ps2-to-riscpc` 的 `#! /usr/bin/awk -f` → `#!/usr/bin/env awk -f`。
`install-keymap`/`kbd-config` 的 `#!/bin/sh` 保留（OHOS 有 /bin/sh）。

### 3. 依赖（conan requires）

运行期外部命令消费关系（脚本 `system()`/backtick 全文核对，勿凭命令名前缀
猜包）：

| 命令 | 归属包 | 已归档 | 声明 |
|---|---|---|---|
| `loadkeys`/`fgconsole`/`dumpkeys` | kbd | kbd/2.9.0 | `requires` |
| `tempfile` | debianutils | debianutils/5.23.2 | `requires` |
| `dpkg --print-architecture`/`--compare-versions` | dpkg | dpkg/1.23.7 | `requires` |
| `gzip`/`awk`/`diff`/`md5sum` | OHOS 基础系统（toybox/busybox） | — | 不声明 |
| `dpkg-reconfigure`（kbd-config 转调） | debconf | debconf/1.5.77（debconf 客户端，无 dpkg-reconfigure 二进制） | 不声明（环境边界） |

## 测试

上游 0 测试 → 自写冒烟 `test_package/test_console_common.sh`（8 项，断言点
全部来自脚本全文核对）：

1. `install-keymap` 在 env PATH（runenv bindirs 注入）；
2. `install-keymap --help` → exit 0 + Usage（参数解析前分支，确定性行为）；
3. `install-keymap` 无参 → exit 1 + Usage；
4. `install-keymap NONE` → exit 0（早退分支，先于 fgconsole/loadkeys/tempfile
   ——不触达虚拟终端路径）；
5. `kbd-config` 在包内且可执行（#!/bin/sh 保留）；
6. `dh_consoledata` 在包内且占位符已全部替换（无 `@DHDIR@` 残留）+ perl -c
   语法校验；
7. `getkmapchoice.pl` 在包内且 `#####COMMON#####` 标记后已插入 common.pl
   （perl -c 不要求，Debconf::Client::ConfModule 未提供——只验落位）；
8. `config.in`/`common.pl` 落位（common.pl 独立 perl -c syntax OK——纯 sub 定义
   无 use 语句；config.in 为 debconf 客户端脚本，断言止步于落位/shebang/0755）。

## 边界

- **keymap 交互声明路径未适配**：`config.in`/`getkmapchoice.pl` 是 debconf
  客户端（`use Debconf::Client::ConfModule`），OHOS 无 debconf 客户端模块；
  `kbd-config` 转调的 `dpkg-reconfigure console-data` 需 debconf 二进制 +
  console-data 键图数据（均未归档）——脚本已落位可被下游消费，交互路径
  记环境边界，不宣称已适配。
- **虚拟终端路径未适配**：`install-keymap` 核心功能（`loadkeys` 加载键图）需
  真实 Linux VT（`/dev/console`），OHOS 无——非 root 冒烟只走三分支早退
  （--help/无参/NONE），不触达 VT 路径。
- **templates 不生成**：`po2debconf`（po-debconf 包）是 Debian 构建工具
  （OHOS 无配方）；keymap debconf 问题模板的消费方是 console-data 键图包
  （未归档）。
- 本包 DEPRECATED（官方建议 console-setup），归档仅为依赖链完整性（kbd/
  console-data 生态消费）。
