# W4 独立审计判决件（人读版）— memdump 1.01

- 审计棒：**z74-memdump-w4b**（只读独立审计，重派轮；前棒 z74-memdump-w4 只留取证件、未交判决件）
- 委托窗：主理-74（Windows 侧，构建机 = B）
- 对象：B 机 worktree `~/qzy/主理-74-memdump-1.01`，分支 `feat/memdump-1.01`，归档 `archives/m/memdump/1.01/`
- **verdict = pass**（P0=0、P1=0、P2=3、P3=3；P2 三项须在建 PR 前回填，均非构建/门禁阻塞）
- 全部读数为本轮亲手重跑，未引用前棒 `raw-evidence-r*.txt` 的任何数字。

---

## 0. 坐标复验（先过这一关）

| 项 | 命令 | 读数 |
|---|---|---|
| HEAD | `git rev-parse HEAD` | `d2cbd7ed9c90146dbfdd9c12b8807875a820434b` ✅ 与委托一致 |
| 分支 | `git rev-parse --abbrev-ref HEAD` | `feat/memdump-1.01` ✅ |
| 远端同名分支 | `timeout 60 git ls-remote origin refs/heads/feat/memdump-1.01` | `d2cbd7ed9c…  refs/heads/feat/memdump-1.01` ⇒ **远端 == 本地** ✅ |
| 最后一次动归档的提交 | `git log -1 --format=%H -- archives/m/memdump` | `d2cbd7ed9c…` ✅ |
| 工作树 | `git status --porcelain -- archives/m/memdump` | 空（clean）✅ |
| 入库文件数 | `git ls-files archives/m/memdump` | 12 件（conandata/conanfile/manifest/notes/patch + test_package 4 件 + 包级 README/commands/manifest）|

---

## A. W2 结构 / 取源 —— 合格

1. **官方址**：`conandata.yml:24` = `http://www.porcupine.org/forensics/memdump-1.01.tar.gz`（作者 Wietse Venema 本人主机）；R39 原文 `docs/ADAPTATION_GUIDE.md:400`（"必须指向官方正式源或权威镜像"）；明文 http 的先例我实读到 `archives/c/cwebx/3.52/conandata.yml:11` 同为官方 http 址。
2. **file:// / 池址扫描**：`git grep -nE "file://|deb\.debian\.org|archive\.ubuntu\.com" -- archives/m/memdump` ⇒ 配方三件（conandata / conanfile / manifest）**零命中**；命中只在 `notes.md:137`（Ubuntu 池，写在"已试过的失败方案"叙述里）与 `notes.md:143`（描述 CI 预下载形态的字符串 `file://`）。台账给的 `deb.debian.org/.../memdump_1.01.orig.tar.gz` **未出现在任何取源字段**，只被用作哈希交叉核验 ✅。
3. **哈希声明 vs 实算**（三条一手）：
   - `curl -sS --max-time 90 http://www.porcupine.org/forensics/memdump-1.01.tar.gz` → `curl_rc=0`、12713 B、`sha256 = 76de8ff167d0779d6c3b2f2f52ca9d1cc22af179c51e976fe6e3b9a5d1e5799f` == `conandata.yml:25`（也与台账池址前缀 `76de8ff167` 同值）；
   - 构建实物体 `.build-cache/predl_cache/a15b713b_memdump-1.01.tar.gz`：同值，`head -c 2 | od` = `1f 8b`（gzip）；
   - `gunzip -c 实物体 | sha256sum` = `179ea799af3dfb7aa7b219bc06a9038f30726e6d81978046ddf4f91c2558c2c4` == `conandata.yml:26` 的 `sha256_uncompressed` ⇒ "同一份字节两种传输形态"的申报为真。
4. **补丁登记**：`conandata.yml:28-32` 有 `patches: - patch_file: "patches/0001-memdump.c.patch" … patch_type: "portability"`，`conanfile.py:84 export_conandata_patches` / `:104 apply_conandata_patches` / `manifest.yaml:26-27 patches_applied` 四处同名 ⇒ **无漏登记**（P1 不成立）。

## B. 运行面与交付口径 —— 合格，无过度宣称

1. **设备节点（我亲手探）**：`python3` stat+open 探针输出
   `/dev/mem stat FAIL errno= 2 No such file or directory` / `/dev/mem open RDONLY FAIL errno= 2` / `/dev/kmem` 两条同 ENOENT；`ls -l /dev | head` 见 ashmem/binder 等节点、无 mem/kmem；对照 `head -c 80 /proc/iomem` 有读数（ramoops 段）⇒ **ENOENT（节点不存在）而非 EACCES/EPERM**，且不是整个 procfs 不可用。与 `notes.md:181-188` 逐字同形。
