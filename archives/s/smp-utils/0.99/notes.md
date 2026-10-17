# smp-utils 0.99 adaptation notes

- **Source**: upstream site sg.danny.cz is unreachable from this network, so
  the byte-verified tarball is pulled from the Debian pool mirror
  (`smp-utils_0.99.orig.tar.xz`, SHA256 in `conandata.yml`). The archive
  directory is named `smp_utils-0.99` (underscore), hence `strip_root=True`.
- **License**: BSD-3-Clause — verified directly from the shipped `COPYING`
  file ("Redistribution and use in source and binary forms ...", Copyright
  2006-2009 Douglas Gilbert), not guessed from the sg3_utils family.
- **Build system**: plain autotools with pre-generated `configure`,
  `Makefile.in` and `ltmain.sh`; no autoreconf, no automake/libtool
  `tool_requires`. No external dependencies (the optional
  `AC_CHECK_LIB(smputils1, ...)` in configure.ac falls back gracefully).
- **Zero patches** (three-part approach):
  1. Host detection: bundled 2018 `config.sub` accepts
     `aarch64-unknown-linux-gnu`; passing `--build`/`--host` with that
     triple (native mode, a52dec precedent) avoids `config.guess`, which
     cannot map HarmonyOS `uname` output on CI workers (E007).
  2. E114: `configure` creates its config.status temp dir with
     `umask 077 && mktemp`; on HMDFS the dir is unwritable, so `umask 077`
     is relaxed to `umask 022` via `replace_in_file` before configuring
     (bwm-ng precedent).
  3. Static linkage: `-static` in LDFLAGS plus `--disable-shared`
     (default options) — `libsmputils1.a` and 29 static `smp_*` binaries,
     qemu-direct and RPATH-free (R26 not applicable: not a system lib).
     Note: libtool swallows a bare `-static` found in LDFLAGS (verified:
     bins came out as dynamic PIE with interpreter set), so the final
     link additionally passes libtool's `-all-static` via a make
     command-line override (`LDFLAGS=-static -all-static`); configure
     itself only ever sees the plain `-static`, which clang accepts.
  4. musl compatibility: `lib/mpi_type.h` typedefs `U32` as the
     glibc-only `u_int32_t`, which musl does not provide; `build()`
     swaps it for the fixed-width `uint32_t` (same stdint family
     already used next to it) via `replace_in_file`.
  5. chk_aac_device guard: `fopen("/proc/devices")` returns NULL on OHOS
     (no `/proc/devices`); upstream only guarded the `fprintf` with
     `verbose`, so `verbose=0` fell through to `fgets(NULL)` → SIGABRT
     (exit 134). Fixed the guard to always return on NULL `fp` via
     `replace_in_file` (commit f32fa138b0).
- **Artifacts**: `libsmputils1` installs to `lib/`; the public header
  installs to `include/scsi/smp_lib.h`; `src/Makefile.am` defines
  `bin_PROGRAMS` with exactly 29 `smp_*` tools.
- **Upstream tests**: none. No `tests/` dir, no `TESTS=` in any
  `Makefile.am`; `make check` is the automake no-op (still run in
  `build()` and expected to exit 0 — T009 evidence).
- **Consumer tests (test_package)**: the C consumer links
  `smp-utils::smp-utils` and asserts the exact SMP function
  request/response length table values taken from `lib/smp_lib.c`
  (REPORT_GENERAL 0/6, DISCOVER 2/12), the numeric suffix parser
  (`smp_get_num("2k")==2048`, `"2KB"==2000`, `"0x10"==16`,
  `smp_get_llnum("1m")==1048576`), and `smp_get_page_size()==4096`,
  plus OHOS-specific checks (aarch64 uname, ELF64 `e_machine==0xB7`,
  no `PT_INTERP` => static). The shell smoke test scans the installed
  `bin/smp_*` (no hardcoded list), runs `--version` on each (29
  assertions), `--help` on `smp_rep_general`/`smp_discover_list`, and
  verifies graceful missing-device failure: exit code 92
  (`SMP_LIB_FILE_ERROR`) with the device name in stderr — valid on OHOS
  where no SAS device exists.

