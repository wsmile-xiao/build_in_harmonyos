# rephrase 0.2 — OHOS 适配记录

- **适配路径**：A（直改配方 + 2 个可移植性补丁）＋ **路径 B 判定 = `hit`（E051）**，本 PR 不升 create、不新建 Issue
- **使用知识库**：E051（`knowledge/graph/E051.kv`）、`knowledge/graph/principles.kv` L179-181（syscall 面差异不可用环境变量/编译参数消掉）；
  补丁写法口径取 `knowledge/drafts/DRAFT-E577-buffer-sysv-ipc-posix.kv`:43,74（逐字宣告 E051 的宏守卫旧方案已因 R8/PF5 失效）
  与 `references/iron-rules.md` R8；`rindex` 口径取 `knowledge/drafts/DRAFT-cconv-0.6.3-rindex-strrchr.kv`
- **知识库扩展**：无（`rindex`、`/dev/tty` 两族在 `knowledge/drafts/` 已有专条，不得由本 PR 主张；详见 §7）
- **关联 Issue**：不适用（路径 B 判定 = `hit` ⇒ 本 PR 不主张新条目，按仓规不建【知识库扩展】Issue；`rindex` 与 `setreuid`/`/dev/tty` 两族均已有既有条目或专条，详见 §7）

## 0. 一句话结论

`rephrase 0.2` 在 HarmonyOS PC（aarch64 / OHOS / musl，clang-15 `aarch64-unknown-linux-ohos`）上
`conan create` + `test_package` 全绿。判绿只押**三一致**（文字 PASS + `**Verdict**` 行 + rc）：
`reports/conan-verify-report.md` 第 3 行 `**Verdict**: PASS` 且 `VERIFY_RC=0`、
`finish` 的 `EXIT_CODE: 0` 且 W3 判决件 `exit_code=0`、消费者断言 **5/5**（`grep -c "^\[PASS\]"` 得 6 = 5 断言行 + 1 汇总行）。
⚠ 本报告生成侧的图标可与文字相反（既有实拍 `✅ G2: FAIL`、`G4 ✅ PASS` 却写"无法找到程序包 ID"），
故 G0-G4 与 L2/L4/L5 的图标**不作证据**，只作披露。源码零功能阉割，仅两处可移植性补丁（补丁内无平台宏）。
上游"口令穷举主流程"因**运行环境**未执行：OHOS PC 不提供 gpg/cryptsetup，且主流程的 stat 守卫先于读 tty（tty 能力面另按仓内既有 pty 路线实测为**可用**，见 §5 未执行清单 S1）。

## 1. 上游事实（全部盘上实测，非引用 SCT 预判）

| 项 | 实测值 | 取证命令 |
|---|---|---|
| 原始归档 | **上游作者官方源** `https://www.roguedaemon.net/rephrase/rephrase-0.2.tar.gz` → `rephrase-0.2.tar.gz`，25587 B，HTTP 200 | `curl -sSIL/-sSL -w 'GET_status=%{http_code} size=%{size_download}'`；2026-09-25 03:11 本窗设备侧复算 `HEAD_status=200 GET_status=200 size=25587` |
| SHA-256 | `54d5bb9f3d7a0e179af1a4569d1ad67a90037ab501380da096ec0eb1fcd473bf` | 官方源落盘 `sha256sum` 与 `conandata.yml` 现值**逐字**相同（**换 URL 未改哈希**）；与 Debian `Sources` 索引 `Checksums-Sha256` 段亦一致（pool 件仅留旁证） |
| 文件数 | 7（CHANGELOG COPYING Makefile README install-sh mkinstalldirs rephrase.c）；`tar tzf` 输出 8 条目 = 1 个前缀目录 `rephrase-0.2/` + 7 个文件 | `tar tzf official.tar.gz`（本窗复算 `N=8`） |
| 语言 | C，源文件 1 个（`rephrase.c`，11811 B） | `ls rephrase-0.2/*.c` |
| 构建系统 | 裸 Makefile（无 configure / 无 autotools / 无 cmake） | 直读 `Makefile` |
| 编译期外部依赖 | **零**：`grep -in "libs\|ldflags\|-l" Makefile` **返回空** | 见左 |
| 链接需求 | 仅 libc（`termios` / `mlock(2)` / `fork`+`execv`+`waitpid` / `stat`） | `grep -n include rephrase.c` |
| **pty 使用** | **无**：`grep -n "openpty\|forkpty\|ptsname\|grantpt\|unlockpt" rephrase.c` **返回空** | 见左 |
| tty 使用 | 仅 `fopen("/dev/tty","r+")` + `tcgetattr`/`tcsetattr`（关回显读口令） | `sed -n '111,180p' rephrase.c` |
| 用途 | GnuPG / Cryptsetup-LUKS **口令变体恢复**（穷举用户自给的候选组合） | `sed -n '26,60p' README` |
| 运行期依赖 | `gpg`（默认 `/usr/local/bin/gpg`）、`cryptsetup`（默认 `/sbin/cryptsetup`），路径编译期烧死 | `grep -n "GPG\|CRYPTSETUP" rephrase.c` |

