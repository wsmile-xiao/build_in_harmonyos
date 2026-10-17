# keyd 2.5.0 适配笔记

## 编译环境
- 构建系统: makefile（上游根目录**只有单个 `Makefile`**，无 `GNUmakefile`/`CMakeLists.txt`/`configure`/`.github/workflows`，官方 tarball 实测）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4。**交付构建实际使用 profile 钉定的 `/data/service/hnp/bin/clang`**（`create11.log:101`），兜底候选 `~/usr/local/bin/clang` 是 `#!/bin/sh` 包装，自带
  `--sysroot=/data/service/hnp/...` + `-fuse-ld=lld` + `-Wl,--code-sign` + `-D__MUSL__`，
  `dumpmachine` 回报 `aarch64-unknown-linux-ohos`）
- 状态: built
- 产物 ELF 凭据: `PT_INTERP = /lib/ld-musl-aarch64.so.1`（确为 OHOS/musl 目标，非本机 glibc 产物）。
  读法固定用 `~/usr/local/bin/llvm-readelf -l`（不依赖 hnp 挂载）：`readelf` 能否解析随 hnp 挂载状态变化——重启前 `which readelf` 报 `no readelf in (...)`，重启后可解析到 `/data/service/hnp/bin/readelf`，故不把 `readelf` 当稳定前提。
  读法固定用 `~/usr/local/bin/llvm-readelf -l`：设备上的 `readelf` 属 hnp 挂载（`/data/service/hnp/bin/readelf`），
  其可见性随挂载状态变化（重启前 `which readelf` 报 `no readelf in (...)`，重启后 `command -v readelf` 能解析），
  所以不当它稳定前提——`llvm-readelf` 才是可复现的那一条

## 编译步骤

上游只有一个 `Makefile`，覆盖点实测如下，因此不需要任何补丁：`PREFIX`(`:5`) 与
`CONFIG_DIR`(`:7`) 是 `?=` 可覆盖赋值；`platform`(`:25`) 是普通 `=`（命令行 `make platform=…`
仍优先于文件内赋值）；`CC` 全文未赋值 ⇒ 由 make 取默认值，配方在命令行传 `CC=<llvm 绝对路径>` 即接管。

```bash
make -j1 platform=Linux CC="<绝对路径 clang>"      # 构建 bin/keyd 与 bin/test-io
./bin/test-io t/test.conf <每一个 t/*.t>           # 上游单元语料，逐用例一个进程（见问题表 #5）
# package() 手工复现 makefile `install:` 目标里的可执行/数据文件安装行（`Makefile:65-79`）；
#   不走 `make install` 的原因是 PATH 无 /bin + 需 root（见问题表 #4），不是因为设备缺 install 工具。
#   不覆盖 :52-57 的 systemd 单元与 :77 的 data/gnome-*（平台无 systemd/GNOME，不随包交付）
```

`platform=Linux` 是**必传**的：本机 `uname -s` 返回 `HarmonyOS`，会命中 makefile 的
非 Linux 分支并给链接行追加 `-linotify`（问题表 #2）。命令行赋值会覆盖 makefile 内的
`= ` 普通赋值，因此无需改源码；Linux 分支与非 Linux 分支的差别仅为 `COMPAT_FILES` 为空。

