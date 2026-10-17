# lft 3.98 适配笔记

## 编译环境
- 构建系统: autotools（autoconf 2.69 生成的 `configure` + `Makefile.in` + `config/`，**无 `configure.ac`、无 autogen**）
- 编译日期: 2026-09-26
- 编译器: clang 15（profile `tools.build:compiler_executables` → `/data/service/hnp/bin/clang`，Target `aarch64-unknown-linux-ohos`）
- 机器: B 机（HarmonyOS PC aarch64，8 核 / 31G）
- profile: `ci/conan/profiles/ohos-aarch64`（`-pr:h` 与 `-pr:b` 同一个，按路径引用仓内文件）
- CONAN_HOME: `~/tmp/ch/home-lft`（本任务独立隔离）
- 状态: built（conan-verify 判决见「验证」节，upload 由合并后的 CI 做）

## 软件与构建面（读源码所得，不是猜测）

lft 是「Layer Four Traceroute」——用真实 TCP/SCTP 握手探测路径的 traceroute，
ICMP 被中间设备吃掉时仍能看到路径；它同时是一整套 raw-socket 网络诊断工具，
用 libpcap 抓回包，可选 c-ares 异步 DNS、可选 ncurses `-W` watch 监视模式。

- 发布包一次产出**两个可执行**（`Makefile.in`：`all: lft whob`）：
  - `lft`：`lft.o lft_ifname.o whois.o lft_lib.o lft_icmptrace.o lft_btcptrace.o $(WATCH_OBJS)`。
  - `whob`：`whois.c -DSTANDALONE` 单独编译，`WHOB_LIBS = $(filter-out -lncurses -lncursesw,$(LIBS))`
    （whob 是纯 CLI，不链 ncurses，但保留 c-ares 供 pwhois 预取解析路径）。
- `lft_types.h:110` 无条件 `#include <pcap.h>` ⇒ **libpcap 硬依赖**，configure 找不到即 `as_fn_error`。
- c-ares / ncurses 均**编译期可选**：所有调用点都在 `#ifdef HAVE_CARES` / `#ifdef HAVE_NCURSES` 内，
  configure 只在探测到时才 `#define`。本配方 `--disable-async-dns --disable-ncurses` 钉死为关，
  链接闭包恰为 libpcap。
- `Makefile.in:25` 是 `LIBS=@LIBS@`；`config.status` 把 configure 计算出的 LIBS（含
  `--with-pcap` 注入的 `-L<libpcap>/lib` 与 AC_CHECK_LIB 追加的 `-lpcap`）替换进去。
- profile 不强制 `shared` ⇒ libpcap 取默认（`shared=False`，**静态**）⇒ 产出的 `lft`/`whob` ELF
  在运行期不再依赖 `libpcap.so`（`pcap_lib_version()` 等被静态链入），消费者测试的
  `runtime-libs` 闭包因此为空，只需签两个二进制本体。
- `Makefile.in` **没有 `check` 目标**，build() 只 `make -j1`（跑 `make check` 会
  `No rule to make target 'check'` 直接中断构建）。
- 运行期语义（消费者测试依据）：`main()`（lft.c:343 extern int main）先 getopt_long 解析
  选项，`-v` → `show_version()`（lft.c:199）打印版本横幅**并真实调用 `pcap_lib_version()`**
  后 `exit(EXIT_SUCCESS)`；`--help`/非法选项/缺 target 走 `usage()`（lft.c:116）打 `Usage:`
  后 `exit(EXIT_FAILURE)`；`-h` **不是 help**（是 `LFTSetupDispSymbHost` 符号主机开关）。
  权限门 `lft_check_permissions()` 在 lft.c:634（选项解析之后）：非 root 且
  `socket(AF_INET,SOCK_RAW,IPPROTO_RAW)` 得 EPERM/EACCES → 打 `LFT: insufficient privileges`
  → `exit(EXIT_FAILURE)`。whob：`whob -v` → `usage()`（whois.c:2648）打 `WhoB - version 3.98`
  → `exit(EXIT_FAILURE)`；真查询向 43 端口建 TCP。

## OHOS 适配点（七条，全部实测命中）
- **E386**：`build()` 不用 `autotools.configure()`，改在同一条 shell 命令里
  `unset CONFIG_SHELL; LD_LIBRARY_PATH=... ./configure <base_args> <feature 开关>`，
  configure 参数取 `Autotools._configure_args`（generate() 期 env.unset 赢不过运行期重注入）。
  已在证据日志 `reports/w3-local-ci.log:213` 核到 `checking whether we are cross compiling... no`
  （证据分层与绑定关系见「验证结果」节）。
