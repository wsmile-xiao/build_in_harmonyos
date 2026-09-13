# digup 0.6.57 适配笔记

## 编译环境

- 目标环境：HarmonyOS PC / OHOS 6.0 / aarch64
- 构建系统：autotools（上游 release tarball 自带 configure / Makefile.in）
- 编译器：Conan profile `tools.build:compiler_executables.c` 指定的 clang 15（target `aarch64-unknown-linux-ohos`）
- 编译日期：2026-09-11
- 状态：built
- 上游源码：`https://panthema.net/2009/digup/digup-0.6.57.tar.gz`
  sha256 `ef132e277277fc28091e714980db55021272fa5c3a9134968cdeeef28305186e`

digup 是自包含的 C 程序：MD5 / SHA1 / SHA256 / SHA512 / CRC32 全部来自自带
源码，文件表用自带的内侵式红黑树，除 C 库外没有任何外部依赖，因此
`requirements()` 为空，也没有需要裁剪的编译选项。

## 编译步骤

配方在 `build()` 中按上游文档走标准 autotools 流程：

1. `apply_conandata_patches(self)` 应用三个平台补丁（见下节）；
2. `Autotools.configure()`（build folder 内 VPATH 构建，`--prefix=/` 由 Conan 决定）；
3. `make -j1`；
4. `make check -j1` 跑上游 automake 测试套件 `test_rbtree test_digest test_digup`。

`generate()` 只生成工具链，不改写 `configure_args`。本仓库 CI 始终把**同一个**
profile 同时传给 `-pr:h` 和 `-pr:b`（`ci/conan/build_and_test.sh`），
`cross_building()` 为 False，Conan 2.29.1 的 `AutotoolsToolchain` 因此
**不注入** `--host`/`--build`，configure 会自行调用打了补丁的 `config.guess`，
按**原生**构建处理（`build == host`）。实测 configure 日志：

```
checking build system type... aarch64-unknown-linux-ohos
checking host system type... aarch64-unknown-linux-ohos
checking whether we are cross compiling... no
```

（`AutotoolsToolchain.__init__` 的三元组生成被 `if self._is_cross_building:`
包住，其中 `_is_cross_building = not universal_arch and cross_building(self)`；
用同一 profile 的 trip-probe 配方实测 `configure_args` 在
`update_configure_args({"--build": None, "--host": None})` 前后**完全相同**，
即剪枝在同构 profile 下是空操作；把 `-pr:b` 换成异构 profile 才会出现
`--host=aarch64-linux-ohos --build=x86_64-linux-gnu`。此处**刻意不剪枝**：
异构场景下剪掉三元组会让 configure 在构建机上跑 `config.guess` 并静默选到
错误架构；保留注入时补丁 `0002` 已经让 `config.sub` 能接受 Conan 的
`aarch64-linux-ohos` 形态，两种调用方式都能规范化到
`aarch64-unknown-linux-ohos`。）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one` | 设备 `uname -s` 返回 `HarmonyOS`，上游 `acscripts/config.guess`（timestamp 2020-01-01）没有任何 HarmonyOS 分支，主 case 落到 “No uname command or uname output not recognized” 兜底而失败 | 补丁 `0001`：在 config.guess 主 case 中新增 `*:HarmonyOS:*:*` 分支，按 `$UNAME_MACHINE` 归一化机器名并直接 `echo "${MACHINE}-unknown-linux-ohos"`；不调用编译器探测，因此不依赖 `$TMPDIR` 可写 |
| 2 | 只补 `0001` 后，三元组被**静默**规范化成 `aarch64-unknown-linux-gnu-ohos`，configure/make 都不报错 | 该版 `config.sub` 的 ambiguous 三元组列表（`nto-qnx* \| linux-gnu* \| linux-android* ...`）与 OS 列表都没有 `linux-ohos`：`config.guess` 产出的 `aarch64-unknown-linux-ohos` 被规范化为 `aarch64-unknown-linux-gnu-ohos`（`host_os` 变成 `linux-gnu-ohos`，任何 `*-gnu*` 分支都会被错误命中），只有 Conan 传入的无 vendor 段形态 `aarch64-linux-ohos` 才会响亮报 `Invalid configuration ... system 'ohos' not recognized` | 补丁 `0002`：两处列表各加入 `linux-ohos*`；自检命令为 `config.sub "$(config.guess)"` 必须**原样返回** `config.guess` 的输出（不能只看 configure 是否通过——只补 0001 时 configure 一样通过） |
| 3 | `config.status` 报 `could not setup config files machinery` / `./confXXXXXX/subs1.awk: Permission denied` | HMDFS 上 `umask 077 && mktemp -d` 建的临时目录当前进程不可写（E011/E114） | 补丁 `0003`：把 `configure` 内两处 `umask 077` 改成 `umask 022`；configure 生成的 `config.status` 同步恢复正常，无需再单独修它 |
| 4 | 只补 `config.guess` 时该补丁可能不生效 | 该补丁是否被执行取决于 configure 是否收到 `--build`：收到时 autoconf 只用 `config.sub` 规范化该字符串、不调用 `config.guess`（手工传三元组的对照实验：探针版 `config.guess` 被调用次数为 0）。本仓库 CI 传同一 profile 给 `-pr:h/-pr:b`，`cross_building()` 为 False，Conan 不注入三元组，因此 configure 会正常调用 `config.guess`，补丁生效 | 不改写 `configure_args`；由补丁 `0001` 负责 `config.guess` 形态、补丁 `0002` 负责 `config.sub` 同时接受两种输入形态，两条路径都覆盖（见「编译步骤」节） |

`scripts/patch-autotools-ohos.pl` 对本包的 2020-01-01 版脚本不适用：它按新版
config.guess 的 `GUESS=` 风格插入分支，而该版每个分支都是
`echo ...; exit ;;`，插入后主 case 不返回、直接落到 unknown 兜底（实测
`bash acscripts/config.guess` 仍报 unable to guess），config.sub 的三个锚点
（`gnu* | android*`、`android-linux)`、`linux-uclibc`）在该版里也都不存在，
脚本只报 `[warn]` 并以 1/5 分退出。因此本包改为直接写静态补丁并逐个验证。

## 源码修改

补丁均在 `patches/`，全部是平台可移植性补丁，不改动 digup 的业务逻辑：

- `0001-config-guess-harmonyos.patch`：config.guess 新增 HarmonyOS 系统识别（E007）；
- `0002-config-sub-ohos.patch`：config.sub 接受 `linux-ohos` 三元组（E122）；
- `0003-configure-umask-hmdfs.patch`：configure 去掉 `umask 077`（E011/E114）。

补丁已用 conan 实际执行的 patch_ng 库路径复核（`patch_ng.fromfile(...).apply(strip=1, root=...)`），
三个补丁全部 `True`，结果树与探索期验证过的源码树逐字节一致。

## 依赖版本

无。digup 只依赖 C 库；`configure` 探测到的 `strndup` / `asprintf` / `getline` /
`lstat` / `readlink` 在 OHOS 上全部存在（`HAVE_*=1`）。

## 验证结果

```bash
# 1. 原生探索（任务私有源码副本，OHOS clang 15）
./configure --prefix=<prefix> && make -j1 && make check
#    → configure: build system type / host system type 均为 aarch64-unknown-linux-ohos
#    → src/test-suite.log: # TOTAL: 3 / # PASS: 3 / # FAIL: 0

