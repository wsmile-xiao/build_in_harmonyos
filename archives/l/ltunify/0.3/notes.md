# ltunify 0.3 适配笔记

## 编译环境
- 构建系统: makefile（上游单个裸 Makefile，无 configure，无自动测试）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（由 conan `tools.build:compiler_executables:c` 注入）
- 平台: HarmonyOS aarch64（HongMeng 1.12.0），构建主机 B 机真机
- 状态: built

## B 判定（3+2）
- **适配路径**：A（标准流程，本包未产生新的知识库条目）
- **使用知识库**：E098（构建环境 PATH 不含 `/bin` ⇒ `install` 在 `make`/`sh` 里取不到，用 cp + chmod 替代；E098 原文「toybox 无 install」这句与本机实测不符，见下「事实修正」节）、E108（Makefile 把 `install` 写成字面量、无 `INSTALL` 变量可覆写 ⇒ `make install` Error 127）、E087/E490（HMDFS 产物执行位）
- **知识库扩展**：无。池件 **M13** 与 **M18** 的**症状**在本包逐字复现，但两者的**机理与修法均不适用**，逐条否证见下表；故不配草稿、不提【知识库扩展】Issue
- **关联 Issue**：不适用（路径 A，无知识库扩展）

## 池件 M13 / M18 适用性否证（逐字证据）

探测环境：B 机 `~/tmp/uc2/z34-ltunify/src/ltunify-0.3`（sha256 `c98a5e44…e4f1` 校验一致的官方 orig tarball 解包）。

### M18（烧死 `CC = cc` ⇒ 必须命令行覆写）——**不适用**

未覆写首错原文（`env -u CC -u CFLAGS make -j1`）：

```
cc -g -O2 -Wall -Wextra -D_FORTIFY_SOURCE=2 -fstack-protector --param ssp-buffer-size=4 -o ltunify ltunify.c -lrt -DPACKAGE_VERSION=
make: cc: No such file or directory
make: *** [Makefile:27: ltunify] Error 127
```

症状与 M18 逐字相同，但**机理不成立**：

1. 本包 Makefile **没有任何 `CC` 赋值**——`grep -nE "^(CC|X11INC|X11LIB|FREETYPEINC|INCS|LIBS)[ ]*[:?]?=" Makefile` 命中 **0**（只有 `CFLAGS ?=` 与 `BINDIR ?=`）；M18 的 `prescan_pattern`（`CC[ ]*=[ ]*cc$` 等）对本 Makefile **零命中**。
2. `$(CC)` 取的是 **GNU make 内置默认** `cc`，而 M18 的立论前提是「config.mk 里 `CC = cc` 文件内赋值压过环境变量 ⇒ 只能命令行覆写」。
3. 反证实验 `CC=clang make -j1`（**只给环境变量、不给命令行覆写**）⇒ 两个二进制 `ltunify` / `read-dev-usbmon` 全部编译链接成功。**说明环境变量路径即可解决，M18 的「必须命令行覆写」不成立。**
4. 本包非 X11 工具，无 `X11INC=/usr/X11R6` / `FREETYPEINC` 烧死路径，M18 的第二层症状（`'X11/Xlib.h' file not found`）无对应面。

### M13（`INSTALL_*` 是可覆写变量 ⇒ 命令行覆写为 cp -f / mkdir -p）——**不适用**

未覆写首错原文（`make CC=clang install DESTDIR=<stage> bindir=/bin udevrulesdir=/etc/udev/rules.d`）：

```
install -m644 -D udev/42-logitech-unify-permissions.rules <stage>/etc/udev/rules.d/42-logitech-unify-permissions.rules
make: install: No such file or directory
make: *** [Makefile:41: install-udevrule] Error 127
```

（家目录裸 PATH 下 `install -m755 -D f sub/out` 亦复现 `sh: install: inaccessible or not found`，rc=127。本轮在同一台 B 机复测：`printenv PATH` 的 8 条目里**无 `/bin`**、`command -v install` 无输出 rc=1、`PATH=/bin:$(printenv PATH) command -v install` 立即解析到 `/bin/install` ⇒ 首错是**查找路径**问题，不是命令缺失，详见下「事实修正」节。）