## 2. 障碍一：`rindex` 在 musl 上不存在（链接期）

- **症状**：`G2 conan create` 失败，`ld.lld: error: undefined symbol: rindex`。
- **根因（钉死为符号裁剪）**：`rephrase.c:443` 用 legacy BSD `rindex(s,'/')` 取 basename。glibc 有 `rindex`
  兼容符号，**OHOS libc（musl 系裁剪）未导出 `rindex` 符号**。声明面读数（**证据保全如实交代**：首适期那两条 `ld.lld: error: undefined symbol: rindex` 与提示 `did you mean: index` 的原始日志，已被成功轮的 `reports/conan-create.log` 覆盖、现件 0 命中，r2 审计亦未起编译复算 ⇒ 下面两句按「当时观察到」而非「本轮可复算」记账）：编译期不报隐式声明、失败只落在
  链接期 ⇒ 声明在、导出符号不在；`ld.lld` 报错同时提示 `did you mean: index` ⇒ `index` 在而 `rindex` 不在，
  当下**可原样复算**的锚点是 `grep -c implicit reports/conan-create.log` = **0**（该翻译单元编译段无隐式声明告警，错误只落在链接期）。综合定性为**符号裁剪**而非"无 BSD 兼容层"（与既有专条 `DRAFT-cconv-0.6.3-rindex-strrchr.kv` 的 root_cause 同口径）。
- **最小复现**：`printf 'main(){return (int)rindex("a/b","/");}' > t.c; clang t.c` → 同样 undefined symbol。
- **失败方案（已试，勿重复）**：`-lutil` / `-lcompat` 补符号 —— OHOS 无这两个库，且问题不是"缺库"而是"缺符号"，
  引库方向本身错。
- **最终方案**：`patches/0001-musl-no-rindex-use-strrchr.patch` —— `rindex (p, '/')` → `strrchr (p, '/')`，
  1 处、逐字等价（`rindex` 与 `strrchr` POSIX 语义相同），属纯改名，无行为变化。
- **适用边界**：任何 2003-2006 年代 glibc 惯例写法用 `index()`/`rindex()` 的 C 包。

## 3. 障碍二：`setreuid`/`setregid` 被鸿蒙判 SIGSYS（命中 E051）

- **症状**：补丁 0001 后编译链接打包全过，但产物**打印版本横幅后立即死**，退出码 **159**
  （= 128+31 = SIGSYS），`test_package` 5 条断言里 4 条红。
- **根因**：`main()` 在 `mlock()` 之后无条件调用 `setreuid(getuid(),getuid())` 与
  `setregid(getgid(),getgid())` 丢弃 root 特权。**鸿蒙内核对这两个 syscall 直接判 Bad system call**，
  且按 E051：该 SIGSYS **不可被 `signal()`/`sigaction()` 捕获**，进程当场终止 ⇒ 任何 handler 方案均无效。
