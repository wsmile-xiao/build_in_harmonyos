# rng-tools 6.17 适配笔记

## 编译环境
- 构建系统: autotools（上游 GitHub tag 归档**不含预生成 configure**，需 autoreconf 自举）
- 编译日期: 2026-09-23（首次构通 2026-09-22 由 DS-35 轮完成；本窗 02:07 重跑通并过本地 CI）
- 编译器: clang 15 / clang++ 15（`/data/service/hnp/bin/clang`，profile `ci/conan/profiles/ohos-aarch64`，`os=OHOS os.version=6.0 arch=armv8 compiler.cppstd=17 libcxx=libc++`，`tools.build:jobs=2`）
- 状态: built（本地 `conan create` 通过；未向制品仓发布，按 R29 不伪造 published）
- 设备: HarmonyOS PC（aarch64，鸿蒙 PC 真机 native 构建，非交叉、非模拟器）

## 编译步骤

配方实际执行序列（`conanfile.py`，全部在 `build()` 内，上游源码零改动）：

1. `source()`：`get(self, **conan_data["sources"], strip_root=True)` 解官方 tag 归档
   `v6.17.tar.gz`（sha256 `4aa50994232da74499b60b3ebf79118e30a1943be375b7d931dcf18df5442fd3`）。
2. `generate()`：`PkgConfigDeps` 为全部依赖生成 .pc（`libcap` 包不自带 .pc，而
   `configure.ac` 对 openssl/libcap 用 `PKG_CHECK_MODULES`）；`AutotoolsToolchain` 追加
   `--build=aarch64-unknown-linux-ohos` 与 4 个 `--without-*`；按 `cpp_info` 把
   `-I/-L/PKG_CONFIG_PATH` 注入 env（jitterentropy 走 `AC_SEARCH_LIBS`、argp 走
   `AC_CHECK_LIB`，都靠 `-I/-L` 命中）。
3. `build()`：
   1. 生成亲和性垫片目录 `np-affinity-compat/`：`rngtools_np_affinity.h`（只声明
      plain 变体 `pthread_setaffinity_np`）+ `rngtools_np_affinity.c`
      （转发 `sched_setaffinity(0, cpusetsize, mask)`）；用 profile conf
      `tools.build:compiler_executables.c` 取到的 `$CC -c` 编译，`llvm-ar rcs
      librngnpcompat.a` 打成归档。
   2. `CPPFLAGS` 前置 `-include <shim.h>`、`LDFLAGS` 前置 `-L <compat_dir>`、
      `LIBS` 前置 `-lrngnpcompat`。
   3. `autoreconf --force --install`（`tool_requires automake/1.18 + libtool/2.5.4`）。
   4. E490：恢复 8 个 autotools helper 的可执行位（`configure config.guess config.sub
      install-sh missing compile depcomp test-driver`）。
   5. E011：把自举产物 `configure`/`Makefile.in`/`tests/Makefile.in` 里的
      `umask 077` 改为 `umask 022`（HMDFS 下 077 会让 config.status 临时目录不可写）。
   6. `ACLOCAL/AUTOMAKE/AUTOCONF/AUTOHEADER/AUTOM4TE` 设为 `:`，防 make 因时间戳抖动重生成。
   7. **configure（本窗改路由，见问题 4）**：
      `CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh <src>/configure --prefix=/
      '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib'
      '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include'
      --build=aarch64-unknown-linux-ohos --without-nistbeacon --without-qrypt
      --without-pkcs11 --without-rtlsdr`
   8. `make -j2`。
   9. `RNGD_JITTER_TIMEOUT=120` 后 `make check -j2`（上游 3 个 shell 用例真实执行，见「验证结果」）。
4. `package()`：`make install DESTDIR=<package_folder>`；产物 `bin/rngd`、`bin/rngtest`、
   `bin/randstat`（纯可执行包，无 lib/，`package_type="application"`）。

## 遇到的问题与解决方案