症状命中，但 **M13 的修法在本包物理上不可执行**：

1. M13 的前提是「上游把安装工具做成**可覆盖变量**（`INSTALL = install` + recipe 引用 `$(INSTALL_PROGRAM)`）⇒ make 命令行覆写」。本 Makefile 的 `install` 是**字面量命令**，`grep -n INSTALL Makefile` 命中 **0**，没有任何变量可覆写。
2. 知识引擎对本错误的实测判决 **TOP1 = E108**（`patch-makefile-in-ginstall`），且 `ginstall` 在 B 机 `~/usr/local/bin/ginstall` **确实存在**；E098（`cp-chmod-replace`）同样命中。⇒ 该症状已被既有条目覆盖，构不成新知识。
3. 因此本包按 **E098** 落地：配方 `package()` 不走 `make install`，直接 `copy` + `os.chmod(0755)`，等价上游 `install -m755 -D` 的落点与权限，零补丁。
4. **同机制的在池草稿已存在**（查重补引）：`knowledge/drafts/DRAFT-ohos-makefile-explicit-toolchain-and-install-vars.md`（按文件名引用，drafts 内 E 号有复用）——其「现象」段 `:5` 写的正是「上游 Makefile 默认使用 `cc` 和 `install`」，「可复用处理」`:9` = 从 `tools.build:compiler_executables` 取 CC 显式传 `make CC=`、`:10` = 不把 `install` 缺失当源码失败而改用 Conan `copy()` 建包边界、`:12` = **不要修改设备全局 PATH**，与本包做法逐条一致；其「证据」`:16-17` 是同形态首错。⇒ 本包是该模式的**第二个实例**，机制已在池 ⇒ **仍判 B = none**（引用它只会加强"不新增知识"的结论）。下节的 `/bin/install` 实测属**条目外事实修正**，投既有条目更新/通用池，不占本 PR 知识位。

## 事实修正：`install` 并非"系统没有"，而是"PATH 里没有 `/bin`"

（2026-09-25 整改轮在 B 机重新实测。此前 `E098` 原文与本包 `conanfile.py` 旧注释、`notes.md` 旧问题表 #2、软件级 `README.md`「安装方式」条、版本级 `manifest.yaml` `knowledge_gained[1]` 一律写成「toybox 无 `install`」，该机理**已被否证**；四处口径已按下列读数改正。）

| 待验事实 | 本机实测读数 |
|---|---|
| `/bin/install` 是否存在 | `os.path.exists` = **True**；`os.stat` mode **`0o100755`**、size **546360** B；`os.access(X_OK)` = **True** |
| 是谁提供的 | `/bin/install --version` → **`toybox 0.8.12`**（rc=0）⇒ 该命令**正是 toybox 提供**，"toybox 无 install"不成立 |
| 能不能真干活 | `cd ~/tmp/uc2/z34-ltunify/w4fix && /bin/install -m755 probe-src.txt itmp/probe.txt` → **`REALCOPY_RC=0`**，落地件 `ls -l` 见 8739 B 文件 |
| 为什么构建里取不到 | `printenv PATH` = `.local/bin`、`.harmonybrew/bin`、`.harmonybrew/sbin`、`/usr/local/bin`、`/data/app/bin`、`/data/service/hnp/bin`、`/usr/bin`、`/vendor/bin`（**8 条目，无 `/bin`**）⇒ `command -v install` 空 rc=1、`sh -c install` rc=**127**（`sh: install: inaccessible or not found`）；把 `/bin` 前置进 PATH 后 `command -v install` → `/bin/install` |
| 能否 `ls /bin` 核实 | `os.listdir('/bin')` → **PermissionError errno=13** ⇒ "存在但不可枚举"成立，这也是旧轮次误判"没有该命令"的直接原因 |
| `cc` 一侧是否同因 | 不受影响：补 `/bin` 后 `command -v cc` 仍为空（`notes.md` 问题表 #1 的根因不变） |

