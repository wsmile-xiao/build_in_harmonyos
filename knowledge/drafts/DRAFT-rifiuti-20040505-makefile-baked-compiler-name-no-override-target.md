# DRAFT-rifiuti-20040505-makefile-baked-compiler-name-no-override-target

**机制一句话**：上游裸 Makefile 把编译器名写成**规则正文里的字面量**（全文件没有 `CC=`/`CFLAGS=` 赋值）⇒ GNU make「命令行变量覆盖 makefile 内赋值」这条标准交叉手法**没有作用对象**；OHOS 设备侧只有 `/data/service/hnp/bin/clang`、无 `gcc`/`cc` 别名 ⇒ 首错落在 shell 解析命令名阶段。解法＝在配方里**逐字复刻**该条编译命令，编译器取自 `tools.build:compiler_executables`（R33），零补丁。

- 来源包：`archives/r/rifiuti/20040505`（上游 `src/Makefile`：10 行 / 215 字节 / sha256 前缀 `f3bb0732`）
- 关联 Issue：#3508 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3508
- 判定：**create**（不是 hit；判据见下节）

## 一、症状（设备一手，逐字）

在解包后的 `src/` 里直接跑上游 `make`：

```
/bin/sh: gcc: inaccessible or not found
cp: bad 'rifiuti': No such file or directory
make: *** [Makefile:4: install] Error 1
```

退出码 `rc=2`。终码是 **Error 1 而不是 Error 127**（`Error 127` 那族是"命令本身找不到"，如 `make: cc: No such file or directory`；本包 make 正常启动、是它派生的 shell 找不到 `gcc`）。

## 二、"覆盖无对象"的三条一手证明

| # | 探针 | 实测读数 |
|---|---|---|
| P1 | `command -v make` | `/data/service/hnp/bin/make`，`make --version` = **GNU Make 4.4.1** ⇒ make 可用（E501 的前提不成立） |
| P2 | `make -n -C src CC=clang` | 打印的 recipe 仍是 `gcc -o rifiuti rifiuti.c -lm -lc;cp rifiuti ../bin` ⇒ 命令行变量没被任何引用吸收 |
| P3 | 裸 `make` 与 `make CC=/data/service/hnp/bin/clang` 的 stderr 对比 | `cmp -s` 判**逐字节相同**、两者 rc 都是 2 ⇒ "换个写法再试一次"不可能成功 |

`verification_cmd`（`.kv` 里那一行，在解包根目录执行；Makefile 若在顶层就把 `src/Makefile` 换成 `Makefile`）：

```
grep -cE '^[[:space:]]*CC[[:space:]]*[:?]?=' src/Makefile; make -n -C src CC=clang 2>&1 | grep -cE '^[[:space:]]*gcc[[:space:]]'
```

期望读数＝**两行输出 `0` 然后 `1`、整体 rc=0**：`0` = 全文件没有 `CC` 赋值（覆盖无对象），`1` = 加 `CC=` 后 recipe 仍以字面量 `gcc` 开头。本窗真跑读数：`SHN_RC=0`（`sh -n` 语法过）、`VC_RC=0`、`stdout = 0/1`（跑在解包根目录，其 `src/Makefile` 与上游逐字一致、sha256 前缀 `f3bb0732`）。

`prescan_pattern`（`^[ \t]+(?:@|-)?(?:gcc|cc|g\+\+)[ \t](?!.*\$(?:\(|\{)C)`，逐行 `re.M`）命中样例＝本包 `src/Makefile:4` 与 `:7`（2 命中）；不命中样例＝`$(CC) -o …`、`${CC} -o …`、`gcc -o … $(CFLAGS)`、`install -m 755 …`、`rm -f …`、`CC = gcc`、`all: install`（自测 12/12 与预期一致；把 `:4` 的字面量改成 `$(CC)` 后重扫 = 0 命中）。

## 三、判重与层次差（为什么不是 hit）

按 `hit` 四条件（同一条目须**同时**覆盖"症状/根因"与"解法"两半），逐条给行号说明既有条目各覆盖哪一半：

