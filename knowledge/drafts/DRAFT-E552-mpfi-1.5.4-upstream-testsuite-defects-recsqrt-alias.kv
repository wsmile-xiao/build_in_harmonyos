# ═══ Draft knowledge entry — mpfi 1.5.4 上游测试套件三类自伤缺陷(texp10 缺 dat/tdiv_ext 类型错配/rec_sqrt 数据错)与 rec_sqrt 别名 bug ═══
# Timestamp: 2026-09-09
# Software: mpfi 1.5.4(官方 tarball d20ba56a8d57d0816f028be8b18a4aa909a068efcb9a260e69577939e4199752)
# Gate: conan create build() 内 autotools.make(target="check")
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-E552
title: mpfi 1.5.4 make check 三测试失败:上游测试框架未完成(IIII 双输出)、tarball 漏发 exp10.dat、rec_sqrt.dat 十六进制指数记法笔误与 inexact flag 错;另含 mpfi_rec_sqrt(a,b) a==b 别名真实 bug
trigger_tool: make check / mpfi testsuite
phase: test
error_signature: Unable to open ./exp10.dat|Unable to open ./rec_sqrt.dat|FAIL: tdiv_ext.*Segmentation fault|FAIL: trec_sqrt|Failed line 9. op = \[@NaN@,-0\]
severity: 3
category: upstream|testsuite|numerical|library
match_keywords: mpfi,tdiv_ext,trec_sqrt,texp10,rec_sqrt.dat,div_ext.dat,make check,check_data
keywords: mpfi, 1.5.4, testsuite, type_iiii, IIII_fun, mpfi_div_ext, mpfi_rec_sqrt,
  exp10.dat, rec_sqrt.dat, 别名, aliasing, p-1 vs @-1, 十六进制指数, inexact flag,
  向外舍入, RNDU, RNDD, 区间, interval, Gentoo fix-tests.patch
approach: mpfi 1.5.4 make check 若 texp10/tdiv_ext/trec_sqrt 失败而其余通过,先分辨三类根因:
  (1) texp10 报 Unable to open ./exp10.dat → tarball 未随源分发该文件(EXTRA_DIST 亦未列),
  删去 texp10.c 的 check_data 调用保留 check_random(512 精度全程真跑);
  (2) tdiv_ext 段错误 → mpfi-tests.h 正确的 IIII 双输出 typedef(2 输出+2 输入)被注释,
  激活的是 1 输出+3 输入错配版本;恢复正确 typedef 并重写 type_iiii.c 的
  read_line_iiii/check_line_iiii 为双输出语义(res1/res2 各读期望、f_IIII(got1,got2,op1,op2)、
  got2/expected2 用独立 mpfi_t 而非复用数据槽位,第二输出 same_value(got2,expected2)
  独立断言,失败信息打印 expected2;禁止 got2 与自身或被函数覆盖的槽位比较),
  check_random 因 random_iiii 未完成(4 参调用)注释;
  (3) trec_sqrt 失败行逐条分辨:数据行与 mpfr_rec_sqrt(-0)=+Inf 实测矛盾者删、
  别名复用行在修完 src/rec_sqrt.c 别名 bug 后保留、十六进制指数笔误行(p-1 应为 p-4,
  差 2^3=8 倍)修值、inexact flag 位错行修 flag(端点舍入方向 1=左/2=右/3=双)。
  mpfi_rec_sqrt 别名 bug 修法:实现内先 mpfr_init2 临时变量存 b->left/b->right 再写 a,
  端点读改写顺序不再自毁输入。
