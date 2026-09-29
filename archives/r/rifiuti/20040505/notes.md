# rifiuti 20040505 适配笔记（HarmonyOS PC / OHOS aarch64）

## 一、概况

- 三方库名称：rifiuti（Windows 回收站 `INFO2` 文件解析器，Keith J. Jones / Foundstone，2004）
- 上游版本：20040505；构建系统：**裸 Makefile（位于 `src/`，顶层没有 Makefile）**，无 configure、无 CMake/meson
- 上游 URL（**官方发布物**；2026-09-27 第 6 轮换源，PF7 由 2 命中归 0）：
  `https://downloads.sourceforge.net/project/odessa/Rifiuti/20040505_1/rifiuti_20040505_1.tar.gz`
  —— 上游项目页 = SourceForge `odessa`（Debian 签名 `rifiuti_20040505-4.dsc` 声明的 `Homepage:` 即
  `https://sf.net/projects/odessa`），其 `files/Rifiuti/20040505_1/` 目录真实列出
  `rifiuti_20040505_1.tar.gz`；本行取的是该发布物在 SourceForge 官方下载主机上的规范直链
  （`/download` 页面自己 302 出去的就是 `downloads.sourceforge.net/project/<项目>/<路径>` 这一支）。
  载体坐标：`conandata.yml:20`（url）/ `:21`（sha256）、版本级 `manifest.yaml:19`（url）/ `:20`（sha256）。
- 取源自证（**第 6 轮一手读数**，B 机，默认 curl UA；命令原文与逐字输出见
  `reports/source-official-url-evidence.md`）：该直链 GET `code=200`、`type=application/x-gzip`、
  `dl=2823`、`redir=1`，落盘 `wc -c` = **2823**，`sha256sum` =
  `3694cf6811c7be96412934ee1f378cf74003472d1a62dc642e2229f4ad5073cc` ⇒ 与 `conandata.yml:21`、
  `manifest.yaml:20` 现声明值**逐字相等**；跳转终链
  `master.dl.sourceforge.net/project/…?<每次新签的时效令牌>` 带过期签名 ⇒ 配方不写镜像名、不写令牌。
- **URL 形态是门槛，不是风格**（第 6 轮 G2 一手现场）：先按页面式
  `https://sourceforge.net/projects/odessa/files/Rifiuti/20040505_1/rifiuti_20040505_1.tar.gz/download`
  换源，curl 侧完全可取（`code=200` / `application/x-gzip` / 2823B / 同哈希 / 2 跳），但
  `conan create` 在 `source()` 里报 `BadZipFile: File is not a zip file`
  （`conanfile.py:83` 的 `get(self, **self.conan_data["sources"], strip_root=True)`）⇒ conan 按
  URL 末段推归档类型，末段 `download` 无扩展名就落到 zip 分支。本棒按红线**不改 `conanfile.py`**，
  改取末段带 `.tar.gz` 的官方直链形态。该坑与既有条目 E392 同族
  （`knowledge/doc/E392.md:11` 签名含 `BadZipFile`），本包是其「URL 形态」变体；失败轮判决件按名
  覆盖，逐字现场留在 `reports/conan-create.log` 与本轮整改日志（见 §十 第 6 轮读数）。
- 换源理由（旧叙述已被一手否证）：本行此前写「上游作者 2004 年后停止发布、原主页已下线，故取 Debian 池址作官方源」，那是把"作者 2004 年的邮箱域 `www.foundstone.com` 不再服务"（本轮一手：`curl` TCP 443 超时 `rc=28`、`code=000`）误写成"上游主页无发布物"。⇒ 按框架处方走首选路径 (a) 换官方直链，**不写例外说明、不用 `--no-preflight`**。
- 池内 `.orig` 的新角色＝**版本与哈希核验旁证**（不再作取源址）：本轮一手对账 = 两枚 tar 包 `cmp` 逐字节相同
  （各 2823B、同一 sha256）、解包树 `diff -rq` **零差异**（differ 行数 **0**）、四个文件 sha256 逐个全等
  （`CHANGES` `ee4bb8756777e09c…`、`Readme.txt` `f637218edfbcb640…`、`src/Makefile` `f3bb073249cc2ff9…`、
  `src/rifiuti.c` `2d75a10c19aa8587…`）⇒ 池内 `.orig` 与官方件是**字节级同一枚发布物**；本包构建实际消费的
  `.build-cache/predl_cache/49d722b2_rifiuti_20040505.orig.tar.gz`（未跟踪件、不入 PR）同一 sha256 ⇒ 换源不动哈希、
  解包树与产物面零变化（rrev 仍因 `conandata.yml` 文本变化而变 ⇒ 见 §七/§十 重跑读数）。
- 取源陷阱（判"可取"不能只看 HTTP 码，一律看**字节数 + sha256**）：① catch-all —— `www.mirbsd.de` 对根路径
  与任意深路径都回 `200 + text/html + 28339 字节`（两者同一 sha256 `0bea0fc36a7d277a…`，即首页本体，与任何 tar 无关）；
  ② 自带浏览器 User-Agent 反而被 SourceForge 反爬拒（本轮一手 `403 + text/html 5929 字节`），默认 curl UA
  才拿到那枚 2823 字节 `application/x-gzip` ⇒ 取源探针不要随手加 `-A`；③ `mbsd.evolvis.org` 可达但不承载本包
  （第 5 轮审计一手 404/319B）⇒ 同路径在他机 200 不等于在本机 200。