## 2026-10-11 — AI 检视 P2/P3 整改轮 (PR !14548, commit 7b66f0b06e)

### 根因
AI 检视报告两类缺陷：
- **P2 (test_consumer.c)**：ELF64 程序头字段解析时，`e_phoff` 为 `Elf64_Off`（8 字节），原代码声明为 `unsigned int`（4 字节）却用 `memcpy(&e_phoff, ..., 8)` 写入，导致栈越界写 4 字节覆盖相邻变量 `e_phentsize`；后续恰好重写该变量致结果「碰巧正确」。OHOS CI 使用 musl（无 FORTIFY_SOURCE）故未触发告警，但在 glibc + `-D_FORTIFY_SOURCE=2` 下会直接中止（rc=134，ASan 报 stack-buffer-overflow）。
- **P3 (test.sh)**：`errout="$("$BIN" /dev/no-such-dev 2>...)"` 赋值从未使用，退出码仍来自 `$?`，属纯可读性问题。

### 处置
1. **test_consumer.c**：字段类型改为与读出宽度等宽，长度改用 `sizeof`：
   ```c
   Elf64_Off  e_phoff = 0;
   Elf64_Half e_phentsize = 0;
   Elf64_Half e_phnum = 0;
   memcpy(&e_phoff, full + 32, sizeof(e_phoff));
   memcpy(&e_phentsize, full + 54, sizeof(e_phentsize));
   memcpy(&e_phnum, full + 56, sizeof(e_phnum));
   for (Elf64_Half i = 0; i < e_phnum; i++) { ... }
   ```
2. **test.sh**：去除无用命令替换赋值，直接调用取退出码：
   ```sh
   "$SMP_BIN_DIR/$tool" /dev/no-such-smp-dev 2>"$SCRATCH/err.txt"
   rc=$?
   ```
3. `readelf` 交叉校验：修复后 `e_phoff=64 e_phentsize=56 e_phnum=13` 与 `readelf -l` 权威值一致；静态二进制 `no PT_INTERP` 断言仍 pass。

### 验证证据
- **本地门禁（WSL 原生盘 /root/ohpcd-work/smp099）**：
  - `conan create` 全绿（L0/L1/L2/L4/L5）
  - test_consumer.c 13 断言全 pass，test.sh 38 断言全 pass，合计 51 断言
  - 产物 `smp_rep_general`：`file` 显示 `statically linked`，`readelf -d` 无 NEEDED
  - 编译零告警（修复前有 `-Wfortify-source: memcpy will always overflow`）
- **CI 门禁（build #81489 触发重建）**：等待 `/rebuild` 后 CI 转绿为证据

### 预防
- `memcpy(&x, p, N)` 里 `N` 与 `sizeof(x)` 不一致即为红线：一律写 `sizeof(x)`，类型名带手册宽度（`Elf64_Off` / `Elf64_Half` / `uint32_t`...）。
- 解析 ELF 等有权威工具的格式，测试必须拿 `readelf` 值做交叉校验；只断言「我解析出的数等于我写死的数」等于自证。
- 交叉编译（musl/无 FORTIFY）不会替你把越界喊出来：给自解析类测试在宿主上并行跑 `gcc -O2 -D_FORTIFY_SOURCE=2` 和 ASan 两条命令行，告警/报告当证据存档。
- test.sh 等 shell 脚本避免无用命令替换赋值（`var=$(cmd)` 且 var 从未使用），直接 `cmd; rc=$?`。
## 2026-10-12 — 管理员复核轮（PR !14548，tip 08f0f0e239）

