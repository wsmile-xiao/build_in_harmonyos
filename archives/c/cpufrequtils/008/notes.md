# cpufrequtils / 008 — 适配记录

> 任务 14913 · 分支 `feat/cpufrequtils-008` · 构建机 HarmonyOS PC aarch64（B 机）
> 记录日期 2026-10-06。

## 1. 源与构建系统

| 项 | 实测值 |
|---|---|
| 上游源 | `https://kernel.org/pub/linux/utils/kernel/cpufreq/cpufrequtils-008.tar.gz`（上游 README 声明的 homepage） |
| HTTP 状态 | 200 |
| size | **56119 B** |
| sha256 | `4e9d9cd5eb573d5b4c82bcb28a8b36f9ca8e780436bc78b1f90c404888445a76` |
| 顶层目录 | `cpufrequtils-008/` |
| 条目数 | **56** |
| Makefile 数 | **5**（顶层、`bench/`、`debug/{i386,kernel,x86_64}/`） |
| 构建系统 | **`make`**（非 autotools、非 cmake —— 无 `configure`/`CMakeLists.txt`，README 只写 `make && su && make install`） |

## 2. 上游测试清点（§12.72 四类口径，N_static = 0）

2026-10-06 在解包后的源码树上逐条实测：

| 口径 | 命令 | 结果 |
|---|---|---|
| `test*/` 框架源码 | `find . -type d -name 'test*'` | **0**（树内唯一含 test 的文件是 `debug/kernel/cpufreq-test_tsc.c`，它不在任何 `test*` 目录下；且其 Makefile 仅在 `CONFIG_X86_TSC=y` 时才把它编成内核模块，默认 `obj-m :=` 为空 ⇒ 默认不构建，x86/ACPI 专用） |
| `*/res` 语料 | `find . -type d -name 'res'` | **0** |
| `**/*RUNTEST*` 脚本 | `find . -iname '*RUNTEST*'` | **0** |
| `src/demo\|examples/*.c` 示例 | `find . \( -path '*/src/demo/*' -o -path '*/examples/*' -o -path '*/demo/*' \) -name '*.c'` | **0** |

按 `rule4家族整改方案` 的清点法复核，同样全 0：

- `grep -rl "int main" --include="*_test.c" --include="test_*.c" .` → 空（rc=1）
- `find . -name "Makefile.test" -o -type d -name test` → 空
- `grep -rn "add_test\|ctest\|enable_testing" .` → 空
- `grep -rn "TESTS\s*=\|check_PROGRAMS\|^check:\|make check" .` → 空
- 目录全集：`bench build debug lib man po utils`（`bench/` 是 benchmark 工具、`debug/` 是架构专用调试工具，均非测试资产，**不计入 N**）

⇒ **N_static = 0**，正文上游表按 0 申报，不拿 `bench/`/`debug/` 凑数。
上游确实无测试套件 ⇒ 按检查清单通用 #12，本包允许仅消费者测试。

## 3. 能力面实测（B 机，2026-10-06 现场跑）

```
/sys/devices/system/cpu/cpufreq          → 存在（policy0..policy5）
cpu0/cpufreq/ 下 scaling_* 文件          → 8 个
scaling_driver                            → dfc_cpu_driver        （可读）
scaling_available_governors               → mips performance userspace misc （可读）
cpuinfo_cur_freq                          → 1550000               （可读）
cpuinfo_min_freq / cpuinfo_max_freq       → 418000 / 2050000      （可读）
scaling_cur_freq / scaling_available_frequencies → system:system 440，**Permission denied**
scaling_governor / scaling_min_freq / scaling_max_freq → 连 stat 都 EACCES（ls 显示 ?????????）
/proc/cpufreq                             → 不存在（现代内核只有 sysfs 面）
```

**读面可用、写面非 root 不可用**。这直接解释了工具行为（下列退出码为 2026-10-06 对**已打包二进制**逐 flag 现场实测，非推断）：

- `cpufreq-info`（默认 / `-e` / `-d` / `-g` / `-l` / `-r` / `-a` / `-s` / `-w`）实测 **rc=0**，
  输出 `driver: dfc_cpu_driver`、`hardware limits: 418 MHz - 2.05 GHz`、
  `available cpufreq governors: mips, performance, userspace, misc`、完整调频统计；
