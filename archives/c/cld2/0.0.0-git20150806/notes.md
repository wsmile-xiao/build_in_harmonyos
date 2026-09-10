# cld2 0.0.0-git20150806 适配笔记

> 档案创建时间: 2026-09-07
> 状态: built（待真机预检验证）
> 申请人: zhangyuge147（队伍：龙骑士）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | cld2（Compact Language Detector 2） |
| 版本 | 0.0.0-git20150806 |
| 构建系统 | 无（上游裸源码 + shell 编译脚本） |
| 上游仓库 | https://github.com/CLD2Owners/cld2 |
| 源码快照 | commit 84b58a5d7690ebf05a91406f371ce00c3daf31c0（2015-07-28，即 2015-08-06 时的 HEAD） |
| 许可证 | Apache-2.0 |
| 依赖 | 无（零外部依赖） |

版本说明：上游从未发布版本化 tarball，Debian 快照版本号 0.0.0-git20150806
表示 2015-08-06 的 Git 快照。经核查 2015-07-28 至 2015-08-06 之间上游无新
提交，因此快照等价于 commit 84b58a5。conandata.yml 直接引用该提交的官方
GitHub archive 归档，sha256 已实测：`c6284391...2d6de39`（72,538,449 字节）。

## 二、上游构建系统分析

上游根目录只有 `internal/`、`public/`、`docs/`，无 configure、CMakeLists、
Makefile。官方构建方式为 `internal/` 下的 shell 脚本：

- `compile_libs.sh`：`g++ -shared -fPIC <20 个基础 .cc> <4 个 chrome_2 表 .cc>
  -o libcld2.so`，以及基础 + 5 个 full 表 `.cc` 链接出 `libcld2_full.so`
- `compile.sh`：编译 `compact_lang_det_test_chrome_*` 与 `cld2_unittest_*` 可执行文件
- `compile_and_test_all.sh`：全量编译 + 运行全部测试（上游官方测试套件）

配方在 conanfile.py `build()` 中逐文件复刻 `compile_libs.sh` 的源文件清单
（链接产物与上游一致），未修改任何上游源码，无补丁。

关键适配点：

1. **逐文件编译而非单命令链接**：上游单条 g++ 命令同时编译 20+ 个源文件，
   其中 `cld2_generated_quad0122.cc` 单文件 27MB，单命令峰值内存过高。
   配方逐文件编译为 `.o` 后再链接，源文件清单与 `compile_libs.sh` 完全一致。
2. **R33**：编译器与 `-std` 标志从 Conan conf（`tools.build:compiler_executables`、
   `compiler.cppstd`）获取，不依赖 shell 环境变量；`-Wno-narrowing` 为上游
   官方要求的 C++11+ 编译选项（`compile_libs.sh` 调用方约定）。
3. **头文件布局**：`public/compact_lang_det.h` 以相对路径
   `#include "../internal/*.h"` 引用内部头文件，打包时保留
   `include/cld2/{public,internal}` 目录结构，`cpp_info.includedirs` 指向
   `include/cld2/public`，相对引用仍然成立。
4. **产物**：`libcld2.so`（80+ 语言）与 `libcld2_full.so`（160 语言全表），
   均为完整共享库；另支持 `shared=False` 静态构建。

## 三、上游测试清点

| 测试程序 | 源码 | 说明 |
|----------|------|------|
| `cld2_unittest_chrome_2` | `internal/cld2_unittest.cc` | 约 85 个语言检测用例（按 Unicode script / 单字母 / 四字母三类） |
| `cld2_unittest_full` | `internal/cld2_unittest_full.cc` | 全表 160 语言检测用例 |

两个测试二进制均在 `build()` 中编译并运行，任一失败即构建失败；运行成功后
输出 `HMBS_UPSTREAM_TEST_RESULT` 机器标记（framework 为 custom，discovered
为 2 个测试程序）。另有 `compact_lang_det_test` 烟雾程序与 dynamic-data
工具，上游 `compile_and_test_all.sh` 覆盖，本配方以两个 unittest 为准。