`CONAN create`（W3）与交付 HEAD 的绑定关系：读数分两份日志、**同一 recipe rev `cd56cda16441f56f5370cef823b92869` 与同一 package rev `33be3c0e0993002089236d75ba5c8920`**：
· `create11.log`（HEAD `d2777f313d`）= 全量构建：`:12` 导出、`:93` `Building from source`（`--build=missing` 下仍真重建）、`:101` `CC="/data/service/hnp/bin/clang"`、`:160` 单元套件解释器以 argv[0] 传入、`:161` 上游 86 例全通过、`:168` `Packaged 103 files`、`:173` `Created package revision`、`:279` 整次峰值内存；
· `create12.log`（HEAD `717e3b0519`）= 交付前最后一次改动只动了 `test_package/` 的 docstring 与文档，**包走缓存**（`:64` 逐字 `33be3c0e0993002089236d75ba5c8920 - Cache`）故不重建，仅复跑 `test_package`：`:168` 消费者断言、`:128` 探针逐字块、`:119` 守护进程错误串、`:170` 本次峰值。
⇒ 这样 86 例与 41 条断言分别绑定到产出它们的真实一次运行，且两份日志的 recipe/package rev 完全相同；文档与 docstring 不进 recipe 哈希（实测改 `notes.md` 后 `conan export` 的 rev 不变）。## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Error 2`：编译器根本起不来 | 仓库 profile `ci/conan/profiles/ohos-aarch64` 的 `tools.build:compiler_executables` 写死 `/data/service/hnp/bin/clang`，而该绝对路径的可达性**随设备状态变化**：重启前的会话里 `stat` 报 `Permission denied` ⇒ 编译器起不来；重启后（2026-09-25 12:3x 实测）同一路径可 `stat`、`os.access(X_OK)` 为真，且交付构建实际就用它（`create11.log:101` 逐字 `CC="/data/service/hnp/bin/clang"`；本体是 symlink → `ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang`，`clang version 15.0.4`、`-dumpmachine = aarch64-unknown-linux-ohos`） | 配方 `_cc()` 按「profile 取值 → `PATH` 上的 `clang` → `cc` → `~/usr/local/bin/clang`」逐个候选用 `os.access(cand, os.X_OK)` 校验后才采用，取不到即 `ConanException`。`~/usr/local/bin/clang` 是真实的 OHOS 包装器（见"编译环境"），因此**仓库 profile 与本地兜底两条路径都由同一份配方覆盖**，不改只读 profile |
| 2 | 链接期 `unable to find library -linotify` | 本机 `uname -s` 返回 `HarmonyOS` ⇒ 命中 makefile 的非 Linux 分支，该分支追加 `-linotify`；OHOS 把 inotify 实现在 musl libc 内，不提供独立 `libinotify` | 构建命令显式传 `platform=Linux` 覆盖 makefile 的 `=` 赋值（`?=`/`= ` 均可被命令行覆盖），走 Linux 分支；不改上游源码、不加假库、不 `#ifdef` 砍功能 |
| 3 | `sh: /data/service/hnp/bin/bash: inaccessible or not found`（与 #1 同源） | 同一 profile 的 `[buildenv]` 把 `CONFIG_SHELL`/`SHELL` 指向 hnp bash；且 conan 先 source 配方生成的 env 脚本、**最后** source profile 的 `[buildenv]`，配方侧 `Environment` 设置必然被覆盖 | 配方 `_posix_shell()` 做与 `_cc()` 同样的 `os.access(X_OK)` 探测（`CONFIG_SHELL` → `PATH` bash → hnp bash → `~/usr/local/bin/bash` → `/bin/sh`），并把选中的解释器**绝对路径显式放在命令第一位**调用套件脚本（绕开会被 `[buildenv]` 覆盖的 `CONFIG_SHELL`/`SHELL`；实测 `create11.log:160` 逐字 `RUN: "/storage/Users/currentUser/usr/local/bin/bash" ".../run-keyd-unit-suite.sh"`）；`test_package/conanfile.py` 复用同一套探测，两处口径一致 |
| 4 | `make install` 不可用 | `make install` 在本包不可用的理由是**需要 root**：`Makefile:72` 执行 `-groupadd keyd`、`$(PREFIX)` 默认 `/usr/local` 非 root 不可写。设备**自带** `install`（`/bin/install` = toybox 0.8.12，补测 `install -D -m 0755`、`install -d`、`install -m 0644`（父目录已存在时）三条均 `rc=0`）。本窗先后两次归因都**不成立**，一并更正：① "设备没有 `install` 二进制"错；② "conan buildenv 把 PATH 重写成不含 `/bin`"也错——仓库 profile 的 `[buildenv]` 用的是 `PATH=+(path)/...`（**前插而非替换**，`create11.log:31-32` 可见），基础 PATH 仍含 `/bin`。⇒ 配方不走 `make install`，而是逐条复现其安装行到 `package_folder` | `package()` 手工复现上游 `install:` 目标里的可执行/数据文件安装行（对应 `Makefile:65-70` 的 `mkdir -p` 与 `:73-79` 的 `install -m755`/`-m644` 行：`bin/`、`share/keyd/layouts/`、`share/keyd/keyd.compose`、`share/doc/keyd/`、`share/man/man1/*.1.gz`；`licenses/` 由配方按 LICENSE 单独拷入，不在上游 `install:` 目标内），并对两个可执行文件显式 `chmod 0o755`（HMDFS 默认 660，E543 家族既有实证）；不覆盖 `:52-57` 的 systemd 单元 `keyd.service` 与 `:77` 的 `cp -r data/gnome-*`（GNOME 扩展）——鸿蒙 PC 无 systemd/GNOME，二者不随包交付 |
| 5 | 上游单元套件跑第 1 例后"消失"，日志只剩一条 | `t/test-io.c:268` 的 `run_test()` 在首个不匹配处直接 `exit(-1)`；上游入口 `./bin/test-io t/test.conf t/*.t` 把 86 个语料喂给**同一个进程**，任何一例失败都会静默截断后面的套件 | 配方 `build()` 按上游 `Makefile:99-113` 的编译行用同一编译器直接链出解释器（`t/test-io.c` + 8 个 `src/*.c`，含其 `-DDATA_DIR=`），随后**逐用例起一个进程**（生成的 `run-keyd-unit-suite.sh`），每例独立计数并打印 `registered=/passed=/failed=`，任例失败即 `build()` 抛错。读数：`[upstream unit suite] registered=86 passed=86 failed=0` |
| 6 | 守护进程与客户端起不了虚拟键盘；`keyd monitor` 直接报错 | **OHOS MAC 把整个 input 子系统对用户态隐藏**：`stat`、`open`、`opendir`、`inotify_add_watch` 四类入口逐字返回 `errno=13 (EACCES)`，且 `opendir("/dev/input")` 是**报错**而不是"列到 0 项"——计数式探测在这里是假绿（详见随包 B 草稿） | 不做静默降级：`test_package` 按上游真实调用序列（`src/vkbd/uinput.c:41`、`src/device.c:218/130/58/260/266`）逐条**断言 errno 为 EACCES**，并配两条阳性对照（`open /dev/null`、`opendir /dev`）证明探针本身有效。运行面限制如实写进 PR"已知限制"，不删用例、不改判通过 |
| 7 | `keyd` 前台启动 rc=255，错误串是 `open: No such file or directory`（ENOENT 而非 EACCES） | 这是**另一条平面**：`src/ipc.c` 先打开编译期写死的 socket 路径 `-DSOCKET_PATH="/var/run/keyd.socket"`，而本机 `/var/run` 不存在 ⇒ 在抵达 uinput 之前就已失败。**该 errno 不能拿来判 input 平面** | 探针与消费者测试把 socket 平面与 input 平面**分开断言**；`ENOENT` 只归因到 `/var/run`，input 平面的定罪只用 #6 的逐字 `EACCES` 证据 |
| 8 | 首次 `gate.sh` 报 `GATE_FAIL:fork 探针失败（python3）`，而 MemAvailable=6336MB 本该过 | SSH 默认 `PATH` 不含 `~/usr/local/bin`（工作区 §4 已记录），gate 的 clang/python3 探测双双落空 ⇒ **假红** | 设备侧命令统一 `export PATH=$HOME/usr/local/bin:$PATH` 后再跑 gate，转 `GATE_PASS:probe=clang`；另用手工 clang 编译+执行证明本机 fork/exec 正常。构建一律再过 `build-slot.sh --mem 6000` 槽位闸 |
| 9 | 消费者测试初版 5 条 FAIL | 全是**我的预期写错**，不是库缺陷：`list-keys` 的空列表项各占一行（按行计数会虚高）、`shift` 不是键名（表里是 `leftshift`/`rightshift`）、`keyd monitor` 在走到 IPC 之前先撞 inotify、本机没有 `us` 之外的隐含布局假设 | 逐条回源码/回真机复算后改为真实数值：`list-keys` 310 个命名键 / 314 行输出 / 310 个唯一项，布局 100 个文件全非空。当时复跑 `PASS=40 FAIL=0 SKIP=0`；W4 审计整改后在交付 HEAD 为 `[test] assertions: PASS=41 FAIL=0 SKIP=0` |

