# libxml2 2.15 enc-handler 匿名 union——旧式 legacyFunc 调用编得过、运行期 SIGSEGV（草案）

> 草稿编号：DRAFT-vcdimager-2.0.1-libxml2-2-15-enc-handler-union-legacy-call-sigsegv
> 来源：vcdimager 2.0.1 适配（GNU vcdimager @ 2.0.1；依赖制品 libxml2/2.15.3.1，构建主机 B / HarmonyOS PC）
> 生成日期：2026-09-26 ｜ 起草署名：主理-64
> 路径判定：Path B（知识库扩展）→ new_draft ｜ 关联 Issue #3434

## 签名凭据（先说清取证方式，别当转述）

第 6 轮（2026-09-25 21:22 起手）的 `reports/conan-create.log` **已被后续轮次覆盖**，且 `reports/`
被仓内 `.gitignore` 忽略（`.gitignore:96`）⇒ 那一轮日志盘上已无原件。本棒把落点全找过一遍：
`~/tmp/uc2/z45-vcdimager/verify-1..6.log` 与 `~/tmp/uc2/z64-vcdimager/verify-7..14.log`（只存判决
摘要、不含编译行）、worktree 的 `.ci_logs/`（只剩 02:58 那一份）、`archives/` 全库
grep `invalid operands to binary expression`（命中的只有 `notes.md:36` 的中文转述与 w3 日志里
**已打补丁版**的 deprecation 告警行）。**原文确实不在盘上。**

⇒ 本条 `error_signature` 的四条 error 行由本棒**在同一棵第 6 轮缓存树上复现取得**：
`p/b/vcdim2af57a684b90d/b`（未打补丁版源码，`grep -c legacyFunc` = 0），编译参数原样取自该树
`build-release/frontends/xml/Makefile` 的 `make -n vcd_xml_common.o`，只把 `-c/-o/-MT/-MD/-MP/-MF`
换成 `-fsyntax-only`（不落任何产物、不改任何输入）。编译器、flags、源文件、头文件与第 6 轮
**四项同源**，故输出即第 6 轮原文（`REPRO_RC=1`，末行 `4 warnings and 4 errors generated.`）。
命令原文见同目录 `.kv` 的 `verification_cmd`。

## 问题描述

### 阶段一：编译期——槽位换了形态

`frontends/xml/vcd_xml_common.c` 的 `_convert()` 按 2018 年写法直调 handler 槽位
（`:245` `if (NULL != handler->output)` / `:246` `ret = handler->output (...)` /
`:250` `handler->input` / `:251` `handler->input (...)`）。libxml2 升到 2.15 后编译直接失败，
四条 error 逐字原文（路径为该轮缓存树实路径）：

```
/storage/Users/currentUser/tmp/ch/home-主理-45-vcdimager/p/b/vcdim2af57a684b90d/b/frontends/xml/vcd_xml_common.c:245:14: error: invalid operands to binary expression ('void *' and 'union (unnamed union at /storage/Users/currentUser/tmp/ch/home-主理-45-vcdimager/p/libxme5a5c01c709a6/p/include/libxml2/libxml/encoding.h:205:5)')
/storage/Users/currentUser/tmp/ch/home-主理-45-vcdimager/p/b/vcdim2af57a684b90d/b/frontends/xml/vcd_xml_common.c:246:29: error: called object type 'union (unnamed union at /storage/Users/currentUser/tmp/ch/home-主理-45-vcdimager/p/libxme5a5c01c709a6/p/include/libxml2/libxml/encoding.h:205:5)' is not a function or function pointer
/storage/Users/currentUser/tmp/ch/home-主理-45-vcdimager/p/b/vcdim2af57a684b90d/b/frontends/xml/vcd_xml_common.c:250:14: error: invalid operands to binary expression ('void *' and 'union (unnamed union at /storage/Users/currentUser/tmp/ch/home-主理-45-vcdimager/p/libxme5a5c01c709a6/p/include/libxml2/libxml/encoding.h:201:5)')
/storage/Users/currentUser/tmp/ch/home-主理-45-vcdimager/p/b/vcdim2af57a684b90d/b/frontends/xml/vcd_xml_common.c:251:28: error: called object type 'union (unnamed union at /storage/Users/currentUser/tmp/ch/home-主理-45-vcdimager/p/libxme5a5c01c709a6/p/include/libxml2/libxml/encoding.h:201:5)' is not a function or function pointer
4 warnings and 4 errors generated.
```

### 阶段二：运行期——「改成员名让编译过了」才是真陷阱