- 解包后目录名为 `rifiuti_20040505_1`（**不等于版本号**），4 个文件 + 3 个目录（共 7 个条目）、
  单枚 `src/rifiuti.c`（211 行）
- 外部依赖：**无第三方库**（只有 `-lm -lc`）⇒ 配方无 `requires`
- 任务号 / 分支 / 提交：见 PR 信息段（回填于建 PR 后）

## 二、症状（一手复现，主窗与执行棒各自独立跑过）

在 `src/` 目录直接执行上游 `make`：

```
gcc -o rifiuti rifiuti.c -lm -lc;cp rifiuti ../bin
/bin/sh: gcc: inaccessible or not found
cp: bad 'rifiuti': No such file or directory
make: *** [Makefile:4: install] Error 1
$? = 2
```

设备编译器面：`command -v clang` = `/data/service/hnp/bin/clang`；`command -v gcc` = 空（无 gcc、无 cc 别名）。

上游 `src/Makefile` 实测 215 字节 / `wc -l` = 10 行（sha256 前缀 f3bb0732，取自解包件），
全文只有四条目（`all: install` / `install` / `installwin` / `clean`），其中含**两条** gcc
编译命令：`:4` = `gcc -o rifiuti rifiuti.c -lm -lc;cp rifiuti ../bin`（`install` 规则正文）、
`:7` = `gcc -DCYGWIN -o rifiuti.exe rifiuti.c -lm -lc;cp rifiuti.exe ../bin`（`installwin`
规则正文，CYGWIN 专用）；默认目标 `all: install` 只走 `:4`，本配方复刻的也只有 `:4`。
**没有任何 `CC=` 或 `CFLAGS=` 赋值**，编译器名 `gcc` 直接写在两条规则的正文里。

## 三、根因

GNU make 的标准交叉手法是"命令行变量覆盖文件内赋值"（`make CC=<交叉编译器>`），
其成立前提是规则正文引用 `$(CC)`。本包规则正文是**字面量 `gcc`**，命令行传 `CC=` 没有任何作用对象
⇒ 失败发生在 shell 解析命令名阶段（`inaccessible or not found`），而不是编译阶段。
分号续跑使第二步 `cp` 再报一次 `bad 'rifiuti'`，最终错误码是 `Error 1` 而非 `Error 127`（这是与 suckless 族签名的可分辨差异）。

真实根因是**构建入口不可参数化**，不是"设备上缺 gcc"。

## 四、最小复现与已试过的失败方案

| # | 尝试 | 结果（一手） |
|---|---|---|
| F1 | `make`（上游原样） | `/bin/sh: gcc: inaccessible or not found` → `make: *** [Makefile:4: install] Error 1`，rc=2 |
| F2 | `make CC=/data/service/hnp/bin/clang` | 输出与 F1 **逐字相同**（echo 出来的命令仍是 `gcc -o …`）⇒ 证明命令行覆盖对本包无效，不是"参数没传对" |
| F3 | 用 clang 手动编译 `src/Makefile:4` 那一行的等价命令（**复算式**：解包 `src/` 内 `clang -c rifiuti.c -o /dev/null`，不落产物） | `F3_RC=0`，stderr 里 `-Wimplicit-function-declaration` 计数 = **5**、末行 `5 warnings generated.`：`exit`（rifiuti.c:151）、`strcpy`（:154）、`malloc`（:168）、`strncpy`（:173）、`free`（**:209**）——2004 年源码不 include `<stdlib.h>/<string.h>`。本机 clang 记为警告非错误，故**未加任何 flag、未改源码**，如实披露；第 4 轮重审窗独立复跑该命令得同一 5 行（记录于 `reports/z75s-audit-result.json` 的 P2 项） |
| F4 | 造一个 `gcc` → clang 的 PATH 转发件 | **主动放弃**：会掩盖真实工具链来源，且不能保证产物是 aarch64-OHOS 目标；与"不造假 gcc"的门禁精神冲突 |
| F5 | 打 `.patch` 把 `gcc` 换成 `$(CC)` | **主动放弃**：F3 已证明无需改源码即可复刻上游语义；补丁会改动构建输入并作废既有 W3 证据 |

## 五、最终方案（零补丁）

在配方 `build()` 内**逐字复刻**上游 `src/Makefile:4` 那条编译命令（同一个 Makefile 的 `:7`
是 `installwin` 的 `-DCYGWIN` 规则，CYGWIN 专用，默认目标 `all: install` 不触发），
编译器从 Conan conf 取（R33）：

```python
comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
cc = comp.get("c") or "clang"
self.run('"%s" -o rifiuti rifiuti.c -lm -lc' % cc, cwd=<src>, env="conanbuild")
```

- 链接集与产物名保持上游原样（`-lm -lc`、产物名 `rifiuti`），不新增编译选项；
- 上游 `install` 目标里的 `cp rifiuti ../bin` 被绕过 ⇒ 产物安装改在 `package()` 完成，
  等效性证据：`test_package` 消费的是安装包里的 `bin/rifiuti`，实测行为断言全通过（见第六节）；
- `patches/` 目录为空，上游源码零改动。

## 六、测试账本（五维，全部来自盘上读数）