## 源码修改

**无**。`patches: []`，`patches_applied: []`。上游 tarball 原样编译，没有删改任何测试用例、
没有 `#ifdef __OHOS__` 砍功能、没有伪造头文件。全部适配点都在配方的环境变量与 make 命令行覆盖层。

## 发现与知识（使用记录，逐条对应 `manifest.yaml` 的 `knowledge_gained`）

- ✅ 路径 B 新增：OHOS MAC 把整个 input 子系统对用户态隐藏——`stat()` 与 `open()` 同为 EACCES（存在性在用户态
  不可判定，区别于 E237 的 ENOENT），且 `opendir("/dev/input")` 返回 EACCES 而非空集合 ⇒ "枚举到 0 个 event*"
  与 "被策略拒绝" 在计数式探测里不可区分。`knowledge_ref: DRAFT-keyd-2.5.0-ohos-input-subsystem-mac-invisible`
- ✅ 自发现（构建面）：`uname -s` 在本机返回 `HarmonyOS`，命中 `Makefile:27` 的非 Linux 分支并追加 `-linotify`；
  OHOS 把 inotify 留在 musl libc 内、不提供 `libinotify` ⇒ 用命令行 `platform=Linux` 覆盖 `:25` 的 `=` 赋值。
  `knowledge_ref: none-本包自发现`