root_cause: 上游 1.5.4 测试子系统三处独立缺陷+库一处真实 bug:
  A) type_iiii.c 双输出测试读取器从未完成,mpfi-tests.h 只留被注释的正确 typedef;
  B) tests/Makefile.am EXTRA_DIST 漏列 exp10.dat,tarball 无该文件;
  C) rec_sqrt.dat 由上游工具生成时把十六进制指数 @-1(16^-1)误写为 p-1(2^-1),
  值差 8 倍;部分行 inexact flag 与端点舍入方向不符;NaN 端点行为与实现
  (MPFI_NAN_P 整区间置 NaN 传播策略)分歧;
  D) src/rec_sqrt.c mpfi_rec_sqrt(a,b) 在 a==b 时第一条 mpfr_rec_sqrt 先写 a->left
  (与 b->left 同内存)再被第二条读取,输入端点自毁(经典读改写别名缺陷;实测探针:
  x=[0.25,4],step1 后 b->left 已变 0.5,step2 得错误上界 1.414 而非 2;Gentoo
  mpfi-1.5.4-fix-tests.patch 以删数据行回避,本修复以修实现根除,保留更多真实数学断言。
affected_scope: 所有平台构建 mpfi 1.5.4 并真跑 make check 的场景(glibc/musl 均命中,
  非 OHOS 特有);别名 bug 影响所有调用 mpfi_rec_sqrt(x,x) 的下游用户(区间端点错误结果)
verification_cmd: grep -c "^/\*typedef int (\*IIII_fun)" tests/mpfi-tests.h  # ≥1 即 typedef 仍被注释;srcdir=<abs> ./tdiv_ext; echo $?  # 139=segfault 未修
rec_priority: 1
rec_approach: patch-testsuite-plus-fix-recsqrt-alias
rec_description: 以配方补丁同时修测试框架(恢复 IIII 双输出 typedef、重写 type_iiii.c
  读取/断言函数、texp10 删缺失 dat 的 check_data、trec_sqrt 换 mpfi_fun_init_II 接
  mpfi_rec_sqrt、mpfr 参照函数传 NULL)与 src/rec_sqrt.c 别名 bug(临时变量先存输入端点),
  rec_sqrt.dat 仅删与 mpfr 实测语义矛盾/别名冲突行,修记法笔误与 inexact flag;
  修复后 159/159 全 PASS
rec_command: (配方补丁 patches/mpfi-1.5.4-fix-tests-and-recsqrt-alias.patch)
rec_auto_fix: false
rec_impl: conandata.yml patches 注册,apply_conandata_patches 自动应用
fallback_priority: 2
fallback_approach: gentoo-style-delete-failing-dat
fallback_description: Gentoo 官方补丁删 rec_sqrt.dat 19 行、div_ext.dat 45 行并注释
  check_random;测试保留量少(牺牲区间包含性/舍入断言),且不修别名 bug(下游 x,x 调用仍错)
fallback_command: (见 https://hina.lysator.liu.se/gentoo-portage/sci-libs/mpfi/files/mpfi-1.5.4-fix-tests.patch)
fallback_auto_fix: false
fallback_impl: 不采用(违背保留舍入/包含性测试最大化的任务目标)
principles: 上游测试失败先分辨"测试框架自伤/数据文件错/库真实 bug"三类;
  区间库的 oracle 是"高精度真值被区间包含",单一浮点比较会漏判向外舍入缺陷;
  别名(a==b)路径的测试行是库 bug 的免费检测器,删行即掩盖
caused_by: 上游 1.5.4 发布仓促:测试子系统未完成即打包+生成工具记法 bug+实现别名缺陷
causes: make check FAIL tdiv_ext(段错误)/texp10(缺数据)/trec_sqrt(数据错+别名);
  下游 mpfi_rec_sqrt(x,x) 区间端点错误
similar_to: E551(同为 mpfi 构建路径但根因不同:E551 是 profile CONFIG_SHELL 布局,
  本条是上游测试/实现缺陷,平台无关)
conflicts_with:
prerequisite_of:
doc_file: knowledge/drafts/DRAFT-E552-mpfi-1.5.4-upstream-testsuite-defects-recsqrt-alias.md
last_updated: 2026-09-09
source_event: mpfi 1.5.4 OHOS 适配 conan create make check 三测试失败,逐一定位根因:
  texp10 缺 dat(删 check_data 后 PASS)、tdiv_ext 段错误(恢复 typedef 仍崩→重写
  type_iiii.c 读取器后 PASS)、trec_sqrt(先删矛盾行→别名行仍败→修实现别名 bug→
  记法行修 p-1→p-4→inexact flag 修 1→3 后 PASS);159/159 全绿;对照实验
  mpfr_rec_sqrt(±0,RNDD/RNDU)=+Inf、0xb.5p-1(5.6568)≠0xb.5@-1(0.7071)完成正反验证
authors: AtomCode (glm-5.3)
source_pr: (本 PR)
source_commit:
metrics_success_count: 0
metrics_fail_count: 0
metrics_confidence: 0.95
metrics_last_used: 2026-09-09