- **最小复现 + 边界探针**（`open()`/调用系，逐条 fork 隔离，阳性对照同进程）：

  | syscall | 结果 |
  |---|---|
  | `getuid()` | OK |
  | `mlock(2KB)` | **OK**（rephrase 的 setuid 门禁本身过得去） |
  | `setuid(getuid())` | **OK** |
  | `seteuid(geteuid())` | OK |
  | `setresuid(u,u,u)` | OK |
  | `setgid(getgid())` | **OK** |
  | `setreuid(u,u)` | **KILLED by signal 31（Bad system call）** |
  | `setregid(g,g)` | **KILLED by signal 31（Bad system call）** |
  | `fork`+`_exit` | OK |

  ⇒ 缺陷面**精确到 `setre{u,g}id` 这一对**，不是"改权限的 syscall 全禁"，也不是 uid 空间/权限不足。
- **定性（三者不混写）**：这是 **OHOS 内核 syscall 实现面差异**（E051 归口），
  **不是**配方缺陷、**不是**权限/能力面问题、**不是**上游逻辑 bug。
- **失败方案（已试，勿重复）**：
  ① 装成 setuid root 绕不过——SIGSYS 发生在 syscall 派发期，与有没有 root 无关；
  ② `signal(SIGSYS, handler)` 捕获——E051 明文禁止（`forbid_1_pattern`），进程直接被 kill，handler 从不被调用；
  ③ 仅靠 `LD_PRELOAD`/编译参数绕过——该类差异无法用环境变量或编译参数消掉（principles.kv L179-181）。
- **最终方案**：`patches/0002-portability-setreuid-setregid-to-setuid-setgid.patch` ——
  把两处调用**无条件**换成实测放行的 POSIX 等价物 `setuid(getuid())` / `setgid(getgid())`，
  原 `exit (3)` / `exit (28)` 分支语义逐字保留，**补丁内不含任何平台宏**。
  **为什么不再用宏守卫**：`knowledge/drafts/DRAFT-E577-buffer-sysv-ipc-posix.kv:43` 逐字写明
  "E051 的推荐方案是 __OHOS__ 宏守卫，已因 R8/PF5 失效；本条目给出的是无平台宏的等价替换路线"，
  同件 :74 的 `forbid_1_reason` 同向；`references/iron-rules.md` R8 的例外档要求"无 POSIX 等价物"，
  本例有等价物 ⇒ 不属例外（`principles.kv` L100-102 的旧口径已被其自身后继条目推翻，本轮改从 drafts）。
  **丢权语义不是削弱而是严格更强**：本包不装 setuid，两调用本是 no-op（euid!=0 时 `setuid(getuid())`
  按 POSIX 直接成功返回）；而当 euid==0 时 `setuid()` 同时清除 real / effective / **saved-set** 三个 id，
  `setreuid(getuid(),getuid())` 只改 real+effective、不清 saved-set ⇒ 换后残留特权更少。glibc/musl/OHOS
  三侧该语义一致，故无需分流。
- **差分证据（证明是补丁 0002 起作用，而非环境漂移）**：conan 缓存里两版产物并存，
  `strings | grep -c setreuid` 与退出码严格对应：

  ```
  .../p/b/rephr140ace5837109/p/bin/rephrase  mtime=02:38  setreuid=3  rc=159   # 只有补丁 0001
  .../p/b/rephra80f90aff3ad7/p/bin/rephrase  mtime=02:43  setreuid=0  rc=7     # 0001+0002（宏守卫版）
  .../p/b/rephr4c08d67b53334/p/bin/rephrase  mtime=03:22  setreuid=0  rc=7     # 0001+0002（**去宏守卫版**，本轮）
  ```
  本轮（整改后重跑）新增第三枚 package id 佐证：`rephr4c08d67b53334` 由去掉 `#ifdef` 分流的补丁 0002 构建，
  `strings | grep -c setreuid` 仍为 0、`test_package` 仍 5/5、产物 35200 B 与宏守卫版同尺寸
  ⇒ 去掉平台宏在 OHOS 侧行为不变（`__OHOS__` 由目标三元组预定义，两版走的是同一条 code path）。