- ✅ 复用同族（工具链面）：CI profile 的 `tools.build:compiler_executables` 把 CC 钉成绝对路径 `/data/service/hnp/bin/clang`，
  该路径的可达性随挂载状态变化（重启前 `stat` 报 `Permission denied`；重启后可见且本次构建即用它，`create11.log:101`）⇒ 配方先 `os.access(X_OK)` 校验 profile 取值再退回 PATH 查找（与
  `CONFIG_SHELL`/`SHELL` 指向 hnp bash 同族）。
  **边界修正（重启后实测）**：该路径并非恒不可见——重启后 `stat`/`os.access(X_OK)` 均通过且交付构建即用它 ⇒ 正确结论是『绝对工具路径的可达性随会话/挂载状态变化，必须运行时探测』，不是『hnp 路径不可用』。`knowledge_ref: 经验汇总 §12.38 / E543 同族`
- ✅ 纠正两条误判（安装面）：`make install` 在本包不可用的理由是**需要 root**：`Makefile:72` 执行 `-groupadd keyd`、`$(PREFIX)` 默认 `/usr/local` 非 root 不可写。设备**自带** `install`（`/bin/install` = toybox 0.8.12，补测 `install -D -m 0755`、`install -d`、`install -m 0644`（父目录已存在时）三条均 `rc=0`）。本窗先后两次归因都**不成立**，一并更正：① "设备没有 `install` 二进制"错；② "conan buildenv 把 PATH 重写成不含 `/bin`"也错——仓库 profile 的 `[buildenv]` 用的是 `PATH=+(path)/...`（**前插而非替换**，`create11.log:31-32` 可见），基础 PATH 仍含 `/bin`。⇒ 配方不走 `make install`，而是逐条复现其安装行到 `package_folder`。结论口径：绝对工具路径与挂载可见性都要**运行时探测**，`install` 是否存在不是本包的门槛。
- ✅ 自发现（IPC 面）：本机 `/var/run` 不存在 ⇒ 守护进程在抵达 uinput 之前先死在 socket 锁的 `open`（ENOENT，
  逐字 `open: No such file or directory`，rc=255；该断言本体是**析取判定**（末行命中 `No such file or directory` 或 `Permission denied` 之一，实测命中前者，`create12.log:119`）⇒ 两个平面的 errno 必须分开断言。
  `knowledge_ref: none-本包自发现`

## 依赖版本

无第三方 Conan 依赖（`requirements()` 为空）。上游只需 libc + Linux input UAPI 头
（OHOS sysroot 自带 `linux/input.h`、`linux/uinput.h`）。

## 验证结果

下面四行逐字取自上述两份日志（括号内为文件名:行号）：