| 维度 | 数值 | 来源 |
|---|---|---|
| `N_static`（上游静态声明） | **0** | 复核 `src/Makefile` 全文：无 `test`/`check` 目标、无 `TESTS` 声明（`NO_TEST_TARGET`） |
| `N_registered`（构建系统注册） | **0** | 同上 |
| `N_executed`（实际执行） | **0**（上游无可执行项） | 不存在可执行的上游测试，未伪造 |
| 未执行/跳过分类 | 不适用 | — |
| `N_consumer`（新增消费者测试） | **22 执行 / 22 通过 / 0 失败** | `reports/conan-create.log:146` = `SUMMARY total=22 pass=22 fail=0`；22 个 `ck` 调用点与 22 条断言一一对应（其中 4 处写在同一行的分号之后），无循环复用 |
| `N_runner` | 1（`test_package/test.sh`） | 不使用 runner 数替代原子用例数 |

消费者测试是**真行为断言**，不是"只跑 --help"：
构造符合 MS `INFO2` 布局的样本文件后逐条比对，覆盖
无参数退出码 **254**（上游 `exit(-2)`）、打开失败退出码 **253**（上游 `exit(-3)`）、
`-t ,` 自定义分隔符输出、`TZ=UTC` 下的时间字段、路径长度不超过 INFO2 记录上限（`0x108-0x04`）等。

> **⚠ 三枚会被 `finish` 重写的日志不入 PR（`review-memory §19` `*.log` 禁入 + 避免「结果档 vs 仓内档」两套读数）**：`reports/conan-create.log`、`reports/w3-local-ci.log`、`reports/g3-finish.log` 已不跟踪，**磁盘仍在本机 `<worktree>/archives/r/rifiuti/20040505/reports/`**，本节与正文引用它们的行号坐标**按本机现件核、关键读数已逐条内嵌**；随 PR 的 `reports/` 件 = `conan-verify-report.md`、`source-official-url-evidence.md` 与 `z75h/z75n/z75s` 三对判决件（共 8 件，内容未改）。

## 七、门禁读数（B 机，两层分列）

> 分列理由：`conanfile.py`、`conandata.yml`、`test_package/test.sh` 都在 recipe revision 面上，
> 触及即令旧 W3/verify 证据作废。故本节把「探索期探针」与「收口轮判决」分开写，
> 本轮（第 6 轮取源整改后重跑，09:01–09:04）的判决读数在 7.2 与 §十 10.3。

### 7.1 探索期读数（09-27 00:35–00:55，早于配方终稿 ⇒ 只作过程留痕，不绑定任何收口 HEAD）

> 探索期那几轮的门探针日志**不随本 PR 附**，本节因此一律不给日志名，只给**复算式**与随 PR 的同源件；所有承载性结论由 7.2 的 `reports/` 判决件 + 下表命令承担。

| 门 | 当时读数 | 复算式（不依赖未随 PR 的日志） |
|---|---|---|
| W0 preflight | `PASS`（`[OK] 预检通过（无依赖需要检查）`，PREFLIGHT_RC=0） | `bash ci/scripts/preflight_check.sh rifiuti/20040505` ⇒ rc=0；第 4 轮重审窗自跑同一命令亦 rc=0（见 `reports/z75s-audit-result.json` 的 P2 项） |
| recipe-search | 无相似配方（语料条数随库增长而变，当时 6173 条），首稿走 conan-init 模板 | `python3 scripts/ohc-run.py recipe-search rifiuti` ⇒ 无同名/相似配方命中 |
| `ohc-run.py build`（探索期与上一收口轮各跑一次，同形失败；本轮按整改指令只复跑 verify+finish，未再跑该子命令） | **不是本包的构建门**：该子命令按 `archives/r/rifiuti-20040505/src` 找探索工作目录，本包是手写归档、无该目录 ⇒ Step1 即 `EXIT_REASON: init_build_failed` / `EXIT_CODE: 2 (resumable)` / `STEP_FAILED: Step1`，且未触碰配方文件（跑完 `git diff` 为空）。真正的编译门是 W3 内部的 `conan create`（G2），见 7.2 | `python3 scripts/ohc-run.py build rifiuti 20040505` ⇒ Step1 判决同上；本包收口不走该子命令 |
| F3 手动编译探针 | clang 编过，5 条隐式声明警告 | 复算式见 §四 F3（`clang -c rifiuti.c -o /dev/null`，本节上行已给全） |
| 单跑 conan-verify（探索期一次） | 结论行 `✅ 配方验证通过: rifiuti 20040505` | 收口轮同门读数在 `reports/conan-verify-report.md:1-44` 与 `reports/g3-finish.log:55-57`（见 7.2）；探索期那次早于 `conandata.yml`/`manifest.yaml` 终稿（03:21–03:22），只作过程留痕 |

### 7.2 本轮收口轮读数（第 6 轮取源整改后重跑，`reports/` 判决件 mtime 09:01:42–09:09，配方面绑定提交 `44f1ba4cce`（z75m 第 06 轮））