把四处改成 `handler->output.legacyFunc (out, &out_size, in, &temp)`（成员名对、类型按头文件的
`xmlCharEncodingOutputFunc`，与旧调用式参数表逐字一致）之后 **编译完全通过、补丁 apply 也通过**，
但 `vcdxbuild` 对任意 XML 输入一律 `Signal 11 (core dumped)`，上游 `check_nrg.sh` 直接 FAIL。
这一层编译器不给任何提示。

## 根因

本棒在制品头文件里实读（`sha256 0eabe928a57824d52b95daba1ee3e663f004d8622800f8c1f40177ea15a8a74c`）：

```
199  struct _xmlCharEncodingHandler {
200      char *name XML_DEPRECATED_MEMBER;
201      union {
202          xmlCharEncConvFunc func;
203          xmlCharEncodingInputFunc legacyFunc;
204      } input XML_DEPRECATED_MEMBER;
205      union {
206          xmlCharEncConvFunc func;
207          xmlCharEncodingOutputFunc legacyFunc;
208      } output XML_DEPRECATED_MEMBER;
209      void *inputCtxt XML_DEPRECATED_MEMBER;
210      void *outputCtxt XML_DEPRECATED_MEMBER;
211      xmlCharEncConvCtxtDtor ctxtDtor XML_DEPRECATED_MEMBER;
212      int flags XML_DEPRECATED_MEMBER;
213  };
```

`:179-181` 的新式 typedef 是 **6 参**：
`typedef xmlCharEncError (*xmlCharEncConvFunc)(void *vctxt, unsigned char *out, int *outlen, const unsigned char *in, int *inlen, int flush);`

union 起始行与编译器报错里的 `unnamed union at encoding.h:201:5`（input）与 `:205:5`（output）
逐字对得上。

两成员**同址但签名不同**，而 libxml2 2.15 内部只把新式 6 参指针填进这块存储 ⇒ 按 4 参
`legacyFunc` 型调用时参数整体错位一格：callee 把第 1 个实参（`out` 缓冲区）当作 `vctxt`
去解引用，第 2 个实参（`&out_size`，栈/全局地址）当作 `out` 指针用 ⇒ 当场段错误。

**缺陷分层是本条的全部价值**：阶段一那条 error 只说明「槽位换了形态」；真正致命的是「同一块
存储两副签名、库只填其中一员」，而这一层编译器看不见。

## 解决方案

1. 先实读制品头文件的 struct 与 typedef，抄下 union 成员名、类型、行号（别拿二手描述当依据）。
2. 用**只读探针**问出「库实际填的是哪一员」——打印两成员的指针值与配套 context 字段。本包实拍：
   ```
   UTF-8        handler=0x5a1b36be78
      in.func=0x5a1b2a34c4 in.legacy=0x5a1b2a34c4 out.func=0x5a1b2a34c4 out.legacy=0x5a1b2a34c4
      inCtxt=0 outCtxt=0 ctxtDtor=0 flags=1
   ISO-8859-1   handler=0x5a1b0540c0
      in.func=0x5a1b2a3278 in.legacy=0x5a1b2a3278 out.func=0x5a1b2a33f0 out.legacy=0x5a1b2a33f0
      inCtxt=0 outCtxt=0 ctxtDtor=0 flags=0
   US-ASCII     handler=0x5a1b054040
      in.func=0x5a1b2a3be4 in.legacy=0x5a1b2a3be4 out.func=0x5a1b2a3be4 out.legacy=0x5a1b2a3be4
      inCtxt=0 outCtxt=0 ctxtDtor=0 flags=0
   PROBE_RC=0
   ```
   ⇒ 两成员读出**同一个地址**（同址），`inputCtxt/outputCtxt` 均为 0，`flags` 非 0：这块存储填的是
   新式 `func`，且新式调用第一个实参就该是这个（可为 NULL 的）`vctxt`。
3. 按库实际填充的那一员写调用式（本包补丁 0001 的最终形态）：
   ```c
   if (NULL != handler->output.func)
     ret = handler->output.func (handler->outputCtxt, out, &out_size, (const unsigned char *) in, &temp, 0);
   ...
   if (NULL != handler->input.func)
     ret = handler->input.func (handler->inputCtxt, out, &out_size, (const unsigned char *) in, &temp, 0);
   ```
   `NULL` 守卫换成员写即可——同址 ⇒ 判空恒等价；决定生死的是**调用签名**，不是成员名。
   `ret` 与 `temp` 的判定口径在新 API 下与 legacy 一致（`inlen` 出参=已消费字节、
   `outlen` 出参=已产出字节、失败一律负值），故补丁只动调用式，未动 `_convert()` 后续逻辑。
4. **修完必须运行期复验**（本步不可省，见「验证」）。

## 验证