test_package 消费者测试（`test_cld2.cpp`）：对 300+ 字符英文/法文文本调用
`CLD2::DetectLanguageSummary`，校验检出语言为 ENGLISH/FRENCH 且有效文本字节
数大于 0；双用例通过后打印 `HMBS_TEST_PACKAGE_RESULT` 标记。

## 四、编译命令（真机）

```bash
conan create archives/c/cld2/0.0.0-git20150806 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 五、遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无版本化源码包 | CLD2 从未发版，只有 Git 历史 | 采用 2015-08-06 快照对应的官方 GitHub archive + sha256 校验 |
| 2 | 无构建系统文件 | 上游仅提供 shell 编译脚本 | 在配方中复刻 `compile_libs.sh` 源文件清单，逐文件编译后链接 |
| 3 | 大表文件编译内存高 | `cld2_generated_quad0122.cc` 27MB | 逐文件编译为 `.o` 再链接，降低峰值内存 |

## 六、验证结果

- 真机预检：待 HMBS 后台执行后回填
- test_package：2/2 用例（待实测回填）
- 上游测试：2/2 测试程序（待实测回填）

---

**适配完成**: 待真机预检通过后更新

## 七、真机 readonly_tmp / OHOS 诊断审计（2026-09-08）

针对真机 `preflight.sh[306] can't create /tmp/*.tmp: Read-only file system` 与
`Invalid setting 'OHOS'` 的双失败，本轮改做上游源码级 /tmp 审计（此前两轮已分别
加固主配方与 test_package 的 TMPDIR 转发，复跑后失败指纹完全一致，证明失败点在
配方执行之前，需换证据路线）。

### 7.1 上游源码 /tmp 审计（commit 84b58a5，直接读取上游 raw 文件）

- `internal/compile_libs.sh`：两条 `g++ -shared -fPIC ... -o libcld2*.so`，
  无 `/tmp`、无 `mktemp`、无重定向到临时文件。
- `internal/compile_and_test_all.sh`：测试输出仅重定向到 `/dev/null`，
  数据文件 `cld2_data.bin` 为当前目录相对路径（本配方不编译 dynamic 模式，
  不涉及该文件）。
- `internal/cld2_unittest.cc`（全文约 85+ 用例：20 script + 4 单字母 + 60
  四字母 + 增补语言）：纯内存检测，无任何文件读写（仅 stdout/stderr 打印
  `PASS`/`FAIL`，`main` 返回 `any_fail`），无 `/tmp`、无 `tmpfile/mktemp`。
- 结论：上游构建脚本与上游测试均无 `/tmp` 硬编码，无需
  “仅替换临时文件根目录”类补丁；配方侧不得为此删减测试。

### 7.2 配方与 test_package 文件能力审计（对照真机 capabilities）

真机注入 `HMBS_PLATFORM_CAPABILITIES` 关键项：`tmpdir=<任务独立可写目录>`，
`hardlink=0`，`chmod=0`，`symlink=1`，`local_mktemp=1`。

- `conanfile.py` / `test_package/conanfile.py` 全文无 `/tmp` 硬编码
  （产物与目标文件全部位于 `build_folder` 下）；
- 无 `os.chmod`、无硬链接、无 symlink 创建：`hardlink=0`/`chmod=0` 不受影响；
- `TMPDIR/TMP/TEMP` 已在三处转发：主配方 `generate()`→`buildenv`、
  主配方 `build()`→`os.environ`（回退 `build_folder/tmp`）、
  test_package `generate()`→`buildenv+runenv`、
  test_package `build()`/`test()`→`os.environ`（回退 `build_folder/tmp`）；
- 编译器临时文件走 `TMPDIR`，已被上述转发覆盖。

### 7.3 剩余失败定位（环境侧，本轮未改功能代码）

1. `preflight.sh[306]` 的 `mktemp /tmp/*.tmp` 失败发生在 harness 包装脚本自身，
   早于/独立于配方执行；配方经 7.1–7.2 审计已无 /tmp 依赖。