| # | 问题症状 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: Neither pthread_setaffinity_np nor pthread_attr_setaffinity_np found`，止步 configure，`make` 一行未跑 | OHOS musl 对这两个 glibc-only `_np` 扩展**声明层与符号层双缺**；`configure.ac:117-121` 是嵌套双探测、双失败即 `AC_MSG_ERROR` 硬中止 | 配方级**两层垫片**（缺一即失败）：`-include` 声明头让 `AC_CHECK_DECL` 的编译探测转绿；`librngnpcompat.a` 经 `LDFLAGS=-L` + `LIBS=-lrngnpcompat` 补符号。上游源码零改动 |
| 2 | musl 无 `argp`，`configure` 直接 `AC_MSG_FAILURE` | rngtest.c 用 argp；musl 不提供，上游走外部 libargp 分支 | `requires("argp-standalone/1.5.0")` + `-I/-L` 注入。**不能**加 `--without-libargp`（那条路是硬错误） |
| 3 | `PKG_CHECK_MODULES([libcap])` 找不到 `libcap.pc` | 已发布的 `libcap/2.73` 包不带 .pc | `generate()` 里 `PkgConfigDeps(self).generate()` 按 `cpp_info` 合成，并把 `generators_folder` 放 `PKG_CONFIG_PATH` 最前 |
| 4 | `configure: error: working directory cannot be determined`，日志伴随 34 条 `shell-init/job-working-directory: error retrieving current directory: getcwd: ...`（errno 乱值 Not supported / Not a socket / Bad address） | 框架 profile 的 `[buildenv]` 把 `SHELL`/`CONFIG_SHELL` 指向 `/data/service/hnp/bin/bash`（harmonybrew bash 5.3），该 bash 在本机 HMDFS **任何目录** getcwd 必挂（本窗实测），autoconf 经 `$CONFIG_SHELL` 重 exec 自身 ⇒ configure 必死。与配方、内存、负载无关 | 配方内显式用 `/bin/sh` 跑 configure，并用命令行赋值把 `SHELL`/`CONFIG_SHELL` 钉到 `/bin/sh`（命令行赋值优先于 `conanbuild.sh` 里已 export 的值；config.status 记录的 `@SHELL@` 同为 `/bin/sh`，`make`/`make check` 不再拉起 hnp bash）。**不改框架 profile**（框架改动须单独 PR）。先例：`archives/a/abx/0.1/conanfile.py`；KB §12.49/§12.38① |
| 5 | `conan-verify` 抛 `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe4 in position 21396`，rc=2 | `scripts/ohc/conan_verify.py:117` 用 `subprocess.run(capture_output=True, text=True)` 严格解码；`CONAN_HOME` 路径含中文（`home-主理-2-rng`）时构建 stderr 里的 CJK 路径在管道分块边界被切断 | 环境侧处置：改用 ASCII `CONAN_HOME`（`cp -a` 出 `home-zl2-rng`，依赖闭包与共享 dlcache 都在，不重下）。**不入配方**，记在此处供后续窗口避坑 |
| 6 | `config.guess` 不识别 HarmonyOS 且在 HMDFS 上执行探测程序被拒（`cannot guess build type`） | E007 家族 | 显式单三元组 `--build=aarch64-unknown-linux-ohos`（实测有效；与 `适配检查清单 #4` 的双三元组写法不同，沿用已验证形态） |
| 7 | 高负载并发构建时 `rngtestjitter.sh` 可能假失败 | 上游 `rngd -O jitter:timeout` 默认 5s，多窗口并发下 jitter 线程调度延迟可超 5s | 上游自带环境旋钮 `RNGD_JITTER_TIMEOUT`，配方在 `make check` 前置为 `120` |

### 最小复现（问题 1，设备实测 2026-09-23，不经 conan、不动配方）

解包 tag 归档（无预生成 configure）→ `autoreconf -fi` → 独立 build 目录执行
`../src/configure --build=aarch64-unknown-linux-ohos --without-nistbeacon
--without-qrypt --without-pkcs11 --without-rtlsdr`，配置日志读数：

```
checking whether pthread_attr_setaffinity_np is declared... no
checking whether pthread_setaffinity_np is declared... no
configure: error: Neither pthread_setaffinity_np nor pthread_attr_setaffinity_np found
```

### 四态分层对照（同源码副本、同依赖、同参数；`~/tmp/uc2/主理-2-rng/no-shim/logs2/`）

