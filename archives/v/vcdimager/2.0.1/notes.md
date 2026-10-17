# vcdimager 2.0.1 适配笔记

## 编译环境
- 构建系统: autotools（configure + Automake parallel tests）
- 编译日期: 2026-09-26
- 编译器: clang 15（profile 里 tools.build:compiler_executables 指向 /data/service/hnp/bin/clang）
- 构建主机: B 机（HarmonyOS PC aarch64，8 核 / 31G），长杆槽 1-2
- CONAN_HOME: ~/tmp/ch/home-主理-45-vcdimager（沿用前任，依赖已缓存，整目录可重建）
- worktree: ~/qzy/主理-64-vcdimager-2.0.1 ｜ 分支 feat/vcdimager-2.0.1
- 棒次: 第 1 棒=主理-45（取源/配方/HMDFS 两关），第 2 棒=主理-64（本笔记所述修复）

## 路径 B 披露声明（3+2 行）

- **适配路径**：路径 B（配方适配 + 知识库扩展）——配方侧三处真实处置（libxml2 2.15 enc-handler
  调用式补丁 0001；toybox diff 的 tool_requires diffutils + configure DIFF 覆盖 + 把本次
  config.status 生成的 check_common_fn 搬进源码树；tool_requires 改走 dependencies.build 取径），
  外加一条新知识草稿。未加 --disable-*、未跳测试、未缩 TESTS 分母。
- **使用知识库**：`E114`（knowledge/graph/E114.kv:21-29，rec_approach `bypass-mktemp`——
  「预建临时目录（不用 mktemp）+ 把脚本里的 ac_tmp=$tmp 改指该目录 + export TMPDIR」）
  确被本配方执行：conanfile.py:305-339 的 _patch_configure_ac_tmp() 做该替换（由 build()
  在 conanfile.py:373 调起），conanfile.py:298-302 注入 PWD/TMPDIR/TMP/TEMP；生效面就是下表
  问题 #8 的两条 HMDFS 报错消失。**命中未采用**：`E490`
  （restore-known-autotools-script-modes）——第 14 轮 G0 报告仍打
  「⚠️ 已知风险 E490 未在配方中处理」（reports/conan-verify-report.md 的 G0 段，随包不入库，
  判决行已逐字抄在这里），本棒实测其症状签名（Permission denied / configure 不可执行 /
  config.guess 不可执行）在本包零命中：官方归档 tar 元数据里 configure、config.guess、
  config.sub、install-sh、missing 五件均已是 -rwxr-xr-x，解进第 14 轮缓存树
  p/b/vcdim6e0343264dee1/b 后实测仍为 -rwxr-x---，且该轮 conan create 的 configure 与
  make -j1 check 全部跑通 ⇒ 该处方对本包无必要性，未为此加 chmod（第 1 棒留下的 E540 与引擎给的
  E528/E386 三条同属误命中、也未采用，判据见「已试过的失败方案与误判纠正」第 1 条）。
- **知识库扩展**：`DRAFT-vcdimager-2.0.1-libxml2-2-15-enc-handler-union-legacy-call-sigsegv`
  （knowledge/drafts/ 内 .kv/.md 配对）——libxml2 2.15 把 xmlCharEncodingHandler 的 input/output
  改成匿名 union（成员 func 与 legacyFunc 同址但签名不同）后，按旧式 legacyFunc 型调用
  **编译通过、运行期参数错位 SIGSEGV**；两臂探针实测 rc=139 对 rc=0，draft-review 判 create
  （TOP3 最高 0.09，低于 0.30 灰区线）。
- **关联 Issue**：`#3434`（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3434）

## 编译步骤
唯一入口是一次 `conan create`（G2 与 W3 跑的是同一条命令，配方里已把上游
`make check` 集成进 build()，不拆成散脚本、不跳过、不裁剪）：

```bash
export CONAN_HOME=$HOME/tmp/ch/home-主理-45-vcdimager
export SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem
export PATH=$HOME/usr/local/bin:$HOME/.local/bin:$PATH
cd ~/qzy/主理-64-vcdimager-2.0.1
sh ~/tmp/uc2/gate.sh 8000                       # 必须 GATE_PASS
sh ~/tmp/uc2/build-slot.sh --kind long --wait 1800 --mem 8000 -- \
  python3 scripts/ohc-run.py conan-verify vcdimager 2.0.1   # G0/G1/G2
python3 scripts/ohc-run.py finish vcdimager 2.0.1 built      # W3 本地 CI 模拟
```

配方内实际执行的编译序列（build() 逐步）：apply_conandata_patches →
_patch_configure_ac_tmp(E114) → 同步 config.status 生成的 check_common_fn →
configure（预置 4 组 *_CFLAGS/_LIBS + DIFF + --build/--host）→ make -j1 →
make -j1 check → 从 test-suite.log 读数上报。

## 遇到的问题与解决方案