| 门 | 实际覆盖 | 证据 |
|---|---|---|
| W3 conan-verify | **有效覆盖只有 G1–G3**：G0（`:8-10`）正文是 `ℹ️ 无法识别构建系统，跳过预查询`、G4（`:34-35`）正文是 `⚠️ 无法找到程序包 ID`、L2/L4/L5（`:37-38`/`:40-41`/`:43-44`）正文是 `⏭️ 跳过（无 cache 路径）`；这五行标题图标一律印 `✅ PASS`、与正文相反 ⇒ 按正文取，**G4 未取到包 ID、L2/L4/L5 跳过都不构成覆盖**；有效门 G1（`:12-24`）/G2（`:26-28`，conan create 成功）/G3（`:30-32`）；判决三一致 = 文字 PASS + `**Verdict**: PASS`（`reports/conan-verify-report.md:3`）+ 包装退出码 0（`python3 scripts/ohc-run.py conan-verify rifiuti 20040505`）；两条结论行原文随 PR 可核 = `✅ 配方验证通过: rifiuti 20040505`（`reports/g3-finish.log:55`）与 `✅    可标记 status: published`（`reports/g3-finish.log:56`）⇒ 探索期单独跑 verify 留下的那份日志不随 PR 附，本节不再引用它；finish 内嵌的那次 verify 同样通过（`reports/g3-finish.log:57` 原文 `✅   conan-verify 通过`） | `reports/conan-verify-report.md:1-44`（全文实测 44 行，Date `:6` = 2026-09-28T18:32:29.996917） |
| W3 本地 CI 判决行 | `L0/L1/L4/L5_RESULT=pass`、`L2_RESULT=skip`（框架初值即 skip、non-blocking，不是运行期覆盖）；`Total: 1 / Success: 1 / Failed: 0`；`SUMMARY total=22 pass=22 fail=0` | `reports/w3-local-ci.log:277`（L0–L5 五行连排 277–281）、`:286-288`、`:261`（全文 291 行，09-28 19:21 档） |
| W4/W5 独立审计（第 3 轮 + 第 4 轮判决件） | 两轮判决的**结构化件 `.json` 逐字复制入本 PR 的 `reports/`、内容未改**，出处不再指向任何执行棒目录，一律以 sha256 对账；**同名 `*.log` 读版按 `.gitcode/review-memory.md` §19（`*.log` 禁入）不随 PR**，本机仍留档（`<worktree>/archives/r/rifiuti/20040505/reports/`），**判决叙述以同名 `.json` 为准**：第 3 轮 `z75h-audit-result.json`（首条 `"verdict": "fail"`、`"audited_commit": "936884515464d79b0cdb80bcd32dff552aeff834"`、6 条 issue；sha256 `0d72286654517b006886c7d4e2ce7439374c48c832eb61924e5bc7fbf1778a52`）与 `z75h-w4-report.log`（同判决人读版，统计行 `统计: P0=0 P1=1 P2=2 P3=3`；sha256 `79ed93c68512e713c15137ce06c4d1de2e997d5f5a1c598401d49e10641087cc`）。第 4 轮（针对改判前 HEAD `83bacdf68e28a664b60ef757857c52c6d9e38b7b`）`z75s-audit-result.json`（`"verdict": "fail"`、同一 `audited_commit`、1 条 P1 + 1 条 P2 + 2 条 P3；sha256 `6c0b831be95b5971a8d46212fcf1f98feb08eacdb7f22a6d0d7e184ac199f93f`）与 `z75s-w4-report.log`（统计行 `统计: P0=0 P1=1 P2=1 P3=2`、结论行 `❌ W5 审计未通过`；sha256 `64dea1599ff8c7e6d37aced8b691b993b1aa20b6382755625e83f822a48d6bc6`）。第 4 轮那条 P1（`hit(E501)` 不满足判 hit 四条件）经主窗复核**成立** ⇒ 本 PR 已改判 **create**，声明与草稿见 §九，本窗按整改指令未重跑任何门禁（构建输入零改动 ⇒ rrev 与 W3 证据继续有效） | 本目录 `reports/` 磁盘实测十件；**随 PR 的 `reports/` 件＝5 件**（`conan-verify-report.md`、`source-official-url-evidence.md`、`z75h-audit-result.json`、`z75n-audit-result.json`、`z75s-audit-result.json`）——**4 件 `*.log`（`conan-create`/`w3-local-ci`/`g3-finish` 三枚会被 finish 改写 + `z75{h,n,s}-w4-report.log` 三枚读版）按 `review-memory §19` 一律不随 PR、磁盘留档**；第 5 轮 `z75n-audit-result.json` 的 P1×2 已由第 6 轮两笔提交整改闭环；"只有三件""只有六件""八件"三代写法均随补件作废；另有 `source-official-url-evidence.md` 经 `git add -f` 随 PR |

L2（smoke）在本包是框架初值 skip 形态（`L2_RESULT=skip`，本轮 `reports/w3-local-ci.log:279`），属 non-blocking（框架判据是 `--version`/`--help` **任一** rc=0 即 pass，本包两者皆非 0，见 `ci/conan/build_and_test.sh:1685-1693` 与 `:1701-1707`），本笔记不把它当作可执行证据；运行期行为证据全部由 test_package 的 22 条断言承担（rifiuti 是纯 stdin/文件解析工具，无网络、无特权设备，故可全测）。

## 八、已知限制与适用边界

- 本机 clang 把 `implicit-function-declaration` 记为警告，故未加 `-Wno-error` 也未补 include；
  若未来工具链升级为错误（clang 新默认），处方是 E063 的 `add-cflags-disable-werror`，不是改上游源码。
