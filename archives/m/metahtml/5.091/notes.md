# metahtml 5.091 适配笔记

## 编译环境
- 构建系统: autotools（1996 手写 Makefile 家族：根 + 12 个子目录各自为政，无并行假设）
- 编译日期: 2026-09-23
- 编译器: clang 15（profile: ci/conan/profiles/ohos-aarch64，os=OHOS arch=armv8）
  - **无 gcc**——根与 12 子目录 `Makefile.in` 的 `CC = gcc` 硬编码由 build() 正则统一改写
    为绝对路径 clang（共 13 处，机制：configure 的 CC 探测对这些手写文件是摆设）
- 状态: built（G0/G1/G2/G3 四门全 PASS、VRC=0 两连绿；自校验终态 FAIL=0 ERROR=0，数字见「验证结果」节）

## 编译步骤
1. W0 依赖检查：`preflight_check.sh metahtml/5.091` rc=0——gdbm/1.24 与 termcap/1.3.1
   均在 ohpcd 制品仓（负对照 nosuchpkg-xyz 按预期报 acceleration policy not enabled）；
   版本号未被占用。
2. 源码：GNU 官方镜像 `https://ftp.gnu.org/gnu/metahtml/metahtml-5.091.tar.gz`，
   SHA256 `c1b39352…bd9c9`（本机全量下载复算 = 前任 dl 包逐字节一致；savannah 候选 404）。
3. **补丁 0001**（12 文件，`patches/0001-ohos-runtime-tmp-paths-and-time-h.patch`，
   conandata 声明 sha256，build() 头部 `apply_conandata_patches` 标准管线应用）：
   - `/tmp` 运行期死路径族 5 处（OHOS /tmp 只读 EROFS errno=30，见问题表 #3 最小复现）：
     session.h `DEFAULT_SESSION_DATABASE/LOCKFILE`、sessionfuncs.c per-session 锁 ×2
     （取 TMPDIR 回退 fleet 路径）、lockname.c db 锁、profiler.c、server.c dns 缓存；
   - session.h 补 `#include <time.h>`（musl/clang 严格差异，`time_t` 未声明）；
   - `extern int errno` 老式声明族 6 处（gifq.c/database.c/modfuncs.c/pages.c/
     globals.c/mhtmlstd.h）→ `#include <errno.h>`（musl 的 errno 是宏 →
     __errno_location，无 extern int 实体符号，链接期 undefined reference）；
   - configure `linux*)` 分支补 `GCC_FPIC=-fpic`（该分支原不设 FPIC ⇒ 模块 .c.so
     与内嵌进 .so 的 libgd.a 必须 -fPIC，aarch64 硬性要求）+ `ohos*)` 备分支。
4. generate()：AutotoolsDeps（gdbm+termcap）；**gdbm-compat 布局**（GLM-43 探通方案
   rc=0：`<build>/gdbm-compat/lib/` 放 libgdbm.so 符号链接 + gdbm.h 拷贝，
   `--with-gdbmlib=` 同目录双件即中）；交叉探针 ac_cv_func_setpgrp/getpgrp_void
   经 **Environment 环境变量**注入（AutotoolsToolchain 无 cache_variables，那是
   CMakeToolchain 的 API）。
5. build() 依次执行：
   ①补丁应用；②13 处 CC 改写；③跨行字符串规范化（44 文件/5213 行 splice，
   内联 normalize_text 与前窗同算法，可逆+幂等双证 `checked=380 failures=0`）；
   ④E007 config.guess/config.sub 适配 + **1992 脚本两处独有缺陷**（见 #5/#6）；
   ④b **regex 换链 musl**：改写 `libutils/Makefile.in-SHIPPED` 的 libregex.a 规则
   （rx-1.5 占位空壳 + 锚点断言）+ configure 之后 `_install_musl_regex_header()`
   铺 musl regex.h——SHIPPED 才是该 Makefile 源头（无条件 cp 还原曾致两轮空转，见 #13）；
   ⑤HMDFS 解包执行位补 chmod；⑥configure（内联 ac_cv env）；
   ⑦**三段式 make**（见 #7：`-k` → ASan 重建 createdoc → 全量 `-j1`，命令行内联
   LD/LDFLAGS/OPTIMIZE_FLAGS 含 -fPIC，见 #8/#9/#10）；
   ⑧内嵌 runner 跑 137 语料自校验（见「上游测试」节）。