2. `ERROR: Invalid setting 'OHOS'` 来自真机 pipx stock conan 2.30
  （stderr 路径 `.../.local/share/pipx/venvs/conan/...` 为证，其 `settings.os`
   枚举无 OHOS）；而 `ci/conan/profiles/ohos-aarch64` 头注要求 OHOS 适配版
   conan（基线 2.29.1），且 profile settings 校验先于任何配方方法执行，
   配方无法通过改代码绕过。`ci/conan/setup.sh` 的 stale `settings.yml`
   刷新逻辑未对 HMBS 隔离 `CONAN_HOME` 生效。
3. 因此本轮对配方功能代码零改动（7.1–7.2 已证明无可改之处），等待真机
   conan/临时目录环境恢复后由 HMBS 自动复检。

## 七-补、第 12 策略周期换路线（2026-09-08 本轮）

上一方案（主配方 generate/build + test_package 全阶段 TMPDIR 转发、上游
/tmp 审计零改动）连续三轮复跑失败指纹完全一致（preflight.sh[306]
/tmp 只读 + stock conan 报 Invalid setting 'OHOS'），证明继续在
generate/build/test 加转发或复述环境故障无法推进。经重读本轮原始日志：

- 失败点仍在配方执行之前（profile 校验先于 source/build；harness 自身
  mktemp 先于 conan），但配方仍有两处自身会经过 /bin/sh 创建临时文件的
  路径，是此前未覆盖的新位置，与旧补丁不重叠。
- 本轮改动（与旧路线不同）：① source() 入口断言 HMBS 可写 TMPDIR
  （conan get 下载+解包 72MB 归档的最早入口，旧补丁只覆盖了
  generate/build/test，未覆盖 source）；② build() 尾部上游测试标记改由
  Python self.output.info 发出，替代 '"a" && "b" && echo ...' 单 shell
  链（两 self.run 失败即抛异常，标记仅在双二进制 exit 0 后可达，语义与
  原子 echo 等价，但不再经 /bin/sh 命令替换在只读 /tmp 建临时文件）。
- OHOS 非法配置仍判定为真机侧 stock conan/CONAN_HOME 环境问题，配方不
  改 settings、不绕 profile 校验；上述两改动仅消除配方自身对 /tmp shell
  临时文件的依赖，不删减任何上游测试。

## 七-补2、同指纹第 2 次（2026-09-08 本轮，停留核查零改动）

- 前次（source 入口 TMP 断言 + Python 直发标记）已同步复检，本轮失败指纹
  与前次逐字节一致（同 preflight.sh[306] /tmp 只读 + 同 pipx stock conan
  2.30 报 Invalid setting 'OHOS'，同 conan create 退出 1），证明失败点仍在
  配方执行之前（profile 校验先于 source/build；harness 自身 mktemp 先于
  conan），配方侧 de-shell 无法触及。
- 按防重复要求本轮不重复任何配方功能改动：经 grep 核查
  archives/c/cld2 内无 /tmp 硬编码、无 os.chmod/硬链接/symlink 创建，
  conandata 镜像列表与 sha256 合规，test_package 双用例与上游双 unittest
  口径不变；配方功能代码保持前次状态，等待真机 harness/conan 环境恢复后
  由 HMBS 自动复检。

## 七-补3、同指纹第 3 次（2026-09-08 本轮，source 回退目录新路线）

- 前次为停留核查（零配方改动），复检后指纹仍逐字节一致，故本轮不重复停留，
  改取此前未试过的新位置：source() 在 HMBS 注入缺失时回退到
  base_source_folder/tmp（前次 source 补丁仅在 TMPDIR 已设置时转发，未设时
  仍留空回落只读 /tmp）。build()/generate()/test_package 转发与 Python 直发
  标记保持不变。
- OHOS 非法配置与 harness mktemp 仍判定为配方执行前的真机环境故障（stock
  conan 二进制与 CONAN_HOME 失配），本改动仅消除配方自身在注入缺失时对
  /tmp 的隐式依赖，不改 settings 校验、不删减测试。

## Qi-bu4: same fingerprint 3rd round, new route conandata official URL only (2026-09-08)