| # | 症状 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译期 4 条 error: invalid operands to binary expression（void * 与匿名 union），全在 frontends/xml/vcd_xml_common.c:245/246/250/251 | libxml2 2.15 把 xmlCharEncodingHandler 的 input/output 改成匿名 union，上游 2018 年的 handler->output(...) 直调在 C 里不再合法 | 补丁 0001 改走 union 成员（先按 legacyFunc 调，见 #2；最终按 func 调） |
| 2 | 打上「handler->output.legacyFunc(...)」后 vcdxbuild 任意 XML 输入都 Signal 11 (core dumped)，check_nrg.sh 直接 FAIL | union 两个成员**同址但签名不同**：2.15 内部只填新式 func(void *vctxt, out, outlen, in, inlen, flush)。按 4 参 legacyFunc 型调用 ⇒ 第 1 个实参（out 缓冲区）被 callee 当成 vctxt 解引用 ⇒ 段错误 | 补丁改为 handler->output.func(handler->outputCtxt, out, &out_size, in, &temp, 0)（input 侧同理用 inputCtxt）；NULL 守卫语义不变（同址，判空等价） |
| 3 | check_vcd11/check_vcd20/check_svcd1 在「vcdimager cksum(1) checksums matched :-)」之后挂掉：diff: vcd11_test0.dump: Invalid argument，脚本 exit 3 | /usr/bin/diff 在 OHOS 是 **toybox 软链**（实测 /usr/bin/diff -> ../../bin/toybox，toybox 0.8.12），对 -w --unified 直接 EINVAL；镜像与 cksum 全对，纯是 harness 用错实现 | configure 命令行预置 DIFF=<conan 依赖图里 GNU diffutils 的绝对路径>（上游 configure 明写支持该覆盖），依赖走 tool_requires diffutils/3.12 |
| 4 | 第 3 条的 DIFF 覆盖第 9 轮已进 configure（config.log 里 result 就是 conan 的 diff），但测试仍报同一 EINVAL | 上游 tarball 里的 test/check_common_fn 是**作者机器上预先烧好 /usr/bin/diff 的生成物**（实拍 mtime 2018-01-08 08:46:41），而 check_*.sh 一律 source 源码树那一份；out-of-tree 下 config.status 把新生成物写到 build 目录 ⇒ 覆盖永远传不进去 | build() 里 configure 之后把 config.status 刚生成的那份搬进源码树；搬之前先自证新物里引用的确实是我们那个 GNU diff 的绝对路径，对不上直接失败（防静默退回 toybox） |
| 5 | generate() 抛 KeyError: diffutils not found in the dependency set | tool_requires 落在**构建上下文**，self.dependencies[名字] 的按名查找只覆盖 host 上下文 | 改为遍历 self.dependencies.build.values() 按 ref.name 取 |
| 6 | test_package 14 项断言里 2 项失败：输出里没有 /libcdio/ | 断言规格写错了：vcd_version_string()（lib/vcd.c:2426 起）只打 GNU 标准横幅，全树 grep 不存在任何 libcdio 版本打印 ⇒ 不是产品/平台缺陷 | 拆掉两条错断言，换成 vcdxgen 生成 XML + vcdxbuild 读回的真实数据面断言（同时充当 #2 的崩溃哨兵）；文件头覆盖面说明一并更正 |
| 7 | W0 预检打印「未找到依赖声明」后直接「预检通过」 | 配方用类属性元组 requires = "a/1", "b/2"，而 ci/scripts/preflight_check.sh:91 的正则只解析调用式 requires(...) ⇒ 依赖面在门禁眼里不存在，假绿 | 声明改成 requirements() 里的 self.requires()/self.tool_requires() 调用式；改后预检如实报出 4 个依赖并逐个 conan download --only-recipe |
| 8 | configure 起手 working directory cannot be determined / config.status 写 subs1.awk Permission denied | HMDFS 拒绝构建树父目录 getcwd；config.status 在新建目录里写文件被拦（E114 家族） | 第 1 棒已处置：配方侧 Environment 注入 PWD/TMPDIR + configure 内 ac_tmp 预置（先例 adcli/0.9.2、abiword-plugin-docbook/3.0.8），本棒复核有效 |
| 9 | 第 12 轮 G2 已全绿，但 HMBS_TEST_PACKAGE_RESULT 报 discovered=14，而同一份日志里 test.sh 的汇总行报「17 项断言，失败 0 项」 | test_package/conanfile.py 把断言条数**硬编码**成 14（1 run×6 + 5 grep + 3 负控制），本棒把 2 条错规格断言换成 5 条真实断言后没跟着改 ⇒ 机器读数与证据不同源 | 改成 _count_assertions() 从同目录 test.sh 现数（run / grep_check 各算 1 条，静态数得 17），passedCount 口径写明「test.sh 自身 FAILED 计数为 0 才等价全过」；失败分支仍记 0，逐条读数留在日志 |


**#3/#4 的取舍补充：覆盖 DIFF 会让上游的 DIFF_OPTS 变成空，比对因此变严（不是变松）**

上游 `test/check_common_fn` 的比对行用的是 `$DIFF $DIFF_OPTS` 两个变量，而 `configure` 只在
`$DIFF <opt> ./configure ./configure` 探针通过时才把 `-w --unified` 追加进 `DIFF_OPTS`
（本轮构建目录里 `configure:17211-17215`；命中时会另向 config.log 打一行
`adding <opt> to diff in regression tests`）。本包是 out-of-tree 构建，`build-release/` 下没有
`./configure`（实测该路径 No such file）⇒ 探针不命中，实读 config.log 只有
`DIFF='<conan 依赖图里的 diffutils>/bin/diff'` 与 `DIFF_OPTS=''`，生成的比对行是
`<GNU diff 绝对路径>  ${outfile} ${rightfile}`（两个空格即 DIFF_OPTS 为空），
pristine tarball 那份同一条则是 `/usr/bin/diff  -w --unified ${outfile} ${rightfile}`。
⇒ 回归比对由「忽略空白 + unified 输出」变成逐字比对，**比原生 Linux 口径更严**；
8 项仍全绿、`test/` 目录 grep `Invalid argument` 零命中。这是取舍不是缺陷，写明备查。

