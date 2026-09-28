# pasco 20040505 适配笔记

## 编译环境
- 构建系统: makefile（上游只有 `src/Makefile`，无 configure / CMake / Meson）
- 编译日期: 2026-09-27
- 编译器: clang（`/data/service/hnp/bin/clang`；本平台无 `gcc`、无 `cc`）
- 状态: built
- 构建主机: B 机（`frp-bar.com:19214`），worktree `~/qzy/主理-74-pasco-20040505`，CONAN_HOME `~/tmp/ch/home-pasco`

## 取源核验（官方址，非重打包源）

上游 = SourceForge **odessa** 项目族，Pasco 的 FRS 目录 `Pasco/20040505_1/`，文件
`pasco_20040505_1.tar.gz`（4032 字节）。四端点各取一次并逐字节比对：

| 端点 | http_code | size | time | sha256 |
|---|---|---|---|---|
| `downloads.sourceforge.net/project/odessa/Pasco/20040505_1/pasco_20040505_1.tar.gz` | 200 | 4032 | 2.65 s | `a3b8ee7be960571410bc564ecc93067755a28650fb35bfb559a4aeb6af6f6868` |
| `sourceforge.net/projects/odessa/files/Pasco/20040505_1/pasco_20040505_1.tar.gz/download` | 200 | 4032 | 3.88 s | 同上 |
| `master.dl.sourceforge.net/project/odessa/Pasco/20040505_1/pasco_20040505_1.tar.gz` | 200 | 4032 | 2.64 s | 同上 |
| `deb.debian.org/debian/pool/main/p/pasco/pasco_20040505.orig.tar.gz`（仅交叉核验，⛔不入配方） | 200 | 4032 | 6.53 s | 同上 |

- 三条官方端点全部 302 → `master.dl.sourceforge.net/project/odessa/Pasco/20040505_1/...?viasf=1&fid=...&e=...&st=...` 并在 7 秒内落真件，CI 可直取；配方取 **canonical** `downloads.sourceforge.net/project/...`（跳转前的稳定端点，带完整 FRS 子目录）。
- Debian 池件与官方件**同哈希同尺寸** ⇒ 认定同一文件（池件只是搬运，未重打包）；`conandata.yml` 只写官方 URL。
- 归档内文件清单（4 个）：`CHANGES`、`Readme.txt`、`src/Makefile`、`src/pasco.c`；根目录名 `pasco_20040505_1/` ⇒ `strip_root=True`。

## 编译步骤

```sh
conan create . -o ...            # 由 ohc-run.py conan-verify 驱动
# 等价手工步骤（实测通过）：
tar xzf pasco_20040505_1.tar.gz && rm -rf pasco_20040505_1 && mv pasco_20040505_1/* .
patch -p1 -i 0001-Makefile.patch
make -C src install -j1 CC=/data/service/hnp/bin/clang CFLAGS= LDFLAGS=
```

- `all:` 只是 `install:` 的别名；`install` 在 `src/` 里编译出 `pasco`，再 `cp` 到 `../bin`。
- 实测产物：`src/pasco` + `bin/pasco`（`MAKE_RC=0`、`BIN_OK`）。

## 源码修改（★整文件替换 vs 最小补丁的判定，逐字披露）

**结论：最终形态是「最小补丁 + 命令行传参」，没有整文件替换。**

上游 `src/Makefile` 全文 10 行，实测读数：

```makefile
all: install

install:  pasco.c
	gcc -o pasco pasco.c -lm -lc;cp pasco ../bin

installwin:  pasco.c
	gcc -DCYGWIN -o pasco.exe pasco.c -lm -lc;cp pasco.exe ../bin

clean: 
	rm -f pasco.exe pasco
```