- 复刻方案仅在"上游只有 1–3 条编译命令"时成本低；复杂 Makefile（依赖 implicit rules 推导）应改打补丁引入 `$(CC)`。
- 有可覆盖变量的裸 Makefile（suckless 族）一律优先覆盖法，本包是"无可覆盖对象"才走复刻。

## 九、B 声明（3+2）

- **适配路径**：路径 A + 路径 B（贡献创新，1 条）。新增机制＝上游裸 Makefile 把编译器名写成**规则正文里的字面量**（全文件无 `CC=`/`CFLAGS=` 赋值）⇒ GNU make「命令行变量覆盖 makefile 内赋值」这条标准交叉手法**没有作用对象**；零补丁修法＝在配方里逐字复刻该条编译命令、编译器取自 `tools.build:compiler_executables`（R33）。
- **使用知识库**：新增草稿 1 条 `DRAFT-rifiuti-20040505-makefile-baked-compiler-name-no-override-target`（`.kv`/`.md` 同 stem 成对，随本 PR 的 `knowledge/drafts/`）；既有条目逐条排除，均**只覆盖一半**（同一条目须同时覆盖根因与解法才构成命中）：
  - **E501**（`knowledge/graph/index.tsv:725` 首字段 E501、`:723` 首字段 E499；正文 `knowledge/doc/E501.md` 全文 31 行）：`:11` 错误特征要求字面 `make: inaccessible or not found`（本包首错是 `gcc: inaccessible or not found` ⇒ 不命中）；`:15` 根因「Some OHOS PR runners do not expose make/cmake to Conan subprocesses」被本包设备实测反证 —— `command -v make` = `/data/service/hnp/bin/make`、`make --version` = GNU Make 4.4.1 ⇒ make 可用；只有 `:18` 方法名 `direct-compile-source-list-and-wrap-link-env` 与 `:20` 说明句「Mirror the upstream Makefile source list in the Conan recipe, compile with the profile compiler」覆盖本包**解法**那一半 ⇒ 终判 **create**（第 4 轮重审 P1 结论，判决件 `reports/z75s-audit-result.json`，主窗复核成立）
  - **E392**（`knowledge/doc/E392.md:11` 签名 `BadZipFile…|KeyError.*compiler_executables`；`:15`/`:20` raw makefile 三陷阱）：只给"配方怎么取编译器"的工程写法，不含"规则正文字面量编译器名"这根因维度 ⇒ 未据其申报命中
  - **E149**（`knowledge/doc/E149.md:11` 签名 `socat.*HarmonyOS|autotools.*platform.*success`；`:20` 「直接使用标准编译流程，无需任何源码修改」）：与本包"构建入口不可参数化"不同形 ⇒ 排除
  - **E063**（`knowledge/doc/E063.md:11-14` 签名、`:17-19` 根因 `-Werror`、`:22` `add-cflags-disable-werror`）：是 §八 那条"工具链若把隐式声明升为错误"的**备用处方**，本轮未启用 ⇒ 不构成命中依据
  - 通用池件 `suckless-baked-paths-makevar-override`（池内件，路径 `经验文档/B草稿库/DRAFT-PKG-VER-suckless-baked-paths-makevar-override.kv`，**未随本 PR**）：`:17` 根因依赖「命令行变量覆盖文件内 = 赋值」且前提是 `config.mk` 里有 `CC=cc` 赋值行，`:28` 修法是 `make CC=<conf 取得> INCS=… LIBS=…` ⇒ 与本包"无把手可覆盖"是同一族的**相反分支**，本包不可用
  - 同族在仓草稿（查重记录，各差一半，逐条行号见草稿 `.md` 第三节）：`knowledge/drafts/DRAFT-cohomcalg-0.32-makefile-gxx-override.kv:17-19`（root_cause 原文：Makefile 有 `CC := g++`/`LD := g++` 赋值 ⇒ 命令行覆盖有效）、`knowledge/drafts/DRAFT-yosys-0.66-custom-makefile-compiler-executables-host-objects.kv:9`（根因是 `CC :=` 自赋导致宿主对象、症状在链接期）、`knowledge/drafts/E543-draft-F833.kv:22`/`:42`/`:43`（入口是 `build.sh` 而非 make，`affected_scope` 原文明写 no Makefile ⇒ 只同签名与解法形状）、`knowledge/drafts/E2182-draft-3B7D.kv:49`（上游预留 `CMDLINE_*` 钩子 ⇒ 本包一个钩子都没有）
- **知识库扩展**：1 条 = `DRAFT-rifiuti-20040505-makefile-baked-compiler-name-no-override-target`（机制正文见 §五；查重面与层次差见该草稿 `.md`；`draft-review` 预审判 **create**，TOP3 相似度 0.23 / 0.19 / 0.17，均低于 0.30 阈值）
- **关联 Issue**：#3508（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3508）——标题「【知识库扩展】rifiuti 20040505：上游 Makefile 规则正文把编译器名写成字面量（不含 CC/CFLAGS 变量）⇒ make 命令行覆盖无对象；OHOS 设备只有 clang 且无 gcc/cc 别名」
- **PR 前缀**：`【知识库扩展】`（标题由主窗改）。历史留痕：本包曾按候选起草 `literal-compiler-makefile-replicate-command` 并建 Issue #3493，随旧判定撤稿与撤销说明（提交 `7bf7629bcd`）；第 4 轮重审的 P1 促成改判 ⇒ 现行口径＝**create**，草稿对与 Issue 号以上三行为准。