2. **制品真执行**：`/storage/Users/currentUser/tmp/ch/home-memdump/p/b/memdue9265e9ba46f1/p/bin/memdump`（39360 B，mtime 01:09）

   | 调用 | rc | 第一条真实 stderr（原文） | stdout |
   |---|---|---|---|
   | `-s 4k` | 1 | `…/bin/memdump: open /dev/mem: No such file or directory` | 0 字节 |
   | `-k -s 4k` | 1 | `…: open /dev/kmem: No such file or directory` | — |
   | `-Z` | 1 | `…: unrecognized option: Z` + `usage:` 横幅 | — |
   | `-v -s 4k` | 1 | `dump size 0x1000` / `page size 0x1000` / `buffer size …` | — |

   ⇒ 可执行、无签名问题，且与 notes.md:192-200 表逐条吻合。`readelf -d`：`NEEDED libc.so`、`FLAGS BIND_NOW`、`FLAGS_1: NOW PIE` ⇒ notes.md:216 申报属实。
3. **断的是运行面不是编译面**：`test.c:67-81` 用 `system()` 真跑制品并回收退出码/stdout 字节数/stderr 全文；`:84-102` 现场 `stat`+`open` 探测设备形态；`:138-147` 在 `/dev/mem` 可读的平台上断「rc==0 + 恰好转出 4096 字节」，本平台断「rc==1 + stderr 点名 /dev/mem + 带当次 strerror + stdout 无转储字节」。⇒ 没有任何"只查存在"的降级。
4. **台账口径更正成立**：notes.md:202-205 声明上游只 `#include <sys/mman.h>`、**全文件无 mmap/munmap**，实际是 `open/read/lseek` ⇒ 委托方"核心是 mmap /dev/mem"的前提被源码证据推翻，本包真正的功能面是物理内存设备节点可用性。
5. **申报范式对齐**：notes.md:212-214 写"运行级环境限制（平台未暴露 /dev/mem），非适配缺陷"，我实读先例 `archives/b/bridge-utils/1.5/notes.md:48-49`（"属运行级环境限制（非适配缺陷…）"）、`:68`（"环境限制非适配问题"）⇒ 同型、如实，**不构成 P1**。

## C. 补丁形状与"扩大改动" —— 补丁合格，分类字段两项待回填

1. `patches/0001-memdump.c.patch` 全文 29 行逐行读：hunk `@@ -113,20 +113,26 @@`，新增恰 6 行（第 14-19 行）：`#ifndef _PATH_MEM` / `#define _PATH_MEM "/dev/mem"` / `#endif` / `#ifndef _PATH_KMEM` / `#define _PATH_KMEM "/dev/kmem"` / `#endif`，删除 0 行，只落在 LINUX2 分支，**无任何平台宏** ⇒ **守卫计数 = 2、确为那两条**；无扩大改动。
2. 占位符扫描：`grep -rniE "pending|TODO|占位|xxxx|FIXME" archives/m/memdump/1.01/` ⇒ 入库 12 件里 **0 命中**；4 条命中全在未入库的 `reports/w3-local-ci.log:48/49`（KC2 步骤名"模板占位符残留检测"本身）与 `:242/:296`（上游源码里的 "depending" 被子串误捕）。`manifest.yaml:59` 的 guard 已是真实守卫串 ⇒ `'pending'` 确实不在盘上。
3. **`platform_only` 判真伪 → 判 False 更自洽，现为工具默认值且无依据（R1-2, P2）**：
   - 出处是工具默认：`scripts/ohc/refresh_patch.py:532 "platform_only": True,  # default assumption for OHOS patches`（同一段代码就是写 `guard: "pending"` 的那一段）；
   - **提交历史实读**：`git show HEAD~1:…/manifest.yaml` 尾部为 `type: auto / platform_only: False / guard: '#ifndef _PATH_MEM / #ifndef _PATH_KMEM'` ⇒ `guard` **从未以 pending 入库**，而 `git diff HEAD~1 HEAD` 的真实改动是 `-platform_only: False` → `+platform_only: True`（外加 work_hash/generated_at 刷新）。委托方"只复原了 guard 这一行"的叙述与提交实况不完全相符；
   - 语义面：本仓**没有** platform_only 的定义（`grep -rn platform_only docs/*.md` = 0 命中），同形态先例分裂——最像的 `archives/t/tcpkali/1.1.1/manifest.yaml:40` 是 `type: portability / platform_only: False / guard: '#ifndef __containerof / #ifndef QUEUE_TYPEOF'`，`DRAFT-8543:58` 的人工回填口径也是 `platform_only: false`；反例 `archives/w/watcher/0.14.5/manifest.yaml:153` 与 `archives/b/bsdiff/4.3/manifest.yaml:72` 用 True；全库 True 1487 个 / False 106 个 manifest；
   - **我的判定**：True 只在"净生效面只在缺该宏的 libc（glibc 上 `#ifndef` 整体跳过）"这一读法下站得住，但它不是本包手工核实的结论（值来自工具默认）、与同形态 portability 先例相反、且台账无一句判定依据 ⇒ 不合格为"已核实分类"，须二选一：改回 `False`，或保留 `True` 并在 notes 写明生效面判据（paths.h 有 24 个 `_PATH_` 宏、`_PATH_MEM`/`_PATH_KMEM` 命中 0；glibc 上自动跳过）。