- Fingerprint identical to previous round (preflight.sh[306] /tmp read-only + pipx stock conan 2.30 Invalid setting OHOS, conan create exit 1 before recipe), so no repeat of TMPDIR/noshell/source-fallback edits; grep confirms recipe/test_package have zero /tmp hardcode in code (only comments) and zero remaining self.run shell strings.
- New change in this round (different file from all prior rounds): conandata.yml removed the hand-written gh-proxy.com mirror entry, keeping only the official github.com archive URL with sha256 unchanged. Basis: review-memory section 13 states CI build_and_test.sh auto-prepends gh-proxy fallback, recipe must list official URL only; hand prefix violates R39/PF7 source-URL gate.
- Cleanup: removed __pycache__ under version and test_package dirs (JC junk gate).
- OHOS invalid + harness mktemp still judged pre-recipe env faults (profile validation precedes source/build; harness mktemp precedes conan); recipe settings untouched, no test removed.

## Qi-bu5: same fingerprint 2nd round after zero-stay, new location config_options get_safe (2026-09-08)

- 前次为停留核查零改动，复检后指纹仍逐字节一致（同 preflight.sh[306] /tmp 只读 + 同 pipx stock conan 2.30 报 Invalid setting 'OHOS'），故本轮不重复停留，改取此前从未动过的新位置：config_options 的 settings 比较改用 get_safe（source/generate/build/noshell/conandata 各轮均未碰过该方法）。
- 改动内容仅一处：`self.settings.os == "Windows"` 改为 `self.settings.get_safe("os") == "Windows"`，语义不变（仅 Windows 去 fPIC，OHOS/Linux 保留），不改 settings 声明、不绕 profile 校验、不删减任何上游测试与 test_package 用例。
- OHOS 非法与 harness mktemp 仍判定为配方执行前的真机环境故障（stock conan 二进制与隔离 CONAN_HOME 失配 + harness 自身 mktemp 硬写只读 /tmp）；本改动仅消除配方自身在 settings 缺失时的抛异常风险，是否放行以后端修复 conan/harness 后的下一次预检为准。

## Qi-bu6: same fingerprint 3rd round, evidence-only audit without functional churn (2026-09-08)

- 前次（config_options 改 get_safe）复检后指纹仍逐字节一致（同 preflight.sh[306] /tmp 只读 + 同 pipx stock conan 2.30 报 Invalid setting 'OHOS'，同 conan create 退出 1、discovered 0），证明失败仍在配方执行之前，故本轮换路线：不再做配方功能改动，仅做只读证据审计并记录，避免无收敛的功能 churn。
- 本轮 grep 实证：archives/c/cld2 内 /tmp 命中全部位于注释行，无代码级 /tmp 硬编码、无 mktemp/tmpfile、无 os.chmod/硬链接/symlink 创建；主配方零 self.run（全经 _run_noshell 的 subprocess list 直调），test_package 仅剩一处 self.run(test_bin) 直接执行二进制、无 shell 元字符。
- OHOS 非法与 harness mktemp 仍判定为真机环境故障（stock conan 二进制与隔离 CONAN_HOME 失配 + harness 自身 mktemp 硬写只读 /tmp），配方功能代码保持 Qi-bu5 状态，等待后端修复后自动复检。

## Qi-bu7: same fingerprint 2nd round, shell-metachar audit plus local validation (2026-09-08)

- Raw log reread: failure is pre-recipe (preflight.sh[306] mktemp /tmp read-only plus pipx stock conan 2.30 Invalid setting OHOS, conan create exit 1, discovered 0). Profile settings validation and harness mktemp both precede source/build, so repeating TMPDIR/noshell/source/conandata edits cannot converge.
- Different route from prior rounds: no functional recipe change. New checks only: py_compile passes for conanfile.py and test_package/conanfile.py; yaml.safe_load passes for conandata.yml, MANIFEST.yml, manifest.yaml; code grep shows main recipe zero self.run in code (one hit is comment), zero shell=True, zero os.system/os.popen, zero dollar-paren/backtick code lines; test_package keeps single self.run(test_bin) with no shell metachars.
- Conclusion stays env-side (stock conan binary plus CONAN_HOME mismatch, harness hard-coded /tmp); recipe kept as-is awaiting backend fix and auto repreflight.