- **适用边界**：任何沿用"`setreuid`/`setregid` 丢 root"这一 BSD/glibc 时代惯例的安全向 C 工具
  （口令/加密/特权辅助类）。同族包遇到 exit 159 时，先按上表逐 syscall 定位，再用无平台宏的 POSIX
  等价替换；不要整片宏关掉功能，也不要在补丁里注入平台宏（R8/PF5 直接拦）。

## 4. 刻意偏离上游的两处（及理由）

1. **不调用 `make install`**：上游 `install` 目标**必须以 root 运行**且
   `./install-sh -c -o 0 -g 0 -m 4711` —— `binmode = 4711` 即 **setuid root**。
   制品包里携带 setuid-root 二进制不可接受。⇒ `package()` 直接 `copy` 出 `bin/rephrase`。
   实测该偏离**不损功能**：`RLIMIT_MEMLOCK` 在本机为 `cur=-1 max=-1`（unlimited），
   故 `mlock()` 门禁在无 setuid 下照常通过（test_package T1 与 test_ohos T4 双重印证）。
   注：`ls -l` 实测产物 `-rwxr-x---`，HMDFS 上 conan copy 未把 `chmod 0755` 落住；
   安全断言只押"无 setuid/setgid 位"，不押 group/other 位（已在 `run_ohos_test.sh` T3 注明理由）。
2. **`prefix=/usr/local` 未被使用**：需更正一处预判——它**不是"烧死不可覆盖"**，
   而是普通 `=` 赋值（非 `?=`），命令行 `make prefix=...` 可覆盖，且 `install` 规则本就支持 `$(DESTDIR)`。
   本配方不走 install 目标，故该可覆盖性未被利用。

## 5. 测试账本

**上游测试（静态发现 → 五维）**：`Makefile` 只有 `all / dist / install / clean / distclean` 五个目标，
`grep -n "check\|TEST\|test" Makefile` 无任何测试目标，无 `test/`、无测试框架绑定。
取证：`tar tzvf rephrase-0.2.tar.gz`（8 条目 = 1 个顶层目录 + 7 个文件 CHANGELOG/COPYING/Makefile/README/install-sh/mkinstalldirs/rephrase.c，无测试件）。⚠ 件名按 W4 r2 的 P2 更正：本轮实际取源件是**官方** `rephrase-0.2.tar.gz`，旧文写的是换源前的 Debian `rephrase_0.2.orig.tar.gz`，照抄原命令会因缺文件而复算失败（数字本身不变）。+ `grep -n "^\.PHONY" Makefile`。

| 静态总数 | 可执行数 | 实测通过数 | 跳过数 | 失败数 |
|---|---|---|---|---|
| **0** | **0** | **0** | **0** | **0** |

分母未因平台跑不动而缩小 —— 上游本来就 **0** 条。四处同源一致：
`test_package/MANIFEST.yml`（`assertion_count: 5` / `test_scenario_count: 5`，`upstream_tests: []`）、
`test_package/test.sh` 实打 **5 条断言行**（`test.sh:30` 的 `ok()` 每次输出 1 行 `[PASS] <Tn>`）、
`test_package/conanfile.py` 下限 **5**、本文件 **5**。
**口径钉死**：`test.sh:80` 还有一行以 `[PASS] counted=…` 开头的
**汇总行**（非断言），故对日志 `grep -c "^\[PASS\]"` 得 **6** 而非 5 —— **断言数本身仍是 5**，
为凑数改逻辑（改前缀/加断言）一律不做。

**自造消费者断言（`test_package/test.sh`，执行已安装二进制，退出码+stderr 判定）**：**5/5 PASS**