### 根因（Septest 10-11 12:05 VERDICT=FAIL，唯一 FAIL = rule6）
- rule6：最新提交 f32fa138b0（10-10 18:02）晚于最新 AI 检视（10-04 08:51）→ 检视未覆盖最新提交，提交后须再次 AI 检视。rule1–5/7–13 全 PASS（rule7 CI 通过 #81489、rule9 新增 M=51、rule11 unresolved=0、rule12 鸿蒙特有 6）。
- 伴随意见 ⚠（comment id=193185400，discussion 7a2508c7…）「test_package 需复核」指向 PR 评论中的 AI 检视 P2：test_consumer.c:93 把 8 字节 `e_phoff` memcpy 进 4 字节 `unsigned int`，栈越界写（OHOS musl 无 FORTIFY 不报警，glibc+FORTIFY 下 rc=134 中止）。该 P2 已于上轮 7b66f0b06e 修复，本轮只复核，**零代码改动**。
- 交接时点快照：P2/P3 已修（7b66f0b06e，作者 lxx0329），docs 提交 08f0f0e239（被并发会话以 lkyz 身份记录，T318 形态），CI 四绿：#81489@f32fa138b0（10-10 21:24）、#84919/#85003@7b66f0b0（10-11 23:10/10-12 00:14）、#85048@08f0f0e239（10-12 00:33）。但 10-11 13:30 的 /ai review 只有「正在进行中」回执、12h+ 无结论回填 → 无覆盖 08f0f0e239 的 AI 检视，rule6 仍 FAIL；未解决 discussion 2 条（193185400 Septest ⚠、193187812 AI P2）。

### 处置（零代码改动，过程闭环）
1. **源码复核**：test_consumer.c 已为 `Elf64_Off`/`sizeof` 等宽读法（P2 已修）；test.sh 直接调用 + `rc=$?`（P3 已清）；conanfile.py 零补丁五件套（--build/--host、umask 077→022、-static/-all-static、u_int32_t→uint32_t、chk_aac_device NULL fp guard）与本文档一致。
2. **本地复验**：同源门禁 r3（WSL /root/wt-smp099，`CI_PACKAGES=archives/s/smp-utils/0.99`、`CONAN_PROFILE=ohos-aarch64-wsl`、`zsh ci/conan/build_and_test.sh`）全绿，`GATE_EXIT_CODE=0`（2026-10-12T01:03:23+08:00）。
3. **过程闭环**：本节写回 notes.md → 以 lxx0329 提交并 push（`git push pushfork HEAD:refs/heads/feat/smp-utils-0.99`）→ `/ai review`（覆盖最新提交、清 rule6）→ 等 CI 转绿 → 两条意见按「意见→处置→证据」回帖并 resolve（T430：`PUT comments/<discussion_id>`，`private-token` 小写头）。

### 验证证据（门禁 r3，日志 /root/gate-smp099-r3.log）
- G0 pass、KC pass（0 errors）；JC 检查模式 incremental（13 个文件），Junk Files: 0
- `conan create passed`；L1a test_package executed、L1b 证据在日志、L1c make check 真跑
- test_consumer.c：`pass=13 fail=0`；test.sh：`pass=38 fail=0`；**合计 51/51**
- L1e 负向破坏测试 confirmed（bin/lib/include 移走后 conan test 失败；跑门禁前临时把 wsl profile 放入仓内、跑完删除，L1e 非空壳，T425）
- CI：#81489 / #84919 / #85003 / #85048 均「CI 校验通过」（Conan test_package + L0 + L1 通过）
- P2 反向证据（上轮已做，存档 /root/smp099-p2-ev/）：before.asan 报 stack-buffer-overflow、before.bin glibc+FORTIFY rc=134；after.asan 零报告；readelf 权威值 e_phoff=64 / e_phentsize=56 / e_phnum=13 与自解析一致

### 坑 / 注意（本轮）
- **仓内 profile 只有 ohos-aarch64（设备路径 /data/service/hnp，WSL 不可用）**：本地门禁必须跑前把 `/root/.conan2/profiles/ohos-aarch64-wsl`（指向 /opt/lpk-fixed/clang，Target aarch64-unknown-linux-ohos）拷进 `ci/conan/profiles/`，**提交前删除**。缺失时 build_and_test.sh L315 `if [ -f "$PROFILE_FILE" ]` 静默丢弃 -pr 参数，conan create 回落到 conan default profile，L1e 变空壳通过（T425 复现路径）。
- **worktree 本地身份被并发会话改成 lkyz**：08f0f0e239 因此记成 lkyz 作者。每次提交前重查 `git config user.name` 并重置 `--local` 为 lxx0329/2028594439@qq.com；已推送历史不改写（改 SHA 会让四绿构建全部作废）。
- **/ai review 回执 ≠ 检视完成**：10-11 13:30 触发后只留「正在进行中」一条，12h+ 无结论。判 rule6 是否已清，必须在评论流里找到新的 AI 检视结论评论，不能认回执。