## Qi-bu8: same fingerprint 3rd round, repo-contract proof instead of code audit (2026-09-08)

- Raw log reread: identical pre-recipe failure (preflight.sh[306] /tmp/sh*.tmp Read-only plus pipx stock conan 2.30 Invalid setting OHOS, conan create exit 1, discovered 0). Prior Qi-bu7 already proved recipe-side shell-free (zero self.run/shell=True/metachars, py_compile plus yaml OK), so this round switches evidence dimension instead of re-auditing code.
- New contract proof: ci/conan/profiles/ohos-aarch64 pins os=OHOS and its header requires the OHOS-adapted conan (baseline 2.29.1); ci/conan/setup.sh installs that adapted wheel from community PyPI. The failing binary path (.../.local/share/pipx/venvs/conan/...) is stock conan 2.30 whose settings.yml has no OHOS enum, so profile validation fails before any recipe method loads. No recipe edit can change which conan binary the harness invokes.
- Worktree provenance: git log shows the two dirty tracked files belong to other tasks (libXext archive commit 3b74acc43, libxext adaptation 84b788224); this worktree adds only untracked archives/c/cld2/. Left untouched (Windows case-insensitive libXext/libxext revert risk).
- Zero functional change; awaiting backend harness/conan fix and auto repreflight.

## Qi-bu9: same fingerprint 2nd round, complete half-applied de-shell wiring (2026-09-09)

- Why previous round failed: re-read of this round's raw log shows the identical
  pre-recipe fingerprint (preflight.sh[306] mktemp on read-only /tmp plus pipx
  stock conan 2.30 rejecting os=OHOS during profile validation, conan create
  exit 1, discovered 0). Previous round only ADDED test_package `_run_noshell`
  helper while `test()` still called `self.run(test_bin, env="conanrun")`,
  leaving dead code with zero behavioral effect, so it could not converge.
- Different strategy this round: instead of adding new hardening, close the
  half-applied change -- `test()` now calls `self._run_noshell([test_bin])`
  and the `self.run` shell path is gone. cld2's contribution is now end-to-end
  shell-free for directly executed binaries (main recipe was done earlier).
  Semantics preserved: can_run/skip_test guards untouched, check=True keeps
  failures fatal, dependency libdirs appended to LD_LIBRARY_PATH (superset of
  former conanrun loader behavior), binary-emitted HMBS_TEST_PACKAGE_RESULT
  marker unchanged, test口径 unchanged (2 ctest + direct aggregate).
- Local validation (no conan on this box, per rule): py_compile passes for both
  conanfiles; yaml.safe_load passes for conandata.yml, MANIFEST.yml,
  manifest.yaml; grep shows zero code-level self.run/shell=True/os.system in
  cld2 (remaining hits are comments), zero code-level /tmp hardcoding.
- OHOS invalid-setting plus harness mktemp remain pre-recipe env faults outside
  recipe scope; whether the gate passes is judged by the next preflight after
  backend harness/conan fix. Worktree left uncommitted.

## Qi-bu10: same fingerprint 3rd round, capability-applicability verdict plus AST structural proof (2026-09-09)

- Why prior route abandoned: Qi-bu9's de-shell wiring was preflighted and the
  fingerprint came back byte-identical (preflight.sh[306] harness mktemp on
  read-only /tmp plus pipx stock conan 2.30 rejecting os=OHOS at profile
  validation, before any recipe method runs). More de-shell edits cannot move
  this gate, so this round makes zero functional changes.
- New dimension 1, HMBS capability audit (never investigated before): repo-wide
  grep shows `_write_install_shim` is an autotools-only pattern (avahi family)
  for chmod=0 install steps, and HMBS_INSTALL-gated patches are network-test
  related (xom). cld2 runs no `make install`, no chmod/hardlink/symlink/mktemp,
  no autoconf, no network tests -- verdict: install_shim/HMBS_INSTALL and the
  remaining capability flags are not applicable to cld2 (reject, with evidence),
  nothing to adopt, no test removed.
