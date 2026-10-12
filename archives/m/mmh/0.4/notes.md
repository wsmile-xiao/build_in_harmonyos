# mmh 0.4 适配笔记

## 编译环境

- 构建系统: autotools（手写 Makefile.in，无 automake；`configure` / `config.h.in` /
  `stamp-h.in` / `sbr/dtimep.c` 为上游 2019 年 autoconf/flex 预生成产物）
- 编译日期: 2026-10-04
- 编译器: OHOS clang 15.0.4（C 语言，`/data/service/hnp/bin/clang`）
- 目标: HarmonyOS PC / aarch64 / OHOS 6.0 / libc++ / cppstd 17
- Conan 2.29.1（OHOS 适配版）
- 源码: `https://marmaro.de/prog/mmh/files/mmh-0.4.tar.gz`
  （sha256 `cda8005bfd490c260d55edd8aa1d90f99a7997daf5e4271a91e423691929108e`，1493406 bytes）

## 编译步骤

```bash
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

配方 build/package 阶段要点：

- `--with-locking=fcntl`：mmh 默认 dot-lock 依赖 `link(2)` 原子创建 `.lock`
  文件，HMDFS 拒绝硬链接（EPERM，真机探针实测）；改用 fcntl 内核锁
  （`F_SETLK`，真机实测可用）。
- `-fcommon`：2019 年版 C 代码依赖 GCC<10 的暂定定义合并语义
  （`char *tmp;` 在 mhbuild.c/mhparse.c 各定义一次、另四处 extern 共享），
  clang≥11 默认 `-fno-common` 会链接期 duplicate symbol。
- `make -j1`：OHOS 上 make jobserver 依赖 mkfifo，HMDFS 不支持，禁并行更稳。
- `make install LN=cp`：`install-lcmds` 用 8 个硬链接造命令别名
  （flists/folders/fnext/fprev/unseen/prev/next/scan），HMDFS 上 EPERM；
  复制语义等价（命令本体按 `argv[0]` 分派）。
- `_freeze_generated()`：补丁应用后把 `configure`/`config.h.in`/`stamp-h.in`/
  `sbr/dtimep.c` 的时间戳统一压到「现在」，使 make 不触发 autoconf/flex
  再生成（宿主工具与 2019 年产物不同代）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始 `config.guess` 在 HarmonyOS 上 rc=1，无法输出三元组 | 2005 年版脚本无 HarmonyOS 分支 | `patches/0001`：新增 `*:HarmonyOS:*:*` 分支（`arm64) MACHINE=aarch64`），输出 `aarch64-unknown-linux-ohos` |
| 2 | `config.sub` 拒绝 `aarch64-unknown-linux-ohos`，或静默规范化成 `...-linux-gnu-ohos` | `maybe_os` 与内核-OS 校验列表均无 `-ohos` | `patches/0002`：4 处补 `linux-ohos*` |
| 3 | 链接失败：`libncurses.a` 不存在 | 制品仓 ncurses/6.6 只提供宽字符库 `libncursesw.a`，mmh 的 tgetent 探测顺序 termcap/curses/ncurses/tinfo 无 ncursesw | `patches/0003`（configure）+ `patches/0004`（configure.ac）：探测顺序补 `ncursesw` |
| 4 | `conan create` 在 `config.status` 阶段失败（临时目录不可写） | HMDFS 把目录 owner 映射为固定 UID，`umask 077` 创建的自有临时目录不可写（E011） | `patches/0003`：`umask 077` → `022` |
| 5 | 首跑全部用例 rc=74 / 命令进入锁等待后失败（表观症状为 context 写入 ENOENT——lockit 重试循环最终 errno 停在 stat 的 ENOENT） | mmh 默认 dot-lock 用 `link(2)` 原子创建 `.lock`，HMDFS 返回 EPERM | 配方 `--with-locking=fcntl`（FCNTL_LOCKING → `lkopen_kernel` 的 `F_SETLK`；无源码补丁） |
| 6 | `refile`/`rcvstore`/`mhstore` 入箱失败 | `folder_addmsg()` 的复制回退只覆盖跨设备错误（EXDEV），HMDFS 的 link EPERM 未覆盖 | `patches/0007`：回退扩展到 `EPERM`/`EOPNOTSUPP` |
| 7 | `make install` 造 8 个命令别名 EPERM 失败 | `install-lcmds` 用硬链接 | 配方安装参数 `LN=cp`（副本，`argv[0]` 分派语义等价） |
| 8 | 构建期 `Permission denied`（rc 126），`make all` 中断于 titles/mh-chart.man7，VERSION 静默变空 | OHOS 内核拒 shebang 脚本 execve；`man/`/`sbr/`/`uip/` 的 Makefile 以反引号直执行 `version.sh`（`man/` 另执行 `gettitles.sh`×4 与 `mh-chart-gen.sh`） | `patches/0005`/`0006`/`0010`：统一改 `sh` 前缀驱动 |
| 9 | 脚本命令入口 `mkdir /tmp/<name>.$$` 直接失败 | OHOS `/tmp` 只读（root:root 0755，真机探针实测不可写） | `patches/0009`（test/setup-test）、`0011`（mhpgp）、`0012`（mhsign）、`0013`（sendfiles）：改 `${TMPDIR:-/tmp}` |
| 10 | 链接期 duplicate symbol（`tmp`） | clang≥11 默认 `-fno-common` 与 2019 年版暂定定义语义冲突 | 配方 CFLAGS 追加 `-fcommon`（复现上游构建语义，非源码缺陷，不落补丁） |
| 11 | `inc`/`scan`/`pick`/`comp`/`forw` 全线 `unable to open format file`（e2e 首跑 8 例全挂的唯一根因） | conan 以 `--prefix=/` + DESTDIR 打包后，format/component 文件（scan.default、pick.default、mhn.defaults、components 等）在包内 `etc/`，而编译期 `NMHETCDIR` 固定为 `/etc`（设备上不存在） | `patches/0008`：`etcpath()` 在编译期路径之前先查 `MMHETC` 环境变量；配方 `runenv_info` 导出 `MMHETC=<包>/etc`（VirtualRunEnv 对消费者自动生效） |

## 源码修改

补丁全部经 `ohc-run.py refresh-patch --auto` 管线生成（R3，per-file-difflib，
`patches_count: 13`），无手工 `.patch`。13 补丁按编号序对 pristine 源码
`git apply -p1` 全部干净应用，结果树与适配树逐字节一致
（工具聚合哈希：orig `6cb42c751c8ff2f1` → work `ba9a5d2e8fc80538`）。

| 补丁 | 目标 | 修改内容 |
|------|------|----------|
| `0001-config.guess.patch` | `config.guess` | 新增 `*:HarmonyOS:*:*` 分支 |
| `0002-config.sub.patch` | `config.sub` | 4 处补 `linux-ohos*`（CPU/内核-OS 组合） |
| `0003-configure.patch` | `configure` | tgetent 探测顺序补 `ncursesw`；临时目录 umask 077→022 |
| `0004-configure.ac.patch` | `configure.ac` | 同步 ncursesw 顺序（与生成物 configure 保持一致） |
| `0005-man-Makefile.in.patch` | `man/Makefile.in` | `version.sh`/`gettitles.sh`/`mh-chart-gen.sh` 改 `sh` 前缀驱动 |
| `0006-sbr-Makefile.in.patch` | `sbr/Makefile.in` | `version.sh` 改 `sh` 前缀（version.o 的 `-DVERSION` 才有值） |
| `0007-sbr-folder_addmsg.c.patch` | `sbr/folder_addmsg.c` | 复制回退 EXDEV → EXDEV/EPERM/EOPNOTSUPP |
| `0008-sbr-path.c.patch` | `sbr/path.c` | `etcpath()` 支持 `MMHETC` 环境变量覆写（conan 包布局定位） |
| `0009-test-setup-test.patch` | `test/setup-test` | 测试套件临时目录改 `${TMPDIR:-/tmp}` |
| `0010-uip-Makefile.in.patch` | `uip/Makefile.in` | `version.sh` 改 `sh` 前缀（各命令编译期版本串） |
| `0011-uip-mhpgp.sh.patch` | `uip/mhpgp.sh` | 临时目录改 `${TMPDIR:-/tmp}` |
| `0012-uip-mhsign.sh.patch` | `uip/mhsign.sh` | 临时目录改 `${TMPDIR:-/tmp}` |
| `0013-uip-sendfiles.sh.patch` | `uip/sendfiles.sh` | 草稿临时文件改 `${TMPDIR:-/tmp}` |

补丁生成与两树哈希由 `refresh-patch --auto`（edit-tracker 精准模式）落盘于
`manifest.yaml` 的 `patch_generation` / `patch_classification` 段。

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| ncurses | 6.6 | 制品仓（OHOS aarch64 二进制） | 静态链接（R26）；仅 `libncursesw.a` 可用 |

## 验证结果

```bash
$ conan create . -pr:h=... -pr:b=...      # rc=0（真机 2026-10-04）
# test.sh 冒烟 4 例 ALL-PASS；test_e2e.sh 端到端 8 例 ALL-PASS
```

- 消费者用例 12/12 全过（冒烟 4 + 完整消费者端到端 8），真机 conan create
  实测全绿（证据：构建日志尾部双 `ALL-PASS`）。
- 上游测试套件 57 例（`test/runalltests` → `runtest` 逐例驱动）真机等效驱动
  全量执行：**TOTAL=57 PASS=49 SKIP=6 FAIL=2**。
  - 2 例 FAIL 均为平台归因：`anno`=用例自造硬链接夹具（`ln`）在 HMDFS 上
    EPERM 不可构造；`rcvstore`=HMDFS 把权限位归一为 0660，`find -perm 0600/640`
    精确匹配必然落空（真机探针实证）。逐例与证据见 `reports/upstream-test-run.md`。
  - 6 例 SKIP 全部合法：缺 valgrind ×1、上游自跳 ×1（"not implemented yet"）、
    缺 UTF-8 locale ×4。
- `verify-build` 四闸门通过：**Verdict PASS**（G1 ✅0/0/0 · G2 ✅0/⚠️1/❌0 ·
  G3 ✅0/0/0 · G4 ✅0/0/0），完整输出见 `reports/quality-report.md`。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/` 40 个命令（34 个 C 程序 + 6 个脚本）与 8 个命令别名 | 别名以 `LN=cp` 副本安装；6 个脚本命令真机调用需 `sh` 前缀（OHOS 内核拒 shebang 脚本 execve） |