⇒ **处置面一字未改**（仍不走 `make install`、`package()` 内 copy + chmod 0755），改的只是**根因表述**；B 判定维持 `none`（属既有条目的事实修正 + 同机制在池草稿的第二个实例，不占知识位、不建【知识库扩展】Issue）。

## 上游测试清点（R51 三步法）

计数口径：**用 python 的 `tarfile` / `os.walk` 逐 member 数，不用 shell 通配**（`*` 不匹配 `.gitignore`，会让清点少一枚；上一版记的 14 就是这么来的）。

```
$ python3 -c "import tarfile;t=tarfile.open('ltunify_0.3.orig.tar.gz');print(sum(1 for m in t.getmembers() if m.isfile()))"   -> 15
$ python3 -c "import os;print(sum(len(fs) for _,_,fs in os.walk('ltunify-0.3')))"                                        -> 15
$ grep -rniE "check|TESTS|add_test" Makefile    -> 0 命中
$ ls tests test check 2>/dev/null               -> 无此类目录（tar 内目录 member 只有 ltunify-0.3/、ltunify-0.3/udev/）
$ grep -nE "^[A-Za-z][A-Za-z0-9_.-]*:" Makefile -> 8 命中
  全部目标（8 枚，含 0 枚测试目标；括号内是 Makefile 行号）:
  all(22) / read-dev-usbmon(24) / ltunify(26) / clean(30) /
  install-home(33) / install(37) / install-udevrule(40) / uninstall(43)
  —— 其中 read-dev-usbmon 与 ltunify 是本包真正要构建的两枚产物目标，上一版清点漏列
```

**结论：上游无测试体系（0 个测试）**，非"未运行"。15 个文件为：Makefile、NEWS、README.txt、hidpp20.c、hidraw.c、keyboard.txt、ltunify.c、notes.txt、read-dev-usbmon.c、registers.txt、shell、udev/42-logitech-unify-permissions.rules、usbmon-setperms、usbmon.awk、**.gitignore**（38 B；上一版的 14 枚清单正是漏了它）。`Makefile` 实测 1173 字节 / **44 行**（以换行结尾，`split('\n')` 会得到 45 段，别把段数当行数）。

## 编译步骤

```bash
cd <source_folder>
make -C <source_folder> CC=clang PACKAGE_VERSION=0.3 -j1
# clang ... -o ltunify ltunify.c -lrt -DPACKAGE_VERSION="0.3"
# clang ... -o read-dev-usbmon read-dev-usbmon.c
```

产物 `ltunify` 96768 B、`read-dev-usbmon` 47616 B；`llvm-readelf -d ltunify` 的 NEEDED 只有 `libc.so`（`-lrt` 未引入运行期依赖）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 报 `make: cc: No such file or directory`（Error 127） | Makefile 未赋 CC，`$(CC)` 取 GNU make 内置默认 `cc`，OHOS 无该别名 | 命令行注入 `CC=<conan conf>`（R33，不裸用 shell `${CC}`） |
| 2 | `make install` 报 `make: install: No such file or directory`（Error 127） | 构建环境的 `PATH` 不含 `/bin` ⇒ `make`/`sh` 查找 `install` 失败（实测 `/bin/install` **存在且可执行**、系 toybox 0.8.12，见「事实修正」节）；上游又把 install 写成字面量、无 `INSTALL` 变量可覆写 | 不走 `make install`，`package()` 内 copy + chmod 0755（E098） |
| 3 | `ltunify --version` 打印空版本串 `Logitech Unifying tool version ` | Makefile:12 用 `git describe` 派生版本，tarball 无 `.git` ⇒ 空；且 Makefile:13 `ifeq (PACKAGE_VERSION, "")` 漏写 `$`，恒走 else 分支，把 `-DPACKAGE_VERSION` 定义成空串 | 命令行注入 `PACKAGE_VERSION=0.3`，零补丁；test_package 第 [2/4] 组断言锁死该回归 |
| 4 | `ohc-run.py init-build` 崩溃 | 框架缺陷 `scripts/ohc/check_env.py:32-33`（`:32` 是 `except Exception:`、未绑 `as e`，`:33` 却是 `return False, str(e)`） 却 `return False, str(e)` ⇒ `NameError: name 'e' is not defined`（触发条件：`~/usr/local/bin/automake` 存在但不可执行） | 不改框架（scripts/ 只读）；改走 `conan-init` 直接生成骨架 + 按 `templates/conanfile-makefile.py.tmpl` 调整 |
| 5 | HMDFS 产物权限 660 不可执行 | 新建文件默认 660（E087/E490 族） | `package()` 内显式 `os.chmod` 补 0755 |