4. `patches/.patch-backup-20260927011231/0001-memdump.c.patch` 与在册件 `diff` = **IDENTICAL**；`git check-ignore -v` 实读 `.gitignore:96 reports/`、`:152 archives/**/patches/.patch-backup-*/`、`:238 .ci-result.json` ⇒ 备份目录、三份门禁状态件、reports/ 全部**不入库**，PR diff 干净。

## D. W3 证据自洽 —— 互锁块逐项实算全中

| 申报（notes.md:312-320） | 我的实算命令 | 读数 | 判定 |
|---|---|---|---|
| 日志 48313 B | `wc -c reports/w3-local-ci.log` | 48313 | ✅ |
| sha256 `0a19960d18449a1e…` | `sha256sum reports/w3-local-ci.log` | `0a19960d18449a1e9a845671c62ed3155c13137d5bad13f8b50713e9ca397e36` | ✅ 与 `.ci-result.json:9` 逐字全等 |
| exit_code=0 / step / timestamp / integrity_hash | `awk` 全文读 | 0 / `W3_local_ci` / `2026-09-27T01:13:07.956750` / `4d7e4bf7a8b277d2` | ✅ |
| `[step]` 47 枚 | `grep -c "^\[step\]"` | 47 | ✅ |
| `_RESULT=` 8 枚（G0/KC/JC/L0/L1/L2/L4/L5） | `grep -nE "_RESULT="` | :23 G0、:63 KC、:90 JC、:1321 L0、:1322 L1、:1323 L2、:1324 L4、:1325 L5 | ✅ 形态也一致 |
| incremental 12 个文件 | `grep -nE "检查模式"` → :71 `检查模式: incremental (12 个文件)` | 与入库 12 件一致 | ✅ |
| `JC_RESULT=pass` | :90 | pass | ✅ |
| `assertions 21/21` | :1305（另 conan-create.log:149） | `memdump consumer test: assertions 21/21 passed` | ✅ |
| 真跑而非 Cache | `grep -nE "Building from source|Calling build\("` | :170 `memdump/1.01: Building from source`、:177 `Calling build()`、:1251 test package 的 `Calling build()`；:156/:1229 的 `- Cache` 只是同一 recipe 的二次解析 | ✅ 真跑 |

- **HEAD 绑定（R1-4, P3）**：`.ci-result.json` 全文 9 行，**没有 commit/HEAD 字段**；`ci-metadata.json:13 "commit": "unknown"`。绑定靠 `archive_dir` 路径 + 远端分支 SHA + 工作树 clean 三方推得；且日志时间 01:13 **早于** HEAD 提交 01:20:40 —— 但 01:13 之后改的只有 manifest 元数据与 notes 追加（`git show --stat`：manifest 6 行 / notes 17 行），构建物侧（conanfile/conandata/patch/test_package）零改动 ⇒ 证据仍有效，正文别把"HEAD 绑定"写成判决件自带属性。
- **L2/L4/L5 的跳过 vs 真跑**：`conan-verify-report.md:37-44` 三件均 `⏭️ 跳过（无 cache 路径）`（notes.md:261-263 申报的就是这份报告，属实）；`w3-local-ci.log:1312-1325` 则显示 CI 侧 L4 `patches clean`=pass、L5 `[ok] bin/ has content`=pass、L2 `--version/--help failed (non-blocking)`=skip ⇒ 两份文件口径不同但各自如实，**没有把跳过说成通过**。
- `conan-verify-report.md:3` = `**Verdict**: PASS`，G0-G4 ✅（:35 G4 附 `⚠️ 无法找到程序包 ID`，notes.md:260 已如实转述）。