| `lib/` 辅助二进制（含 `mmhwrap` 脚本） | 各命令的内部依赖 |
| `etc/` format/component 数据（scan.default、pick.default、mhn.defaults、components 等） | 经 `MMHETC` 定位（0008） |
| `man/`、`licenses/COPYRIGHT` | BSD-3-Clause |

## 注意事项

- `0008`（`etcpath()`/`MMHETC`）是包管理器/cache 布局定位问题，非 OHOS 特有：
  `MMHETC` 未设置时行为与上游完全一致（严格回退到编译期 `NMHETCDIR`）。
- 6 个脚本命令（mmh/mhsign/mhpgp/print-mimetype/sendfiles/whatnow2）与
  `lib/mmhwrap` 在 OHOS 真机需以 `sh` 前缀调用；C 命令不受影响。上游发行包
  即脚本形式安装，适配层不改命令本体。
- 上游测试套件依赖的 ed/valgrind/UTF-8 locale 在真机缺失，属测试环境缺口，
  非配方问题；ed 已以最小实现补齐（驱动差异 D7），其余如实记录为 SKIP。
  驱动差异（D1-D7）与逐例定性见 `reports/upstream-test-run.md`。
- 存档时 `configure` 等生成物的时间戳冻结由配方在 `source()` 之后执行，
  不影响 `export_sources()` 的补丁应用顺序。

## 结束标记

status: closed — 编译与验证均已完成，交付物齐备。
---

**编译结束**: 2026-10-04 16:45
**最终状态**: built