```bash
[upstream unit suite] registered=86 passed=86 failed=0   # create11.log:161 上游 86 例全部执行并通过
[test] assertions: PASS=41 FAIL=0 SKIP=0   # create12.log:168 test_package 消费者断言（交付 HEAD 上复跑）
MEMCAP[probe] peak=176MB budget=0MB rc=0 用时14.4s   # create11.log:279 整次构建峰值内存（本包 max_rss_mb=176）
MEMCAP[probe] peak=94MB budget=0MB rc=0 用时3.8s   # create12.log:170 复跑 test_package 时峰值
```

消费者断言 40→41 的来源：W4 独立审计指出原探针 `denied()` 把 `ENOENT`/`EPERM`/`ENODEV` 也算 PASS、却在文档里声称『逐例断言 EACCES』，属表述强于实现。整改后 6 个入口逐例断言 `errno==EACCES`（其余 5 例只是把宽松判定收紧，条数不变），净增的 1 条来自新增入口 `stat /sys/class/misc/uinput/dev`⇒ 总数 40→41，与 `create11.log:277` 一致。

探针逐字读数（`test_package` 第 3 层 `probe_input` 的 stdout，逐字粘贴自 `create12.log` 第 128..150 行，未重排列宽、未删 detail 行）：

```
== keyd input-subsystem probe, uid=20020084 euid=20020084 ==
CASE control open /dev/null       rc=3    errno=0   -                        PASS
                                  fd=3
CASE control opendir /dev         rc=0    errno=0   -                        PASS
                                  243 entries listed
CASE stat /dev/uinput             rc=-1   errno=13  Permission denied        PASS
                                  existence undecidable from user space
CASE stat /sys/class/input        rc=0    errno=0   -                        SKIP
                                  mode=0755 (input class directory)
CASE stat /sys/class/misc/uinput/dev rc=-1   errno=13  Permission denied        PASS
                                  existence undecidable from user space
CASE open /dev/uinput (w)         rc=-1   errno=13  Permission denied        PASS
                                  no fd: UI_SET_EVBIT/UI_DEV_CREATE unreachable
CASE open /dev/input/event0       rc=-1   errno=13  Permission denied        PASS
                                  no fd: EVIOCGBIT capability probe unreachable
CASE opendir /dev/input           rc=-1   errno=13  Permission denied        PASS
                                  device discovery sees no keyboards
CASE inotify_init1                rc=3    errno=0   -                        PASS
                                  descriptor created
CASE inotify_add_watch /dev/input rc=-1   errno=13  Permission denied        PASS
                                  hotplug watch on the keyboard directory
SUMMARY pass=9 skip=1 fail=0
VERDICT OK
```

测试数字同源口径（五维账本，与 `test_package/MANIFEST.yml`、`manifest.yaml`、PR 正文一致）：

| 维度 | 数 | 口径 |
|---|---|---|
| `N_static` 上游静态声明 | 86 | `t/*.t` DSL 语料文件去重计数（Makefile 两条入口消费同一批文件） |
| `N_registered` 构建系统注册 | 86 | 单元入口 `bin/test-io t/test.conf t/*.t`（Makefile:113）+ 集成入口 `t/run.sh → t/runner.py -ev *.t`，**同一批 86 例，不重复计入分母** |
| `N_executed` 实际执行 | 86 | 单元入口逐例执行，86/86 通过 |
| 未执行 / 平台受限 | 86 | 端到端集成入口 0 执行：`t/run.sh` 第 5-9 行 `whoami != root` 即 `sudo` 重启自身（本机无 root、无 sudo），且 input 子系统整片 EACCES（问题表 #6/#7），逐字 errno 见本文件问题表 #6/#7 与「探针逐字读数」代码块，86 例语料清单见本节末尾 |
| `N_consumer` 新增消费者 | 41 条断言 / 2 个程序 | `probe_input.c`（内核接口 errno 断言）+ `test_keyd.py`（**执行**已安装 `keyd` 的 CLI/守护/客户端路径并断言；对 `keyd-application-mapper` 只断言存在位与可执行位——它需 root 与真实键盘，故不执行——再断言打包数据面） |