## 源码修改

**无**（0 个补丁；三处问题全部用 make 命令行变量与配方内复制解决，符合 R1 参数最少化与 R9 探索纪律）。

## 依赖版本

编译期与运行期均无 Conan 依赖，仅 `libc.so`。

## 验证结果

设备真机（构建主机 B 机）实测：

```bash
$ make -C <src> CC=clang PACKAGE_VERSION=0.3 -j1     # rc=0，两产物生成
$ ./ltunify --version
Logitech Unifying tool version 0.3
Copyright (C) 2013 Peter Wu <lekensteyn@gmail.com>
$ ./ltunify --help | grep -c -e pair -e unpair -e list           # 4
$ ./read-dev-usbmon </dev/null ; echo $?
Usage: ./read-dev-usbmon /dev/usbmonX
1
$ ./ltunify -d /dev/hidraw0 list
/dev/hidraw0: Permission denied                                  # 优雅报错，无崩溃
$ llvm-readelf -d ltunify | grep -i needed
  (NEEDED) Shared library: [libc.so]
```

## 硬件运行期能力探测（诚实披露）

ltunify 的全部实质功能都要打开 `/dev/hidraw*` 并与 USB「Logitech Unifying 接收器」交换 HID++ 报文。B 机实测：

| 能力面 | 实测 | 影响 |
|---|---|---|
| `/dev/hidraw0`、`/dev/hidraw1` | **节点存在但 `stat` 即 Permission denied**（本轮复测：`os.stat` → errno **13**；`os.listdir` → errno **20**（不是目录）），非"无节点"；存在性的一手证据是本节上方 `./ltunify -d /dev/hidraw0 list` 返回 `Permission denied` 而非 `No such file` | 配对/查询主路径不可执行 |
| `/sys/class/hidraw` | **类别目录本身可 stat**（`os.stat` OK，mode `0o40755`；`ls -d` rc=0 并把路径原样打印出来），但**枚举被拒**：`os.listdir('/sys/class/hidraw')` → errno **13**。⚠ 同一形态在本机 `/sys/class/net` 上也出现（`os.listdir` → errno 13）⇒ 是**设备层 opendir 权限受限**，不能读成"hidraw 类别不存在" | 无法枚举 hidraw 节点，与上一行合起来构成主路径不可执行 |
| Logitech Unifying 接收器（046d:c52b/c532/c52f/c534） | 无该硬件（`lsusb` 亦不存在） | 无真实设备可驱动 |
| `/dev/usbmon*` | **不存在**（`ls: /dev/usbmon*: No such file or directory`） | `read-dev-usbmon` 的抓包解析能力不可执行 |
| `/etc/udev` | **不存在** | udev 规则无法在实机验证生效 |

**因此以下功能面本次未覆盖，不得当作已通过**：`list` / `pair` / `unpair` / `info` / `name` 的真实 HID++ 报文交换、配对超时路径、`hidpp20.c` 的 2.0 特性查询、`read-dev-usbmon` 的报文解析、udev 规则的实际提权效果。test_package 只覆盖命令行面（版本串、usage、help 子命令声明、runenv 导出）。