## 十、最终状态

**最终状态**：三层分开记，不混写。

### 10.1 探索期读数（00:35–00:55 的独立门探针，早于配方终稿 ⇒ 只作过程留痕，不充当本轮证据）

- preflight rc=0（`[OK] 预检通过（无依赖需要检查）`）— 复算式 `bash ci/scripts/preflight_check.sh rifiuti/20040505` ⇒ rc=0
- recipe-search：无相似配方（语料条数随库增长而变，当时 6173）— 复算式 `python3 scripts/ohc-run.py recipe-search rifiuti`
- 单跑 conan-verify：结论行 `✅ 配方验证通过: rifiuti 20040505` — 探索期那轮日志不随 PR 附；收口轮的同源结论行原文在 `reports/g3-finish.log:55`
- 构建准入：`build-slot.sh --kind short` 机动短槽放行——探索期两跑各取到一枚短槽，后一次收尾行原文
  `SLOT_DONE:ok MemAvailable=15584MB`（探索期槽日志不随 PR 附 ⇒ 只给命令与原文、不给坐标；
  本轮收口轮的槽读数见 §10.3「槽位」行）

### 10.2 前两轮收口读数（`reports/` 同名件已被本轮重跑按名覆盖 ⇒ 只留结论与当时值，不再给行号坐标）

- **`c60ae8c702` 版配方，`reports/` mtime 03:21–03:22 那一轮**：W3 conan-verify 有效覆盖 G1–G3
  （G0 预查询跳过、G4 未取到包 ID、L2/L4/L5 跳过；标题图标与正文相反，按正文取）；
  W3 本地 CI `L2_RESULT=skip`、`L0/L1/L4/L5=pass`、`SUMMARY total=22 pass=22 fail=0`；
  `.ci-result.json` 当时值 `integrity_hash=1d2511ec4486f42c`、
  `log_sha256=03e38debd9b59c2d312b85be2a448f2d225f21e78669669e022f77065c332084`。
- **`6440cbd891` 版配方，`reports/` mtime 04:57–04:58 那一轮**（分支 HEAD `9368845154…` 即第 3 轮
  审计件里的 `audited_commit`）：三条门禁结论与上一轮同形；`.ci-result.json` 当时值
  `timestamp=2026-09-27T04:58:34.408123`、`integrity_hash=2375652156096c75`、
  `log_sha256=454f83c42d96bd79931213babe3fdbda488cf54a6c638c8f0672f7f21e061e6f`。
  本轮 P1（`conanfile.py` 的 127 假陈述）触及构建输入 ⇒ rrev 变 ⇒ 这一轮的判决整批作废，只作历史。

### 10.3 本轮收口读数（第 6 轮取源整改后重跑，B 机，配方面绑定提交 `44f1ba4cce`，读数收拢提交 `a7f15e1f`）