## 2026-10-12 — 收尾轮（PR !14548，HEAD 7dfc9dba06）

### 闭环状态
- **CI**：#85155@7dfc9dba06 全绿（Conan test_package 通过 / L0 通过 / L1 通过，worker CI-018，10-12 01:25）。至此该 PR 绿构建覆盖全部头 SHA：#81489 / #84919 / #85003 / #85048 / #85155。
- **AI 检视**：仍只有「正在进行中」回执（193188311 / 193220064），结论未回填（T483 形态，不重复触发）。结论落地后 rule6 自动清。
- **行级意见 resolve**：对 193185400（Septest ⚠，disc 7a2508c7…）与 193187812（AI P2，disc 074d88bd…）按 T430 姿势 PUT discussion_id，均 403 "You don't have the authority to resolve this."（trace dee5b14a158ad1627c23b40c1d66a159 / 844b 前缀，见回帖），与 T456 一致：fork 提交者对评审位 diff_comment 无 resolve 权限。已按 T456 处置发回执并请评审自行 resolve，不借账号绕过。

### 意见 → 处置 → 证据（逐条）
| 意见 | 处置 | 证据 |
|---|---|---|
| Septest ⚠ test_package 需复核（193185400） | P2/P3 修复已于 7b66f0b06e 落地；本轮零代码改动复核：源码读法核实（Elf64_Off/sizeof）+ 门禁 r3 全绿 + CI #85155 绿 | notes 上一节验证证据；回帖 193220590 |
| AI 检视 P2 e_phoff 越界写（193187812） | 同上修复；反向证据存档 /root/smp099-p2-ev/（before ASan 报 stack-buffer-overflow / rc=134，after 零报告，readelf 权威值交叉校验） | 同上 |
| rule6 FAIL（AI 检视未覆盖最新提交） | /ai review 已触发（10-12 01:09），在途等待结论回填 | 回执 193220064 |

## 2026-10-12 — CI 守护重复派活复核轮（PR !14548）

### 根因
- 派活来源：Septest ⚠「test_package 需复核」（193185400，diff_comment，disc `7a2508c72f3f6de0d99ef597778a9e1b1af3529c`，resolved:false）与 AI P2 e_phoff 越界写（193187812，disc `074d88bd3441de1f138f9a0d24df96d5842e5106`，resolved:false）仍未 resolve —— 上轮（收尾轮）按 T430 姿势 PUT discussion_id 均 403 `You don't have the authority to resolve this.`（T456：提交者对他人 diff_comment 无 resolve 权限），守护对同一未 resolve 意见重复派活。
- 实质整改上轮已闭环：P2/P3 修复（7b66f0b06e）、同源门禁 r3 全绿（51/51 断言，GATE_EXIT_CODE=0）、CI 五绿（#81489 / #84919 / #85003 / #85048 / #85155，覆盖全部头 SHA）、逐条回帖（193220590 / 193221260）。
- rule6 唯一残留：AI 检视结论未回填（10-11 13:30 /ai review 在途 12h+ 无结论，10-12 01:09 重触发被「已有任务正在处理中」拒绝，T483），无覆盖最新提交的检视结论。

### 处置（零代码改动）
1. resolve 重试：两条意见再按 T430 姿势 PUT discussion_id 各一次，回执原样记录进 PR 回帖（T456 处置：403 回执可引用为确证，不伪造 resolve、不删改他人意见，无权限置为已解决时请有权限的评审操作）。
2. `/ai review force`（T482）：!14465 vtgrab 先例 —— force 可打破在途任务楔入状态，立即获「正在进行中」回执；触发覆盖本提交的 AI 检视以清 rule6。
3. push 本 docs 提交后立即 `/rebuild` 触发 CI；CI 结论以 PR 评论流为准，不在本文件回写构建号，避免额外 docs 提交让 rule6 时点再次后移（T483 预防）。