- `cpufreq-info -f` 走 `cpufreq_get_freq_kernel()` → 读 `scaling_cur_freq`（440 不可读）
  → 返回 0 频率 → `utils/info.c` 的 `get_freq_kernel()` 返回 `-EINVAL` → main `return (ret)`
  ⇒ **零输出、rc=234**（-22 回绕）。`-p` 同因（需读 `scaling_governor`/`scaling_min_freq`/
  `scaling_max_freq`，三者连 `stat` 都 EACCES），实测同样 **rc=234、零输出**；
- `cpufreq-info -y` 是 **rc=0 但数值是错的**：`cpuinfo_transition_latency` 实测原值 **0**
  → `sysfs_get_one_value` 返回 0 → 回落 `proc_*`，而 `/proc/cpufreq` 不存在 ⇒ 返回
  **-ENOSYS(-38)**；`utils/info.c:427` 的 `get_latency()` 只把 **0** 当失败，于是把 -38 当
  `unsigned long` 按 `%lu` 打印成 **18446744073709551578**（= 2^64 − 38），退出码仍是 0。

`-f`/`-p` 是**权限面**、`-y` 是**平台面**导致的静默异常返回，**不是本包缺陷、也不是能力缺失**；
测试断言因此不对 `-f`/`-p`/`-y` 的输出做内容断言。

## 4. 四处适配（全部落在配方内，不改上游源码、不加平台宏）

### 4.1 空壳 `<libintl.h>` + 链接桩不导出 gettext

- 现象：`make` 在 `utils/info.c` / `utils/set.c` 报
  `call to undeclared function 'gettext'` → `incompatible integer to pointer conversion
  passing 'int' to parameter of type 'const char *'`（clang 15 把 `-Wint-conversion` 判 error）。
- 实测根因：`ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/libintl.h` 只有 **353 B**，
  只定义 `__USE_GNU_GETTEXT` / `__GNU_GETTEXT_SUPPORTED_REVISION` / `__fa`（且立即 `#undef __fa`），
  **零函数声明**。
- 只补声明还不够：SDK 的链接桩 `sysroot/usr/lib/aarch64-linux-ohos/libc.so`（79 KB、1592 个
  已定义符号）**不含** `gettext`/`textdomain` ⇒ `ld.lld: error: undefined symbol: gettext`。
- 取证反转：设备运行时的系统 musl loader `/lib/ld-musl-aarch64.so.1`（SONAME `libc.so`）
  实测导出 `gettext` / `dgettext` / `ngettext` / `textdomain` / `bindtextdomain`。
- 方案（配方 `build()` 内）：
  1. 生成私有 `libintl.h`（按 musl 公开声明逐字补齐 9 个函数），`-I` 前置于 sysroot；
  2. `LDFLAGS="-L/lib -l:ld-musl-aarch64.so.1"` 取**真实**符号。
  实测验证：`clang g2.c -L/lib -l:ld-musl-aarch64.so.1` 编译+链接+运行
  （输出 `hello` / `cpufrequtils`），`llvm-readelf -d` 的 `NEEDED` 只有 `libc.so`，不新增依赖。
- **不引入** conan 依赖、**不用**桩函数/恒等宏 —— 三条路里只有这条既零依赖又是真符号。

### 4.2 没有 `install` 二进制 ⇒ package() 手工拷贝

- 实测：`/usr/bin/install`、`/bin/install`、`$PATH` 内均无 `install`
  （`sh: install: inaccessible or not found`；busybox 有该 applet 但上游 Makefile 硬编码
  `/usr/bin/install -c`）。
- 这正是知识图 **E098**（「鸿蒙用 toybox，toybox 不含 install」，推荐 `cp-chmod-replace`）的场景。
- 方案：不跑 `make install`，由 `package()` 按上游 `install-lib`/`install-tools`/`install-man`
  的布局手工拷贝并 `chmod 0755`，软链 `libcpufreq.so` → `libcpufreq.so.0.0.0`、
  `libcpufreq.so.0` → `libcpufreq.so.0.0.0` 按上游命名重建。

### 4.3 `cpufreq-aperf` 是 x86 专用 ⇒ aarch64 不构建

- 编译期：`utils/cpuid.h` 的 `asm volatile("cpuid" : "=a" …)` 在 aarch64 报
  `error: invalid output constraint '=a' in asm`。