注：本轮 `L2_RESULT=**pass**`（`reports/w3-local-ci.log:252` 原文 `L2_RESULT=pass: ltunify --version OK, read-dev-usbmon failed`；细节 `:247` `[ok] L2: ltunify --version OK`、`:248` `[warn] L2: read-dev-usbmon --version/--help failed (non-blocking)`）—— 上一版把它写成 `skip` 是**错的**，据实改正。但改正后它的证据力同样有限：框架 L2 只在包内**裸跑** bin 的 `--version`/`--help`、**不加载 Conan 运行环境**，且本轮该步只对 `ltunify` 一枚成立、`read-dev-usbmon` 在这一步是失败的非阻塞告警 ⇒ **L2 只证明一枚 bin，不得当作整体"可执行"证据**；可执行性只认 runenv 内的 7/7 断言（`:221-230` 逐条 `PASS`、`:232` `assertions: 7  passed: 7  failed: 0`、`:233` `ALL TESTS PASSED`）与 `:242` 的 `L5: bin/ has content`。上表功能面证据一律取自本机 `conan create` 的 test_package。

## 门禁重跑记录（2026-09-25 整改轮，全部门禁按新 HEAD 重跑）

本轮改写了 `conanfile.py` 的 `package()` 注释（配方注释计入 recipe revision）⇒ 旧一轮 W3 / conan-verify 证据**作废**，按轻量单在 B 机直接重跑；`CONAN_HOME=~/tmp/ch/home-ltunify`，三步构建均经 `~/tmp/uc2/build-slot.sh --kind short` 取机动槽（日志首行 `SLOT_OK` 可证）。

| 步骤 | 判决件与行号 | 读数 |
|---|---|---|
| conan-verify | `~/tmp/uc2/z34-ltunify/verify3.log:9 / :13 / :15 / :22 / :26` | `G1: PASS`、`G2: PASS`、`G3: PASS`、`✅ 配方验证通过: ltunify 0.3`、`VERIFY_RC=0`；入库报告 `reports/conan-verify-report.md:3` `**Verdict**: PASS`、`:6` `**Date**: 2026-09-25T06:47:14.641062`；G0 `:8` / G1 `:12` / G2 `:26` / G3 `:30` / G4 `:34` 节标题均 PASS。**两处不粉饰**：G4 段内 `:35` 是 `⚠️ 无法找到程序包 ID`；`L2`/`L4`/`L5` 三节（`:37`、`:40`、`:43`）标题打 ✅ 而正文是 `⏭️ 跳过（无 cache 路径）` ⇒ 不计入通过证据 |
| W3（在 `finish` 内） | `finish2.log:64 / :65`、`.ci-result.json` | `✅ 本地 CI 模拟通过`、`✅ W3 本地 CI 模拟通过`；`.ci-result.json`：`timestamp 2026-09-25T06:47:27.553065`、`exit_code 0`、`integrity_hash e5b8b467c3646fa5`、`log_sha256 14150d4e8aa87479b11a54742965546c1df16e8b6974a38775343eef505c4405`（被哈希件 `reports/w3-local-ci.log` 实测 **12099 字节**、md5 `936330b720b85b2d0beb8c65a4ac1d1d`）。按 `scripts/ohc/finish.py:249-252` 原式 `sha256("<timestamp>:ltunify:0.3:0")[:16]` 复算 = `e5b8b467c3646fa5` ⇒ **MATCH**；按 `:263-267` 复算 `sha256(w3-local-ci.log)` ⇒ **MATCH**。W3 日志形态防伪：`^[` 标记 **72** 枚、`RESULT=` **8** 枚，mtime 与 `timestamp` 同轮（06:47） |
| finish | `finish2.log:110 / :137` | `失败步骤: step5b, step8`、`FINISH_RC=2`（阻塞门禁 W3 已过；红因见下节两条） |
| graph validate | `graphv2.log:173 / :175 / :185` | `✅ All checks passed (169 warnings)`、`.kv 540 / .md 540 / index rows 540`、`GRAPH_RC=0`（`finish2.log:84` 另有 `✅ graph validate 通过`） |
| knowledge_check | `kc2.log:24 / :25 / :26` | `KC_RESULT=pass`、`KC_ERRORS=0`、`KC_RC=0`；KC1–KC5 逐项 `[OK]`，`.kv` 540 份、index 行一致 |
| PF1–PF9 静态闸 | `pf.log:1 / :2-3 / :4` | `PF_RC=1`：PF9 × 软件级三件套（互斥族，见下节）、PF7 源 URL 两条；其余项未产生 finding。`pf.log` 跑在整改提交 `ed3aab7e33` 上（本表前五行的门禁同在树内该 SHA 时执行）；`pf2.log:1-3` 是在 `a2638df73e` 上的复跑，红项清单**逐字相同** ⇒ 该闸只对变更路径敏感，本文件之后的改动（仅 notes.md，非构建输入）不影响其读数 |