| 步 | 命令 | rc | 判决读数（全部本轮一手） |
|---|---|---|---|
| 准入 | `sh ~/tmp/uc2/gate.sh 3000` ×3（轻量 C 包取 3000MB 档） | 0 / 0 / 0 | `GATE_PASS:probe=clang`，MemAvailable 5919/5844/5608MB，编译器进程 0、RSS 0MB；三次分别紧接"放置改动 / verify / finish"之前 |
| 槽位 | `build-slot.sh --kind short --wait 1800 --mem 2500` ×2 | — | 两次各取到机动短槽：原文 本轮 finish 的 `SLOT_OK 09:01:42 cmd=python3 scripts/ohc-run.py finish rifiuti 20040505 built`（原文在 `reports/g3-finish.log:3`，同日志 `:1` 印 `本机长杆 0/2 · 机动 2/3（总 5 槽）`）；verify 轮的槽读数不随 PR 附（只给命令与 rc=0）；verify 轮收尾原文 `SLOT_DONE:ok MemAvailable=5816MB`；开工探得 `本机长杆 0/2 · 机动 0/3` |
| verify | `python3 scripts/ohc-run.py conan-verify rifiuti 20040505` | **0** | 三一致：文字结论行 `✅ 配方验证通过: rifiuti 20040505` + `**Verdict**: PASS`（`reports/conan-verify-report.md:3`）+ rc=0；G1/G2/G3 打印 PASS，实际有效覆盖仍是 G1–G3（见 7.2） |
| finish | `python3 scripts/ohc-run.py finish rifiuti 20040505 built` | 包装 rc=2 | 阻塞门 W3（框架内部键 `step35`、打印为 Step 5/10）**双绿标记在 `reports/g3-finish.log:63-64`** = `✅ 本地 CI 模拟通过 (日志: …/reports/w3-local-ci.log)` + `✅ W3 本地 CI 模拟通过`；判决块 `:123` = `║ EXIT_REASON: finish_success`、`:124` = `║ EXIT_CODE: 0 (知识整理已完成)`；`失败步骤` 行 `:110` 原文 `⚠️    失败步骤: step5b, step8` ⇒ **step35 与 step4 均不在失败键列表内，Step5 未红**；红项 `step5b` = 打印为 Step 7/10 的知识图谱完整性检查（`scripts/ohc/finish.py:315-334`，本包 `unreferenced=4`）、`step8` = 打印为 Step 10/10 的 submit 就绪预检（`finish.py:408`，缺 `reports/test-report.md`/`packaging/`/`.staging-verified`）；`:127` 的 `STEP_FAILED: Step6` 是 `finish.py:538` 在非阻塞分支里写死的字面量（`is_blocking = False` 见 `:533`），而 `finalize-archive` 打印 `finalize-archive 有警告 (RC=2)`（`:76`）后仍把内部键 `step4` 记成 True（`finish.py:306-313`）⇒ 属框架侧同类噪声，不作本包门禁。**另披露**：`reports/g3-finish.log:73` 是框架 finalize 对**当时那份** notes.md 的回显（finish 跑于 09:01–09:04，notes 在此之后才重写），其中 `:73` 印出的旧片段带着 `g2-verify.log` 与 Date `2026-09-27T04:58:04` 两个**本 PR 内并不存在**的坐标 ⇒ 按日志字面去找会落空，这批行既不属本轮判决、也与 7.2/10.3 读数无关；现行值一律以 `reports/conan-verify-report.md`（Date 见 `:6` = 2026-09-28T18:32:29.996917）与下表"归档判决"行的 `.ci-result.json` 复算式为准。日志本体按证据纪律**未作任何改动** |
| W3 判决 | `reports/w3-local-ci.log`（291 行，09-28 19:21 档） | — | `:277-281` = L0 pass / L1 pass / **L2 skip** / L4 pass / L5 pass；`:286-288` = Total 1 / Success 1 / Failed 0；`:261` = `SUMMARY total=22 pass=22 fail=0` |
| 归档判决 | `.ci-result.json`（随本轮重写，本窗已复算） | `exit_code=0` | `step=W3_local_ci`、`timestamp=2026-09-27T09:03:45.125275`、`integrity_hash=b5ebda842cb8d1d5`、`log_sha256=235f30e33262d94c9cdc3c85651461aee9da4ccfc76c9387de069896d453dd02`；复算方式 = 按 `finish.py:251-252` 自算 `sha256("2026-09-27T09:03:45.125275:rifiuti:20040505:0")[:16] = b5ebda842cb8d1d5`（== 存储值），按 `finish.py:263-267` 自算 `sha256(reports/w3-local-ci.log) = 235f30e33262d94c9cdc3c85651461aee9da4ccfc76c9387de069896d453dd02`（== 存储值），两项 match 均为 True |
| 测试账本 | `reports/conan-create.log`（148 行） | — | `[PASS]` 22 行 / `[FAIL]` 0 行；`SUMMARY total=22 pass=22 fail=0` 在 **`:146`**；提交态 `test_package/test.sh` 复算 `ck` 调用点 = **22**（`grep -n "ck "` 命中 23 行，扣掉 `:30` 的函数定义 `ck() { # ck <label> <rc>`；其中 18 处行首、4 处写在同一行的分号之后），分母未缩、未并 skip、未删断言；两条失败路径断言（254/253）未被 set -e 吞，口径见表下"失败路径断言"一句；上游静态 `N_static/N_registered/N_executed = 0/0/0`（Makefile 无 test/check 目标） |

> **准入口径更正（本窗实测）**：`gate.sh` 的参数是位置量 `<MemAvailable_MB> <编译器进程数上限> <RSS_MB> <swap余量> <inode余量>`，
> **不存在 `--light` 这个选项**；传 `--light` 会落进 `TH_MEM`，而判据 `[ "$avail_mb" -lt "$TH_MEM" ]` 遇到非数字
> 参数直接返回假（本窗实测 `sh -c 'if [ 5919 -lt --light ]; then echo LT_TRUE; else echo RC=$?; fi'` 输出 `RC=1`）
> ⇒ 内存下限那一项被**静默跳过**。§10.2 前一轮记的"`gate.sh --light` ×3"因此没判过内存，本轮一律显式传 `3000`。

失败路径断言口径：`test_package/test.sh:23` 为 `set -euo pipefail`，两条退出码断言的调用点在 `test.sh:128`、`:136`，写法是把命令替换拆成 `&& echo 0` 与 `|| echo 1` 两支交给 `ck` 记账 ⇒ 失败退出码不触顶 set -e（判决行见 `reports/w3-local-ci.log:248`、`:250`，两条均 `[PASS]`）。

随本 PR 的 `reports/` 末态**十件**（前四件是本轮原始输出，后六件是三轮独立审计判决件；全部逐字入 PR、内容未改，sha256 为设备实测全值，复算命令 `git ls-files 'archives/r/rifiuti/20040505/reports/*' | xargs sha256sum`）；另有取源证据件 `source-official-url-evidence.md`（sha256 `2089c564f2374e1b439d2be805ae147f6d7575fba5dff385ca61216680b83124`）被 `.gitignore:96` 忽略 ⇒ **已 `git add -f` 随 PR**，指向不再悬空：
`conan-create.log` = `3019eb8801f329e50ca7492c74a72738ba1dce0c66a8c84c7c6bdc813e616068`；
`conan-verify-report.md` = `6b30c0fb1ce632912cce6ab838b14bdc5caca53798e7819a5538f3b0de805d41`；
`w3-local-ci.log` = `235f30e33262d94c9cdc3c85651461aee9da4ccfc76c9387de069896d453dd02`；
`g3-finish.log` = `991943c9d6ad2fba3ad60e8629b79e0971c23e305b4e4019bb00ebdb9b73548f`（本轮 finish 原始输出，其 `:73` 的 finalize 回显已在 §10.3 披露）；
`z75h-audit-result.json` = `0d72286654517b006886c7d4e2ce7439374c48c832eb61924e5bc7fbf1778a52`；
`z75h-w4-report.log`（第 3 轮读版）**不随 PR（§19）**、磁盘留档 ⇒ 判决叙述见同名 `z75h-audit-result.json`；
`z75s-audit-result.json` = `6c0b831be95b5971a8d46212fcf1f98feb08eacdb7f22a6d0d7e184ac199f93f`；
`z75s-w4-report.log`（第 4 轮读版 = 本包改判 create 的直接依据）**不随 PR（§19）**、磁盘留档 ⇒ 判决叙述见同名 `z75s-audit-result.json`；
`z75n-audit-result.json` = `45e28e0d4e66fb389e8024ab6f34ce03e81b3c3770e175fab258de4b2c81a8f7`；
`z75n-w4-report.log`（第 5 轮读版，`verdict=fail P1×2`，其两条 P1 已由第 6 轮 `d0a4261308`/`44f1ba4cce` 两笔提交整改、**闭环**）**不随 PR（§19）**、磁盘留档 ⇒ 判决叙述见同名 `z75n-audit-result.json`。