## 源码修改

| 文件 | 改动 | 说明 |
|------|------|------|
| frontends/xml/vcd_xml_common.c | 补丁 0001（patches/0001-vcd-xml-common-libxml2-2.15-enc-handler-union.patch）：_convert() 里 2 处 handler->output / handler->input 直调改为 func(<方向>Ctxt, out, &out_size, in, &temp, 0) 新式调用 | 不改 TESTS、不改任何测试文件、不加平台宏（PF5 合规）；ret 与 temp 的判定口径在新 API 下与 legacy 一致（inlen 出参=已消费字节、outlen 出参=已产出字节，失败一律负值），故补丁只动调用式，未动 _convert 的后续逻辑 |

按 R6「只改源文件不改生成文件」：test/check_common_fn 属**上游发布归档里预烧好路径的生成物**，配方**不编辑其内容**，只把 config.status 本次生成的同类产物搬到该位置（等价于 in-tree 构建下自动发生的事），细节见上表 #4。

## 依赖版本（W0 一手证据）

全部为 configure.ac 里的硬性 PKG_CHECK_MODULES，不用 --disable-* 绕残废包。
预检命令：bash ci/scripts/preflight_check.sh vcdimager/2.0.1（本棒把声明改成调用式之后才真正生效）

| 依赖 | 用途 | 发布态证据（2026-09-26，构建主机 B，本棒实测） |
|---|---|---|
| libcdio/2.3.0 | cdio + iso9660 + udf 合集（libiso9660 不需要独立配方） | [OK] 已发布（conan download --only-recipe，rev 011d2512246208d85a9afec61a933dfe） |
| popt/1.16 | CLI 参数解析 | [OK] 已发布（rev cca44e0c65c2ff043d329f27a068a956） |
| libxml2/2.15.3.1 | xml 前端 | [OK] 已发布（rev d306e63f5f09376deb0038a5da1f2837） |
| diffutils/3.12（tool_requires） | 上游 test/ 的回归比对必须是 GNU diff | [OK] 已发布（rev 1847bcef5ee9aa67290e4a1ef7f69306）；二进制包可直接下载：create 日志里 Package installed 6b129b068851896169fae42d399fa922d239ce8a |
| zlib/1.3.1 | 非本包直接依赖（前任留档） | [OK] 已发布（rev 2ee7c0eeb8f4dfef8982d0c5c1551a61） |

R35 合规：判发布态只用 conan download --only-recipe 与精确 install，未用通配 conan list。
libiso9660 的三条 dl-*.txt 是 rc=1 但错误体为空/「system acceleration policy not enabled」，
按 R35 口径**不构成**未发布的一手证据；且 libcdio/2.3.0 归档本体即含 libiso9660.pc.in 与
lib/iso9660/，其 package_info 亦声明 cpp_info.libs = ["iso9660","udf","cdio"] ⇒ 本包不缺依赖。

## 验证结果

### 上游测试五维账本（rule4 口径，读数取自 automake 自己的 test-suite.log）

静态分母来源：test/Makefile.am 的 TESTS 块逐字 8 项
（check_sizeof、check_bitfield、check_nrg.sh、check_vcd11.sh、check_vcd20.sh、check_svcd1.sh、testassert、testvcd），
XFAIL_TESTS = testassert。**分母未缩减、未加任何 --disable-*、未跳测试。**

| 维度 | 数值 | 依据 |
|---|---|---|
| 静态总数 | 8 | test/Makefile.am TESTS 块（不是估计，是声明值） |
| 可执行数 | 7 | 8 项全部被 automake 调起；其中 testvcd 需物理 CD-ROM 内有 VCD，运行期自行返回 77 跳过（test/testvcd.c:68 与 SKIP_TEST_RC=77 定义在 :49） |
| 实测通过数 | 6 | test-suite.log 的 # PASS: 6（check_sizeof、check_bitfield、check_nrg.sh、check_vcd11.sh、check_vcd20.sh、check_svcd1.sh） |
| 上游预期失败 | 1 | # XFAIL: 1（testassert，上游自标 XFAIL_TESTS，照实计 XFAIL 不当通过） |
| 跳过数 | 1 | # SKIP: 1（testvcd，缺光驱介质；非平台限制，CI 同样会 SKIP） |
| 失败数 | 0 | # FAIL: 0、# XPASS: 0、# ERROR: 0 |

上游日志路径（本轮实跑落点，reports/ 被 .gitignore 忽略，故在此写明相对位置）：
test/test-suite.log 与 test/<每条>.log，位于 conan 构建目录
CONAN_HOME/p/b/<vcdimager-rev>/b/build-release/test/；聚合读数同时打进
conan-create.log 的 Testsuite summary 块，并由 _emit_upstream_test_result()
以 HMBS_UPSTREAM_TEST_RESULT= 单行 JSON 输出。

### 消费者测试（test_package/test.sh）账本

| 维度 | 数值 |
|---|---|
| 静态断言数 | 17（原 14，本棒拆掉 2 条错规格、补 5 条真实数据面断言） |
| 实测通过 | 17 |
| 失败 | 0 |
| 读数位置 | conan-create.log 的「== 消费者测试汇总：17 项断言，失败 0 项 ==」 |