## E. 测试质量（rule4 / rule12）—— 合格

- 上游计数：notes.md:222-232 清点 tar 内 **12 个成员**、Makefile 目标 `what all manpages memdump memdump.1 clean depend`（无 check/test，`make -n check` 报无此规则）⇒ **上游测试总数 = 0**；`test_package/MANIFEST.yml:11-20` 同值（`upstream_tests: []`、`upstream_test_in_build: false`）。全文无"上游测试全通过"字样 ✅。（委托方提示的"tar 内 4 文件"与盘上 12 成员不符，但两口径下 N=0 结论一致。）
- 消费者断言真执行：`conan-create.log:126` 实读 `RUN: "./test_memdump" "/storage/…/p/bin/memdump"` ⇒ 传的是**交付二进制的绝对路径**，`:149` 打印 21/21。
- 断言数我按 test.c 源码逐条数（本平台 absent 分支）：A4+B3+C4+D2+E2+F3+G2+H1 = **21** ⇒ 三处同源、无少报。
- **鸿蒙特有测试面（≥1）在哪**：本平台独有的 7 条以上断言（A1-A4 / B1-B3 的"设备节点缺失形态"）+ G2"map 文件建了但为空"，全部只在"OHOS 无 /dev/mem 节点"这一平台事实下成立；`grep -rn "鸿蒙特有测试" docs ci scripts` 仅命中 `scripts/ohc/submission.py:603` 的 PR 正文模板行 ⇒ **该行由收口窗填，数字须与本件同源**。
- 无按平台裁剪：`test.c:138-147` 的 openable 分支保留 ⇒ notes.md:241"跳过 0"属实。
- 口径提示（R1-5, P3）：`manifest.yaml:29-33 test_results: type: manual / total: 21 / passed: 21` 用的是**断言**口径，可执行测试数是 1（MANIFEST.yml:23-27）；`type: manual` 也与 test.c 的自检计数机制（`assertions_run`）不符 ⇒ PR 正文三处（manifest / MANIFEST / 正文）须同口径声明，防 rule4"少报/混口径"。

## F. B 证据三问（只交证据，不下 B 结论）

**候选机制**：musl 系 OHOS libc 的 `<paths.h>` 不导出 `_PATH_MEM`/`_PATH_KMEM` 宏，须 `#ifndef` 特征守卫 + 回退字面量。
**我的机制自证**：`printf "#include <paths.h>\n" > ph.c; clang -E -dM ph.c` ⇒ `grep -c "_PATH_"` = **24**（_PATH_BSHELL/_PATH_CONSOLE/_PATH_DEFPATH/_PATH_DEV/_PATH_DEVNULL/_PATH_KLOG/_PATH_LASTLOG/_PATH_MAILDIR…），`grep -E "_PATH_MEM|_PATH_KMEM"` **输出为空、rc=1** ⇒ 宏确实不在头里（**不是"没 include"**），机制成立。

检索命令与命中数（一律 `upstream/main -- knowledge`，含 graph/drafts/doc）：

| 检索式 | 命中 |
|---|---|
| `_PATH_MEM\|_PATH_KMEM\|dev-dot-mem` | **0** |
| `paths\.h` | 2（都在 `DRAFT-E681-samhain-local-file-mode-fix-chain.kv:23/:70`） |
| `/dev/mem\|/dev/kmem` | 15（全在 `DRAFT-ohos-peripheral-lib-failed-open-footgun` .kv/.md） |
| `#ifndef .*_PATH_\|字面量回退` | **0** |
| `undeclared identifier` | 390（家族极宽） |
| `Content-Encoding` / `x-gzip` | 84 / 53（`DRAFT-E690-content-encoding-x-gzip-conan-decode-two-faced-sha256`） |
| `CC=clang` / `CC = gcc` 家族 | 149 / 15（`E714-raw-makefile-literal-pin`） |
| `makedefs` | 0；`unsupported system` 6；`uname -s\|makedefs` 166（`E007`/`E140`/`E160`） |
| `宏常量\|feature macro` | 23（E267/E407/E086 族，无 paths.h 设备路径宏） |