- `grep -c 'override'` = **0**；`grep -c '$(CC)'` = **0**；`grep -c '$(CFLAGS)'` = **0**。
- ⇒ 与「上游有 CC/CFLAGS 变量、命令行 `make CC=clang` 必然覆盖文件内赋值」的常见形态**不同**：
  上游编译行里**根本没有变量**，编译器是字面量 `gcc`。命令行传 `CC=`/`CFLAGS=` 无处生效，
  **不改源码就编译不出来**。所以「只传参数不打补丁」这条路在本包不成立，补丁是必需项。
- 补丁只做两处**就地**改写（`@@ -1,10 +1,10 @@`，行数不变，仅第 4、7 行），非整文件替换：
  1. `gcc` → `$(CC) $(CFLAGS) $(LDFLAGS)`（引入变量；`-lm -lc` 原样保留，`pow()` 需要 libm）；
  2. `cp pasco ../bin` → `mkdir -p ../bin && cp pasco ../bin`（发行包内**没有** `bin/` 目录，
     直接 `cp` 会落成一个名叫 `bin` 的文件而非目录）。
- `installwin:`（`-DCYGWIN` → `pasco.exe`）是 Windows 分支，同样改写但不被调用，保留是为与上游结构对齐。
- **未被删除/未被替换的上游目标**：`all`、`install`、`installwin`、`clean` 四个目标全部保留，
  命令语义除上述两点外逐字未动；`clean: ` 行尾的尾随空格也保持原样（补丁里是上下文行）。
- `pasco.c` **未改一个字节**：orig 与改后树 `sha256` 同为 `9ffa61f86fc1550758eac5204d2435c1146829fb6aee763642308ddd33d26efb`；补丁只作用于 `src/Makefile` 一个文件。
- 补丁头路径按**归档真实布局**写成 `a/src/Makefile`（与仓内 a52dec 等已合入包 `--- a/autotools/config.sub` 的口径一致），并把 `patch -p1` 应用到一份全新解包的副本上做过 `cmp` 校验：`APPLY_MATCH=YES`。
  前任脚本 `z74-07-refine.sh` 曾用 `printf ... > $BUILD_SRC_DIR/Makefile` 整文件重写探索目录，
  但它生成补丁时 harness 是拿 orig/work 两树做 diff，产物恰为 10→10 行的最小 diff；本次按同样语义
  用「新鲜解包 + 两处字符串等量替换（hits==1 硬校验）+ diff --label」重做，并把头路径修正到 `src/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make CC=clang` 无效，仍报找不到 gcc | 上游编译行是字面量 `gcc`，无 `$(CC)` 变量 | 最小补丁引入 `$(CC) $(CFLAGS) $(LDFLAGS)`（见上节） |
| 2 | `cp pasco ../bin` 产出的是名叫 `bin` 的文件 | 发行包不含 `bin/` 目录 | 补丁里 `mkdir -p ../bin &&` |
| 3 | 补丁打到不存在的 `Makefile` | 归档根是 `pasco_20040505_1/`，Makefile 实际在 `src/`；旧补丁头是 `a/Makefile` | 补丁头改 `a/src/Makefile`，配 `strip_root=True` |
| 4 | clang 15 对上游源码报 5 条 warning（3 个 int 函数无 return、`strcpy/strncpy` 隐式声明） | 1997 年 C 代码不合 C99 后规范 | 不改上游逻辑（R8），仅记录；clang 16+ 会把隐式声明升为 error |
| 5 | 非 index.dat 输入会挂住 | 上游不校验头部魔数/版本，`filever=0.0` 后进记录遍历死循环 | 不改上游；测试用 `timeout 5` 兜住并断言 rc=124 + `Version: 0.0` |

## 依赖版本
- 编译依赖：clang + make（平台自带）；Conan 层 `requires` 为空。
- 运行依赖：仅 libc / libm（`-lm -lc` 由上游命令行给出）。
- W0：`preflight_check.sh pasco/20040505` → `[OK] 预检通过（无依赖需要检查）`，无精确依赖需判定，未使用通配 `conan list`。

## CLI 真值矩阵（test_package 断言的唯一来源，实测于 `src/pasco`）