覆盖面：7 枚安装出来的 CLI 逐个真执行 -V/--version 并断言版本串 2.0.1；
vcdxgen 由 mpeg 轨道生成 videocd.xml（断言 stdout 成功提示 + 生成文件里的 <videocd 根节点）；
vcdxbuild 读回该 XML（断言它推进到 mpeg 扫描诊断，即 libxml2 解析面已跑通且未段错误）；
两条负控制（非法选项必须非零退出，防无条件 return 0 的假绿）。

## 最小复现

### 复现 A：libxml2 2.15 enc-handler 的 union 签名陷阱（不需要整包构建，秒级）
```bash
H=$HOME/tmp/ch/home-主理-45-vcdimager
L=$H/p/libxme5a5c01c709a6/p          # libxml2/2.15.3.1 制品
cd ~/tmp/uc2/z64-vcdimager/probe
/data/service/hnp/bin/clang -w -I$L/include/libxml2 -L$L/lib -lxml2 -o armA armA.c
/data/service/hnp/bin/clang -w -I$L/include/libxml2 -L$L/lib -lxml2 -o armB armB.c
LD_LIBRARY_PATH=$L/lib ./armA ; echo ARM_A_RC=$?     # 期望 139（SIGSEGV）
LD_LIBRARY_PATH=$L/lib ./armB ; echo ARM_B_RC=$?     # 期望 0，并打印 out=abc
```
两臂只差一处调用式（同一 handler、同一 UTF-8 输入）：
  armA  = handler->output.legacyFunc(out, &out_size, in, &temp)                 → Signal 11 (core dumped)，ARM_A_RC=139
  armB  = handler->output.func(handler->outputCtxt, out, &out_size, in, &temp, 0) → ret=3 out_size=3 temp=3 out=abc，ARM_B_RC=0
运行时读数（同目录 probe.c）：xmlFindCharEncodingHandler("UTF-8") 返回非空 handler，
in.func == in.legacyFunc（同址）、out.func == out.legacyFunc（同址）、inCtxt/outCtxt/ctxtDtor 均为 0、flags=1
⇒ 「判空守卫」在 union 下恒等价，真正决定生死的是**调用签名**，不是判空成员名。

### 复现 B：toybox diff 与 GNU diff 的两臂（用第 7 轮留下的真实夹具）
```bash
H=$HOME/tmp/ch/home-主理-45-vcdimager
B=$H/p/b/vcdim54c781a20bf5f/b/build-release/test     # 第 7 轮现场
S=$H/p/b/vcdim54c781a20bf5f/b/test
cd $B
/usr/bin/diff -w --unified vcd11_test0.dump $S/vcd11_test0.right ; echo SYSDIFF_RC=$?   # 2，diff: vcd11_test0.dump: Invalid argument
$H/p/diffu1466ff337ed2a/p/bin/diff -w --unified vcd11_test0.dump $S/vcd11_test0.right    # 0（内容逐字一致）
ls -l /usr/bin/diff                     # lrwxr-xr-x ... /usr/bin/diff -> ../../bin/toybox
/usr/bin/diff --version | head -1       # toybox 0.8.12
```
⇒ 镜像与 vcd-info 输出本来就是对的，FAIL 完全由 diff 实现造成。

### 复现 C：补丁与归档对字（零构建）
```bash
cd ~/tmp/uc2/z64-vcdimager/patchtest && rm -rf tree3 && mkdir tree3 && cd tree3
tar xzf ~/tmp/uc2/z45-vcdimager/src/vcdimager-2.0.1.tar.gz --strip-components=1
patch -p1 -i ~/qzy/主理-64-vcdimager-2.0.1/archives/v/vcdimager/2.0.1/patches/0001-*.patch   # APPLY_RC=0
```
⚠ 踩过的坑：hunk 头 @@ -242,13 +242,13 @@ 与正文行数必须严格一致——把调用拆成两行续写后
行数变 15，**patch --dry-run 仍报 RC=0，真实 apply 却不生效**（静默），所以补丁改动必须做真 apply 复核。

## 已试过的失败方案与误判纠正

1. **E540（shadow-ci / runner-path-prepend）是误命中，不是本包根因**。判据：如果 PATH 缺工具是真根因，
   报错应是 make/not found 一类；实拍首错是 C 语言语法错（invalid operands to binary expression）。
   本棒未照它给的 EXTRA_PATH 命令去「修 PATH」。同类误命中还有第 9/10 轮引擎给的 E528、E386
   （E386 命中的详细文档 doc/E330.md 讲的是 CMake SONAME 软链接，与命中的 error_signature 明显不对题——
   这条知识条目缺陷第 1 棒已记在台账 C3，仍留给主理裁定，本棒未动知识位）。
2. **「补丁登记了却没落地」的两种猜测均被否证**：(a) 陈旧缓存跳过 source()——CONAN_HOME 里每轮都是
   新的 p/b/vcdim<hash> 目录（20:29/20:45/20:48/21:12/21:17/21:22 六枚），recipe revision 变就重开目录，
   source() 每轮真跑；(b) build() 把未打补丁的源码树复制进 build 目录——basic_layout 下
   source_folder = p/b/<rev>/b，报错文件路径正是该目录里的源文件本身，编译走 build-release/ 子目录，
   不存在外部 src 复制。真正原因是**时间线**：conandata.yml 与补丁文件的 mtime 是 21:27，
   而第 6 轮 conan create 在 21:22:30 就已起手，那一轮导出的配方快照里根本没有 patches 段。
3. **把 legacyFunc 当成「与原调用签名一致」的替代成员**（第 1 棒补丁的原始写法）：语法过、语义错，
   后果是 vcdxbuild 全线段错误。已在 #2/复现 A 处置。