两臂探针（`~/tmp/uc2/z64-vcdimager/probe/`，`armA.c`/`armB.c` 只差一处调用式，同一
`xmlFindCharEncodingHandler("UTF-8")`、同一输入 `"abc"`）——本棒 2026-09-26 复跑读数：

```bash
H=$HOME/tmp/ch/home-主理-45-vcdimager
L=$H/p/libxme5a5c01c709a6/p                  # libxml2/2.15.3.1 制品
cd $HOME/tmp/uc2/z64-vcdimager/probe
LD_LIBRARY_PATH=$L/lib ./probe ; echo PROBE_RC=$?   # 实拍 PROBE_RC=0（读数见上一节）
LD_LIBRARY_PATH=$L/lib ./armA  ; echo ARM_A_RC=$?   # 实拍 Signal 11 (core dumped)、ARM_A_RC=139
LD_LIBRARY_PATH=$L/lib ./armB  ; echo ARM_B_RC=$?   # 实拍 out=abc、ARM_B_RC=0
```

- A 臂（`handler->output.legacyFunc(out, &out_size, in, &temp)`，即「让编译通过的第一版补丁」）：
  只打印出 `calling through the 4-arg legacyFunc type...` 就被信号打死，
  **ARM_A_RC=139**。
- B 臂（`handler->output.func(handler->outputCtxt, out, &out_size, in, &temp, 0)`，即最终形态）：
  `new-API arm: ret=3 out_size=3 temp=3 out=abc`，**ARM_B_RC=0**——3 字节输入被原样按 UTF-8 转出，
  结果正确。

包级证据（vcdimager/2.0.1，构建主机 B）：第 15 轮 `conan-verify` **Verdict: PASS**（G0/G1/G2/G3/G4
全过）；上游 `make check` 静态 8 项 = PASS 6 / XFAIL 1 / SKIP 1 / **FAIL 0**（`check_nrg.sh` 已不再
段错误，SKIP 的是需要物理 CD 的 `testvcd`）；消费者 `test_package` 17 项断言 / 17 通过 / 0 失败；
W3 本地 CI 模拟通过。打补丁后的编译读数（同一处四行只剩 deprecation 告警，不再是 error）：
`vcd_xml_common.c:245:26: warning: 'output' is deprecated`、`:246:22`、`:246:44 'outputCtxt'`、
`:250:26 'input'`、`:251:22`、`:251:43 'inputCtxt'`，末行 `6 warnings generated.`——
即 union 成员本身在 2.15 也被标 deprecated，但那是告警不是缺陷（本包未加 `-Wno-deprecated`）。

## 适用边界

- 适用：任何按 2.15 之前 API 写的 `xmlFindCharEncodingHandler` / `xmlGetCharEncodingHandler` 取回
  handler 再直调 `input`/`output` 槽位的 C/C++ 代码。
- **可推广的一般判据（本条真正的复用面）**：遇上游把回调槽改成 union（成员同址但签名不同）时，
  「编译通过」不代表修好——库内部可能只填其中一员，旧式成员调用会在运行期参数错位崩溃
  ⇒ 必须运行期复验。
- **成立窗口（把边界划到版本内，别只划到年代）**：正解所走的 `func` 成员与随它的方向上下文
  `outputCtxt` / `inputCtxt`，**在 libxml2 2.15.3 自身就带 `XML_DEPRECATED_MEMBER` 标注**
  （实测制品 `include/libxml2/libxml/encoding.h:204/208/209/210`）⇒ 打了补丁的编译会出 6 条
  `-Wdeprecated-declarations` 告警（一手位置：本轮 `archives/v/vcdimager/2.0.1/reports/w3-local-ci.log`
  内由 `vcd_xml_common.c:245/246/250/251` 触发的 6 条告警行（机器可读锚 `grep -nE "vcd_xml_common\.c:2[45]" reports/w3-local-ci.log`；本轮落在 512、521、530、539、548、557 行，紧随其后的 566 行为「6 warnings generated.」）。本包未加 `-Wno-deprecated`
  把它压掉。⇒ 本条机制的适用范围是「2.15 系列仍保留这些废弃成员的期间」；后续版本一旦整体移除，
  判据不变（union 槽位按新式 `func(<方向>Ctxt, ..., flush)` 调用 + 必须运行期复验），
  但要换的是成员名而不是调用式——照搬本条字面改写的包应先探目标版本还在不在这些成员。
- 不适用：只用 `xmlReadDoc` / `xmlParseFile` 等高层接口、不碰 `_xmlCharEncodingHandler` 结构体的包。
- 取证注意（构建主机 B 的坑）：`/tmp` 只读 ⇒ 临时落点一律 `$HOME/tmp/...`；复现 error 原文时用
  `-fsyntax-only`，别在别人的缓存树里落 `.o`/`.Po`。

