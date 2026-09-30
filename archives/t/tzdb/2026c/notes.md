# tzdb 2026c 适配笔记

## 编译环境
- **构建系统**: 纯 Makefile（无 configure；`make` + `make check` + `make install DESTDIR=`）
- **编制日期**: 2026-09-28
- **平台**: arm64-ohos（OpenHarmony PC，真机预检待执行）
- **状态**: built（配方初稿，真机 rule4 门禁通过前不提交）
- **补丁数量**: 0 个 .patch 文件（portability 修复改为配方内子串替换 `_patch_zic_eperm_fallback`，见下；Conan 严格补丁曾因 hunk 行号漂移报 source file is different）

## 上游信息
- **上游**: IANA Time Zone Database 2026c（2026-07-08 发布：Alberta 切永久 -06，Morocco 切永久 +00，zic 整数溢出修复）
- **仓库**: https://github.com/eggert/tz（上游维护者官方仓库，与 IANA 发布同源）
- **源码包**: `https://github.com/eggert/tz/archive/refs/tags/2026c.tar.gz`
- **sha256**: `99fcce3d468fbb94b9395db2d4a83777ffdf7740a1890ba2e52e8ae089cc8e3b`（下载实测）
- IANA 双包哈希备查：tzcode2026c `b1cffc3a…`、tzdata2026c `e4a178a4…`；
  选用 GitHub 单包的原因：统一 Makefile（code+data 同树，避免双 Makefile 覆盖）、
  tar.gz 免 lzip 依赖、CI 对 GitHub URL 自动加镜像 fallback。

## 编译步骤（conan create 全流程）

```bash
conan create archives/t/tzdb/2026c --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 下载 tag 包并 strip_root（顶层 `tz-2026c/`）。

### 2. 构建（build()）
- `make -j1 CC=<conf> AR=<conf> RANLIB=<conf> AWK=<gawk|nawk|awk 功能探测> VERSION=2026c`（R9/R33）
  产出：`zic`、`zdump`、`tzselect`、`libtz.a`、tab 文件。
- AWK 选择依据：上游 Makefile 明示 mawk/busybox awk 不可用，建议 AWK=gawk/nawk；
  配方以 `BEGIN{print 1}` 自测按 gawk→nawk→awk 优选并透传 `AWK=`（now.ck 的 checknow.awk
  是最重的 awk 使用者：getline<文件> + 超长关联键；真机 awk 方言差异会导致
  “identical from now on” 误报）。探测失败回退为 `awk`，不破坏构建。
- `VERSION=2026c` 必需：tar 包内无 `version` 文件且构建目录非 git 仓库，
  不传则 `version`/`version.h` 回退为 `unknown`，导致 `news.ck` 失败且
  `zic --version` 失真。

### 3. 上游测试（build() 内 `make check`，19 .ck）
`check` = check_mild（17）+ back.ck + now.ck：
check_web 4（theory/tz-art/tz-how-to/tz-link，curl 缺失自动跳过）、
check_zishrink 2（posix/right）、其余 11（character-set/white-space/links/
mainguard/name-lengths/news/slashed-abbrs/sorted/tables/ziguard/tzs）。
计数源：全新源码树中 19 个 `.ck` stamp 文件的存在性
（存在=通过，缺失=失败；不做 stdout 字符串计数），打印
`HMBS_UPSTREAM_TEST_RESULT`。失败即抛异常中断构建。

### 4. 打包（package()）
`make install DESTDIR=<package_folder>`（同组 make 变量）暂存：
`usr/bin`（tzselect、zdump）、`usr/sbin`（zic）、
`usr/share/zoneinfo`（REDO 默认 posix_only 编译的单套数据 + tab 文件）、
`usr/lib/libtz.a`、man 页、`etc/localtime`（Factory 默认）、LICENSE→licenses/。

## 依赖
- 零 library 依赖（构建仅需 make/cc/awk/grep/diff，真机工具链提供；check_web 需 curl+外网，缺失自动跳过）。
- 文档工具缺口（真机实测）：`make check` 经 `character-set.ck/white-space.ck → ENCHILADA → MANTXTS → workman.sh`
  需要 `groff` 或 `mandoc+col` 或 `nroff+perl` 三选一；真机三者皆无（`workman.sh: please install groff ...`，
  `make: *** [Makefile:1123: newctime.3.txt] Error 1`，止步 6/19）。
  配方 `_ensure_mantxts_for_check` 在三者皆无时把 9 个 man 源文件原样预置为 `.txt`
  （仅提供文档输入、非空且复用已通过 grep 的源内容；有任一工具时让上游正常生成），19 个 `.ck` 仍真实执行。
- now.ck 单点失败（真机实测 18/19）：`checknow.awk` 报 `zones ... identical from now on`
  （Sydney/Brisbane、Norfolk/Bougainville），即 28 年窗口内两 zone 的 zdump 输出被判相同。
  前轮已证伪两条假设：`AWK=gawk` 生效后仍失败（非 awk 方言）；`./date +%s`=1790640757
  墙钟正常；now.ckd 内 Sydney（904B）与 Brisbane（289B）均为内容不同的常规文件。
  剩余解释是 `-t $now,$future` 范围退化：`future=$((28*366*24*60*60+$now))`=2676067957
  超过 INT32_MAX，若配方 shell 算术为 32 位则回绕成负数，`zdump -i` 退化为单时刻输出
  （2026-09-29 Sydney 与 Brisbane 同为 AEST +10 → 判 identical）；而 zdump.c 源码确认
  `-t` 解析用 `strtoimax`+`time_t`（64 位干净），且无需 `-t` 的 tzs.ck 已通过，
  故优先怀疑配方 shell。上一轮曾试全局 `SHELL=` 覆盖（真机选中 /usr/bin/zsh），
  结果 18/19 跌到 5/19：zsh 缺省不做 POSIX 词拆分，`$(ZIC) $$leap` 等配方展开为单参数，
  报 `Can't open  leapseconds`（注意双空格）、zishrink-right.ck 中断，check_mild 先失败
  导致 now.ck 的 `./date` 根本没编出来——全局换解释器路线已证伪并回退，SHELL 保持
  HMBS 注入的 /bin/sh 不变。本轮改走单点算术路线：配方 `_patch_nowck_future_awk`
  只把 Makefile 中 now.ck 的 `future=$((...))` 一行改写为 `$(AWK) 'BEGIN{printf "%.0f"}'`
  命令替换（数值完全一致，awk 双精度在 2.6e9 精确，无科学计数法），不断言削弱、
  不跳过测试；失败取证保留 shell/python 双算 future、字面量范围 zdump 实测与 now.ckd 普查，
  下轮日志可直接验证 awk 算术是否生效。
  工程教训（2026-09-29）：文件编辑工具会把配方源码里的双美元符塌成单美元符，导致 Makefile 补丁 token 永远 miss、build() 在测试运行前直接抛错；凡涉及 make 转义的补丁必须经 Python（chr(36) 构造）写入，并在落盘后用 repr 逐行核验。
  now.ck 第二阶段曾报 `UTC: no data`（18/19）：上游用两个 `find -type f` 枚举已安装 zone，而无 hardlink 文件系统上 EPERM 回退把 link 装成 symlink，type-regular 过滤静默跳过它们；第二阶段 zone 表里唯一的 link 名恰是 UTC（配方显式追加），故恰好只缺它。配方 `_patch_nowck_find_symlinks` 把两处发现改宽为 regular-or-symlink，zdump 沿 symlink 读到相同字节，断言原样运行；弃用的替代路线是让 zic 回退用 copy，那会改变交付产物布局。