4. **DIFF 覆盖「配了但不生效」**：第一次以为 configure 不认命令行 DIFF（错，config.log 证明它认），
   真因是测试读的是源码树里上游预烧的旧生成物。
5. **用 stdout 断言文件内容**：vcdxgen 把 XML 写到 -o 目标文件，stdout 只有成功提示 ⇒
   grep_check 断言 <videocd 必假失败（第 11 轮实拍），已改为对文件做 grep。
6. 未使用任何 --disable-* / 未跳测试 / 未缩 TESTS 分母；未手改 .ci-result.json 等生成证据件。

## 适用边界（给后续包参考）
- 复现 A 的机制适用于**任何按 2.15 之前 API 调 xmlFindCharEncodingHandler / xmlGetCharEncodingHandler
  再直调 input/output 的老代码**（union 化后判空恒真、调用必错位）；不适用于只用
  xmlReadDoc/xmlParseFile 等高层接口、不碰 handler 结构体的包。
- 复现 B 的机制适用于**上游把 configure 探测结果烧进随包发布的测试脚本**（@VAR@ 已替过、
  且脚本从 srcdir source）的 autotools 包；这类包只改 configure 命令行变量不够，必须处理
  「源码树里那份旧生成物」。判据：生成物 mtime 等于归档打包时间（本包 2018-01-08）而不是本轮构建时间。
- toybox 家族（diff/sed/expr/file/…）在 /usr/bin 下是软链，凡 configure 用 AC_PATH_PROG 探到
  /usr/bin/<tool> 并被烧进脚本，都要按「实现不是 GNU 版」复核，不能只看退出码。
- HMDFS getcwd 与 E114 两关（第 1 棒）在本包已由配方侧 Environment + configure ac_tmp 处置，
  本棒复核有效；CMake 包不适用该判据。

## B 候选机制台账（本棒只做证据与四范围查重计数，判档交主理）

第 1 棒已立 C1（HMDFS getcwd）/C2（合集包多 .pc 名）/C3（E490+E386 测试 shell）/C4（check_env.py 崩溃，框架件）。
本棒新增 4 条，四范围 = knowledge/graph/ ｜ knowledge/drafts/ ｜ 经验文档/B草稿库/ ｜ 经验文档/手册/07-技术速查.md。

### N1  libxml2 2.15 enc-handler：union 同址不同签名，按 legacy 型调用新式指针必段错误
- 一手证据：复现 A 两臂（139 vs 0）+ encoding.h:200-208 结构体原文 + encoding.h:180 的 func 六参 typedef。
- 查重计数：knowledge/graph/ 对 legacyFunc|xmlCharEncodingHandler|EncConv 命中 **0**；
  knowledge/drafts/ 同关键词命中 **0**；经验文档/B草稿库 **0**；手册/07 **0**。
  最接近的只是 error_signature 形状像：knowledge/drafts/DRAFT-8945-botan3-clang15-libcpp20-target-attr.kv:23、
  DRAFT-cloop-3.14.1.3-nmu1-ohos.kv:6、DRAFT-libcxx15-missing-cpp20-spaceship.kv:11、E999-draft-B5EC.kv:10、
  E565-draft-2404.kv:10（全是 C++/Qt 的 invalid operands，无一是"结构体成员 union 化 + 函数指针签名"），
  E2175-draft-623C.kv:9 含 Error loading shared library libxml2\.so\.16（libxml2 升级副作用的**另一层次**：装载面）。
  ⇒ 层次差：现有条目都在"编译器不接受/找不到符号"，本条在"编译得过但运行期参数错位"，无同层条目可对齐行号。

### N2  OHOS /usr/bin/<tool> 是 toybox 软链：configure 探到的绝对路径被烧进随包测试脚本
- 一手证据：复现 B 两臂 + ls -l /usr/bin/diff -> ../../bin/toybox + toybox 0.8.12。
- 查重计数：knowledge/graph/ 命中 **toybox 家族 E010**（knowledge/graph/E010.kv:10 error_signature、:14 match_keywords、
  :18 root_cause、:20、:27 rec_description），但 E010 覆盖面是 **sed/expr** 且处方是"装 GNU 工具 + PATH 前置"；
  另有 E043（/bin/sh 是 toybox ash）、E076:39（toybox 替代 GNU coreutils 作 fallback）、E098:16（命令缺失）。
  knowledge/drafts/ 命中 toybox 的：DRAFT-13491-lesspipe-2.27-toybox-file-mime-fallback.*、
  DRAFT-9200-lddtree-shell-tool-portability.*、DRAFT-11301-ohos-compile-fail-suite.* —— 分别是 file/ldd/编译面。
  经验文档/B草稿库 **0** 同机制（只有 DRAFT-PKG-VER-hongmeng-signal-ownership-fcntl-unimplemented.kv:14 的
  Invalid argument 字样，是 fcntl 能力墙，不相关）；手册/07 **0**。
  ⇒ 层次差待主理判：E010 是"构建期工具行为差异 + 装 GNU 替代"，本条是"测试期系统绝对路径被烧进脚本
  + 用上游 precious var 指向 conan 制品"，处置面与生效面都不同一层。

### N3  tarball 里预烧好 @VAR@ 的旧生成物挡住 configure 覆盖（本条与 N2 是同一条链的下一层）
- 一手证据：srcdir 那份 check_common_fn mtime **2018-01-08 08:46:41** vs build 目录那份 02:16:43（本轮生成）；
  config.log:588 result 已是 conan 的 diff；srcdir 那份 grep 仍是 /usr/bin/diff。