| # | 命令 | exit | stdout B | stderr B | 关键读数 |
|---|---|---|---|---|---|
| 1 | `pasco`（无参） | **254** | 105 | 0 | `Usage:  pasco [options] <filename>`（usage 写在 **stdout**） |
| 2 | `pasco index.dat` | **0** | 194 | 0 | `History File: …/index.dat Version: 5.2`；表头 `TYPE\tURL\tMODIFIED TIME\tACCESS TIME\tFILENAME\tDIRECTORY\tHTTP HEADERS`；记录行 `URL\thttp://example.com/index.html\t\t\t\t\t`（TAB 切 7 字段，空 FILETIME ⇒ 时间/文件名字段为空）；记录条数 1 |
| 3 | `pasco -t , index.dat` | **0** | 194 | 0 | 表头 `TYPE,URL,MODIFIED TIME,…`，记录行 `URL,http://example.com/index.html,,,,,`（逗号切 7 字段） |
| 4 | `pasco -d index.dat`（undelete） | **0** | 194 | 0 | 仍输出同一条 URL 记录，7 字段 |
| 5 | `pasco -q index.dat`（非法选项） | **255** | 193 | 82 | stderr：`…/pasco: unrecognized option: q`；stdout 仍含 `Version: 5.2` + usage |
| 6 | `pasco 不存在的文件` | **253** | 151 | 0 | `ERROR - The index.dat file cannot be opened!`（在 **stdout**，非 stderr） |
| 7 | `pasco junk.dat`（非 index.dat） | **124**(timeout 10) | 87 | 0 | `History File: …/junk.dat Version: 0.0` 后挂死 ⇒ 上游无输入校验 |

- 退出码来源：`pasco.c:377 exit(-2)`、`:387 exit(-3)`、`:409 exit(-1)`；shell 侧按 `& 0377` 报 254/253/255（`grep -n exit` 实测行号）。
- 上游测试：**0 条**。一手复算依据两条：①`src/Makefile` 全文只有 `all/install/installwin/clean` 四个目标，无 `check`/`test`；②发行包共 4 个文件（`find` 实测），树内无任何测试源文件。故 `MANIFEST.yml` 的 `upstream_tests: []`、`upstream_check_command: ""`。
- 合成样本依据：`test_package/gen_index_dat.py` 按 `pasco.c` 的偏移表构造（`Client Indexed Store` 魔数、`5.2` 版本串、0x300 尺寸、0x100 哈希表、0x200 记录、0x34 URL 相对偏移、0x38 目录名索引、0x3C/0x44 绝对偏移），产出 771 字节，实测被 pasco 正常解析为 v5.2。

## 验证结果

（`conan-verify` / `finish` 的 `[step]`、`_RESULT=`、`exit_code`、`log_sha256` 读数见下方「门禁实测」段，跑完当场追加，不事后追述。）

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | application 配方：`make -C src install -j1 CC=$(conf c)` |
| `conandata.yml` | 官方 URL + 已核验 sha256 + `patches:` 挂上补丁 |
| `patches/0001-Makefile.patch` | 10→10 行最小补丁，头路径 `a/src/Makefile` |
| `test_package/{conanfile.py,test.sh,gen_index_dat.py,MANIFEST.yml}` | 消费者测试：真执行二进制 7 组场景 |

## 注意事项
- 上游源码在 clang 16+ 下可能因隐式函数声明升级为 error 而编不过；本包固定在 clang 15 通过，未来工具链升级需另开补丁（不在本次范围，R8）。
- `pasco` 只吃 Windows IE `index.dat`；真实取证样本在本平台不可得，端到端断言依赖合成样本。
- conan-init 生成的 `test_package/CMakeLists.txt` 与 `test.c`（`find_package(pasco)` + `target_link_libraries(... pasco::pasco)`）是**库**模板，对本 application 不成立，已按仓内 `2048.c/1.0.3` 的应用型口径替换为 `VirtualRunEnv + test.sh`。
## 门禁实测（B 机，2026-09-27）