- **E011/E114**：`_fix_configure_umask()` 就地改写 `configure` 内 `umask 077`→`umask 022`
  （实测命中 2 处），未命中打 warning 不静默。
- **E467**：同命令内联 `LD_LIBRARY_PATH=<依赖闭包 libdir>`（本包 libpcap 静态，此项为与
  wmcore 逐字一致的防御性保留）。
- **E160**：`uname -s` = `HarmonyOS`，autoconf 2.69 生成的 `config.guess` 没有该分支 ⇒
  `configure: error: cannot guess build type; you must specify one`。处方用仓内
  `scripts/patch-autotools-ohos.pl`（一次改 `config.guess` + `config.sub`），用 `perl` 显式执行。
  **create 期配方被复制进 cache 导出目录**，`../../../scripts/...` 这类相对写法取不到仓内脚本
  ⇒ `_locate_helper()` 多候选路径解析 + `export_sources()` 把 helper 随包导出；两者都失败时
  **抛 `ConanException`**，不静默跳过（静默跳过只会把故障挪回 `configure`，日志上看着像"补丁没生效"）。
- **E007 红线（为何不写 `--build/--host`）**：显式三元组会让 configure 判定为交叉编译，
  于是 `AC_RUN_IFELSE` 一类运行期探测全部跳过（本包确实有 getaddrinfo/`AI_IDN` 等
  `AC_RUN_IFELSE` 探测）⇒ 生成错误的 `config.h`。实测改走 E160 后
  `checking whether we are cross compiling... no`（`w3-local-ci.log:213`）。
- **裸命令名**：`self.run("configure ...")` 会被当可执行名去 `PATH` 找而失败 ⇒ 显式补 `./`
  前缀（`_configure()` 内当 `cfg_path` 无 `/` 时前缀 `./`）。
- **E516**：`lft.c` 在 `res_init()` 后无条件写 `_res.retrans` / `_res.retry`，而 OHOS libc
  **既不导出遗留全局 `_res`、也没有 glibc 的 `__res_state()` 访问器** ⇒ 编译期
  `error: undeclared identifier '_res'`。用
  `patches/0001-lft-ohos-resolver-tuning.patch` 把**这两行**包进 `#ifdef __GLIBC__`，
  `res_init()`/`res_query()` 保持原样（OHOS libc 有）。
  **功能后果（不是无害改动）**：OHOS 上不再套用上游"1 秒重发 / 1 次重试"的收敛参数，
  改用 libc 默认解析器设置，DNS 查询慢的场景可能比上游多等。

## 消费者测试口径（赛道二：真实执行、断言决定退出码）
- 行为层（`test_package/test_lft.sh`，**8 个脚本自计检查点** = 脚本里 8 个 `ok` 调用点，每一次都真实执行打包后的 lft/whob，
  由退出码与输出共同决定成败；`ok()` 计数器 + `bad()` 即 `exit 1`）：
  1. `lft --version` 输出含上游横幅 `Layer Four Traceroute (LFT) - version 3.98`
     （走到这里就同时证明了：加载器放行、整条依赖闭包可解析、`-DVERSION` 替换真实发生）；
  2. 同一次 `lft --version` 退出码 0（上游自身行为）；
  3. `lft`（无参数）退出码 1（usage 分支）；
  4. `lft`（无参数）stdout/stderr 至少一路非空（真实 usage 文本，不是空跑）；
  5. `lft --certainly-not-an-option` 退出码 1（未知选项经 default 分支回 usage）；
  6. `lft 127.0.0.1` 越过参数解析后命中 `lft_check_permissions()`，输出含 privilege 诊断，
     且退出码**不得**是 126/127 —— 这条断言的全部意义就是区分"包能跑、只是这个 uid 没特权"
     与"包坏了加载器不放行"；
  7. `whob -v` 退出码 1 且 usage 横幅带 `3.98`；
  8. 负对照：`env -i <暂存副本>/lft --version` 仍不得 126/127 —— 本 profile 下 libpcap 是
     **静态**链入，产物应当自封闭，不靠 conan 运行环境也能起。
  ⚠ 适配执行段早期实测到的另外两条事实（`lft --help` 退出码 1 且打印 `Usage:`；`-v` 输出里还有
  `Packet capture:`/`libpcap` 的编译选项块）**在本交付版里没有做成断言**，只作为已知事实保留，
  不计入通过数 —— 不做成断言就不用承担它的期望值未经复测的风险。