- 查重计数：knowledge/graph/ 命中 6 处但都是 pre-generated **输入件**语义（E286.kv:37 provide-pre-generated-inc-files、
  E426.kv:15、E447.kv:15、index.tsv:672 等），无一条讲"已生成物挡住覆盖"；knowledge/drafts/ **0**；
  经验文档/B草稿库 **0**；手册/07 **0**。
  ⇒ 判据可复用：凡 configure 变量覆盖配了但不生效，先看被改的是不是归档里预烧过的生成物（看 mtime）。

### N4  门禁正则盲区：类属性元组式 requires 让 W0 预检与 PF4 依赖闸看不见依赖
- 一手证据：ci/scripts/preflight_check.sh:91 的正则只匹配调用式；改前打印「未找到依赖声明」+「预检通过」，
  改后同一命令如实报 4 个依赖并逐个 conan download。
- 查重计数：knowledge/graph/ **0**；knowledge/drafts/ 仅 DRAFT-ohos-conan-wheel-missing-distro.md:8
  提到 preflight_check.sh（那是 wheel 缺 distro 致 preflight 跑不起来，不同机制）；
  经验文档/B草稿库 最接近的是 DRAFT-PKG-VER-conan-override-drops-requirement.kv:10 与 .md:9
  （同为"requires 面的假绿"，但机制是 conan 的 override 语义不引入依赖，不是解析正则盲区）；
  手册/07 **0**；另 经验库/01-使用方法与开工闸门.md:48 是人工程序口径（不用通配库存结果代替），非工具盲区。
  ⇒ 若主理判 create，注意本条的载体是**仓内门禁脚本**，与"包"无关，可能更适合框架件/通用池而不是本 PR 的知识位。
- 失效面补证（本棒第 13 轮之后才拿到）：仓内 CI 的 **L0i（R36 依赖发布闸）同样只认调用式**——ci/conan/build_and_test.sh 里那段 _L0I 内嵌 Python 用 ast.walk 只收 requires/tool_requires/build_requires 的 **Call 节点**，类属性元组式在 AST 里不是调用 ⇒ 声明的4 枚依赖对 CI 依赖闸也是隐形的；本棒改调用式后 W3 的 L0i 才真的看到依赖面。另：同文件 L0g 用正则 conan\s+(install|download|create|upload|export).*\s-r[= ] 扫 conanfile.py **全文（含注释与文档串）**，前任在文档串里写的三条 conan download … -r=ohpcd 直接把 W3 判红（实拍 L0_RESULT=fail: gate failed: hardcoded_remote），故配方内记证据只记读数、不记 remote 参数名。

### N5  conan tool_requires 在构建上下文，self.dependencies[名字] 只覆盖 host 上下文
- 一手证据：第 8 轮实拍 KeyError 文本 + 改遍历 dependencies.build 后 generate() 正常。
- 查重计数：knowledge/graph/ 命中 E241.kv:43、E264.kv:23、E300.kv:21,30,36、E473.kv:30、E499.kv:18
  （全部是 self.dependencies[名字] 的**正向用法**，且都是 host 依赖/CMakeDeps 场景，无一条讲 build 上下文取路径）；
  knowledge/drafts/ 命中 VirtualBuildEnv 的有 DRAFT-10251-libnfc-tools-*.md、DRAFT-E2175-static-pkg-*.kv/.md、
  DRAFT-libical3-pkgconfig-consumer-chain.md；经验文档/B草稿库 命中
  DRAFT-PKG-VER-custom-configure-only-cli-args-no-env.kv:22,24,38（讲 VirtualBuildEnv 对手写 configure 不生效）、
  DRAFT-PKG-VER-lib-cli-tools-missing-from-consumer-runenv.kv:25,70（VirtualRunEnv 的 run=True 门槛 +
  os.path.join(self.dependencies[ref].package_folder, "bin") 写法）；手册/07 **0**。
  ⇒ 本棒判读：N5 与既有"conan 依赖上下文可见性"条目最可能同层（尤其 lib-cli-tools 那条 .kv:70 已在教同类取法），
  倾向 hit，请主理按行号对齐后定档；本棒未建 Issue、未动 knowledge/drafts。

## 交付物
本包交付物是 7 个命令行程序（不是库归档）：vcdimager、cdxa2mpeg、vcd-info、
vcdxbuild、vcdxgen、vcdxrip、vcdxminfo，另有内部库 libvcdinfo（package_info 只对外声明它）。
commands.json 在软件级目录 archives/v/vcdimager/commands.json（R38）。

## 证据件位置与可读性披露
reports/ 被仓内 .gitignore 忽略（.gitignore:2 packaging/、:96 reports/），本笔记里按行号引用的
conan-create.log / config.log / test-suite.log 只对构建主机 B 该次运行有效；
凡被引用的**判决读数已逐字抄进本笔记**（上游汇总 7 行、消费者汇总行、两臂 RC、mtime、
软链目标、diff 报错原文），因此不依赖随包日志也可复核。驱动脚本与分轮日志：
~/tmp/uc2/z64-vcdimager/（run-verify.sh、verify-7..13.log、preflight-*.txt、
dl-diffutils-3.12.txt、evidence-round7.md、probe/armA.c+armB.c+probe.c、patchtest/、difftest2/）。