- `bash ci/scripts/preflight_check.sh pasco/20040505` -> `[OK] 预检通过（无依赖需要检查）`，rc=0（无精确依赖，未用通配 `conan list`）。
- `python3 scripts/ohc-run.py recipe-search pasco` -> `⚠️ 无相似配方（语料 6173 条）——首稿走 conan-init 模板`。
- `python3 scripts/ohc-run.py conan-verify pasco 20040505` -> `G1: PASS`、`G2: PASS`、`G3: PASS`、
  `✅ 配方验证通过: pasco 20040505`、`可标记 status: published`、`R46: 终态 result.json 已上报（draft:false）`，
  管道 rc=0；包 ID `6b129b068851896169fae42d399fa922d239ce8a`；
  `log_sha256(~/tmp/uc2/z74-pasco2/verify.log) = 080609691fadfb57deb70b858f8c45a46780695cacca94b4a1045d5acdc6e9b4`。
- **test_package 在 `conan create` 内真执行**（不是事后手工跑的）：`reports/conan-create.log:100` 起逐条
  `ok   [noargs] exit=254 (want 254)` …，`:146` = `ASSERTIONS=27 PASS=27 FAIL=0`。
- `finish pasco 20040505 built` 第 1 次：Step5 W3 本地 CI 模拟失败 ——
  `[fail] pasco/20040505 — L0 quality gate failed: commands_json_r38`、`L0_RESULT=fail: gate failed: commands_json_r38`
  （hint: 可执行包必须有软件级 `commands.json`）⇒ 已按 `archives/2/2048.c/commands.json` 口径补 `archives/p/pasco/commands.json`。