| 条目 | 行号证据 | 覆盖了哪一半 | 为什么不能当 hit |
|---|---|---|---|
| **E501** | `knowledge/doc/E501.md:11`（错误特征字面 `make: inaccessible or not found\|cmake: …`）、`:15`（根因「Some OHOS PR runners do not expose make/cmake to Conan subprocesses」）、`:18`（方法名 `direct-compile-source-list-and-wrap-link-env`）、`:20`（说明「Mirror the upstream Makefile source list in the Conan recipe, compile with the profile compiler」）；`knowledge/graph/index.tsv:725` 首字段 E501 | **只覆盖解法**（`:18`/`:20`） | 签名要求命令名是 `make`/`cmake`，本包是 `gcc` ⇒ `:11` 不命中；`:15` 的"runner 不暴露 make"被 P1 直接反证（设备 make 可用）⇒ 症状与根因两半都不成立 ⇒ 第 1 条件不过 |
| **E392** | `knowledge/doc/E392.md:11`（签名 `BadZipFile…\|KeyError.*compiler_executables…`）、`:15`/`:20`（三陷阱：`get()` filename、`compiler_executables` 用 `check_type=dict` 整体取、`make` 要加 `cwd`） | 只覆盖"raw makefile 配方的三个工程陷阱"，含本包解法里**取编译器那一步**的写法 | 根因不是"入口不可参数化"，签名也不含命令名解析失败 ⇒ 不同维度，不构成 hit |
| **E149** | `knowledge/doc/E149.md:11`（签名 `socat.*HarmonyOS\|autotools.*platform.*success`）、`:15`/`:20`（configure 自动检测平台、`direct_compile` 无需改源码） | 只是"标准流程直接编过"的泛化条目 | 本包恰恰**不能**走标准流程；签名与根因都不同形 |
| **E063** | `knowledge/doc/E063.md:11-14`（签名 `-Werror.*implicit-function` 等）、`:17-19`（根因：项目开 `-Werror` 把警告升错误）、`:22`（方法名 `add-cflags-disable-werror`） | 覆盖本包**另一条已知限制**（5 条隐式声明警告）的将来处方 | 本包首错与它无关（本轮 clang 只记警告，未启用该处方）⇒ 属"备用解法"，不是本机制的根因 |
| 池件 `suckless-baked-paths-makevar-override`（通用池 `经验文档/B草稿库/`，**未随本 PR**） | 该池件 `:17` 根因原文依赖「GNU make 语义"命令行变量覆盖文件内 = 赋值"」且前提是 `config.mk` 里有 `CC=cc` 赋值行；`:14` 签名 `make: cc: No such file or directory`＋`Error 127`；`:28` 修法 `make CC=<conf 取得> INCS=… LIBS=…` | 覆盖"有把手时命令行覆盖"那一分支的解法 | 本包**没有把手** ⇒ 该修法失效；两条件相反 ⇒ 属同一族的另一分支，正是本条要新增的判读 |
| `knowledge/drafts/DRAFT-cohomcalg-0.32-makefile-gxx-override.kv` | `:15` 标题（Raw Makefile hardcoding CC:=g++）、`:17-19` 根因（`CC := g++`、`LD := g++` 赋值存在）、`:38` `rec_approach: make-cmdline-cc-override` | 同上一分支（覆盖有效） | 本包 Makefile 无 `CC :=` 赋值 ⇒ 该条解法不可用，不能当 hit |
| `knowledge/drafts/DRAFT-yosys-0.66-custom-makefile-compiler-executables-host-objects.kv` | `:9` 根因（`CXX :=`/`CC :=` 自赋 ⇒ conf 到不了 make，**静默产出宿主对象**）、`:13` 解法（环境前缀注入 `CC= CXX=`）、`:20`（对硬赋值 `:=` 必须命令行或改 Makefile） | 症状面在**链接期**（`skipping incompatible`），不是命令名解析期 | 根因与签名均不同形；其"必须有一个可赋值的 CC"前提在本包不存在 |
| `knowledge/drafts/E543-draft-F833.kv`（aria 0.1.1） | `:22` 签名**含** `gcc: inaccessible or not found`、`:42` 根因（入口 `build.sh` 硬写 `/bin/bash` 与 `gcc`）、`:43` `affected_scope` 原文「with **no Makefile**, configure, CTest, or formal test directory」、`:49`/`:50` 解法（自定义配方用 Conan 提供的 clang 直接编源码） | **同签名 + 同解法形状**两半都沾 | 入口是 shell 脚本而非 make ⇒ 不涉及"命令行变量覆盖"；`affected_scope` 明文把 Makefile 场景排除在外 ⇒ 指不出"覆盖无对象"这一根因行。按"查重以完整条目为单位"，本条是它的 Makefile 对偶分支 |
| `knowledge/drafts/E2182-draft-3B7D.kv` | `:42` 根因、`:49` `rec_approach: upstream-cmdline-flag-hooks`、`:51` `rec_command: make CC=<conf编译器> CMDLINE_CPPFLAGS=…` | 上游**预留了命令行钩子**时的注入法 | 本包上游一个钩子都没有 ⇒ 另一分支 |
| `knowledge/drafts/DRAFT-9639-minibwa-profile-cc-path-fallback.kv` | `:24` 根因（conf 里的编译器绝对路径在本机不存在 ⇒ `No such file or directory`/`Error 127`） | conf 取值的**存在性**容错 | 与本包机制无关（本包 conf 路径可用，问题是 Makefile 不引用它） |