## 已知非阻塞项（照实披露，未为凑绿改动任何表单）

- `step5b` 全仓存量红、`step8 gen_summary` 框架缺陷均为框架预期，与本包无关（`L2_RESULT=pass` 不属本条，其证据力限定见上节「注」）。本轮判决件（B 机 `~/tmp/uc2/z34-ltunify/`，整改重跑轮）：`verify3.log:26` `VERIFY_RC=0`、`finish2.log:137` `FINISH_RC=2` 且 `:110` `失败步骤: step5b, step8`（红因 `:80-83` 为 E219/E253/E305「字段为空」，**全部是基线上他人条目**）、`graphv2.log:185` `GRAPH_RC=0`、`kc2.log:26` `KC_RC=0`（`:24` `KC_RESULT=pass`、`:25` `KC_ERRORS=0`）。
- **PF9 与「软件级三件套」互斥（框架级冲突，本窗只披露、不改框架、不为此改表单凑绿）**：对整改提交后的 HEAD 复跑 `python3 scripts/ohc/preflight.py . origin/main HEAD` ⇒ `PF_RC=1`（`~/tmp/uc2/z34-ltunify/pf.log:4`）。唯一的路径类红项在 `pf.log:1`：`PF9 分支/路径闸: 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）…（490 例）: archives/l/ltunify/README.md, archives/l/ltunify/commands.json, archives/l/ltunify/manifest.yaml`。这三枚软件级文件是本包按仓内规范交付的（`git ls-tree -r HEAD --name-only -- archives/l/ltunify` 实测 10 枚在列，三枚均在），而 PF9 要求**所有**变更路径都带版本层 ⇒ 两条判据互斥；PF9 自报 **490 例**说明这是全仓普遍形态、不是本包写法问题。本窗选择**保留三件套**、接受 PF9 红，不删文件凑绿（同族先例：rephrase / jnoise / jpegqs / light / lighter）。另注口径：`preflight.py` 只在 `__main__` 里对 findings 逐条 `log_fail`、全绿时才 `log_ok`，所以 `pf.log` 只列红项 ⇒ 本轮红项清单 = PF9×1 + PF7×2，其余 PF1–PF6/PF8 与 R52 交叉校验为「未产生 finding」，本窗不把它们写成逐条 ✅。
- **PF7 源 URL 闸（R39）同轮报 2 条红**：`pf.log:2-3` 把 Debian pool 判为「下游重打包源」（锚点 `conandata.yml:5`、版本级 `manifest.yaml:10`）。本包源件是 Debian 主仓的 **pristine upstream** `orig` 包，`sha256` = `c98a5e4450bc4344d2646009ea30bee3036a4a64b3a95e4c45509567ebf5e4f1`（本窗对 `tarfile` 与 `conandata.yml` 两侧同值复算）⇒ 属官方托管例外面，照实披露、不改 URL。
- `.handoff.json` 的 `step_failed: "Step6"`（本轮实测同件 `exit_reason=finish_success`、`exit_code=0`）⇒ Step6 未产出 release / debug 两枚 tar.gz，属归档交付物缺失、不阻塞 W3。
- submit 就绪三件缺失：`reports/test-report.md` 不存在、`.staging-verified` 不存在、`packaging/` 为**空目录**（`find packaging -type f` 无输出），而 `finish` 日志仍写「需创建」⇒ 两条并存事实照实并列，未据此判绿。
- 上游 tarball 不含 LICENSE 正文文件，许可证按源码头部署名判定为 GPL-3.0-or-later。
---

**编译结束**: 2026-09-25 06:47
**最终状态**: built
