# chkboot 1.3 适配笔记

## 上游信息
- **仓库**: https://github.com/grazzolini/chkboot
- **版本**: 1.3（tag `v1.3` → commit `33ea87521dcb1d72c5e9e6417f7882b3f3227d73`）
- **语言**: 纯 shell（bash）+ 配置/数据；`Architecture: all`，**无编译型源码**
- **构建系统**: 上游顶层 `Makefile`（`all:` 为空目标；`install:` 用 `install(1)` 拷文件）
- **许可**: GPL-2.0-only（`LICENSE.md` + `GPLv2.md`）
- **依赖**: 无第三方依赖（`conan download chkboot/1.3 -r=ohpcd --only-recipe` → rc=1，
  属“目标库自身未发布”，非依赖缺口；全树无 find_package/pkg-config/链接声明）
- **源码 tarball**: `194fa7eb89dcedf4e2d098408e48e6cea0a3627b512ce09aeacc6255e43e58fc`
  （11569 B / 19 条目；与 Debian orig tarball `cmp` 逐字节一致）

## 环境
- 平台: HarmonyOS PC arm64（`HarmonyOS localhost HongMeng Kernel 1.12.0`，aarch64 Toybox）
- bash: `/data/service/hnp/bin/bash`（GNU bash 5.3.0）；**无 `/bin/bash`、无 `/usr/bin/bash`**
- make: GNU Make 4.4.1（`/data/service/hnp/bin/make`）
- conan: 2.29.1（OHOS 适配版），remote `ohpcd`
- 关键缺失命令: `install`（coreutils）、`zenity`、`xmessage`、`systemctl`、`findmnt`、`lsblk`、`gcc`
- 只读/不存在路径: `/etc`（Read-only file system）、`/var/lib`（不存在）、`/boot`（存在但 EACCES）

## 构建方式（真实命令与退出码见 evidence/14b-make-install-adapted.log）
```bash
# 1) 上游 all: 为空目标（无编译）
make -j1                                     # rc=0, "Nothing to be done for 'all'."
# 2) 安装（含 3 个可选目标）
make install          DESTDIR=<staging>      # rc=127 → 修复后 rc=0
make install-systemd  DESTDIR=<staging>      # rc=0
make install-pacman   DESTDIR=<staging>      # rc=0
make install-initcpio DESTDIR=<staging>      # rc=0
```
产物（staging）→ 包内布局：`usr/bin/*` → `bin/`；`etc/default/chkboot.conf` →
`res/default/`；`etc/profile.d/*` → `res/profile.d/`；systemd/pacman/initcpio 资产 →
`res/{systemd,libalpm-hooks,initcpio}/`。

## 遇到的问题与解决

| # | 问题（首个真实错误） | 根因 | 解决 |
|---|--------------------|------|------|
| 1 | `make install` → `install -D -m644 chkboot.conf …` / `make: install: No such file or directory` / `*** [Makefile:10: install] Error 127`（rc=2 退出 / 命令 rc=127） | OHOS 未提供独立 `install(1)`（coreutils 缺失；busybox 1.37 有 `install` applet 但未建同名入口），上游 Makefile 的 `install:` 直接调用该命令 | recipe `build()` 生成指向平台 busybox 的 `install` shim 并前置 `PATH`；**上游源码零改动**（证据 13-install-shim-probe.log） |
| 2 | `chkboot-check` 在 OHOS 上误报 `CHKBOOT ALERT!` 且 `cat: /: Permission denied`，退出码与真实状态无关 | `/etc` 只读 → 无法存在 `/etc/default/chkboot.conf`；`source` 失败后变量未定义，`${CHKBOOT_DATA}/${CHANGES_ALERT}` 塌缩成 `/`，`[[ -s / ]]` 为真 | 补丁 0001-0005：`source "${CHKBOOT_CONF:-/etc/default/chkboot.conf}"`（未设置时行为与上游逐字一致）；`package_info()` 的 runenv 默认指向包内 `res/default/chkboot.conf` |
| 3 | `bin/chkboot-desktopalert` 执行即 `bad interpreter: /bin/bash: No such file or directory`（rc=126） | 上游该脚本 shebang 为硬编码 `#!/bin/bash`，而 OHOS 无 `/bin/bash`（bash 在 `/data/service/hnp/bin/bash`） | 补丁 0004：shebang 改为同工程其它 5 个脚本一致的 `#!/usr/bin/env bash` |