适配后合计 127 ≥ 上游静态 86。

### 上游 86 例语料清单（逐字取自官方 tarball 的 `t/*.t`，与 `N_static` 同源）

altgr-modifier-guard.t, chord.t, chord-disambiguate.t, chord-double.t, chord-hold.t, chord2.t, chord3.t, clear.t, composite.t, composite2.t, composite3.t, composite4.t, control.t, disarm.t, disarm2.t, disarm3.t, layer.t, layer1.t, layer2.t, layer3.t, layer4.t, layerm.t, layout.t, layout-mods.t, layout-mods2.t, layout-seq.t, layout2.t, macro.t, macro-disarm.t, macro-hold.t, macro-hold-1.t, macro-hold-2.t, macro-nested.t, macro-unicode.t, macro-unicode-2.t, meta.t, mod.t, mod2.t, mod3.t, oneshot.t, oneshot+overload.t, oneshot-single-key.t, oneshot10.t, oneshot11.t, oneshot12.t, oneshot14.t, oneshot2.t, oneshot3.t, oneshot4.t, oneshot5.t, oneshot6.t, oneshot9.t, oneshotm.t, oneshotn.t, oneshotn3.t, overload.t, overload-expire.t, overload-expire2.t, overload-nested.t, overload-nested2.t, overload-oneshot.t, overload-same-key.t, overload-swap.t, overload1.t, overload2.t, overload3.t, overload4.t, overload5.t, overload_2.t, overload_2-2.t, overload_3.t, swap.t, swap-oneshot.t, swap-toggle.t, swap2.t, swap3.t, swap4.t, swap5.t, swap6.t, swap8.t, swap9.t, timeout1.t, timeout2.t, toggle.t, toggle-2.t, toggle2.t


## 知识使用记录

- 复用 E237（编译期验证 + 运行期如实降级）、E543（HMDFS 默认 660 需 `chmod +x`）、
  E584（seccomp SIGSYS 假绿家族，用于区分本条不是 SIGSYS）、E386（conan env 脚本 source 顺序）、
  E017 之外的下载面：本包 URL 未走镜像。
- 新增：`DRAFT-keyd-2.5.0-ohos-input-subsystem-mac-invisible`（同 stem `.kv`/`.md` 成对，同一原子 PR）。
  与 hw-1 名下 `DRAFT-libevdev-1.13.7-meson-harmonyos-uapi-header-probe`（构建期 uapi 头探测）
  是**不同机制**，仅以 `similar_to` 互指。
- **未申报** M15（`t/runner.py:197 on_timeout()` + `:204-205 signal.signal(signal.SIGALRM, ...)/signal.alarm(20)`
  的静默失效）：集成入口在本机 0 执行，从未真机撞出该失效模式，按"没撞上不得申报"不写进草稿。

## 注意事项

- keyd 是**需要 root 的输入设备守护进程**。本包交付的是：可正常编译链接的 OHOS/musl ELF、
  上游 86 例单元语料全量通过、100 个布局与手册/示例数据面完整、以及**逐字 errno 断言过的**
  运行期能力边界。守护进程的真实改键行为在 OHOS 非特权会话下不可能工作（`/dev/uinput`、
  `/dev/input/event*` 整片 EACCES），这一点在 PR"已知限制"与消费者测试中同源披露，
  不以"编译通过"冒充"功能可用"。
- 平台任务 7806 声明语言为 `cpp`，上游 2.5.0 实际是 19 个 `.c`（`src/` 下 18 个 + `t/test-io.c`）/ 0 个 `.cpp` 的纯 C 项目，
  构建系统 makefile。语言不匹配证据保留在 `reports/`，由用户对外说明（本包不走"无法适配"赛道）。
- `keyd --version` 输出为字面量 `keyd v2.5.0 ()`：上游用 `git describe` 生成版本尾巴，
  而 release tarball 无 `.git`，故括号内为空。消费者测试断言"三形态互洽"而非具体字符串非空。
- `make -j1`：本包体量小，且设备由多窗口共用，按工作区资源纪律不开并发。
---

**编译结束**: 2026-09-25 11:59
**最终状态**: built