# 1b. 三元组自检（必须原样返回，不能只看 configure 是否通过）
bash acscripts/config.guess                      # → aarch64-unknown-linux-ohos
bash acscripts/config.sub "$(bash acscripts/config.guess)"
#    → aarch64-unknown-linux-ohos（只补 0001 不补 0002 时这里会返回
#      aarch64-unknown-linux-gnu-ohos，而 configure 仍然 rc=0）

# 2. 干净 conan create（设备，OHOS profile，profile 用绝对路径）
conan create archives/d/digup/0.6.57 \
  -pr:h=$HOME/ws/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 \
  -pr:b=$HOME/ws/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 \
  --build=digup/*
#    → Apply patch (portability) ×3
#    → RUN: make -j1 / RUN: make check -j1
#    → PASS: test_digest / test_digup / test_rbtree，# TOTAL: 3 / # PASS:  3
#    → test_package: HMBS_TEST_SUMMARY discovered=21 passed=21 failed=0 skipped=0
```

test_package 不是 print-only：它用已安装的 `bin/digup` 真跑 CLI，断言摘要文件的
具体记录（如 `a948904f...447  a.txt`）、二次校验退出码 0、篡改内容后被
报 `a.txt CHANGED.` 且退出码 1、未知选项退出码 255，覆盖 md5/sha1/sha256/sha512
四种摘要类型。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/digup` | Conan 应用包中的命令行程序 |
| `share/man/man1/digup.1` | 上游 man page（`make install` 安装） |
| `licenses/COPYING` | 上游 GPL-3.0-or-later 许可证 |

## 注意事项

- `configure` / `config.status` 的 `umask 077` 修复只影响临时目录权限，不改
  变任何构建语义；在非 HMDFS 文件系统上同样安全。
- `config.guess` 与 `config.sub` 必须**成对**补齐：只补 `config.guess` 时
  configure 不会失败，但三元组会被静默规范化成 `aarch64-unknown-linux-gnu-ohos`
  （`host_os` 变成 `linux-gnu-ohos`）。自检命令：
  `bash acscripts/config.sub "$(bash acscripts/config.guess)"`
  必须原样返回 `config.guess` 的输出。
- 上游 `make check` 使用 automake 测试驱动，统计单位是**测试程序**（3 条），
  不是内部断言数；取数命令写在 `manifest.yaml` 的 `validation.upstream_tests.command`。
- 本包刻意不改写 `AutotoolsToolchain.configure_args`：同构 profile（本仓库 CI）
  下本来就没有三元组，改写是空操作；异构 profile 下剪掉三元组会让 configure
  在构建机上跑 `config.guess` 并静默选错架构。