| 态 | 注入 | configure | make | `rng-tools-config.h` |
|---|---|---|---|---|
| S1 全裸 | 无 | **rc=1** 同一处 `AC_MSG_ERROR` | 未跑 | 未产出 |
| S2 仅 `-D_GNU_SOURCE` | `CPPFLAGS=-D_GNU_SOURCE` | **rc=1** 同一行同一错（日志与 S1 逐字节相同，sha256 一致） | 未跑 | 未产出 |
| S3 仅声明层 | `-include shim.h` | rc=0，`#define HAVE_PTHREAD_SETAFFINITY 1` + `#undef HAVE_PTHREAD_ATTR_SETAFFINITY` | **rc=2** 首错 `ld.lld: error: undefined symbol: pthread_setaffinity_np`（引用点 `rngd_jitter.c` 的 `thread_entropy_task` / `rngd_notime_start`） | 同左 |
| S4 声明层 + 符号层 | 再加 `LDFLAGS=-L<compat>`、`LIBS=-lrngnpcompat` | rc=0 | **rc=0**，`rngd` + `rngtest` 双产物齐 | 同 S3 |

### 已试过的失败方案（不得当修复手段）

- **`-D_GNU_SOURCE`**：S1 与 S2 的 configure 日志逐字节相同 ⇒ 对本案两个 `_np` 接口零效果。
  配方里仍保留该宏（沿用已验证配方、为其它 GNU 扩展兜底，**其必要性未单独验证**），
  代价是 10 个上游 TU 自带 `#define _GNU_SOURCE` 触发 10 条 `-Wmacro-redefined` **告警**
  （告警非错误，见 `reports/conan-create.log` 第 259/265/277/283/303/315/325/337/348/354 行）。
- **只补声明层（S3）**：configure 过、`make` 死在 undefined symbol ⇒ 符号层不可省。
- **把 `.o` 绝对路径塞进 `LDFLAGS`**：与 `-L 目录 + -l 名字` 语义不同，configure 的
  conftest 与生成的 Makefile 只能稳定解析后者，本案采后者。
- **`--without-libargp`**：musl 缺 argp 时该选项直接 `AC_MSG_FAILURE`，是死路。
- **换 `CONAN_HOME` / 降负载 / 重试**治问题 4：均无效（问题 4 是 shell 层，不是文件系统抖动）。

## 源码修改

**无补丁、无源码改动**（`patches/` 为空，`conandata.yml` 的 `patches: {}`）。
亲和性垫片是 `build()` 里生成的配方侧文件（`np-affinity-compat/`），
按仓库口径"不是补丁"（先例：`archives/o/openssh/10.0p1/conanfile.py`）。
`configure`/`Makefile.in` 里的 `umask 077→022` 属 E011 配方内运行时替换，不改上游 tarball。

## 依赖版本

- 运行依赖（`requires`，4 个，均已在制品仓发布且可消费）：
  `openssl/3.5.8.1`、`libcap/2.73`、`argp-standalone/1.5.0`、`jitterentropy-library/3.6.3`
- 构建工具（`tool_requires`，2 个）：`automake/1.18`、`libtool/2.5.4`
- 显式关闭的可选熵源（依赖重且平台无用）：`--without-nistbeacon`（libxml2+libcurl+jansson）、
  `--without-qrypt`（libcurl）、`--without-pkcs11`（libp11）、`--without-rtlsdr`（USB 硬件）；
  jitter 与 RNDR 熵源保留（零额外负担，`sys/auxv.h` + `getauxval` 由 musl 提供）

## 验证结果

> 证据文件位置说明：`archives/r/rng-tools/6.17/reports/` 被仓库根 `.gitignore:96
> reports/` 全仓忽略，构建日志不入 PR；下列读数均为本窗设备实跑原文摘录，
> 复核方式是按本节命令在目标机重跑 `conan-verify` / `build_and_test.sh`。