```
[PASS] T1 bare invocation exits 7 (usage path reached; mlock(2) passed without setuid)
[PASS] T2 banner carries version 0.2 (upstream Makefile DEFS -DVERSION is baked in)
[PASS] T3 usage line matches the compiled-in profiles[] table
[PASS] T4 --luks exits 4 naming /sbin/cryptsetup (baked path + stat() guard)
[PASS] T5 unknown profile option exits 7 (argument parser rejects it)
---
[PASS] counted=5 required=5 failed=0
rephrase 0.2 consumer test: 5/5 assertions PASS
```

**OHOS 专项（`test_ohos/run_ohos_test.sh`）：6 PASS / 0 FAIL / 2 跳过**（T1 AArch64 ELF、T2 无宿主路径泄漏、
T3 无 setuid 位、T4/T4b mlock 门禁+无 setuid 抱怨、T5 `--gpg-key` 命中 `/usr/local/bin/gpg`）。

**未执行清单（功能面，如实申报，不伪造通过）**：
1. `S1` 交互读模式路径（`read_pattern()`，`rephrase.c:111-182`，第 118 行 `fopen("/dev/tty","r+")`）—— **未执行**，
   但**已按仓内既有 pty 路线实测**（`knowledge/drafts/DRAFT-E5xx-tui-app-pty-test-harness.kv` 的 `pty.fork` 驱动；
   证据 `~/tmp/uc2/z32b-rephrase/probe_pty2.py` + 同目录 `s1-pty-probe2.log`；整改重构建后对**新产物**
   `p/b/rephr4c08d67b53334/p/bin/rephrase` 复跑同一探针得 `s1-pty-probe3.log`，读数逐字相同）：
   - **tty 能力面本身在真实 ctty 下全绿**：`pty.fork()` 子进程实测 `open("/dev/tty")=OK fd=3`、
     `os.ttyname()` 解析到 pts 从端（同法 shell `tty` 输出 `/dev/pts/1`，`TTYRC=0`）、
     `tcgetattr=OK echo_before=1` → 清 `ECHO|ECHOE|ECHOK|ECHONL` 后 `tcsetattr(TCSAFLUSH)=OK echo_after=0`、
     写 `Enter pattern: ` 后按上游同款**逐字节 `read(fd,1)`** 回喂 6 字节得 `read_back=b'abcde'`（遇 `\n` 截断）、
     恢复 termios 后 `echo_restored_flag=0`，探针进程 `CAP_RC=0`。
     ⇒ 先前的 `/dev/tty` `open()`=**ENXIO(6)**（阳性对照 `/dev/null`=OK、`/dev/ptmx`=OK、`/dev/pts/ptmx`=ENOENT、
     `/dev/console`=EACCES）**只是"本进程无 ctty"的环境属性，不是 OHOS 终端能力缺失**；旧口径已按此更正。
   - **`S1` 仍不可执行的具体原因（与终端能力无关）**：`read_pattern()` 的唯一调用点在 `rephrase.c:479`，其前面
     第 463-477 行是**编译期烧死的** `conf.path`（`/usr/local/bin/gpg`、`/sbin/cryptsetup`）`stat()` 守卫。
     同一 pty 下实测真实二进制：`rephrase gpg-key` → **rc=4**、`rephrase --gpg-key k` → **rc=4**，
     stderr 均为 `/usr/local/bin/gpg does not exist (or is in a directory I cannot read)`
     ⇒ 程序在**到达 `read_pattern()` 之前**就已退出。跨过这道守卫须在设备系统树新建 `/usr/local/bin/gpg`
     （红线：不碰系统区、不为凑绿灯造假日志），且跨过后仍需真实 gpg/cryptsetup 才能走完 `find_passphrase()`。
     即 pty 路线对本用例不适用的根因是**上游缺依赖**，正是 `S2` 同一条。