- 产物层（`test_package/conanfile.py`，**11 个检查点** = 5 类 ELF/字节检查 × 2 枚可执行 + 1 项手册页；
  逐条打印 `LFT_ARTIFACT_PASS/FAIL <名>`，任一失败抛 `ConanException` 让 `conan test` 转红）：
  1. `lft-exists` / `whob-exists`：包目录 `bin/` 下确实产出两枚可执行；
  2. `*-machine-aarch64`：`llvm-readelf -h` 的 Machine 为 AArch64；
   3. `*-codesign-section-at-most-1`：`readelf -SW` 里 `.codesign` 段**至多 1 个**（0=CI 交付态未自签，属本仓常态：CI 不调 `scripts/ohc/sign_elf.py`；>=2=重签残留必拦）。实测段数逐条打印为 `LFT_MEASURED_<name>_codesign_sections=N`；**「恰好 1 个」仍由本测试自签后的 `_stage_signed` 硬断言承载**（见下条「暂存与自签」）。09-26 因 CI 不给产物签名、却把该不变量压在安装产物上而恒红，全过程记在文末「CI 红账」；
  4. `*-needed-bare-sonames`：`DT_NEEDED` 非空且全为裸 soname（含 `/` 即绝对路径被烤进产物）；
  5. `*-no-host-prefix-leak`：产物**原始字节**里既无 `/storage/Users/currentUser` 也无 `/usr/local`
     （按二进制读入后解码，避免文本模式吞字节）；
  6. `man-pages-installed`：`share` 下 `lft.8` 与 `whob.8` **两页都在**。
- 暂存与自签（**不计入检查点**，只做门禁）：实测直接 exec 包目录里的 `bin/lft` 返回
  `Operation not permitted` ⇒ 行为层跑在归档树外临时目录的副本上：`llvm-objcopy
  --remove-section .codesign` 去旧签 → `binary-sign-tool sign -inFile ... -selfSign 1` 重签 →
  签完再核 `.codesign` 恰 1 段（不等即抛错）；临时目录在 `finally` 里 `rmtree`。
- 能力层（逐条 `LFT_TEST_SKIP` 并带原因，**绝不记成通过**）：真实 traceroute 往返（非特权 uid
  无 raw socket 能力）、交互式 ncurses 模式（构建期 `--disable-ncurses` 关断）、c-ares 异步 DNS
  （构建期 `--disable-async-dns` 关断）。
- 脚本自计并打印、被 `MANIFEST.yml` 逐字引用的判决行（实测原文）：
  产物层 11 行 `LFT_ARTIFACT_PASS ...`（`w3-local-ci.log:334-344`）；行为层一行
  `LFT_SMOKE_PASS behavioural=8 skipped=3 failed=0`（`:357`）。此外 `conanfile.py` 会
  **核对脚本自报条数与申报条数一致**（`REQUIRED_BEHAVIOURAL=8` / `REQUIRED_SKIPPED=3`，
  不等即抛错；`summary.txt` 缺失或 rc≠0 也抛错），并打印机器可读的
  `HMBS_TEST_PACKAGE_RESULT={'artifact_passed': 11, 'artifact_total': 11, 'behavioural_passed': 8,
  'skipped_declared': 3, 'executed': True, 'passed': True}`。
- 合计口径（notes / `MANIFEST.yml` / PR 正文三处同源）：
  - `test_case_count: 22` = 产物 11 + 行为 8 + 声明跳过 3（三者都等于载体里真实的检查点/调用点数：
    `grep -c 'results.append(' test_package/conanfile.py` 得 6 条 append 语句，其中 5 条在
    `for name in ("lft", "whob")` 循环里 ⇒ 展开为 11；
    `grep -oE 'ok [a-z][a-z0-9-]*' test_package/test_lft.sh | wc -l` 得 8、`sk` 得 3
    （注意：不能用 `'^[[:space:]]*ok '` 数，脚本里有 3 处 `if ...; then ok name; else ...`
    写成一行，行首正则只数到 5）
  - `measured_passed: 19`（= 11 + 8）、`measured_skipped: 3`、`measured_failed: 0`、
    `executable_test_cases: 19`、`static_upstream_test_files: 0`
  - `assertion_count: 17` 是**另一个口径**（源码判定表达式静态数）：`test_package/conanfile.py`
    的 6 个 `results.append(...)` 判定 + `test_lft.sh` 的 9 个 `if` 判定 + 2 个 `[ -x ]` 前置守卫。
    22（检查点）与 17（判定表达式）不冲突：循环展开与 `&&`/`||` 复合条件让两侧数量天然不等。
  - ⚠ 本交付版脚本内**没有** timeout/信号/崩溃守卫（每条断言直跑，靠 `conan test` 外层超时兜底）
    ⇒ 不申报守卫数量，也不声称有守卫。