**① 症状是否同形于既有条目？** 部分同形、**判据相反**。唯一近邻 `DRAFT-E681` 第 4 类断点收的是"glibc 传递 include 假设"（`_PATH_MOUNTED` 在 paths.h 里、缺显式 include），其自检命令 `grep -c _PATH_MOUNTED …/sysroot/usr/include/paths.h` 明写"预期: 1（宏在，缺的是 include）"；本包同族命令实测该宏集里 `_PATH_MEM`/`_PATH_KMEM` 命中 **0** ⇒ 正落在 E681 判据的反面，症状同族不同因。`DRAFT-ohos-musl-glibc-specific-symbols` 的 Symptom 是函数/变量符号 + "跨文件批量出现"（本包 3 处引用集中单 TU）⇒ 不同形。
**② 处方是否同一条？** 否。E681 = 补显式 include；musl-symbols = 替换为 POSIX 等价函数/变量符号；failed-open-footgun = 断 open 失败 errno 并守住访问器；本包 = 照上游自身 SUNOS5 分支写法加 `#ifndef` 特征守卫 + 字面量回退、**禁用平台宏**（notes.md:96，R8）。处方层检索命中 0。
**③ 既有条目边界是否把"头文件宏常量缺失"排除在外？** 是。`DRAFT-ohos-musl-glibc-specific-symbols.md` 的 Scope 表（:24-28）只列变量/函数两类符号；同族差异化表（:10-13）把问题面切成 内核 syscall(E051) / socket 结构与常量(E086) / 头文件结构(E102) / 头文件冲突(E091) / libc 符号层 五格，**没有"头文件宏常量"一格**；E086 虽是常量面但限定 `SO_PEERCRED` 且处方用 `__OHOS__` 宏（本包明确不用）。
**另判（本包其它 OHOS 偏差是否另有未覆盖机制）**：三条全部**已覆盖** —— 老 Apache `Content-Encoding: x-gzip` 双面 sha256 = `DRAFT-E690`；`CC = gcc` 写死 + "命令行 > 文件 > 环境"的注入点 = `E714`（notes.md:47-48 与它同结论）；`uname -s = HarmonyOS` 令平台探测失配 = `E007`/`E140`/`E160`（`makedefs` 一词本身 0 命中，家族入口在 E007/E160）。⇒ 若升 B，证据面支持"只押 paths.h 宏常量这一条机制"，把已收的三条折进同一草稿会撞重。

---

## 问题清单（详见 audit-result-r1.json 的 issues）

| id | 级别 | 一句话 | 位置 |
|---|---|---|---|
| R1-1 | P2 | `patch_classification.type` 仍是占位值 `auto`（DRAFT-8543:70 明写不能作为提交态；conandata 已是 portability） | manifest.yaml:57 |
| R1-2 | P2 | `platform_only: True` 是 refresh_patch 工具默认值，HEAD 提交无依据地把 False 翻成 True，同形态先例（tcpkali）用 False | manifest.yaml:58 |
| R1-3 | P2 | notes 引用的补丁 work 指纹 `b09ede81583b2496` 与 manifest 现值 `0eb759e0eb8fac58` 不同源（第二次 finish 后未跟改；补丁字节实测未变） | notes.md:164 / manifest.yaml:51 |
| R1-4 | P3 | 判决件不携带 HEAD 字段、日志早于 HEAD 提交 7 分钟（改动仅元数据）；绑定需三方推 | .ci-result.json / ci-metadata.json:13 |
| R1-5 | P3 | `test_results` 用断言口径 21 + `type: manual`，与"可执行测试 1 件"需三处同口径 | manifest.yaml:29-33 |
| R1-6 | P3 | 哈希校验从 conan 内建通道移交配方自实现（双哈希归一化，实测三值全对）；CI worker 侧形态待实跑 | conanfile.py:96 |

**未审项**：任何 build/create/verify/finish；PR 标题/正文 3+2、B 草稿与 Issue 成对性、`$P presubmit`；CI worker 环境差异；`deb.debian.org` 直连复算（已用官方址 curl + 实物 + gunzip 三路等价互证）。

**取证工件**（B 机 `~/tmp/uc2/z74-memdump-w4b/`）：`official.tgz`（curl 官方址原件，12713 B，sha256 76de8ff167…）、`ph.c`（paths.h 探针源）、`out1.txt`/`err1.txt`/`err2.txt`/`err3.txt`/`err4.txt`（制品真执行的 stdout/stderr 原文）、本件与 `audit-result-r1.json`。