### 验证证据
- 本轮零代码改动：test_package 复核结论与上轮门禁 r3 一致（test_consumer 13 断言 + test.sh 38 断言 = 51/51，日志 /root/gate-smp099-r3.log，2026-10-12T01:03:23+08:00）。
- AI 检视车道横向抽样（2026-10-12 实测）：!14759 有「审查未能完成」失败回执（通道在回填结论，非死队列）；!14465 `/ai review force` 触发成功（回执 193216722「正在进行中」）—— 车道活，force 可用。
- 本轮 CI：push 后 /rebuild 触发，结果见 PR 评论流（CI 校验通过/失败评论）。

## 2026-10-12 — Septest ⚠「test_package 需复核」再复核轮（PR !14548，tip 9e55e60a27）

### 根因
- 派活来源：Septest 行级意见 `193185400`（diff_comment，disc `7a2508c72f3f6de0d99ef597778a9e1b1af3529c`，resolved:false）「⚠ test_package 需复核,详见 PR 评论中的审查结论」。所谓审查结论 = AI 检视报告 `193149901`（10-10 21:26，逐文件确认段明写 `test_consumer.c` P2 栈越界写 + `test.sh` P3 无用赋值）。该意见 10-11 12:05 提出时两处缺陷**尚未修**（修复提交 `7b66f0b06e` 在 10-11 13:2x），故本轮是「复核 + 举证」轮，不是再修一遍。
- 本轮复核中新发现（属 test_package 陈述口径、非代码）：PR 描述「适配后测试用例统计」表**分组不互斥**——
  - 「单元测试 13」的说明只枚举 9 条库 API（13 = 9 API + uname 1 + ELF 3，后 4 条又在「鸿蒙特有 6」里被再计一次）；
  - 「集成测试 32」的说明实列 35 条（29 `--version` + `--help`×2 + 缺设备×4），说明与计数不符；
  - 合计 51 恰好成立只是因为「多算 4 / 少算 4」互相抵消（T475 / T320 同族：分组不互斥 ⇒ 相加虚增/虚减）。

### 处置（本轮零代码改动）
1. **test_package 逐行复核**（按 T430/T475 口径三处对齐）：
   - `test_consumer.c`：取字段类型宽度 = ELF64 布局宽度、读取长度一律 `sizeof(x)`（`Elf64_Off` / `Elf64_Half`）⇒ P2（e_phoff 越界写）已清；`test.sh`：`"$BIN" ... 2>err; rc=$?` 直接取退出码 ⇒ P3（无用赋值）已清。
   - `conanfile.py` 零补丁五件套（`--build/--host`、`umask 077→022`、`-static/-all-static`、`u_int32_t→uint32_t`、`chk_aac_device` NULL fp guard）与本文档开篇一致，无回归。
   - 三处断言计数一致：`test_package/MANIFEST.yml` `assertion_count=51`、本文件 51、PR 描述合计 51。
2. **PR 描述修正**（API `PATCH /pulls/14548`，回读校验）：单元测试 13→**9**、集成测试 32→**36**（补上此前漏写的「安装产物数量≥29 计数×1」）、补全测试范围 bullet 改为 **9+36+6=51**。改后分组互斥、逐条可核（`MANIFEST.yml` 的 `test_package_tests` 列出 23 个条目，其中 test.sh 的 29 个 `--version` 断言在清单里合并为 1 条），合计行仍 51、与上游对比仍 +51；模板字段行/复选框未动。

### 验证证据（本轮，2026-10-12）
- **本地同源门禁 r4**（WSL 原生盘 `/root/wt-smp099`，head `9e55e60a27`；`CI_PACKAGES=archives/s/smp-utils/0.99`、`CONAN_PROFILE=ohos-aarch64-wsl`、`zsh ci/conan/build_and_test.sh`，日志 `/root/gate-smp099-r4.log`）：
  - `GATE_EXIT_CODE=0`（2026-10-12T02:08:28+08:00）；`L0_RESULT=pass`、`L1_RESULT=pass`、`L2_RESULT=pass`（29 个 `smp_* --version` 全 OK）、`L4_RESULT=pass: no patches`、`L5_RESULT=pass: bin/ has content`
  - `smp-utils consumer: pass=13 fail=0`；`[summary] pass=38 fail=0` ⇒ **51/51**
  - L1e：`[sabotage] bin/ / lib/ / include/ moved away` → `[ok] L1e: Negative test confirmed — test genuinely depends on smp-utils`（**不是 `[skip]`**，T411/T425 排除空壳）
  - 跑完 `git status`：`conandata.yml` 仍是官方 URL（无镜像注入残留），`ci/conan/profiles/` 只剩 `ohos-aarch64`（临时 wsl profile 已删）