2. `S2` 口令穷举主流程 —— `command -v gpg` / `command -v cryptsetup` 均 **NOTFOUND**，
   `fork`+`execv` 目标不存在；`main()` 的 `stat(conf.path)` 守卫先行，故实测以 exit(4) 终止（即 T4/T5 断言的行为）。

## 6. 门禁读数（原文，含框架面存量红）

| 门禁 | 读数 |
|---|---|
| `bash ci/scripts/preflight_check.sh rephrase/0.2`（**W0 依赖预检，与下面 §6.1 的 PF1–PF9 不是同一物**） | `W0_RC=0`，`[OK] 预检通过（无依赖需要检查）`（本包零依赖 ⇒ 必绿；此前各轮报的"preflight rc=0"仅指这一条） |
| `scripts/ohc-run.py recipe-search rephrase` | `SEARCH_RC=0`，top1 = 本包骨架（catalog 首次自动重建 6175 配方） |
| `scripts/ohc-run.py build rephrase 0.2` | `BUILD_RC=2` —— `EXIT_REASON: init_build_failed`、`STEP_FAILED: Step1`（见下行说明，非本包缺陷） |
| `scripts/ohc-run.py conan-verify rephrase 0.2` | **03:21 重跑（换源 + 去宏守卫后）**：`VERIFY_RC=0`；`reports/conan-verify-report.md:3` = `**Verdict**: PASS`；G0/G1/G2/G3/G4 五行文字均 PASS（图标不单独引证，见 §0 口径）；日志尾 `✅ 配方验证通过: rephrase 0.2`、`SLOT_DONE:ok` |
| `scripts/ohc-run.py finish rephrase 0.2 built` | **03:22 已执行**：外层 `FINISH_RC=2` 与判决 `EXIT_CODE: 0`、`EXIT_REASON: finish_success` **并存**（`STEP_FAILED: Step6`；框架存量非阻塞，本窗未为此改 `scripts/`）；`Step 5/10: 本地 CI 模拟 (W3)` → `✅ W3 本地 CI 模拟通过`；判决件 `0.2/.ci-result.json`（358 B）`timestamp=2026-09-25T03:22:18.951223`、`exit_code=0`、`integrity_hash=75597fd731288790`＝本窗按 `sha256("<timestamp>:rephrase:0.2:<exit_code>")[:16]` **复算逐字一致**、`log_sha256=eca863c92daeca77b0cec68c4d9ac59a06426e7d810c42987e6de13d0b553ae3` ＝ `sha256(reports/w3-local-ci.log)` **全串相等**；`reports/w3-local-ci.log` 12120 B / 03:22 / md5 `a38cf7556cb3`，与 `reports/conan-create.log` 5268 B / md5 `d74ed60f69af` **不同**（W3 日志非 create 日志的副本）；该 w3 日志内 `grep -c "^\[PASS\]"` = **6**、`roguedaemon` = 1、`deb.debian.org` = 0、`__OHOS__` = 0 |
| `scripts/ohc-run.py graph validate` | **03:22 已执行**：`GRAPH_RC=0`，Coverage 540 entries（`forbid_*` 366/540=67%、`fallback` 376/540=69%、`principles` 158/540=29%、`auto_fix` true=130 / false=400） |

### 6.1 PF1–PF9 源码闸真实读数（本窗首跑；此前各轮从未执行）

命令：`python3 scripts/ohc/preflight.py . origin/main HEAD`（worktree 根；base = `origin/main`）

| 轮次 | head | rc | 命中 |
|---|---|---|---|
| 改前 | `1a53b2e9` | 1 | **PF5** 补丁平台宏闸（R8）：`patches/0002-ohos-…patch:7` 新增 `__OHOS__`；**PF7** 源URL闸（R39）×2：`0.2/conandata.yml:7`、`0.2/manifest.yaml:11` 的 `deb.debian.org`；PF9（框架存量，见下） |
| 改后 | 本轮整改提交 | 1 | **仅 PF9**；**PF5 = 0 命中、PF7 = 0 命中** |

