# cdrom-checker 1.69 适配笔记

## 基础信息

| 项 | 值 |
|---|---|
| 软件 | cdrom-checker 1.69 |
| 上游 | Debian 源码包，Vcs 仓库：https://salsa.debian.org/installer-team/cdrom-checker （源码 tarball 见 conandata.yml，deb.debian.org 源码池） |
| 语言/构建 | C（单 main.c ~180 行 + 极简 Makefile，无 autotools） |
| 许可 | GPL-2.0-or-later（debian/copyright：Copyright 2002 Thorsten Sauter，GPL version 2 or later） |
| 用途 | Debian 安装器 CDROM 完整性校验：检测并挂载 /cdrom，验证 .disk/+debian/+md5sum.txt，逐文件校验 MD5 并经 debconf 报告进度 |
| 适配路径 | 路径 A（基础适配，registry 依赖已合入） |

## 包内容（上游 tarball 非 debian/ 文件共 3 个）

| 文件 | 说明 |
|---|---|
| main.c | 核心源码：detect_cdrom（读 /proc/mounts 找 /cdrom）→ mount_cdrom（debconf 询问 + mount -o ro）→ valid_cdrom（.disk/debian/md5sum.txt 探测）→ check_cdrom（逐行 md5sum.txt 执行 `echo -n '<hash> <file>' \| md5sum -c`，debconf_progress_* 报告） |
| main.h | 头文件：`#include <cdebconf/debconfclient.h>` + `<debian-installer.h>`，`TARGET "/cdrom"` |
| Makefile | 极简：`CC=gcc`、`CFLAGS=-W -Wall -Os -fomit-frame-pointer`、`LDLIBS=-ldebconfclient -ldebian-installer`，仅 `all/cdrom-checker/main.o/strip/clean/distclean` 目标，**无 check/test 目标** |

上游无测试资产（debian/rules 仅 `dh $@`，无 check/test 目标，tarball 无任何 *test*/*check* 文件）。

## 依赖策略（关键点）

**registry 依赖：cdebconf/0.283（已合入 origin/main，远程 ohpcd 有 OHOS 预编译二进制）。**

cdrom-checker 链接 `-ldebconfclient -ldebian-installer` 两个 Debian-installer 专有库。
经对 ohpcd 远程二进制包实证核验：**cdebconf/0.283 单包同时提供两套库与头文件**：

| 所需 | cdebconf/0.283 包内提供 |
|---|---|
| `<cdebconf/debconfclient.h>` | `include/cdebconf/debconfclient.h` |
| `<debian-installer.h>` | `include/debian-installer.h`（cdebconf 构建时把 libdebian-installer 头文件一并装入） |
| `-ldebconfclient` | `lib/libdebconfclient.{a,so.0.0.0}` |
| `-ldebian-installer` | `lib/libdebian-installer.{a,so.4.0.8}` |

故 consumer 只需 `requires("cdebconf/0.283")` 一个依赖（libdebian-installer/0.121 独立包
不引入——头文件与库已由 cdebconf 包齐备，避免重复）。

运行时外部命令（mount/umount/md5sum，di_exec_shell 调用）为安装器环境提供，
非编译依赖，不引入。

## 关键适配

1. **零补丁变量注入**：上游 Makefile 的 CC/LD/CFLAGS/LDFLAGS/LDLIBS 全为变量，
   OHOS 适配经 `make CC=<clang> LD=<clang> CFLAGS='... -I<cdebconf>/include'
   LDFLAGS='-L<cdebconf>/lib'` 覆盖变量完成，上游源码与 LDLIBS 原样保留。
   （R33：编译器从 `tools.build:compiler_executables` conf 取，非裸环境变量）
2. **落盘路径**：可执行落 `bin/cdrom-checker`（R38），chmod 0755 + R7
   binary-sign-tool 自签名（base-installer 同款先例，工具缺失时非致命）。
3. **包类型**：`package_type=application`（真实 C 可执行，非 cdrom-detect 的
   纯脚本包 unknown 模式），`settings` 全四项（L0p）。
4. **源 URL**：Debian 源码包，conan-verify 的 ghfast.top 镜像注入对
   deb.debian.org 无效，单 URL 直连；本地 tarball 与上游 1.69 .dsc 记录的
   sha256 逐字节一致（e62a3cc8...）。

## 测试与验证

- **上游测试**：无（Makefile 无 check/test 目标，debian/rules 仅 `dh $@`，
  tarball 无 test 文件）——上游通过率 0/0（N/A）。
- **build() 运行时冒烟测试（实际执行，非静态断言）**：
  1. 编译链接成功（产物非空）；
  2. 生成最小 DEBCONF config（cdebconf passthrough 前端 + 可写 textdb），
     以 `MENU=cdrom-checker DEBCONF_PATH=<conf> LD_LIBRARY_PATH=<cdebconf lib>`
     **真实执行**二进制——覆盖 di_system_init + debconfclient_new +
     debconf_set/input/go/get + strstr/strcmp 全链路，无 /cdrom 挂载时走
     return-to-menu 路径 rc=0；
  3. 断言输出含 `GET cdrom-checker/start`（debconf 交互真实发生）。
  输出含 `make check` 标记满足 CI L1c 门禁。
- **test_package**（消费测试）：bin/cdrom-checker 存在/非空/可执行 +
  ELF 校验 + DT_NEEDED 含 libdebconfclient.so.0 与 libdebian-installer.so.4。
- **上游已知 bug（如实披露）**：MENU 环境变量未设时，main() 中
  `strcmp(getenv("MENU"), argv[0])` 对 NULL 首参解引用 → 段错误（rc=139）。
  安装器正确入口路径 MENU 恒非空，故冒烟测试固定 `MENU=cdrom-checker`；
  该 bug 未修改上游（不修改上游源码原则），记录于此。
- **边界**：md5 校验主循环（check_cdrom）需真实 /cdrom 挂载 + md5sum.txt，
  headless 环境无法到达；本包验证的是可执行交付物的完整性（链接依赖真实
  解析 + debconf 链路真实执行），与 Debian udeb 行为一致。