- 运行期：该工具读 `MSR_IA32_APERF(0xE8)` / `MSR_IA32_MPERF(0xE7)` 与 `/dev/cpu/*/msr`，
  aarch64 / HarmonyOS 无此接口。
- 方案：`make` 目标限定为 `cpufreq-info cpufreq-set`（`libcpufreq` 与 `build/ccdv`
  作为其前置自动构建），`package()` 不打包该工具。上游只给 `cpufreq-info.1`/`cpufreq-set.1`
  两个 man 页，也印证它是附属工具。
- 与既有知识的边界：`knowledge/drafts/DRAFT-infoware-cpuid-arch-guard` 已覆盖
  「用架构宏守卫 + 零值回退保 API」的解法；本包不保留该 API（无消费方），
  采用「不构建」是另一种解法，**不据此判 hit**。

### 4.4 `strip -s` 会剥掉 `.codesign` ⇒ 签名必须排在 strip 之后

- 实测链路：`llvm-strip -s --remove-section=.note --remove-section=.comment` 之后
  `llvm-readelf -S | grep -c codesign` 由 1 → **0**，该 ELF 执行报
  `Permission denied`（shell rc=126）；`binary-sign-tool sign` 补回 `.codesign` 后同一文件立即可执行。
  对照组：未 strip 的 `libcpufreq.so.0.0.0` 自带 `.codesign` 占位段。
- 方案：`package()` 里 `objcopy --remove-section .codesign`（摘残留占位）→
  `binary-sign-tool sign -selfSign 1` → `os.replace` → `chmod 0755`。
  上游 Makefile 只对三个工具执行 `STRIPCMD`，`.so` 不 strip。

## 5. 测试（三处同源：manifest.yaml / test_package/MANIFEST.yml / PR 正文）

- **上游**：N_static = **0**（清点证据见 §2）。
- **适配后**：`test_package` **21 条断言**（A01–A21，编号连续无空洞）：
  - A01–A06 包布局（可执行位、共享库、SONAME 软链、头文件声明）
  - A07–A16 CLI 实跑（两处 `--help` 横幅与 rc、默认输出、`-e`、`-d` driver 解析、
    两条**保证不写 sysfs**的参数闸）
  - A17–A21 libcpufreq 真实 API：编译链接 `consumer.c`（`-I<包>/include -L<包>/lib -lcpufreq`）
    → 运行 → `cpufreq_cpu_exists(0)`、`cpufreq_get_driver(0)` → `conanrun` PATH 可解析工具
- **安全性**：A15 用 33 字符 governor 名触发 `set.c` `case 'g'` 在 getopt 循环内
  `return -EINVAL`（早于任何 sysfs 写）；A16 用"零参数"触发 `At least one parameter…`
  早退。两者都够不到 `scaling_*` 写入口，**测试不改设备调频状态**。
- `consumer.c` 对能力面相关项用 `SKIP`（`SYSFS_LIMITS_SKIPPED` / `SYSFS_LATENCY_SKIPPED`）
  表达，不把"读不到"写成通过。

## 6. 已知闸口（留给后续阶段，本轮终点在 W4 审计前）

- **PF9 vs PF8/PF8-R38 互斥假阳性**：R38 要求 `commands.json` 落在软件级
  `archives/c/cpufrequtils/commands.json`（4 段路径），而 PF9 按 `len(f.split("/")) < 5`
  判「缺版本目录层」。同一条 preflight 的 PF8 又要求 CLI 包必须有它。
  既有处置口径（经验库 §12.82 / `反馈/pending/主理-1-PF8与PF9自相矛盾拦住新CLI工具包-0930.md`）：
  **手工跑 `run_preflight(repo,"upstream/main","HEAD")` 确认仅 PF9 这一条命中后，
  走逃生口并在 PR 正文 `## 补充说明` 披露**，⛔ 不要为过闸删 `commands.json`（那会转成 PF8/L0k 真失败）。
- **conan-verify / finish 的两条基线假阳性**（与本包无关，属仓库既有）：
  `check_knowledge_completeness` 因 `knowledge/graph/{E219,E253,E305}.kv` 空 `root_cause` 恒红；
  `check_pr_atomicity` 硬编码 `origin/main...HEAD` 报 **2109** 文件（2026-10-06 实测；
  真口径 `upstream/main...HEAD` 实测 **11** 文件，两数都是本次现场跑出来的，不是估的）。