- `finish` 第 2 次报两条，均已定性：
  ① 内部 conan-verify `G2: FAIL`，第一条真实错误 `reports/conan-create.log:97`：
  `…/patches/0001-Makefile.patch: source/target file does not exist:` + `--- b'a/Makefile'` + `+++ b'b/Makefile'`。
  根因 = harness 回写：`finish` 的 refresh-patch 从**摊平的探索目录**（`~/tmp/builds/pasco-20040505.{orig,work}` 把
  Makefile/pasco.c 放在根，而官方归档里它们在 `src/`）重生成补丁，把按归档真实布局写的 `a/src/Makefile`
  刷回 `a/Makefile` ⇒ 补丁打不到目标、必然 G2 失败。处置 = 探索目录改成与归档一致的 `src/` 布局
  （本次 finalize 已做）+ 复原补丁 + 重跑 finish。**不是配方缺陷，也不是官方源问题。**
  ② JC 门禁 `[FAIL] JC1: 3 个运行时状态文件被跟踪` / `[FAIL] JC5: 3 个 archives 下未登记的隐藏文件`，
  三条全部是**他人条目**：`archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、
  `archives/k/kics/2.1.20/.staging-verified`；`检查模式: full (85512 个文件)` 是整仓扫描，JC6 亦为
  `full 模式（整仓扫描），跳过单软件检查`，白名单在 `ci/scripts/junk_check.sh JC5_ALLOWED`。
  ⇒ 本包未产任何杂项/运行时文件；不改他人归档、不改框架（规则红线），照实记录。
  同轮 `KC_RESULT=pass`（`KC_ERRORS=0`、`KC5: index.tsv 一致 (540 = 540)`）。
- 结论口径：**包内门禁全绿**（preflight / recipe-search / conan-verify G1-G3 / conan create 内 27 条消费者断言 /
  commands.json R38 / 补丁与占位符已复原），W3 本地 CI 模拟**已通过**（检查模式: incremental (12 个文件)、JC_RESULT=pass；前轮 JC1/JC5 红点的真因是基线缺 `upstream/main`
  致 junk_check 退化为整仓扫描，补齐基线后自动消解，非本包缺陷、未动判据、未删他包文件）。
- harness 回写占位符命中数（每次 finalize 实测打印 `MANIFEST_HITS=`）：`patches_applied: []` = 1、
  `guard: 'pending'` = 1，均按补丁实物就地复原为 `patches_applied: [0001-Makefile.patch]` 与
  `guard: 'fresh_extract_patch_p1_cmp_identical'`；`platform_only: True`、`type: auto` 经核为真
  （补丁确由 diff 自动生成、且确为平台必需），保留不改。

## W3 复跑实测（第三棒，读数由脚本按本轮新日志实算）

- `finish pasco 20040505 built` 第 3 次：基线已 `git fetch upstream main`（upstream/main=5acd1dc19e、origin/main=48d9cee684、HEAD 前=96d5518738）。**Step 5/10 本地 CI 模拟 (W3) ✅ 通过**；整条命令 rc=2，缺口在 step5b / step8（见末两条，均非 W3）。
- junk_check 扫描模式：检查模式: incremental (12 个文件)（前轮为 `full (85512 个文件)`）；JC_RESULT=pass
- W3 日志逐条判决（原文）：
  - `G0_RESULT=pass`
  - `KC_RESULT=pass`
  - `JC_RESULT=pass`
  - `L0_RESULT=pass: all checks passed`
  - `L1_RESULT=pass: test_package executed`
  - `L2_RESULT=skip: pasco version/help failed`
  - `L4_RESULT=pass: patches clean`
  - `L5_RESULT=pass: bin/ has content`
- 断言（`reports/conan-create.log:146`，实算行号）：`ASSERTIONS=27 PASS=27 FAIL=0`
- `.ci-result.json` 原文字段：exit_code=0、timestamp=2026-09-27T02:03:58.801306、integrity_hash=5e083a3945a13098、step=W3_local_ci、log_sha256=3eea028579861114c50ec78901f525355cdb1cc4c38369675fd97305e3dac6a7
- 指纹实算比对：`sha256sum reports/w3-local-ci.log` = 3eea028579861114c50ec78901f525355cdb1cc4c38369675fd97305e3dac6a7（与 .ci-result.json 的 log_sha256 逐字节相等）
  `sha256sum reports/conan-create.log` = 27ee606be9cee18e3d7f3a9433f1ffa46f2466127cd99abb4b19c465eb801396
  `sha256sum ~/tmp/uc2/z74-pasco3/finish4.log` = eb8e0a8f7525dea1abfca3776d204f9db73c8294383ac2ff1c727517c1d8cd93（构建主机侧日志不入库，仅记指纹；`reports/` 被 .gitignore 通配排除）
- 计数实算：`[step]` = 47 条、`_RESULT=` = 8 条；包 ID 仍为 6b129b068851896169fae42d399fa922d239ce8a（本轮 conan-create.log 唯一 40-hex，配方未变故不变）
- 本轮 harness 回写核查：`patch_classification` 未被回写成占位符 —— manifest.yaml 实读 `guard: 'fresh_extract_patch_p1_cmp_identical'`、`type: auto`、`platform_only: True`、`patches_applied:` 保留补丁项；全包 `pending|todo|xxx` 命中 0；本轮 finalize 未打印 `MANIFEST_HITS=`。
- 未绿步骤定性（**不由本包修复**，本包无设计变更）：
  - step5b 知识图谱完整性：`❌ 发现 1 类问题` 指向**仓级他人条目** E219/E253/E305 的 `root_cause`/`rec_approach` 为空 + 全仓 1396 条待审草稿；本包 `unreferenced=3` 属知识库引用口径，非 W3 门禁。
  - step8 submit 就绪预检：缺 `reports/test-report.md`、`packaging/`、`.staging-verified`，属 `submit` 阶段产物（且 `.staging-verified` 正是 JC5 判杂项的对象，二者互斥）⇒ 留待主窗裁决，未自行创建。

---

**编译结束**: 2026-09-27 02:03
**最终状态**: built