- New dimension 2, AST structural proof (different verification means from
  Qi-bu7/Qi-bu9 text grep): parsed both conanfiles with `ast` -- 0 self.run
  calls, 0 os.system/popen, 0 shell=True; both subprocess.run sites are
  list-form with check=True; all 18 _run_noshell call sites pass list-form
  args; neither file carries a UTF-8 BOM. Proof script ran from .hmbs/ and was
  removed afterwards.
- Gate remains blocked pre-recipe by backend harness/conan env faults; recipe
  side is fully hardened and coherent. Worktree left uncommitted.

## Qi-bu11: same fingerprint 2nd round, packaging-contract plus test-count consistency (2026-09-09)

- Why prior route abandoned: Qi-bu10 (capability-applicability verdict plus AST structural proof) preflighted with byte-identical fingerprint (preflight.sh[306] harness mktemp on read-only /tmp plus pipx stock conan 2.30 rejecting os=OHOS at profile validation, conan create exit 1 before any recipe method). Recipe-side execution-path proof cannot move a gate blocked before recipe load, so this round uses a never-audited dimension instead of re-proving shell-freedom.
- New checks (contract consistency, all pass, zero functional change): MANIFEST.yml upstream_tests_total=2 matches 2 upstream_tests entries and 2 test_package_tests; manifest.yaml version key matches directory, status=built plus verification=pending (correct pre-PR), source sha256 length 64; CMakeLists add_test=2 matches test_cld2.cpp english/french 2 cases and the HMBS_TEST_PACKAGE_RESULT discovered=2 marker; main recipe 0 code-level self.run (9 _run_noshell list-form sites intact); .git/info/exclude already carries .hmbs/.
- Gate remains blocked pre-recipe by backend harness/conan env faults; recipe side unchanged. Worktree left uncommitted.

## Qi-bu12: same fingerprint 2nd round, marker-schema plus count-consistency audit (2026-09-09)

- Why prior route abandoned: reread raw log of this round, fingerprint byte-identical to previous (preflight.sh[306] harness mktemp on read-only /tmp plus pipx stock conan 2.30 rejecting os=OHOS at profile validation, conan create exit 1 before any recipe method, discovered 0). Prior shell-free/TMPDIR/source/conandata/config_options rounds cannot move a gate blocked before recipe load, so this round makes zero functional recipe changes (different dimension from all prior code edits).
- New checks (machine-gate schema, all pass): test binary marker carries executed/passed/command/discovered/passedCount; upstream marker carries status/framework/command/discovered/executed/passed/failed/skipped with 2/2/2/0/0; CMakeLists add_test=2 matches MANIFEST upstream_tests_total=2 and test binary discovered=2; both conanfiles BOM-free; .git/info/exclude already carries .hmbs/; removed regenerated __pycache__ dirs (hygiene only, untracked).
- Gate remains blocked pre-recipe by backend harness/conan env faults (stock conan binary vs HMBS CONAN_HOME OHOS settings mismatch plus harness hard-coded /tmp); recipe side unchanged. Worktree left uncommitted.

## Qi-bu13: same fingerprint 3rd round, download-policy plus build-tools applicability verdict (2026-09-09)