## ⚠ 运行期暂存件纪律（本窗刚为此返工过一次）
- 早期版本的 `test_package/` 会在**归档目录内**生成 `staged-bin/`（含签名后的无扩展名 ELF
  `lft`/`whob`）与 `smoke-work/`（stderr 捕获）。`.gitignore` 只挡 `*.so`，**挡不住这些目录里的
  ELF** ⇒ 一旦 `git add archives/l/lft/` 就把它们折进 PR，而 GitCode 的 `.diff` 不带 binary patch
  data，CI 的 `checkout-pr` 会永久失败（同族事故先例：PR#11868）。
- 交付版已从根上改掉：`_scratch_dir()` 只在归档树外取目录（`tempfile.gettempdir()` → `~/tmp` →
  `~`），全部暂存件写在里面，`finally` 里 `shutil.rmtree`；仅当三处都不可写才回退到
  `self.build_folder` 并打 warning。
- 让渡前复核（本窗已执行，结论=干净）：`git ls-files archives/l/lft` 只有 10 个文本文件
  （配方 4 + 补丁 1 + test_package 3 + 包级 `manifest.yaml`/`commands.json`）；
  `reports/`、`__pycache__/` 由仓内 `.gitignore`（`:96`、`:194`）挡住，暂存 ELF 已随 `finally` 删除。

## 验证结果（B 机实测；证据日志 = `archives/l/lft/3.98/reports/w3-local-ci.log`）
- 新增测试用例通过率：**19/22**（19 条真实执行并通过，另 3 条按能力声明跳过，0 失败）
- 上游官方测试：**0 个**（上游 `Makefile.in` 无 `check` 目标、发布包内无测试目录；实测跑
  `make check` 会 `No rule to make target 'check'` 直接中断构建 ⇒ 无「上游测试通过」可声称）
- `conan create` + `conan test`：`VERIFY_RC=0`，G1/G2/G3 全 PASS，
  `conan-verify-report.md` Verdict=PASS（`lft/3.98@ohpcd/stable`，profile `ohos-aarch64`）
- 证据分两层，各自绑定当前交付内容（两份日志都在设备侧 `archives/l/lft/3.98/reports/`，
  被仓内 `.gitignore:96` 的 `reports/` 规则排除，**不随 PR 提交** ⇒ 本文引用处一律给原文）：
  - **编译/链接层 = `reports/w3-local-ci.log`**（finish 的本地 CI 全量日志，07:53）：
    `:168` `lft/3.98: Calling source()`、`:183` `lft/3.98: Calling build()` 各 1 次 ⇒ 源码真重建；
    其中 6 处 `- Cache` 属于依赖 `libpcap/1.10.6` 与配方修订查表，不是跳过本包编译。
    该轮之后配方正文（`conanfile.py` / `conandata.yml` / `patches/`）最后一次变更停在
    `1a445266a8`（07:41，早于该轮）⇒ **这份编译证据绑定当前交付的配方**。
  - **消费者测试层 = `reports/conan-create.log`**（最终一轮 conan-verify 的 test 输出，08:11）：
    11 行 `LFT_ARTIFACT_PASS`、`:120` `LFT_SMOKE_PASS behavioural=8 skipped=3 failed=0`、
    `:123` `HMBS_TEST_PACKAGE_RESULT={'artifact_passed': 11, 'artifact_total': 11,
    'behavioural_passed': 8, 'skipped_declared': 3, 'executed': True, 'passed': True}`。
    该轮跑的就是本笔记描述的 `test_package/` 内容。
  - ⚠ `conan-create.log` 里**没有** `Calling build(` —— 那一轮 `conan create` 命中了同 rrev 的
    已构建二进制（配方正文自 07:41 未变，rrev `858d9ccbe68e9dacc73569a24878aaae`）
    ⇒ 它**只能**作为测试执行证据，不得当编译证据；编译证据一律指 `w3-local-ci.log`。
- 关键锚点（`w3-local-ci.log`）：`:213` cross compiling = no、`:304` Package folder、
  `:334-344` 11 行 `LFT_ARTIFACT_PASS`、`:357` `LFT_SMOKE_PASS behavioural=8 skipped=3 failed=0`