## 已试过的失败方案

1. **只改成员名（`legacyFunc` 版补丁）**：编译过、apply 过，运行期 vcdxbuild 全灭
   （`Signal 11 (core dumped)`，上游 `check_nrg.sh` FAIL）。这条正是本条知识要拦的坑。
2. **把 DIFF/PATH 之类的 harness 问题当成本条根因**：第 7 轮 `check_nrg.sh` 的失败与
   `check_vcd11/20/svcd1` 的失败是**两族不同的根因**（前者是本条 SIGSEGV，后者是 OHOS
   `/usr/bin/diff` 为 toybox 软链），不要并成一条处置。
3. 高层接口替换（fallback 方案）本包**未采用**——`_convert()` 需要按 `handler->name` 判方向并做
   一次显式转换，改高层接口要动函数契约，超出「只改调用式」的最小修复面（PF5 口径）。

## 查重结论（四范围）

- `knowledge/graph/`：grep `legacyFunc` / `xmlCharEncodingHandler` / `xmlCharEncConvFunc` → **0 命中**。
- `knowledge/drafts/`：同关键词 → **0 命中**（本棒复核；`draft-review` 不扫该目录，故手工 grep）。
- `经验文档/B草稿库/`：`legacyFunc` / `xmlCharEncodingHandler` / `enc-handler` → **0 命中**。
- `经验文档/手册/07-技术速查.md`：同关键词 → **0 命中**（前任台账 N1 已计数，本棒独立复算一致）。

形状相近但**层次不同**、因此不算重复的条目（按文件名 + 行号引用，不写裸 E 号——本仓草稿里
E 号被大量复用）：

- `knowledge/drafts/DRAFT-tweeny-4.1.0-v4-api-consumer-migration.kv:10` 的 `error_signature`
  四条全是**编译期**符号/类型错（`no member named 'onStep'`、`static assertion failed`…），
  同文件 `:14` 的 `root_cause` 是「破坏性 API 升级 ⇒ 消费者改调用式迁移」——那条到编译期为止；
  本条独有的是「改成员名编得过之后，运行期才崩」这一层，且判据是探针而非头文件阅读。
- `knowledge/graph/E490.kv:8`（`Permission denied` / 执行位家族）与
  `knowledge/graph/E114.kv:5`（`config.status` mktemp 写拒绝）同属 autotools 适配面，
  但机制与本条无关（本条不涉及文件模式与临时目录）。

## 查重预审判决（`draft-review` 原文，未为过闸改措辞）

沙箱项目根 `~/tmp/uc2/z64-vcdimager/kbcheck`（`knowledge/drafts/` 只放本稿，`knowledge/graph`
软链主检出），于 worktree 内执行 `python3 scripts/ohc-run.py draft-review -p <沙箱>`，2026-09-26 实拍：

```
  草稿总数: 1  |  空壳(缺 signature/root_cause): 0
  预审分布: 疑似重复(merge-into) 0 | 灰区(review-similar) 0 | 疑似新知(create) 1
    DRAFT-vcdimager-2.0.1-libxml2-2-15-enc-handl   0.09
```

单份详情 `draft-review DRAFT-vcdimager-2.0.1-... -p <沙箱>`（以下整段为工具输出原样；
其中 `根因:` 三行是**工具自身按 80 字截断**候选条目 root_cause 后的产物，非本棒摘录）：

```
  质量预检: signature=✅  root_cause=✅  rec=✅
  相似正式条目 TOP3:
    E063  score=0.09  (sig=0.16 kw=0.0 cat=0.0)
        根因: 项目启用了 -Werror(或某些类别如 -Werror=implicit-function-declaration),
将所有编译器警告视为错误。musl/c
    E093  score=0.08  (sig=0.14 kw=0.0 cat=0.0)
        根因: getpass() 是 GNU 扩展函数（POSIX 已标记为废弃），
musl libc 不实现此函数。
软件源码中直接调用 getpass() 时，
mus
    E462  score=0.08  (sig=0.1 kw=0.04 cat=0.0)
        根因: SELinux/HMMAC blocks ptrace system-wide on HarmonyOS, so gdb/strace cannot attac

  📌 预审建议: create
     疑似新知——无高相似条目，可考虑人工审核后纳入
```

阈值口径（该工具 `_MERGE_TH=0.55` / `_REVIEW_TH=0.30`）：≥0.55 merge-into、0.30–0.55 灰区
review-similar、<0.30 create ⇒ 本稿最高分 **0.09，判 create**，未落灰区。
注意该工具的相似面只取 `knowledge/graph/index.tsv`、**不扫 `knowledge/drafts/`**，故上一节的
四范围手工 grep 才是 drafts 面的查重依据，两者不可互相代替。