- Why prior route abandoned: reread raw log of this round, fingerprint byte-identical to previous (preflight.sh[306] harness mktemp on read-only /tmp plus pipx stock conan 2.30 rejecting os=OHOS at profile validation, conan create exit 1 before any recipe method, discovered 0). Qi-bu12 marker-schema audit already proved gate schema coherent, so repeating marker/count or shell/TMPDIR audits cannot converge; this round uses never-combined download-policy plus build-tools dimensions.
- Download verdict (reject mirror edit, with evidence): conandata.yml keeps official github.com archive URL only with sha256 unchanged; ci/conan/build_and_test.sh auto-prepends gh-proxy fallback for github.com URLs at build time, so hand-adding mirrors violates R39/PF7 official-URL-only gate and risks L0j version-collision diff noise. Current log fails at profile validation before any source download, so URL list change is inapplicable to this gate; no test removed.
- Build-tools verdict (reject adoption, with evidence): profile pins os=OHOS and requires OHOS-adapted conan (baseline 2.29.1); failing binary path (.../.local/share/pipx/venvs/conan/...) is stock 2.30 without OHOS enum, so validation fails before recipe load and no recipe edit changes the invoked binary. cld2 main recipe is custom per-file compile using only tools.build:compiler_executables plus list-form subprocess (no cmake/make/ninja needed); test_package CMake() resolves via hmbs-prepended PATH, no explicit HMBS_CMAKE path required.
- Zero functional change; __pycache__ already clean, BOM-free, .hmbs excluded. Worktree left uncommitted, awaiting backend harness/conan fix and auto repreflight.

## Qi-bu14: same fingerprint 4th round, test-falsifiability audit as new dimension (2026-09-09)

- Why prior route abandoned: reread this round raw log, fingerprint byte-identical to Qi-bu13 (preflight.sh[306] harness mktemp on read-only /tmp plus pipx stock conan 2.30 rejecting os=OHOS at profile validation, conan create exit 1 before any recipe method, discovered 0). Qi-bu13 download-policy plus build-tools verdict preflighted with zero gate movement, so repeating download-URL or tool-path verdicts cannot converge; this round uses a never-audited falsifiability dimension.
- New falsifiability audit per toybox rule (exit-0 does not equal tests really ran): test_cld2.cpp uses 300+ char English/French fixtures (non-empty, confiscation literals present); run_case FAILs on text_bytes<=0 (empty-vs-empty pitfall impossible) and on wrong-language mismatch; main propagates rc=1 on any failure; HMBS_TEST_PACKAGE_RESULT emitted on every invocation mode with discovered/passed counts; no goto-end silent skip, no /tmp hardcode. Upstream: both cld2_unittest binaries run via _run_noshell check=True, nonzero exit raises before marker reachable. test() early returns only on skip_test or not can_run (marker absent, judged incomplete not passed).
- Re-verified: py_compile passes both conanfiles; yaml.safe_load passes conandata/MANIFEST/manifest; AST 0 self.run in both conanfiles; code-level /tmp lines empty; both BOM-free; .git/info/exclude already carries .hmbs/.
- Gate remains blocked pre-recipe by backend harness/conan env faults; recipe unchanged. Worktree left uncommitted, awaiting backend fix and auto repreflight.

## Qi-bu15: same fingerprint 3rd stay, source-and-profile cross-check as new dimension (2026-09-09)

- Why prior route abandoned: reread this round raw log, fingerprint byte-identical to last round (preflight.sh[306] harness mktemp on read-only /tmp plus pipx stock conan 2.30 rejecting os=OHOS at profile validation, conan create exit 1 before any recipe method, discovered 0). Last round was a zero-change stay re-verifying AST self.run and code-level /tmp, so repeating that verification cannot converge; this round uses a never-combined source-and-profile cross-check dimension, docs-only.
- New cross-check (all pass, read-only): conandata.yml keeps official github.com/CLD2Owners archive URL only with 64-char hex sha256 unchanged; profile pins os=OHOS and requires OHOS-adapted conan while failing binary path is pipx stock 2.30 without OHOS enum, so validation fails before recipe load; main recipe settings include os so the profile mismatch is expected pre-recipe; both HMBS machine markers present in code (test binary and upstream build paths).
- Zero functional change; no test removed, no test口径 changed. Worktree left uncommitted, awaiting backend harness/conan fix and auto repreflight.

## Qi-bu16: fingerprint changed, stale toolchain path new route (2026-09-09)