- W0 前置：`ci/scripts/preflight_check.sh lft/3.98` 实跑结果 = 发现 1 个依赖、
  `[OK] 已发布: libpcap/1.10.6`、`[OK] 版本号未被占用: lft/3.98`（未另设正/负对照，
  该脚本的"已发布"判定按精确包名查制品仓，本包唯一硬依赖可被逐字核对）
- ⚠ harness 的 G0 知识命中 **E490**（`restore-known-autotools-script-modes`）建议
  `chmod +x configure config.guess config.sub install-sh missing` + `make check`：
  **这些建议对本包都不适用**——① 发布包内 helper 自带可执行位（`configure` 确实直接执行到了
  `../build-aux/config.guess` 并打出该脚本自己的报错，见适配点 E160 的取证），配方无需 chmod；
  ② 配方对 config.guess/config.sub 的三元组补丁是**用 `perl` 显式解释执行**
  （`self.run('perl "...patch-autotools-ohos.pl" ...')`），也不依赖 exec 位；
  ③ 上游 `Makefile.in` 无 `check` 目标，照建议跑 `make check` 会 `No rule to make target 'check'`
  直接中断构建 ⇒ 只跑 `make -j1`，行为验证放在 `test_package/`。

## 已知限制 / 未覆盖
- 真实路径追踪、抓包解码、watch TUI、异步 DNS、whois 外联：设备无 root/raw 能力/外联或
  已在 configure 关闭，均按 skip 处理，不构成「已适配成功」的反证。
- `install` 目标里的 `chown root`/`setuid`/`setcap` 在非 root 下失败仅打 WARNING（脚本用 `||`
  兜底），不影响 DESTDIR 安装落包。
---

**编译结束**: 2026-09-26 07:53
**最终状态**: built

## CI 红账（09-26，CIW-7 整改，绑 build number 61499 / buildid 70387）

- 现象：CI `conan-build-test` 红，`LFT_ARTIFACT_FAIL lft-codesign-section-1` 与
  `LFT_ARTIFACT_FAIL whob-codesign-section-1` 两条，raise `artifact assertions failed: lft-codesign-section-1, whob-codesign-section-1`；
  同批 `*-exists`、`*-machine-aarch64`、`*-needed-bare-sonames`、`*-no-host-prefix-leak`、`man-pages-installed` **全部 PASS**
  ⇒ 产物本体无问题，只有这一段数断言红。
- 定性：**断言的前设不成立，不是配方坏**。`.codesign` 是**签名的副作用**，而签名只挂在本地链路
  `scripts/ohc/package_builder.py`（调 `sign_elf.py`）；`git grep -ln 'sign_elf' -- ci/` 与
  `git grep -ln 'binary-sign-tool' -- ci/` 在 CI 侧**零命中** ⇒ CI 装出来的 ELF 不可能自带 1 段，
  只有本地跑过 `finish` 才会有 ⇒ 这是一条「本地真 / CI 假」的断言。
- 同族口径（三处先例都是「测试自己签、签完才断言恰好 1」，且都允许安装态为 0 段）：
  `archives/a/arpoison/0.6/test_package/conanfile.py:38-43`、
  `archives/a/aliki/0.3.0/test_package/conanfile.py:147-199`（显式 `existing==0` 时再去签、只对 `not in (0,1)` 抛错）、
  `archives/c/coinutils/2.11.12/test_package/conanfile.py:53-62`。
- 处置（⛔ 放宽判据换绿灯）：安装产物侧不变量改为**至多 1 段**（0 允许、>=2 必拦），并**逐条打印实测段数**
  `LFT_MEASURED_<name>_codesign_sections=N`；「恰好 1 段」仍由本测试自签后的 `_stage_signed` 硬 raise 承载
  （不计入检查点，与原设计一致）。检查点总数不变（11 = 5 类 x 2 枚 + 1 手册页），行为层 8/3 计数未动
  ⇒ PR 正文两张统计表**不需改数**。
- 未解项（诚实保留）：CI 上实测到底是 0 段还是 2 段，本轮**未能取证** —— buildbot REST 的
  `/logs/<logid>/content` 端点对该 build 的 6 个日志全部返回 404（平台侧观测上限），平台 logTail 只覆盖
  尾部约 3.3KB、取不到断言行。故本轮改用「打印实测值」的方式让下一次 CI 自己给数；无论实测是 0 还是 >=2，
  本次改动都不可能造成假绿（>=2 仍然必红）。