## 适配后测试（test_package，R34）
`test_tzdb.sh <package>` 6 个真实断言：zic/zdump `--version` 含 2026c、
zoneinfo TZif 魔数、Shanghai gmtoff=28800、New York EST/EDT 双规则、
zic 编译自定义 zone 后 zdump 回读（桩二进制无法通过）。
conanfile 打印 `HMBS_TEST_PACKAGE_RESULT`（discovered/passedCount=6）。
运行 cwd 取 HMBS 注入的 TMPDIR（addchain 先例，避 HMDFS getcwd 坑）。

## 补丁说明
- 配方内 `conanfile.py:_patch_zic_eperm_fallback`（portability，无 .patch 文件）：zic 写
  重复内容 zone 文件时先试 `linkat(AT_SYMLINK_FOLLOW)` 硬链接，仅把
  `EXDEV/ENOTSUP` 视为"不支持"并走自带的 symlink/copy 回退；HMBS 真机
  （HMDFS，hardlink 能力 0）以 `EPERM`（Operation not permitted）失败，
  原逻辑直接判致命错误导致 `zishrink-posix.ck` 中断。替换把 `EPERM`
  并入同一回退分支（`dolink` 内一处 `if`），正常文件系统行为不变。
  采用单 token 子串替换并前置校验（缺失主动抛错），替代脆弱 .patch：
  实测 2026c `zic.c:1786` 处 `if (link_errno == EXDEV || link_errno == ENOTSUP)`，
  旧补丁 hunk 头 `-1785,7` 与实际行号差 2 行，Conan 严格打补丁直接报
  `source file is different - b'zic.c'` 中断整个 build()。
- 另见配方 `CFLAGS=-DHAVE_GETTEXT=0`（OHOS 无 libintl 运行时，上游
  Makefile 注明的官方无 gettext 主机方案，`LDLIBS` 无需 `-lintl`）。