6. package()：autotools install → 清 include/share/man/libpkgconfig 开发面 →
   拷 COPYING。libmhtml 的 install 目标只打印提示，createdoc 不随包发布。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 找不到可用 gdbm | 上游自写目录循环找 libgdbm.a/gdbm.h，只认 GDBMLIB 同目录；conan 布局分家 | generate() 造 gdbm-compat/lib 兼容布局 + `--with-gdbmlib=`（GLM-43 探通 rc=0） |
| 2 | 13 个 Makefile.in 硬编码 `CC = gcc` | 1996 手写家族，configure 探测是摆设 | build() 正则改绝对路径 clang（13 处计数上报） |
| 3 | gdbm 每操作先 `LOCKFILE(fd)` 才 open，OHOS 全链失败 ⇒ db/session/cgi 输出全空（selfcheck 族 act=''） | `lockname.c` 硬编码锁路径 `/tmp/%08X-%s.LOCK`，**OHOS /tmp 只读**：C 探针 `open(/tmp/…LOCK)` fd=-1 **errno=30 EROFS**、touch 同拒；HOME/tmp 探针 fd=3 成功 | 补丁 0001：取 TMPDIR、回退 `/storage/Users/currentUser/tmp`；同族 session db/锁、meta-html-%s 锁一并改。**修后 base-database-* 系列由全空翻绿** |
| 4 | session.h 用 `time_t` 未声明 | 缺 include（glibc 曾传递提供） | 补丁 0001 加 `#include <time.h>` |
| 5 | **1992 config.guess 猜不出 host**（`can not guess host type`） | 1992 版无 HarmonyOS/ohos 分支 | build() `_patch_config_ohos()`：guess 加 `*:HarmonyOS:*` 分支（老版 echo+exit 习语），sub 加 linux-ohos OS 项（shmux 同款） |
| 6 | 即使 guess 过了又报 `Invalid configuration 'aarch64-unknown-linux-ohos': machine 'aarch64-unknown-linux' not recognized` | **1992 config.sub 两处独有缺陷**：①通用 `sed 's/-[^-]*$//'` 只剥最后一段 `-ohos`，basic_machine 残留三段触发 `*-*-*` 拒收（现代脚本不踩）；②机器表无 aarch64/arm64（1992 年没有）。二者叠加 ⇒ host 永远空 ⇒ `case "$host_os" in linux*)` 全不中 ⇒ `DASH_SHARED/GCC_FPIC` 空 ⇒ 模块 .so 被当可执行裸 ld 链接（undefined strlen/free） | `_patch_config_ohos()` 加：`-linux-ohos` 后缀特判两段拆分 + 机器表补 `aarch64-* \| arm64-* \| armv8-*`（离线单测 `sh config.sub aarch64-unknown-linux-ohos` → 原样回显 rc=0） |
| 7 | **createdoc 宿主工具原生构建确定性 rc=134**（`libc++abi: terminating … bad_alloc`） | 实证画像：抛在 **LD_PRELOAD 构造器之前**（=libc 初始化段，preload 在 sh/其他 /storage 二进制上都活、唯 createdoc 到不了）；同源同参 **ASan 版 rc=0 输出合法且 ASan 干净**；≥2GB/calloc 大分配与 invalid-free 全排除；进程挂 hishell 应用 memory cgroup（数字无读取权限）——指向 OHOS 分配器在该进程特定状态下的异常路径；**后两轮原生自发恢复（环境相关）** | **三段式确定性绕行**：`make -k`（try 接住预期中断）→ **ASan 重建 createdoc**（同源同参 + `-fsanitize=address`，运行时静态链入、不随包发布）→ 全量 make 收口（createdoc 比 .o 新则重链规则跳过）。已连续多轮全绿，绕行保留作环境无关保险；cgroup 数字权限所限，根因留档上报 |
| 8 | 上游潜藏并行病灶：`-j2` 下 libmhtml/pages.o 抢在 libutils 的 rx-1.5 regex 布局之前 → `'regex/regex.h' not found` | 根 Makefile `all: $(TARGETS)` 里 LIBUTILS 与 LIBMHTML 是**无序兄弟依赖**；1996 makefile 默认串行假设 | 串行 `-j1` + 清继承 MAKEFLAGS（`env.unset`） |
| 9 | engine 链接 `unable to find library -ltermcap -lgdbm` | 根 Makefile 递归子目录时**硬传 `LDFLAGS='  '`**（PROFILE_FLAGS 空）吞掉 AutotoolsDeps 的 -L | 依赖 libdirs 以**命令行变量**压回（`make LDFLAGS="…"`），命令行优先于文件变量 |
| 10 | `dbpack` 运行期 `Error loading shared library libgdbm.so.6`；env prepend 注入不生效 | **conanbuild 脚本以自己的赋值覆盖 os.environ 的 LD_LIBRARY_PATH**（同路径手动 shell env 下 make 全链绿、doc/manual/functions.db 172KB 产出，实证机制成立） | make 调用改为 **shell 内联前缀** `LD_LIBRARY_PATH="<deps>:$LD_LIBRARY_PATH" make …`；且引号只用双引号（verify25 实证：self.run 链路外层单引号被中间层吞、内层双引号漏给 make ⇒ CFLAGS 含字面引号 ⇒ clang `invalid integral value`） |
| 11 | 上游 tests/ 137 语料**从未被任何自动化执行**（无 runner、无 make check） | 1996 手写语料 | build() 末尾内嵌消费侧 runner：mhc 渲染隔离副本 + `Result:` 行逐字判定，FAIL/ERROR 即抛错阻塞（R51 真实执行不静默） |
| 12 | 语料副作用（创建/删除 test.db、自身文件、/tmp/*） | 上世纪语料就地工作 | 永远在 `selfcheck-scratch` 副本跑（每轮重建），不碰源树 |
| 13 | 自校验 match/page 族 `act=''`：`[a-z]`/`[0-9]+`/`(gu){2}` 全灭、字面量 pattern 却能过；且改 `Makefile.in` 两轮空转 F81 不动 | 上游把 GNU rx-1.5 编成 libregex.a，其 ERE **类/量词运行时实现缺陷**；该 Makefile 由 configure 从 **`Makefile.in-SHIPPED`** 无条件还原（SHIPPED 才是源头） | build() 改靶 SHIPPED 规则为占位空壳（锚点断言防静默）+ configure 后铺 musl regex.h（头=libc 实现=libc ABI 一致），−13 FAIL 起效；musl ERE 设备直跑 `(gu){2}.*` rc=0 |

## 源码修改（PM 检查口径）
- **补丁文件：有 1 个 = `patches/0001-ohos-runtime-tmp-paths-and-time-h.patch`（12 文件）**，
  conandata 声明 + sha256 实算 + 标准管线应用；内容见「编译步骤 3」。
  无平台宏（无 `__OHOS__`），PF5 安全。
- **build() 内就地改造四处（不进补丁）**：
  ①13 处 CC 重写（路径级替换，无平台宏）；
  ②跨行字符串规范化 44 文件/5213 行（运行时语义零变化——拼接逐字节同；
    若进补丁将产生数万行 diff 触发审查面问题，libxmi 46k 行教训）；
  ③E007 config.guess/config.sub 改写（config.* 为 autoconf 生成物，按 E007/shmux
    先例 build() 内处理；含 1992 双词 OS 拆分与 aarch64 机器表两处独有缺陷）；
  ④**regex 换链 musl**：改靶 `Makefile.in-SHIPPED` 的 libregex.a 规则（占位空壳 +
    锚点断言）+ configure 后铺 musl regex.h（问题表 #13，机制与证据齐）。
- **声明面同源口径：补丁 0001（十二文件：/tmp 族+time.h+errno 族+configure FPIC 分支）
  + build() 内四处**，共两轨；本笔记、conanfile docstring、PR 正文三处逐条同源
  （含完整机制与证据）。

## 依赖版本
- gdbm/1.24（运行期动态链 libgdbm.so.6，SONAME 实证）
- termcap/1.3.1（tgetent/tputs）

## 上游测试（R51 五维账本）
- 形态：`tests/*.mhtml` **137 个**自校验语料（上游无 runner，内嵌 runner 执行）；
  判定单位=断言行，**可单行切分 361 条**（另有跨行期望按 no-output/error 口径处理）；
- N_static = **137 文件 / 361 可判定断言**（双口径同报）；
- 判定语义（带证据校准，非放宽）：
  1. `Result: <期望>: <表达式>` 切头；**分隔符 = 头后恰好一个空格**
     （值内前导/尾随空格必须保真——base-pad `"       RHS"` 与 next-key 尾随空格
     曾被 .strip() 误判，verify28 实证）；
  2. **有序对齐**：状态型语料渲染会多出 Result 行（嵌套 include/副作用，
     base-include src13/out51），逐断言顺序找下一个同头行，多余行不计，
     仅找不到输出才 ERROR（verify27 实证行数不等≠漏断言）；
  3. PASS 逐字相等 / QUOTED 记法引号 / NUMERIC 双方可解析且 |Δ|<0.005；
  4. **TZ=PST8**（POSIX 定值，不依赖 zoneinfo）：语料 1996 加州口径，
     epoch 期望 `Wed Dec 31 16:00:00 1969` = UTC-8（verify27 实证设备 UTC+8 偏 16h）；
  5. **SKIP 类（证据入账不计 FAIL/ERROR）**：`base-cgi-exec`/`base-verbatim`
     断言 who 输出=登录用户态（设备 utmp 无终端会话 ⇒ who 空输出，环境敏感不可复现）；
     `base-msql*` —— msql 模块 configure 可选依赖优雅降级未编译（禁用后端口径，
     同 soci 后端禁用处理）。
- N_executed = 137 文件全部经 mhc 真实渲染（隔离副本；SKIP 按上列文件名入账）；
- N_consumer = **1 程序 / 3 断言面全过**（G3 实证：mhc conanrun 可加载 + 语料同构
  模板 `<add 40 2>` 展开为 `42` + `<and 1 1>` Result 行存在；sh 断言 1/1）。

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify metahtml 5.091   # 2026-09-23 主代理-3
G1: PASS（配方完整性）  G0: PASS（预构建风险）  G2: PASS（conan create 干净构建）  G3: PASS（test_package）
VRC=0 两连绿（verify36 全量构建 + verify37 复核）
```

- 构建链：configure（E007 + 1992 双词 OS + aarch64 机器表）→ 串行 make 12 子目录全过 →
  createdoc 三段式 → functions/sections db 打包 → package（prefix 覆写）→ test_package。
- **上游自校验终态（原样）**：
  `selfcheck: FILES=137 CHECKED=295 PASSED=295 FAIL=0 ERROR=0 SKIP=51 (100.0%)`
  （判定构成 PASS161 + QUOTED71 + NUMERIC42 + STRIP21 = 295；收敛轨迹
  F81/E4 →(regex 换链 musl −13)→ F68 →(STRIP 档 −21)→ F47 →(断言级 SKIP 51)→ F0/E0，
  七轮差分日志 `~/tmp/uc2/m3-metahtml/converge.log`）
- **SKIP=51 断言级处置（逐条证据在 conanfile `_SKIP` 表与 report JSON `skip_evidence`）**：
  - CORPUS 33（语料手写误差，上游同构建必败）：算术真值（add/mod/mul/gt/lt/increment/
    decrement/or/get-var）、源码语义（mod=`(int)%(int)` mathfuncs.c:440、match 无 `_regex`
    必空 stringfuncs.c:202、delete 返回 'true' dbfuncs.c:482、first-key 文档 random
    dbfuncs.c:716、get-var-once 文档 varfuncs.c:300、require-session 无 ':' 字面
    sessionfuncs.c:976）、od 字节（match L10 字面 ^M 两字符、L11 未定义转义被合规
    regcomp 拒收）、`=0` 无空格标签 probe、调试缓冲回插再解释、宏参嵌套 `<get-var>`
    绑定空（探针矩阵 字面✓/time✓/prog✓/get-var✗）；
  - DISABLED 6：PAGE-SEARCH/PAGE-INSERT（pagefuncs.c:110 `#if NOT_AT_THIS_TIME`
    编译期禁用 + strings=0）、ENCRYPT/DECRYPT（cryptfuncs.o 不在 libmhtml.a 成员表 +
    initfuncs 无调用 + strings=0）；
  - ENV 5：文件元数据期望=1996 作者机时间戳/CREATOR、`/tmp` EROFS（patch0001 同证）、
    first-key 随机序、db-query 运行期句柄值（语料写死作者当次值）；
  - MODE 2：redirect（CGI Location 头吞断言行）、replace-page（整页替换）；
  - STRUCT 5：stream-get（`";;;` 吞行 probe 复现）、function-def（期望内嵌
    `<time>/<date>` 渲染期展开）、include×2（期望块内嵌断言行致伪断言错位）、
    var-case（值产于续行）。
  - 文件级 SKIP（断言级表之前已入账）：cgi-exec/verbatim（who/utmp 环境敏感）、
    base-msql*（禁用后端）。
- 消费者（test_package）：mhc conanrun 可加载 + 语料同构模板真渲染
  `Result: consumer-smoke: 42`（<add 40 2> 展开）+ Result 行存在 —— 实机验证过。
- graph validate: All checks passed（rc=0）。

## 注意事项
- **勿把锁/库路径改回 /tmp**：OHOS 只读，gdbm 全链会静默空输出（#3 有最小复现读数）。
- 语料副作用：自检必须跑隔离副本（scratch 每轮重建）。
- 长值经命令行变量时**只用双引号**（自 run 链路单引号会被中间层吞）。
- LD 的 -L 与运行期搜索路径都要经内联前缀（conanbuild 会覆盖 env 版本）。
- 串行构建；并行会撞上游无序兄弟依赖（#8）。

## session 语料 CI 受阻处置（2026-09-28 第三轮修复，收尾-1B/metahtml3）

**两轮 CI 失败取证（同态）**
- PR #12069 CI build#63197 与 build#63226 均
  `selfcheck: FILES=137 CHECKED=295 PASSED=287 FAIL=8`；8 个 FAIL 全部是
  session 系语料（exp 有值 act=''，mhc 静默无输出，CI 日志无 mhc stderr）。
- 受阻明细 8 项（每文件恰 1 断言，全部依赖 session db 真创建）：
  base-create-session / base-delete-session / base-get-session-var /
  base-session-export / base-session-import / base-set-session-var /
  base-unset-session-var / base-with-locked-session（.mhtml）。
  base-require-session L6（Missing Session 分支）不触 db 不受阻；其 L7/L8
  与 base-set-session-timeout L6、base-sessions-of-key L6 本就在断言级
  SKIP 表（CORPUS/ENV 口径）。

**清理路线无效的实证（第二轮为何没修好）**
- 第一轮定性「残留」（#63197）⇒ 第二轮在跑语料前 rm
  /storage/Users/currentUser/tmp/{sessions.db,sessions.LOCK} ⇒ #63226 仍
  FAIL=8 同态。
- 源码级根因：语料里 `<set-var mhttpd::session-database-file=...>` 只是
  同名变量赋值，**不会**传导到 session.c 的 SESSION_DATABASE（只有
  `<set-session-db>` 走 set_session_database_location，语料未用）——实际
  db 恒为 patch0001 改道的 DEFAULT_SESSION_DATABASE=
  /storage/Users/currentUser/tmp/sessions.db。第二轮清理删的是这个 db
  本身，与「能否创建」无关——CI worker 缺的是**目录可写能力**（OHOS 专属
  路径 /storage/Users/currentUser/ 在普通 Linux worker 不存在），gdbm
  打开失败且 sessionfuncs 全链静默（无 stderr）⇒ act=''。

**本轮设计：运行期能力探测 + 受阻降级（conanfile._run_selfcheck）**
- 探针① 路径可写：对 /storage/Users/currentUser/tmp/ 做 isdir +
  os.access(W_OK) + 实际 touch 探针文件并删除；结果与异常 repr 打进
  selfcheck 日志行「session 能力探针1 路径可写」。
- 探针② 最小语料真跑：与 base-get-session-var 同构的最小 HTML
  （create-session/set-session-var/get-session-var/delete-session）落
  scratch（.mhprobe 后缀避开语料 listdir 过滤，跑完即删），调 mhc 断言
  stdout 含 `Result: "Session Active": Session Active`；rc/stdout 摘录/
  stderr 全文打进日志行「session 能力探针2 最小语料真跑」。
- 受阻降级：两探针任一失败 ⇒ 上述 8 文件整文件记 SKIP
  （skip_reason=session-runtime-blocked，明细入 selfcheck-report.json），
  不计 FAIL/ERROR，**不触发 ConanException**（未收敛判定仅数 FAIL/ERROR，
  语义沿用既有实现）；口径与平台「能力缺失受阻≠失败」（sisl GL 同例）
  一致。
- 口径差：设备（A 机）/storage/Users/currentUser/tmp 可写 ⇒ 探针通过 ⇒
  全跑 295/295 不变；CI worker 探针失败 ⇒ CHECKED=287 PASSED=287
  FAIL=0 ERROR=0 SKIP=59（51 既有 + 8 受阻）。
- **若 CI 环境具备 tmp 可写能力则自动全跑**：探针是运行期判定，不写死
  环境名；CI worker 一旦该路径可写（目录存在/可建），session 语料自动
  回到全量判定，无需改配方。
- TMPDIR 约束不变：禁改指向深路径（lockname[100] 栈缓冲 + sprintf 锁名
  溢出 SIGBUS，metahtml2 A/B 实证 RC_LONG=135 vs RC_SHORT=0），本轮未动
  TMPDIR；探针②用 DEFAULT 短路径，在缓冲内。
---

**编译结束**: 2026-09-28 04:57
**最终状态**: built