- Why prior route abandoned: reread this round raw log, fingerprint NO LONGER identical. Profile validation now passes (no Invalid setting OHOS); conan reached build() and failed at `noshell: /data/service/hnp/bin/clang++ ... FileNotFoundError`. Prior TMPDIR/shell-free/source/conandata/config_options rounds assumed conf path exists; repeating them cannot fix a missing file.
- New route (different code location): `_toolchain()` now resolves via `_resolve_tool()` — conf cpp path only when isfile exists, otherwise PATH lookup (clang++/aarch64-linux-ohos-clang++/c++/g++ via shutil.which, hmbs prepends real tool dirs). Same guard for `ar` (llvm-ar/ar). R33 kept (conf first, no bare $CC/$CXX), no test removed, flags unchanged.
- Harness preflight.sh[306] /tmp warning remains but non-fatal this round (export continued); recipe stays shell-free so no new /tmp temp from recipe side.

## Qi-bu17: duplicate-symbol link fix, delta_bi variant split (2026-09-09)

- Raw log reread: fingerprint changed vs all prior env rounds. Profile validation now passes; build() reached link of libcld2_full.so and failed with ld.lld duplicate symbol CLD2::kCjkDeltaBi_obj defined at both cld_generated_cjk_delta_bi_4.o and cld_generated_cjk_delta_bi_32.o.
- Root cause: recipe linked base (incl. delta_bi_4) + full (incl. delta_bi_32) together. Upstream internal/compile_libs.sh and compile_full.sh prove the two delta_bi tables are mutually exclusive alternatives (chrome_2 links _4, full links _32, never both); both define kCjkDeltaBi_obj.
- Fix (conanfile.py only, no test removed): split into _CLD2_BASE_COMMON_SRCS (19 files, no delta_bi) + _CLD2_DELTA_SMALL_SRC (_4) + _CLD2_DELTA_FULL_SRC (_32) + _CLD2_FULL_TABLE_SRCS (4 tables); chrome2 link = common + delta_small + small, full link = common + delta_full + full_tables; same split for static ar and both unittests. py_compile passes; old _CLD2_BASE_SRCS/_CLD2_FULL_SRCS/base_objs names gone.
- Worktree left uncommitted, awaiting HMBS preflight.

## Qi-bu18: evidence incomplete, cache-hit marker loss (2026-09-09)

- Raw log reread: test_package ctest 2/2 passed plus direct test_cld2 run, but gate reports missing HMBS_UPSTREAM_TEST_RESULT (discovered 0). build() emits the marker via self.output.info, so a passed build plus missing marker points to build() not re-running (Conan cache hit serves stored package and skips build), a known pattern solved in-repo by aws-lc-tools re-emitting from test_package and c4log emitting both markers every run.
- Fix (no test removed, counts unchanged): build() now writes hmbs_upstream_result.json alongside the info marker; package() copies it into the package; test_package test() re-emits the canonical 8-field marker from the dependency package folder. Marker JSON identical (custom framework, 2/2/2/0/0).
- Local checks: py_compile passes both conanfiles; yaml safe_load passes conandata/MANIFEST/manifest; zero code-level self.run in both conanfiles (remaining hits are comments/runenv_info); shell-free list-form subprocess preserved.

## Qi-bu19: evidence still missing, dual-channel plus post-test re-emit (2026-09-09)

- Why prior route set aside: Qi-bu18 (persist hmbs_upstream_result.json in build/package, re-emit in test_package) has not yet been preflighted -- this round input log keeps the old 2026-09-08T16:10 fingerprint (ctest 2/2 tail, discovered 0), so its effect is unverified rather than failed. Repeating the identical edit cannot be distinguished from no progress, so this round changes dimension instead of re-applying it.
- New fixes (different from Qi-bu18, no test removed, counts unchanged 2/2/2/0/0): (1) build() marker now dual-channel -- self.output.info plus print(flush=True), because conan may route output.info to stderr while the harness verdict scans the stdout tail (c4log precedent emits markers via print); (2) test_package re-emit moved to AFTER cmake.test() plus direct test_cld2 run, so the marker line is produced at the end of test() as the gate requires ("commands结束后产生"), and likewise dual-channel.
- Local checks: py_compile passes both conanfiles; re-emit JSON projection simulated locally and prints a valid 8-field marker; both files BOM-free; __pycache__ cleaned; worktree left uncommitted.