```text
# conan create（reports/conan-create.log，02:07 轮，CONAN_HOME=home-zl2-rng）
rng-tools/6.17@ohpcd/stable#d92cb1b6d828854cb1068a84f09414a6
package_id: 39a5addc491d438943b48e97b202c2736f991927
checking whether pthread_attr_setaffinity_np is declared... no     # 故意不声明 attr 变体
checking whether pthread_setaffinity_np is declared... yes         # 声明层垫片生效
PASS: rngtestzero.sh / PASS: rngtesturandom.sh / PASS: rngtestjitter.sh
# TOTAL: 3   # PASS: 3   # SKIP: 0   # FAIL: 0   # XFAIL: 0   # ERROR: 0
test rng-tools 6.17: OK (rngtest FIPS reject/accept + rngd version)
getcwd / shell-init 命中数 = 0
产物: bin/rngd 4180480 B, bin/rngtest 121344 B, bin/randstat 18816 B

# 逐用例 .log 尾部（本窗两轮构建各自重跑并产出 3 份 .trs，:test-result: PASS；
# autotools 语义：exit 77 才是 SKIP，本包三条均为 exit status: 0 = 真通过）
PASS rngtesturandom.sh (exit status: 0)   # bits sent to output: 2000000 / FIPS successes: 100, failures: 0
PASS rngtestzero.sh    (exit status: 0)   # 反向断言：bits sent to output: 0 / successes: 0, failures: 100（全零流被 FIPS 拒绝）
PASS rngtestjitter.sh  (exit status: 0)   # rngd 仅开 jitter 源真实产熵 successes: 100，12.3s 后 killall 收尾

# conan-verify G0–G4（reports/conan-verify-report.md，02:07 轮）：Verdict PASS，G0/G1/G2/G3/G4 全绿
#   L2/L4/L5 在该入口为 "⏭️ 跳过（无 cache 路径）"，真正的 L0–L5 见下方本地 CI 模拟
#   G4 的 "⚠️ 无法找到程序包 ID" 是 conan_verify.py:737-741 取 id 方式所致的既有告警，
#   `conan list` 与 .ci-result.json 均证实包已产出，非真缺陷

# 本地 CI 模拟 W3（reports/w3-local-ci.log，ci/conan/build_and_test.sh，与 CI worker 同一入口）
G0_RESULT=pass  KC_RESULT=pass  JC_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L1c: Upstream official tests (make check/ctest) executed in build phase
L1e: Negative test confirmed — test genuinely depends on rng-tools
L2_RESULT=pass: randstat --version OK, rngd --version OK, rngtest --version OK
L4_RESULT=pass: patches clean     L5_RESULT=pass: bin/ has content
Total: 1  Success: 1  Failed: 0  Pass rate: 100.0% (1/1)
.ci-result.json: exit_code=0 step=W3_local_ci integrity_hash=2286f75872ed115f

# 五维账本（上游测试清点）
N_static = 3      # tests/Makefile.am: dist_check_SCRIPTS = rngtesturandom.sh rngtestzero.sh rngtestjitter.sh; TESTS = $(dist_check_SCRIPTS)
N_registered = 3  # automake parallel-tests 注册 3 个，产出 3 份 .trs（:test-result: PASS）
N_executed = 3    # make check 实跑，# PASS: 3 / # SKIP: 0 / # FAIL: 0
未执行分类 = 0    # 无 SKIP、无 XFAIL、无 ERROR
N_consumer = 1    # test_package/test.c（6 处 if-guard 断言，见 test_package/MANIFEST.yml）
```