- **PF5/PF7 已归零且不需要 `--no-preflight`、不需要例外登记**：PF5 靠去掉宏守卫（§3），PF7 靠换成上游作者官方源（§1，sha256 未动）。
- **PF9 是框架自相矛盾，只披露不改**：PF8/R38 强制 CLI 包提供**软件级** `commands.json`、G1 结构件又要求软件级 `README.md`/`manifest.yaml`，而 PF9 判据 `len(f.split("/")) < 5`（`scripts/ohc/preflight.py:570`）必然拒绝任何软件级新文件；`preflight.py:31-32` 即该要求所在。仓内 37 个既存归档带同类软件级件。⇒ 本包 PR 面材料**仍带 `--no-preflight`，且理由只剩这一条存量冲突**（不再包含 PF5/PF7）；修 PF9 豁免属框架改动，须单开 PR，归主窗上报，本窗未碰 `scripts/`、`ci/`。
- 框架面其余存量红（同口径**只记不修**）：step5b `unreferenced`、step8 `gen_summary`、step3 `G0 找不到原始 tarball`、step10 `packaging`/`.staging-verified`/`test-report`；以及 verify 报告把 `G4 ✅ PASS`（正文"无法找到程序包 ID"）与 `L2/L4/L5 ✅ PASS ⏭️ 跳过` 记成绿灯——本窗**不引用这些图标作功能证据**，功能证据是 w3 日志内 `test.sh` 实跑 6 行 `[PASS]`（5 断言 + 1 汇总）与 `conan-create.log`。
- **`EXIT_CODE: 0` 与外层 `FINISH_RC=2` 并存**这一事实此前通篇未披露，本轮起如实登记（见上表 finish 行）。

- **`ohc-run build` Step1 红是码路错配，不是构建失败**：Step1 断言 `archives/r/rephrase-0.2/src` 存在，
  那是 `init-build` 的探索期暂存布局；手写配方直接落在归档布局 `archives/r/rephrase/0.2/`，两者不同码路。
  该步随即自行转 `init-build` 并把 `rephrase` 误猜成 Savannah 项目去搜 `download.savannah.nongnu.org`
  （**错误上游**）。**否证记录**：本包与 Savannah 无任何关系——上游作者主页 `https://www.roguedaemon.net/rephrase/`
  （已写入软件级 `manifest.yaml` 的 `homepage`），官方 tarball 亦在该域下（本窗实测 HTTP 200 / 25587 B / sha256 与配方现值逐字相同），
  故 init-build 的 Savannah 猜测是**错的**，其 `download.savannah.nongnu.org` 取源路径不得采纳。
  按既有纪律：**不伪造 src 目录、不重跑 init-build 覆盖手写配方**，且**不跑 `ohc-run.py build`**（本批已两次实拍它会断言探索期布局并覆盖手写配方）。
  真正的构建/链接/打包/测试门禁由 `conan-verify` 的 G0–G4 承担，已全绿。
- **槽位与内存**：两次构建均由 `build-slot.sh --kind short --mem 2500` 起、`SLOT_DONE:ok` 收；
  `gate.sh 2500` 两次 `GATE_PASS`（`MemAvailable=12459MB` / `11166MB`，`PSI_full=avg10=52~54`，load≈20）。
  本轮整改重跑同口径：`gate.sh 2500` → `GATE_RC=0`、`GATE_PASS: MemAvailable=9513MB MemFree=824MB swap余=49971MB PSI_full=avg10=60.94 load=20.1`；
  verify 与 finish 各占一次机动槽、均以 `SLOT_DONE:ok` 收（`build-slot.sh --kind short --mem 2500 --wait 3600`）。
  ⚠ 派单时"B 机只剩约 1GB 可用"的口径不准：`MemFree` 确实只有 ~820MB，但 gate 判据 `MemAvailable` 有 11-12GB。
- 本轮**未**修改 `scripts/`、`ci/`、他人归档、`knowledge/graph/` 正式条目、`经验文档/`；
  未 kill 任何他人进程（`rephrase` 相关进程全部由本窗起、自然结束）。