- **P2 对照取证（本轮重跑，`/root/smp099-p2-r4/`）**：
  - before = `git show 7b66f0b06e^:archives/s/smp-utils/0.99/test_package/test_consumer.c` 的 phdr-walk 段：`gcc -O2 -Wall -Wextra -D_FORTIFY_SOURCE=2` 报 3 处 `-Warray-bounds`（`forming offset [4, 7] is out of the bounds [0, 4] of object 'e_phoff'`），运行 **rc=134（Aborted）**；ASan+UBSan 报 `ERROR: AddressSanitizer: stack-buffer-overflow ... WRITE of size 8`
  - after = 当前文件同段：**零告警、rc=0、ASan 零报告**
  - readelf 交叉校验：自解析 `e_phoff=64 / e_phentsize=56 / e_phnum=10`，与 `readelf -h/-l`（Start of program headers 64、Size 56、Number 10）一致，`no PT_INTERP` assertion PASS
- **PR 描述回读**：`PATCH -> 200`，回读 `len=2365`、`EXACT_MATCH=true`，head SHA 未变（仍 `9e55e60a27`）

### 未闭环项（平台侧，非本包可自决）
- **行级意见 resolve**：对 Septest ⚠（`193185400`，disc `7a2508c7…`）与 AI P2（`193187812`，disc `074d88bd…`）按 T430 正确姿势 `PUT /pulls/14548/comments/<discussion_id>` 仍 **403 `You don't have the authority to resolve this.`**（本轮 trace_id `eb5913c6d69034c7a532a39a4b0e9acb`；`?resolved=true` 变体同 403；`/comments/<disc>/resolve`、`/discussions/<disc>/resolve` 均 404）。根因同 T405/T456：acc3/lxx0329 是 fork 提交者，对评审位的 diff_comment 无 resolve 权限。已按 T405 处置在 PR 发回执请评审自行 resolve，**不借他账号 token（红线）**。
- **rule6**：需一条覆盖最新提交的 AI 检视结论；`/ai review force`（T482）已触发，结论回填即清。
- 本轮 docs 提交后由 `/rebuild` 触发 CI，结果以 PR 评论流为准（不在本文件回写构建号，避免又一次 docs 提交把 rule6 时点后移）。

## 2026-10-12 — 静态链接回归整改轮（PR !14548，父提交 8d632cf0cb）

### 根因（clean 重建下门禁 L1 变红，暴露真实配方缺陷）
- 现象：`/root/gate-smp099-r6.log`（`git clean -fd test_package/` 后重建）test.sh 在静态断言处
  `FAIL smp_rep_general has dynamic deps — NEEDED [libc.so]`，`L1_RESULT=fail`；安装产物
  `smp_rep_general` 为 `pie executable ... dynamically linked, interpreter /lib/ld-linux-aarch64.so.1`。
- 机制：automake 的 `check` 目标会重跑 `all`；本机 clean 重建时确实发生了**二次链接**
  （日志 `libtool: link: /opt/lpk-fixed/clang` 共 **58** 行 = 29 行带 `-static` + 29 行不带）。
  旧配方只在第一次 `make` 上传 `LDFLAGS='-static -all-static'` —— 命令行变量**不跨 make 进程**；
  `make check` 是新进程，重链时只看到 Makefile 里的裸 `-static`（configure 阶段
  `tc.extra_ldflags` 注入），libtool 把裸 `-static` 当自己的选项吞掉 → 动态 PIE。
  这正是 T164 的同一机制，只是当时没覆盖「`check` 触发的重链」与「`install` 重链」路径。