## 注意事项
1. 不要在别的包上照搬 DIFF=<绝对路径> 之前先确认该包测试真的 source 了被烧路径的生成物；
   若上游脚本用 PATH 找 diff，正解是 VirtualBuildEnv + tool_requires，而不是预置变量。
2. 本包的 testvcd 需要物理 CD-ROM 内有 (S)VCD 才会执行，任何机器上都会 SKIP 1 —— 
   报数时必须把它如实计成 SKIP，不许并进通过数。
3. conan 对本包只缓存过 recipe 时（conan download --only-recipe）不代表有二进制包；
   diffutils 这次是实测 Package installed <pkgid> 才确认能直接下载。
4. 第 1/2 棒之间未改动第 1 棒留下的 HMDFS 两处处置（PWD/TMPDIR 注入、configure ac_tmp 预置），
   复核有效；若后续包重构这两处，注意 build() 里 check_common_fn 搬运发生在 configure 之后。

## 路径 B 候选（不定档）
候选机制见上节 N1-N5 与第 1 棒台账 C1-C4（在 reports/knowledge-candidate-ledger.md，不随 PR）。
**本棒不判 create/hit/none、不建 Issue、未动 knowledge/drafts 与 B草稿库**，判档与 3+2 声明行由主理出。
注意 N5（conan 构建上下文取依赖路径）与既有池件
DRAFT-PKG-VER-lib-cli-tools-missing-from-consumer-runenv.kv:70 高度可能同层 ⇒ 若要升 create
需先按行号对齐、对不上就降 hit；N2/N3 与 E010 的层次差判读见台账正文。

### 对话 1
- 主理-64（第 1 执行棒，2026-09-26 01:4x-02:4x，构建主机 B）：接手 主理-45 的【交接】行，
  先用 mtime/git 对字时间线否证了「陈旧缓存」与「build() 复制未打补丁源码树」两条嫌疑，
  定位第 6 轮 G2 红是补丁登记晚于该轮 conan create 起手；随后修掉三族真实缺陷
  （libxml2 2.15 enc-handler 调用式、toybox diff 与上游预烧生成物、conan 构建上下文取径），
  并把 test_package 两条错规格断言换成真实数据面断言、把硬编码计数改成同源推导。
  第 13 轮 conan-verify G0-G4 全 PASS（SLOT_RC=0）；第 14 轮（改完 L0g 后重跑，配方 revision 已变，
  旧日志不充数）再次 G0-G4 全 PASS 且 SLOT_RC=0；上游 make check TOTAL 8 / PASS 6 / SKIP 1 / XFAIL 1 / FAIL 0，
  消费者 17 项断言 0 失败；W3（finish step 5/10）2026-09-26 03:00 通过（该轮读数是本棒第 1 棒的证据，W5 整改后因构建输入变动已重跑，**当前生效的绑定读数见「对话 2」与状态行**）。
  W4 独立审计未做（审计者不得是被审者），交主理派独立棒。

### 对话 2
- 主理-64（W5 审计整改棒，2026-09-26 04:2x-04:5x，构建主机 B）：按判决件
  `~/tmp/uc2/z64-vcdimager/audit-r1.md`（P0=0 / P1=2 / P2=7）清零两条 P1、顺改四条零成本 P2：
  ①`test_package/test.sh` 的夹具目录去窗口化——原写死某窗任务级可丢弃目录，且
  `mkdir -p ... || WORK="."` 的兜底恰好是该文件注释自己防的「第二轮覆写」形态；改为
  `${TMPDIR:-${TMP:-${TEMP:-$HOME/tmp}}}/vcdimager-test-package.$$`（每轮唯一；不用 `mktemp -d`，
  HMDFS 上它给出 `drwx--S---`；两处都建不了就直接 `exit 1`，绝不退回包目录）；
  ②补软件级 `archives/v/vcdimager/README.md`（`knowledge/ARCHIVE-SPEC.md:72` 标「必须」）；
  ③`manifest.yaml` build_date 改 2026-09-26；④草稿 .md 删掉探针 printf 里的
  `(what patch 0001 does)` 串；⑤本文件补 `DIFF_OPTS` 变空的取舍披露；⑥本文件 testvcd.c 行号
  :67 → :68。test.sh 属构建输入 ⇒ 改完先提交推送、再重跑 **verify（第 15 轮，SLOT_RC=0）** 与
  **W3（第 2 轮，三判据见状态行）**；W3 的 L2 行仍是
  `L2_RESULT=pass: cdxa2mpeg --version OK, vcd-info failed, ...`（与披露 1 同形，未据此改判）。
- 一处新观察（不影响判决，留档）：verify 第 15 轮 recipe revision 未变 ⇒ `conan create` 缓存命中
  （`Already installed`、未重建），那一轮 `conan test` 的每条命令后都跟一行
  `shell-init/job-working-directory: error retrieving current directory: getcwd ...`
  （bash 取不到自身 cwd 的形状），17 项断言照全过；同一份 test.sh 在 W3 那轮（真跑全新构建）里
  该噪音 **0 次**（`grep -c job-working-directory` = 0）。⇒ 判为 harness 侧 cwd 现象、不是夹具
  改动的回归，也未据此放宽任何断言。W3 整改轮（第 3 轮）夹具实际落点 `/storage/Users/currentUser/tmp/vcdimager-test-package.20321`（$$ 唯一、每轮变；锚 `grep -n vcdimager-test-package. reports/w3-local-ci.log`）。