## 7. 本窗对预扫假设的复算结论（改前 → 改后）

| 假设 | 判决 | 改前 → 改后 |
|---|---|---|
| 源码 URL / 25587 B | **证实** | 无需改 |
| 语言 c、c=1 | **证实** | 无需改 |
| 构建系统 make、共 7 文件 | **证实** | 无需改 |
| 单 Makefile 且 `/usr/local` **烧死** | **部分推翻** | 烧死不可覆盖 → `prefix = /usr/local` 是普通 `=`，命令行可覆盖且 install 支持 `$(DESTDIR)`；**真正的坑是 `binmode = 4711` setuid root + `install` 需 root**，假设里没提 |
| 零外部依赖 | **证实** | `Makefile` 无任何 `LDLIBS/LIBS/LDFLAGS/-l` 行；无需因 `-lutil` 停手 |
| 用到 `openpty`/pty（本包最可能出问题的点） | **推翻（假前提）** | 全文无 `openpty/forkpty/ptsname/grantpt/unlockpt`，§3 的 a/b/c 三岔路不成立 → 真实 tty 面只有 `/dev/tty` + `termios`；**最可能出问题的点实际是 musl 缺 `rindex` 符号（链接期）与 `setreuid/setregid` SIGSYS（运行期）** |
| B 判定 | **`hit`（E051）** | 机制一句话：鸿蒙对 `setreuid`/`setregid` 判不可捕获的 SIGSYS(exit 159)，须换成放行的 `setuid`/`setgid` —— **E051 已逐字记载该机制与禁令**，非新知识（本轮补丁已按 R8/PF5 去掉宏守卫）。**查重口径（本轮重做）**：同批扫四范围 = `knowledge/graph/*.kv` + `knowledge/graph/index.tsv` + `knowledge/drafts/*.kv` + `archives/**/notes.md`；
  本窗设备侧复算命中文件数：`setreuid` → graph 2 / index.tsv 1 / drafts 4 / archives-notes 7；
  `rindex` → graph 0 / index.tsv 0 / **drafts 7** / archives-notes 27；`/dev/tty` → drafts 6。
  命中件名：SIGSYS 系 = `knowledge/graph/E051.kv`（`error_signature` 含 `setreuid.*killed|setregid.*SIGSYS`，
  `verification_cmd` 即 `os.setreuid(0,0)` → 预期 159）+ `principles.kv` L179-181；
  rindex 系 **drafts 已有 ≥4 条专条** = `DRAFT-cconv-0.6.3-rindex-strrchr.kv`、`DRAFT-irqbalance-1.9.4-rindex-strrchr.kv`、
  `DRAFT-rdma-core-61.0-rindex-strrchr.kv`、`DRAFT-motif-2.3.8-musl-no-rindex-xpm-guard.kv`；
  tty/pty 系已有 = `DRAFT-E5xx-tui-app-pty-test-harness.kv`、`DRAFT-E569-mdp-stdin-tty-freopen-pty-dual-channel.kv`、
  `DRAFT-ired-0.6-interactive-tty-wrapper-exclude-headless-l2.kv`、`DRAFT-pty-driven-interactive-test-traps.kv`。
  **结论：本 PR 主张 `hit`(E051)，路径 A + 路径 B 判定 = hit，不升 create、不新建 Issue** —— `rindex` 与 `/dev/tty`
  均不得由本 PR 主张（drafts 里已有专条）；上一轮"知识库零命中"是**只扫 `knowledge/graph` 的假前提**，已被否证并更正。
  唯一具备新知识潜质的对照（`open("/dev/tty")`=ENXIO 无 ctty / pty 下有 ctty 时 =OK，而 `open("/dev/ptmx")` 恒 OK）
  转交主窗写入 `经验文档/B草稿库/` 通用池，本 PR 不主张、不建 Issue。 |
---

**编译结束**: 2026-09-25 03:22
**最终状态**: built