适配验证在 HarmonyOS PC 真机（aarch64、native conan 构建）完成，全部读数为设备实跑原文。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/rngd` | 4180480 B | 熵守护进程（hwrng/rdrand/jitter/RNDR 源，`--without-*` 关闭四类重依赖源） |
| `bin/rngtest` | 121344 B | FIPS-140-2 随机性检测工具 |
| `bin/randstat` | 18816 B | 上游 contrib 附带工具（随 `make install` 装入 bin/） |
| `archives/r/rng-tools/6.17/conanfile.py` | 15014 B | 配方（含两层亲和垫片与 `/bin/sh` 路由） |
| `archives/r/rng-tools/6.17/test_package/` | — | 消费者测试 test.c（6 处断言）+ MANIFEST.yml |
| `knowledge/drafts/DRAFT-rng-tools-6.17-musl-pthread-affinity-decl-and-link-shim.{md,kv}` | — | 路径 B 知识草稿（判定 create） |

`packaging/*.tar.gz`（release/debug 包）本窗未产出——该目录同被 `.gitignore` 覆盖，
且已合入先例（`archives/v/vamps/0.99.2`、`archives/p/pforth/2.0.1`）归档内亦无 `packaging/`，
PR 不含二进制包。

## 已知限制与适用边界

1. **亲和性垫片有行为差异，不是完全等价**：`pthread_setaffinity_np` 的实现丢弃 `thread`
   形参、只作用于调用线程（转发 `sched_setaffinity(0, …)`）。`rngd_jitter.c:290`
   传的是 `pthread_self()`（本就是自身）语义不变；但 `rngd_jitter.c:86`
   在 `rngd_notime_start` 里传的是 `notime_thread_id`（另一个线程），那一处退化为
   **给调用线程设亲和**。因上游掩码是 `CPU_SET` 全核，只影响性能不影响正确性。
   attr 变体 `pthread_attr_setaffinity_np` **故意不声明**，使 configure 落进
   `HAVE_PTHREAD_SETAFFINITY` 分支（该分支调用点更少、退化面更小）。
2. **rngd 守护态"向内核熵池注熵"未做端到端验证**：`make check` 与 test_package 均以
   非 root 运行，用例日志可见 `[namedpipe]: Initialization Failed`、
   `can't open /proc/sys/kernel/random/poolsize: Permission denied`、
   `unable to adjust write_wakeup_threshold: Operation not permitted`。
   本次真实覆盖的是 rngtest 的 FIPS 判定路径（正/反向）、jitter 熵源产熵、
   三个二进制的 `--version` 响应；把 rngd 作为系统守护进程长期注入熵池需
   root/相应能力，不属本包验证范围，亦无 systemd/init 集成。
3. `-D_GNU_SOURCE` 的全局注入**未单独验证其必要性**（沿用 2026-09-22 已验证配方，
   为其它 GNU 扩展兜底），已证其对本案两个 `_np` 接口零效果；代价是 10 条
   `-Wmacro-redefined` 告警。移除它需要另做一轮全量构建验证，本窗未做。
4. 功能面按平台可用性显式收窄：nistbeacon（libxml2+libcurl+jansson）、qrypt（libcurl）、
   pkcs11（libp11）、rtlsdr（USB 硬件）四类熵源经 `--without-*` 关闭。
5. 本包不改上游源码、不产补丁 ⇒ 若上游未来调整 `configure.ac` 的亲和探测，
   声明层垫片的分支落点需重测（判据见「四态分层对照」表）。
6. 问题 4/5 属设备与工具链环境坑，修法一是配方内的 `/bin/sh` 路由（随包交付、
   对 CI worker 同样有效），二是 ASCII `CONAN_HOME`（仅本机操作纪律，不入 PR）。

### 对话 #1（2026-09-22 DS-35 轮）

- W0 依赖核验：4 个运行依赖 + 2 个 tool_requires 全部制品仓已发布可消费。
- W1 配方：argp-standalone 外链、PkgConfigDeps、4 个 `--without-*`、autoreconf 自举、
  E490/E011、单三元组 `--build`。
- W2/W3：亲和性两层垫片打通 configure+link，`conan create` 成功，
  `make check` 3/3 PASS、test_package OK，`conan-verify` G0–G4 全绿（11:10 轮）。

### 对话 #2（2026-09-23 主理-2 轮）

- 亲和性机制定性纠偏：由"musl 把声明藏在 `_GNU_SOURCE` 之后"改判为
  **声明层+符号层双缺、`-D_GNU_SOURCE` 零效果**（四态分层对照 S1–S4 实拍），B 判定定为 create。
- 补齐 B 草稿 `knowledge/drafts/DRAFT-rng-tools-6.17-musl-pthread-affinity-decl-and-link-shim.{md,kv}`
  与查重（E094/E211/E147 均不同签名，`draft-review` 相似度低于阈值）。
- 校正 `test_package/MANIFEST.yml` 的 `assertion_count`（7→6，逐行依据 38/44/51/55/62/66）。
- 该轮 `conan-verify` 01:30 失败于问题 4（getcwd 风暴），判为设备级、非配方缺陷，未闭环即中断。

### 对话 #3（2026-09-23 主理-3 轮，本窗）

- 复测确认问题 4：`cd <构建目录> && /data/service/hnp/bin/bash -c pwd` rc=1，
  同目录 `/bin/sh`、`/system/bin/sh` rc=0，`python3 os.getcwd()` 正常 ⇒ 按 KB §12.49
  在配方内做 `/bin/sh` 路由（不动框架 profile）。
- 复跑 `conan-verify` 02:07 轮 G0–G4 全绿（create 日志 0 条 getcwd 命中）。
- `finish rng-tools 6.17 built`：W3 本地 CI 模拟通过并产 `.ci-result.json`（exit_code=0）；
  step25 的 G0 clean-verify 报 "configure 失败 (exit 127)" 属工具自述的预期行为
  （tag 归档无预生成 configure，G0 不走 `build()`），不阻塞；step5b/step8 两项失败为
  仓库既有噪音（1397 个待审草稿、`gen_summary` 的 `'str' object has no attribute 'append'`），
  与本包无关。
- 回填 `notes.md` 与 `manifest.yaml`（此前均为未填模板），并做 `yaml.safe_load` 与
  .kv 行级解析自检。

---

**编译结束**: 2026-09-23 02:11
**最终状态**: built