- 为何此前一直「绿」：该二次链接与**重建时序**相关（同机 r5 只出现 29 行链接、未重链，
  且 r5 的 test_package 实际打在缓存包 `smp-u957bec1f180ce` 上）；`git clean` 后的 r6
  触发重链，潜伏缺陷才暴露。也就是说：只有「干净重建且触发重链」的路径才会红，旧配方
  在该路径上不可靠；CI 若未触发重链同样只会「假绿」。

### 改动（最小，仅 `conanfile.py` 一个文件，零补丁）
- `static_make_args = None if self.options.shared else ["LDFLAGS='-static -all-static'"]`，
  把该命令行变量**重复传给每一个 make 调用**：
  - `build()`：`autotools.make(args=static_make_args)` 与
    `autotools.make(target="check", args=static_make_args)`
  - `package()`：`autotools.install(args=static_make_args)`
- shared 路径行为不变（args=None）；未改上游源码、补丁文件、test_package。

### 验证证据（本轮）
- **强制重链对照**（同一构建目录、同一套对象，只切换是否带覆盖；脚本 `/root/relink.sh`，
  构建目录 = r7 的 `.../b/build-release`）：
  - `touch lib/*.lo src/*.o src/*.c` 后 `make`（**不带**覆盖，旧路径）→
    `pie executable, dynamically linked, interpreter /lib/ld-linux-aarch64.so.1`，
    `readelf -d` NEEDED=1（libc.so）；BuildID `c25734bbc20773f8` —— 与 r6 失败产物同一 BuildID。
  - 再 `touch` 后 `make LDFLAGS='-static -all-static'`（新路径）→
    `statically linked`，`readelf -d` NEEDED=0；BuildID `f1b78ff67efbdf3f`。
- **本地同源门禁 r7**（head 含本修复，日志 `/root/gate-smp099-r7.log`，2026-10-12）：
  - `GATE_EXIT_CODE=0`；`L0_RESULT=pass`、`L1_RESULT=pass`、`L2_RESULT=pass`、
    `L4_RESULT=pass: no patches`、`L5_RESULT=pass: bin/ has content`
  - `smp-utils consumer: pass=13 fail=0`；`[summary] pass=38 fail=0` ⇒ **51/51**
  - `ok smp_rep_general has valid ELF type (EXEC)`、`ok smp_rep_general has no NEEDED libs (fully static)`
  - L1e：`[ok] L1e: Negative test confirmed — test genuinely depends on smp-utils`（非 skip）
  - 三条 make 均带覆盖：`make LDFLAGS='-static -all-static' -j32`（L251）、
    `make check LDFLAGS='-static -all-static' -j32`（L412）、
    `make install DESTDIR=... LDFLAGS='-static -all-static' -j32`（L437）
  - 跑完 `git diff` 仅 `conanfile.py` 一处；门禁把 `conandata.yml` 还原为官方 URL 属实
- **P2 对照本轮重跑**（`/root/smp099-p2-r4/harness.c`，`-DOLD_CODE` 只切换修复前/后）：
  - 旧码：`gcc -O2 -D_FORTIFY_SOURCE=2` 有 3 处 `-Warray-bounds`，运行 rc=134
    （`*** buffer overflow detected ***: terminated`）；ASan 报
    `stack-buffer-overflow ... WRITE of size 8`（1 条）
  - 新码：0 告警、rc=0、ASan 0 报告；`/bin/ls` 权威值 `e_phoff=64 / e_phentsize=56 /
    e_phnum=13` 与自解析一致

### 未闭环项（平台侧，非本包可自决）
- **行级意见 resolve**：Septest ⚠ `193185400`（disc `7a2508c7…`）与 AI P2 `193187812`
  （disc `074d88bd…`）按 T430 姿势 PUT discussion_id 仍 **403
  `You don't have the authority to resolve this.`**（本轮 trace `7217d854…` / `c722258a…`；
  `?access_token=` 变体 403 `bd18b039…`）。根因同 T405/T456：acc3/lxx0329 是 fork 提交者，
  对评审位 diff_comment 无 resolve 权限；不借他账号 token、不删改他人意见，已发回执请评审自行 resolve。
- **rule6**：需一条覆盖最新提交的 AI 检视结论；`/ai review force` 结论回填即清。