## 源码修改（patches/，全部经 `refresh-patch --auto` 生成）
| 补丁 | 文件 | 改动 |
|------|------|------|
| 0001-chkboot.patch | `chkboot` | `source` 配置路径支持 `CHKBOOT_CONF` 覆盖（+注释） |
| 0002-chkboot-bootcheck.patch | `chkboot-bootcheck` | 同上 |
| 0003-chkboot-check.patch | `chkboot-check` | 同上 |
| 0004-notification-chkboot-desktopalert.patch | `notification/chkboot-desktopalert` | shebang `/bin/bash` → `/usr/bin/env bash` + 配置路径覆盖 |
| 0005-notification-chkboot-profilealert.sh.patch | `notification/chkboot-profilealert.sh` | 配置路径覆盖 |

补丁内**无平台宏**（未使用 `__OHOS__` 之类条件编译），默认值保持上游原状，仅在
显式设置 `CHKBOOT_CONF` 时改变行为 → 对非 OHOS 平台零影响。

## 上游测试（R51 三步法）
1. **清点（真实命令/退出码见 reports/test-report.md §1）**：
   - `make -n check` → `make: *** No rule to make target 'check'. Stop.`（rc=2），
     `make -n test` / `make -n testall` 同样 rc=2
   - 上游 tar 19 条目中无任何测试文件（`tar tzf | grep -i test` → rc=1）
   - 结论：**上游无自动化测试套件、无测试入口**
2. **发行版侧唯一测试入口**：Debian autopkgtest 4 用例
   （`debian/tests/0001-no-changes … 0004-kernel-update`，
   `Restrictions: isolation-machine, needs-root, breaks-testbed, needs-reboot`）——
   需真实 `/boot` 分区 + 重启，本环境不可原样运行；已在 `test_package/test_chkboot.sh`
   中做**场景等价移植**（dist-0001/0002/0003/0004）。
3. **实跑统计**：`test_package/test_chkboot.sh` 10 用例 → 8 PASS / 0 FAIL / 2 SKIP
   （SKIP 原因：dist-0002 需 root，本机 `sudo -n` rc=1；dist-0004 需 apt + 真实
   /boot + 重启）。逐项名称与日志路径见 reports/test-report.md §2。

## 鸿蒙适配要点（含鸿蒙特有用例 ≥1）
- 鸿蒙特有用例 4 个：`ohos-script-syntax-all`、`ohos-conf-from-package-env`、
  `ohos-conf-override-required`、`ohos-desktopalert-degradation`
- `/etc` 只读 → 全部运行期配置经 `CHKBOOT_CONF` 注入；包不写系统目录
- OHOS 无 systemd/pacman/mkinitcpio → 三类开机集成资产仅作 `res/` 参考数据保留
- OHOS 无桌面通知后端（zenity/xmessage）→ `chkboot-desktopalert` 已自带 `-x` 探测，
  无后端时干净 `exit 1`（不改上游代码）
- `chmod`/权限：HMDFS 下 `install -m644` 实际落盘为 660（E046 平台限制），不影响
  脚本可执行性判断（`-x` 对 660 仍成立），已在验证中记录

## 验证结果
```bash
conan create . --version=1.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... # 见 reports/conan-create.log
conan-verify chkboot 1.3                                                   # 见 reports/conan-verify-report.md
bash test_package/test_chkboot.sh <package_folder>     # TOTAL=10 PASS=8 FAIL=0 SKIP=2
ohc-run.py finish chkboot 1.3 built                                        # W2/W3 见 reports/w3-local-ci.log
```

## 注意事项
- `chkboot` 主命令有 **root 门禁**（上游行为，未修改）：非 root 运行 rc=1；
  完整 baseline/diff 流程需 root（本机无免密 sudo，故该用例在非 root 下 SKIP）。
- OHOS `/var/lib` 不存在，上游默认 `CHKBOOT_DATA=/var/lib/chkboot` 不可用，
  使用时需在 `CHKBOOT_CONF` 指向的配置里改到可写目录。
- 包内 `res/systemd`、`res/libalpm-hooks`、`res/initcpio` 是 Arch/Debian 侧资产，
  OHOS 不加载，请勿据此认为有开机自动检查能力（需由 OHOS 侧自行安排调度）。
---

**编译结束**: 2026-09-26 00:40
**最终状态**: built