## 已知限制
- 真机预检尚未执行：通过数以 HMBS 标记为准，PR 正文待回填。
- `check_web` 依赖 validator.w3.org 外网可达；若真机/CI 出现 curl 在但
  外网不通导致 4 个 .ck 失败，将如实记 environment gap，不跳过整个套件。
- 包内 `usr/lib/libtz.a` 为构建副产物（上游 install 默认安装），头文件
  未随包安装，故 `cpp_info.libs` 留空，消费者以工具 + 数据为主。


## 2026-09-29 symlink-find 1/2 fix
- Symptom: _patch_nowck_find_symlinks raised applied 1/2.
- Root cause: second find spans a make line continuation ("-prune backslash-newline + indent -o -type f ! -name"); literal single-space token "-prune -o -type f !" never matches. First token matched.
- Fix: keep exact first token, match second with whitespace-tolerant regex -o\s+-type f\s+!\s+-name (verified against upstream 2026c Makefile: 2x -type f, 0x -type l; patched widened count 2, old tokens gone). No assertion change.


## 2026-09-29 test_package TZDIR export fix (3rd route)
- Symptom: 06:38 log `[fail] Shanghai zdump exit=0` + `zdump: unknown timezone 'Asia/Shanghai': No such file` while head/-f saw the same path. Previous window/grep routes kept inline `TZDIR=... cmd` prefix, so they failed identically.
- Root cause: inline TZDIR prefix never reached zdump under conanrun-wrapped sh (empty TZDIR lookup -> ENOENT). Plus `if ! cmd` + `$?` always prints exit=0 and bare failing cmd under set -e aborts before capture.
- Fix: `export TZDIR` (plus ls -l proof), file+grep on -c 1985,1995, correct `set +e/cmd/code/set -e` capture; same export applied to New York and round-trip checks. No assertion weakened.

## 2026-09-29 test_package Shanghai cutoff fix (2nd route)
- Symptom: same fingerprint after 1st fix (unbounded -v): upstream 19/19, test_package still stops after 3/6 oks. So the 1st hypothesis (empty 2024,2025 window) was necessary but not sufficient; unbounded output + VAR=$(...)+case matching is suspect (size/silent set -e abort leaves no [fail] line).
- Different route: small deterministic window that DOES contain Shanghai transitions (DST 1986-1991) via -c 1985,1995, streaming through file+grep -q instead of shell-var case match, with explicit zdump exit-code branch and cat of the log so failures are never silent. Still greps real gmtoff=28800 from packaged data, no weakening.

## 2026-09-29 test_package Shanghai cutoff fix
- Symptom: upstream 19/19 passed, test_package stopped after 3/6 oks at Shanghai offset.
- Root cause: `zdump -v -c 2024,2025 Asia/Shanghai` prints zero lines because Shanghai has no transitions in that window (no DST since 1991); `-c` filters verbose output to transitions only, so grep for gmtoff could never match even with `-v`.
- Fix: drop `-c` for Shanghai (`zdump -v Asia/Shanghai`), dumping full history which always contains gmtoff=28800 lines. New York keeps `-c 2024,2025` (has yearly DST transitions). No assertion weakened.

## 2026-09-29 test_package Shanghai fix
- Symptom: upstream 19/19 passed, test_package failed at Shanghai offset with empty output.
- Root cause: zdump prints gmtoff= only in verbose mode (show() v flag, zdump.c); test invoked zdump without -v so needle could never match.
- Fix: run zdump -v -c 2024,2025 Asia/Shanghai with TZDIR and keep stderr (2>&1) for diagnostics; same bounded verbose pattern as the New York check. No assertion weakened (still greps gmtoff=28800 from real packaged data).

## 2026-09-29 test_package absolute-path fix (4th route)
- Symptom: 07:45 log upstream 19/19, test_package still `[fail] Shanghai zdump exit=1 unknown timezone 'Asia/Shanghai': No such file` while `[ -f ]`/`head -c 4`/`ls -l` saw the same file and zdump --version passed. Exported TZDIR (3rd fix) did not survive to zdump under conanrun-wrapped sh.
- Root cause: TZ-name lookup depends on TZDIR env propagation, which conanrun-wrapped sh repeatedly delivers empty for (inline prefix and export both proved ineffective across rounds).
- Fix: pass absolute file paths to zdump (`$TZDIR_DATA/Asia/Shanghai`, `$TZDIR_DATA/America/New_York`, `$ROUNDTRIP/zi/Test/Example`) so no lookup depends on TZDIR; keep export as belt-and-braces. Same packaged binary + same packaged data, same windows/needles (Shanghai -c 1985,1995 gmtoff=28800, NY EST/EDT, round-trip EST); 6 assertions unchanged, no weakening. Round-trip temp dir switched to `mktemp -d` absolute path (also avoids relative-TZDIR cwd sensitivity and the edit-tool `$`-collapse pitfall).