**查重口径与读数（可复算式，第 6 轮整改现取）**：检索面与树一律写成命令，读者在本仓根逐字重跑即可。树固定取 base `48d9cee6844d0fca1f25e86c2df1293b904855d8`（**不写 HEAD**：本 PR 分支 HEAD 随整改轮次移动，且本 PR 自带的草稿对会让 `knowledge/drafts` 面的计数各 +1 ⇒ 按 base 数在 HEAD 上复算必差 1）。以下全部读数为本棒一手，未沿用审计窗数字。

- 实物计数（base 树，文件数口径）：`git show 48d9cee684:knowledge/graph/index.tsv | wc -l` = **766**；`git ls-tree -r --name-only 48d9cee684 -- knowledge/graph | grep -c '[.]kv$'` = **542**；`… -- knowledge/doc | grep -c '[.]md$'` = **540**；`… -- knowledge/drafts | grep -c '[.]kv$'` = **1468**、`… | grep -c '[.]md$'` = **1452**；`… -- knowledge/graph knowledge/drafts | grep -c '[.]kv$'` = **2010**（下文的解析面）。`knowledge/kv/` 在本仓**不存在**（`test -d knowledge/kv` ⇒ MISSING）⇒ 不在面内。
- 关键词命中数（**文件数口径**；命令模板 `git grep -l -F '<词>' 48d9cee684 -- <面> | wc -l`，固定串匹配、大小写敏感）。**窄面** = `knowledge/graph knowledge/drafts`（条目实体所在，判重以完整条目为单位 ⇒ 判别力以此面为准）；**宽面** = `knowledge`（另含 `knowledge/doc` 的 540 件 E 条目正文）。逐词 窄面/宽面：`inaccessible or not found` 67/82、`compiler_executables` 109/117、`baked` 9/9、`hardcoded` 34/37、`hard-coded` 12/14、`literal compiler` 0/0、`no CC` 2/2、`Makefile` 819/872、`override` 138/156。其中 `Makefile` 819 与 `override` 138 过泛、无判别力，只作粗筛。
- **旧数作废说明**：本句上一版给的是 67/108/9/30/9/0/2/876/129（同序），其中 6 项不可复算 —— `compiler_executables` 108、`hardcoded` 30、`hard-coded` 9、`Makefile` 876、`override` 129 在「base/HEAD × 窄/宽」四种组合里**都不出现**（`Makefile` 876 甚至高于全部可复算值的最大 874），而 `inaccessible or not found` 67 只在窄面成立、与旧句自述「面含 knowledge/doc」相互矛盾 ⇒ 属混合口径无命令。现一律换成上表的命令 + 面 + 树口径，读者可逐条复算。
- 再用真实解析器 `scripts/ohc/models.py:parse_kv_file` 把 `knowledge/graph` + `knowledge/drafts` 共 **2010 件 .kv** 逐条解析，按"根因特征词 × 解法特征词"组合打分做人工比对 ⇒ 能同时指出"根因＝规则正文字面量编译器名（无变量可覆盖）"与"解法＝复刻编译命令＋编译器取自 conf"两行的条目**为 0**（最接近的是上表 `E543-draft-F833` 与 `DRAFT-cohomcalg-0.32-makefile-gxx-override`，各差一半，行号见上）。⇒ 判 **create**。

## 四、解法（零补丁）

配方 `build()` 逐字复刻 `src/Makefile:4` 那条命令，命令名换成 conf 里的 C 编译器；`cp rifiuti ../bin` 的安装语义移到 `package()`。上游 `:7` 是 `installwin` 的 `-DCYGWIN` 规则，默认目标 `all: install` 不触发，本包也不复刻。不新增编译选项、链接集保持 `-lm -lc`、产物名保持 `rifiuti`。

## 五、适用边界 / 解除条件 / 风险

- 成本只在"上游编译命令 1–3 条且无 implicit-rule 推导"时低；复杂 Makefile 走 `fallback`（打补丁引入 `$(CC)`）。
- 若上游 Makefile **有** `CC :=`/`CC =` 把手 ⇒ 本条不适用，改用命令行/环境覆盖那一族（见上表 cohomcalg/yosys/池件）。
- 本包另有 5 条 `-Wimplicit-function-declaration`（`rifiuti.c` 未 include `<stdlib.h>/<string.h>`，本机 clang 记警告不记错误）；若未来工具链升为错误，处方是 E063，而不是改上游源码。
- 风险：复刻会随上游命令漂移而失效 ⇒ 取用者须先 `make -n` 比对复刻串，再决定是否改走补丁分支。