### 需主理知悉的三处披露
1. **W3 的 L2 行有歧义**：w3-local-ci.log 里 L2_RESULT=pass，但同行文字写
   「cdxa2mpeg --version OK, vcd-info failed, vcdimager --version OK, vcdxbuild/vcdxgen/vcdxminfo/vcdxrip failed」。
   这不是包缺陷：L2 是**不载 runenv 的裸跑**，xml 前端与 vcd-info 在裸跑下取不到 libxml2.so.16；
   权威读数按框架 *_RESULT 行与 test_package（conanrun 下 17/17 全过、-V 全部 rc=0）。
   本棒未据此放宽任何断言，也不建议把 L2 的 failed 字样当可执行性证据。
2. **finish 会把 conandata.yml 的 url 回写成镜像列表**（tsinghua/ustc/aliyun + 官方址），
   属框架 get_mirrors trap 而非本棒改动 ⇒ 收口时已从 HEAD 还原为**官方原址单值**
   （与第 14 轮 conan-verify 所用配方一致，也符合 R39/PF7 的取源口径）。
   ⛔ 后续任何人再跑 finish 都会再脏一次，建 PR 前须复核 git status。
3. **B 判定留给主理**：本棒按任务书只出候选机制台账（N1-N5 + 前任 C1-C4）与四范围查重行号，
   未判 create/hit/none、未建 Issue、未动 knowledge/drafts 与 B草稿库，故 PR 正文的 3+2 声明行需主理补。
状态：built（**W5 P1-1 整改轮（第 3 轮 W3）绑定读数**：本轮唯一构建输入改动 = conanfile.py 里 `HMBS_UPSTREAM_TEST_RESULT` 的计数行由 `"passed": passed + xfailed` 收回到 `"passed": passed`，与仓内既有房屋口径一致（本 worktree 实测 `grep -rl HMBS_UPSTREAM_TEST_RESULT archives/ --include=conanfile.py | wc -l` = 830 份，其中字面 `"passed": passed,` 318 份；`+ xfailed` 形式除本包外仅 `archives/a/adcli/0.9.2/conanfile.py:339` 一份）。recipe revision 因此由 `fbe01201d389083dcfbda56b00c22ce9` 变为 `119ae29923f093c64c4faaec1143a72d` ⇒ 上一轮 W3 证据整体作废、已重跑 finish。finish 一次跑完：Step4 conan-verify「G1: PASS / G0: PASS / G2: PASS / G3: PASS」+「✅ 配方验证通过: vcdimager 2.0.1」；Step5 打印「✅ W3 本地 CI 模拟通过」（驱动日志 `~/tmp/uc2/z64-vcdimager/w3-r3.log`，不随包）；Step6 finalize-archive 返回 RC=2（缺 release/debug tar.gz + 「notes.md 无对话记录」，与上一轮 w3-r2.log 同形、非本轮新引入，W3 阻塞门禁本身已过）；`.ci-result.json`：exit_code=0、step=W3_local_ci、timestamp=2026-09-26T06:14:07.859832、integrity_hash=f1446a8f951a9504、log_sha256 与下行实算值逐字相同（三值均由工具写入未手改）。`reports/w3-local-ci.log`：mtime 2026-09-26 06:14、78789 字节、sha256 `3fbeb7b418166d95afe07d4a7f3742893b06ead39e83f9e07522a018e8192e99`、`[step]` 48 枚 / `_RESULT=` 10 枚、尾行「[step] All packages built and tested successfully ✅」；本轮为全新构建（`Calling build()`、`Package 'd946a5afc940aaf67b9ac959e79cdc644bd0fe0d' built`、build folder `vcdim0d30dbd4ef710`、`Created package revision 4ae90bfb0e418808e76ee8d125e73ae2`）。**上游测试三处同源（一律给机器可读锚；行号只作本轮定位辅助，重跑不再作废）**：① automake 汇总（锚 `grep -n '^# TOTAL:' reports/w3-local-ci.log`，本轮 715-721 行）= `# TOTAL: 8 / # PASS: 6 / # SKIP: 1 / # XFAIL: 1 / # FAIL: 0 / # XPASS: 0 / # ERROR: 0`；② `HMBS_UPSTREAM_TEST_RESULT`（锚 `grep -n HMBS_UPSTREAM_TEST_RESULT reports/w3-local-ci.log`，本轮 :739）= discovered 8 / executed 7 / **passed 6** / failed 0 / skipped 1 / xfail 1；③ 本目录 `manifest.yaml` 的 `upstream_tests_passed: 6`。三者同一个值，并落实本笔记「注意事项 2：SKIP 不许并进通过数」——xfail 与 skip 各按自己的字段单列，`passed` 不再并入任何非 PASS 项。逐条判决行（本轮行号）：PASS 6 项 :703-708（check_sizeof、check_bitfield、check_nrg.sh、check_vcd11.sh、check_vcd20.sh、check_svcd1.sh）、XFAIL 1 :710（testassert）、SKIP 1 :711（testvcd）。消费者 test_package 17/17（锚 `grep -n 消费者测试汇总 reports/w3-local-ci.log`，本轮 :993；`HMBS_TEST_PACKAGE_RESULT` discovered=17/passedCount=17 本轮 :996；`grep -c "^----- \["` = 17、`grep -c ❌` = 0、cwd 噪音 `grep -c job-working-directory` = 0）。finish 再次回写的 conandata.yml 镜像已由 `git show HEAD:archives/v/vcdimager/2.0.1/conandata.yml` 还原为官方原址单值。未上传制品仓）
---

**编译结束**: 2026-09-26 06:07
**最终状态**: built