### 10.4 第 6 轮读数（2026-09-28 收尾-7 按当前 HEAD 实算回填；本节是 §一 末尾「见 §十 第 6 轮读数」的落点）

> 起因：第 6 轮（`d0a4261308` 取源换 SourceForge 官方直链 + `44f1ba4cce` 改 `/download` 页面式直链，
> 两笔配方面提交）之后 `finish` 于 **09:01–09:04 重跑**，`reports/` 四件按名覆盖 ⇒ 上一版 §7.2/§10.3
> 里的哈希与行号全部作废。本节给**当前 HEAD 上现算**的值，复算命令逐条附上。

- **四件 sha256（`sha256sum` 现算）**：`conan-create.log` = `3019eb8801f329e50ca7492c74a72738ba1dce0c66a8c84c7c6bdc813e616068`；`conan-verify-report.md` = `6b30c0fb1ce632912cce6ab838b14bdc5caca53798e7819a5538f3b0de805d41`；
  `w3-local-ci.log` = `235f30e33262d94c9cdc3c85651461aee9da4ccfc76c9387de069896d453dd02`；`g3-finish.log` = `991943c9d6ad2fba3ad60e8629b79e0971c23e305b4e4019bb00ebdb9b73548f`。
- **`.ci-result.json`（finish 自写、未手改）**：`timestamp=2026-09-27T09:03:45.125275`、`exit_code=0`、`integrity_hash=b5ebda842cb8d1d5`、
  `log_sha256=235f30e33262d94c9cdc3c85651461aee9da4ccfc76c9387de069896d453dd02`；复算 = `sha256("2026-09-27T09:03:45.125275:rifiuti:20040505:0")[:16] = b5ebda842cb8d1d5`（== 存储值）、
  `sha256(reports/w3-local-ci.log) = 235f30e33262d94c9cdc3c85651461aee9da4ccfc76c9387de069896d453dd02`（== 存储值）。
- **`w3-local-ci.log` 全文 291 行（09-28 19:21 档；每次 finish 都会换档，换档须重对）**：`SUMMARY total=22 pass=22 fail=0` 在 `:261`；
  `L0/L1/L2/L4/L5_RESULT` 五行连排 `:277-281`（`L2_RESULT=skip` 在 `:279`）；
  `Total/Success/Failed` 在 `:286-288`；两条失败路径断言判决行 `:248`、`:250`（两行现件仍为 `[PASS]`）。
- **`g3-finish.log` 全文 136 行**：`SLOT_OK 09:01:42` `:3`；`✅ 配方验证通过` `:55`、`可标记 status` `:56`、
  `conan-verify 通过` `:57`；W3 双绿 `:63-64`；`finalize-archive 有警告 (RC=2)` `:76`；
  `失败步骤: step5b, step8` `:110`；`EXIT_REASON` `:123` / `EXIT_CODE` `:124`；
  `:73` 是框架 finalize 对当时 notes 的回显（含本 PR 内不存在的坐标，见 §7.2 披露）。
- **`conan-verify-report.md` 全文 44 行**：`**Verdict**: PASS` `:3`、`Date` `:6` = `2026-09-28T18:32:29.996917`。
- **`conan-create.log` 全文 148 行**：`SUMMARY total=22 pass=22 fail=0` `:146`。
- **取源证据件**：`reports/source-official-url-evidence.md`（sha256 `2089c564f2374e1b439d2be805ae147f6d7575fba5dff385ca61216680b83124`）被 `.gitignore:96` 忽略
  ⇒ 本轮 `git add -f` 随 PR，`notes.md:15` 与 `conandata.yml` 注释里的指向**不再悬空**。
- **随 PR 的 `reports/` 共 10 件判决/日志 + 1 件取源证据**，复算：
  `git ls-files 'archives/r/rifiuti/20040505/reports/*' | xargs sha256sum`。
- **⛔ 本轮未动 `conanfile.py`**（其 `url = ""  # CI fills this` 占位符来自框架模板，全仓 1208/12350 同形
  ⇒ 改它会动 rrev、作废 W3/verify，属框架面，另案提框架方）。
---

**编译结束**: 2026-09-28 18:32
**最终状态**: built