- **`knowledge_gained` 由 5 条变 4 条（`knowledge_count 5→4`）＝ 内容移位，不是缩分母**
  —— 2026-10-06 按主理裁决 A 处置，三件事记全：
  1. **搬家理由**：原第 5 条「OHOS 非 root 进程下 sysfs cpufreq 是分级可见面…」是**本包能力面实测记录、
     不是知识库条目**。查重实测：`knowledge/graph/index.tsv` 对 `cpufreq`=**0**、`scaling`=**0**、
     `sysfs.*Permission`=**0**、`non-root`=**0**、`假通过`=**0**；`ENOSYS` 仅 1 命中且是 `E051`
     （SIGSYS/unimplemented syscall，与本条无关）。最接近的 `E031`（`/proc` 被拒 → 方案 `sudo-run`）、
     `E240`（macOS 能力拆分+负向测试）、`E161`（coreutils 管道 stdin 被拒 → 改用文件）
     **均非同症状、解法也不同** ⇒ 挂任何号都只能写「同族」，而手册对「只写同族不算依据」是收紧口径
     ⇒ 按**不硬凑**移出知识段（本 PR 唯一知识位已给第 1 条，**一 PR 一知识**）。
  2. **原句逐字仍在两处**：① `manifest.yaml` 的 `quality_gates.capability_face`（新，含同款说明注释）；
     ② 本文件 **§3 能力面实测**（一字未改）。搬家前后字符串已用脚本逐字比对 = **True**。
  3. **性质说明（给 W4 的口径）**：`knowledge_count 5→4` 是**内容移位**，
     **不是 `rule4` 意义的"缩测试分母"** —— 测试分母是 `N_static / N_registered / N_executed`
     （本包 **0 / 0 / 0**）与 **21 条 consumer 断言**，**本轮一字未动**（`manifest.yaml`
     `test_package.assertion_count: 21`、`test_package/MANIFEST.yml`、本文件 §5、
     `reports/test-report.md` 四处仍同源）。
  4. 另：前 4 条以行尾注释 `  # ref: <号>` 挂号（写法与仓内 655 个 `unreferenced=0` 的 manifest 一致）：
     ① `DRAFT-cpufrequtils-008-ohos-libintl-stub-musl-symbol-link` ② `E098` ③ `E077`
     ④ `E221` + 通用池草稿 `DRAFT-PKG-VER-lib-cli-tools-missing-from-consumer-runenv`。
     ⚠ 第 4 条的 runenv 半边**刻意不挂 `E428`**：`doc/E428.md` 的方案是「消费者侧算绝对路径」，
     与本条「配方侧写 `runenv_info`」**不是同解法**，挂上去即引用不精确。

## 7. 构建与验证命令

```bash
export CONAN_HOME=$HOME/tmp/ch/home-cpufreq
export PATH=$HOME/usr/local/bin:$HOME/.local/bin:$PATH
export SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem

bash ci/scripts/preflight_check.sh cpufrequtils/008
python3 scripts/ohc-run.py recipe-search cpufrequtils
python3 scripts/ohc-run.py conan-verify cpufrequtils 008
python3 scripts/ohc-run.py finish cpufrequtils 008 built
```

**门禁序列里 `build` 一步是按成文口径跳过的，不是漏跑**：`ohc-run.py build cpufrequtils 008`
首跑即 `EXIT_REASON=init_build_failed`、`EXIT_CODE=2 (resumable)`、`STEP_FAILED= Step1`，
首条真实错误为 `❌ 源码目录不存在 …/archives/c/cpufrequtils-008/src` + `用法: python3 ohc-run.py init cpufrequtils 008 --url=…`；
根因是 `cpufrequtils` 不在 `scripts/software-registry.yaml`（实测 `grep -c cpufreq` = 0），
`init-build` 取不到 URL。按 **经验库 §12.60①**（libnewuoa 三连：conan-init 会用模板覆盖已就位配方，
**对策 = 配方文件全量就位后不要跑完整 build 一条龙，直接 `conan-verify`，其 create 不触发 init**）
改走 `conan-verify → finish → submit`。这条路径由 `conan create` 实跑验证，W3 本地 CI 同源，
证据见 `reports/conan-create.log`、`reports/conan-verify-report.md`、`reports/w3-local-ci.log`、
`.ci-result.json`。
---

**编译结束**: 2026-10-06 05:37
**最终状态**: built
