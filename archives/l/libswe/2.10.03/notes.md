# libswe 2.10.03 适配笔记

## 编译环境
- 构建系统: makefile (上游纯 Makefile, 无 configure/CMake)
- 编译日期: 2026-09-17 (首轮工作树), 真机预检 2026-09-19 (最新, 149 floor 四轮同指纹)
- 编译器: clang (Conan conf 注入, R33)
- 状态: built (test_package 7/7 通过; 上游 setest 12219 执行/149 失败 (2026-09-19 最新, 01=112/02=0/04=3/05=1/07=12/08=5/09=10/10=6), 豁免见 test_package/MANIFEST.yml)

## 编译步骤

用文字描述实际编译步骤: 复用系统 make, 仅构建可移植目标
`libswe.a [libswe.so] swetest swevents swemini`, 有意跳过 RHEL-only 的
`swetests` 目标 (写死 `-L/usr/lib/x86_64-redhat-linux6E/lib64/` + `-static`,
OHOS 上无法链接, 与测试无关)。setest harness 另行编译
(`setest` 单二进制目标, CFLAGS 去 `-g` 改 `-O0`, 见下表 #4)。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | setest harness 用 GCC 内嵌函数, OHOS clang 拒编 | setest.c/multivalues.c 手写内嵌函数 + testsuite.m4 生成的 generated_tests.c 均为 GCC-only 扩展 | patches/0001 (手写内嵌函数提升为文件静态函数) + patches/0002 (m4 模板改 divert, 按套件静态结构体 + 文件作用域函数); 库本体零改动 |
| 2 | `swetests` 目标 OHOS 上链接失败 | 上游 Makefile 写死 RHEL 路径 + 全静态 | 只构建可移植目标子集; 该目标是 swetest 的静态变体, 不含测试 |
| 3 | 上游 JPL 迭代无法运行 (538/12757) | 默认 JPL 文件 de431.eph 达 2.6GB, 发布包不含, 无法低成本补齐 | conanfile `_write_nojpl_expectations` 从 t.exp 派生 t_nojpl.exp: 仅删 iephe 含 JPL 位小节, section-id 按用例内连续重排 (reader 顺序 seek 不变量), 期望字节一致; 等价 ctest -E, 命令与计数如实上报 |
| 4 | 真机 exit 137 (OOM killer) | setest Makefile 默认 `-g` 无优化, m4 生成的 generated_tests.c 单编译单元峰值内存被 supervisor 杀掉 | setest 构建 CFLAGS 去 `-g` 改 `-O0` + 链接 `-s`, 单作业; 库构建同样去 `-g` |
| 5 | SWIEPH 迭代大面积 Moshier 回退 (首轮 1210 失败) | 发布包不含任何 .se1 数据文件 | build() 从官方镜像补数据: 行星 .se1 全日期覆盖 + 小行星 short+long + sat/sepm + seorbel.txt + sefstars.txt, 分级完整性下限 + 缺必需文件直接报基础设施错误 |
| 6 | 数据时代漂移 (1210→494) | master .se1 系 DE441 重建 (2026-04), t.exp 系 2022 时代 | 行星 .se1 主取 DE441 前最后提交 b51a0833 不可变快照; sefstars/seorbel 主取最早快照 eecb996a (2023-09-20) |
| 7 | 残留 515 失败迭代: 前两轮“换镜像源”路线已 plateau (494→515), 禁止重复 | 见下节“第三轮取证结论”: 剩余失败驱动为上游标签内期望过期 (2.10.02a 生成的 t.exp vs 2.10.03 代码行为) + 已绝版的旧 sat 文件覆盖范围, 非镜像可解 | 不再调镜像; 改为: (a) 配方加 era-tier 日志 (哪个文件走了 pin/master/mirror 回退逐文件记录, 非 pin 命中告警), 让下轮日志可判定锚定是否生效; (b) MANIFEST 豁免按上游官方 diff 实证重写, 纠正前轮错误假设 (sat lower-limit 与版本有关); (c) 本笔记沉淀证据链 |
| 8 | 残留 349 失败迭代 (2026-09-19 真机: 01=132/02=5/04=7/05=5/07=23/08=32/09=10/10=135): 上一轮 era-pin+豁免重写有效但未过门 (515→349, suite_07 87→23 证明数据侧仍有收益), 但继续调镜像已无收益 | 见下节“第三轮取证结论”与“第五轮证伪”: suite_04 配对失衡假设被 t.exp 实数证伪 (期望已含双 NONUT 小节), 其余为代码行为漂移/绝版数据, 镜像路线 plateau | 改走夹具一致性路线 (conanfile 新增 `_fix_suite04_fixture`, 已于第五轮证伪并整体删除, 见 #10): 预期 suite_04 7→0 未达成 (最新 382 轮 suite_04 仍为 7), 其余保持全量执行+诚实上报+豁免, 不子集化造绿 |
| 9 | 真机在星历抓取阶段掉线 (2026-09-19 预检, 同一 readonly_tmp 指纹第 3 次: 日志头部 preflight.sh[306] 报 /tmp 只读, 但构建随后正常推进到库编译与星历抓取, 证明该噪声非致命; 真正的中断是抓取中 SSH 会话被远端关闭, 最后可见行为是一次行星文件 off-pin 回退) | 前四轮已把配方内 TMPDIR 加固做尽 (source/generate/build/test_package 全 pin + prefix 导出 + build-local 回退); 同一机制重复加码不可能修复 harness 自身 mktemp 与会话掉线 | 换主机级熔断路线 (与前四轮不同实现): (a) 先对官方 v2.10.03 做 /tmp 硬编码审计 (顶层 Makefile、setest/Makefile、reader.c、checkpoints.c、setest.c 测试路径均无 mktemp/tmpnam//tmp; 测试态 prepare_cmd 为 NULL 走 fopen、无 popen; -p 内联走 fmemopen), 确认无上游硬编码可改, 不删测试不改口径; (b) conanfile 抓取循环加主机级熔断——同一主机连续 2 文件失败即跳过该主机剩余请求 (tier 顺序/下限/era-tier 日志/全局熔断不变, 无可用 URL 时仍全量尝试, 健康网络行为一致), 把病态主机串行 stall 从约 59 文件量级降为 2 个; 可证伪 (熔断未触发而全量完成即 stall 假设错) |
| 10 | 第五轮证伪 (2026-09-19, 382 失败轮): `_fix_suite04_fixture` 未起效 (suite_04 仍为 7, 且 suite_01 +3/suite_10 +30 波动指向数据 off-pin 回退, 非夹具) | 对 v2.10.03 归档实数: t.exp suite_04 期望小节按用例为 {1:8, 2:2, 3:1, 4:1} 共 12——TESTCASE 2 已含 iephe:2 与 iephe:66 双小节、TESTCASE 3 期望即 NONUT daya (19.527903…), 与 t.fix 双值展开 1:1 一致; 头部 2.10.02a 只是版本号未更新, 内容已同步; 且 suite_04 TESTCASE 3 代码根本不读 iephe (suite_04_ayanamsa.c 无 GET_I(iephe)), 加行无展开效应。归一化反而制造 1-run-vs-2-section 失衡并删除上游新增 NONUT 断言, 属输入改写 | 本轮整体删除 `_fix_suite04_fixture` (调用+方法), 上游输入零改动、精度保持 1e-8; suite_04 豁免改写为 TESTCASE 1 值漂移 (ayanamsa 定长表/NONUT 守卫); 可证伪 (若 suite_04 从 7 变为其他数则另有配对问题) |
| 11 | 第六轮 (2026-09-19, 552 失败轮: 01=205/02=8/04=11/05=5/07=87/08=32/09=10/10=194): 较 382 轮 suite_07 23→87 恰为无小行星数据基线数 (与第三轮 87 一致), suite_01 +70、suite_10 +29、suite_04 +4 (ayanamsa_ex SWIEPH 的 rc 亦依赖 .se1) 均为同轮数据抖动侧证; 行星必需文件未触发缺失熔断, 故为 scryr.io 单主机瞬时超时 + 行星 off-pin 回退, 非代码漂移 | 小行星/sat 文件仅 scryr.io 单主机、无 git 回退, 原单次 8s 尝试不可恢复; 前五轮分别调过镜像/era-pin/夹具/主机熔断, 均未覆盖“单主机瞬时抖动的重试” | 与前五轮不同路线: sat/小行星抓取加单主机重试 (3 次 x 15s, 死主机熔断与连续熔断仍限总 stall, 健康网络首试即中、行为一致) + 缺失小行星文件逐个具名告警 (suite_01/07 归属), 套件口径与期望字节均不变; MANIFEST suite_07 豁免补记 87→23→87 波动证据; 可证伪 (若下轮 suite_07 仍为 87 且无缺失告警, 则为 MPC 漂移而非抖动) |
| 12 | 第七轮 (2026-09-19, 516 失败轮: 01=193/02=8/04=7/05=5/07=87/08=32/09=10/10=174): 上一轮重试加固证伪——suite_07 仍为 87 无数据基线 (552→516 未回 23), suite_01 193 仍高于 132 on-pin 基线 +61、suite_10 174 高于 135 基线 +39, serr 直方图仍为 sepm lower-limit 越界, top diffs 47.7/47.0/28.0 为 Moshier 回退量级。重试不能修复持续性单主机不可用, warn-and-continue 更把断网伪装成测试失败 | 前六轮分别假设“换镜像/era-pin/夹具/主机熔断/瞬时抖动重试”可解; 516 证据否决瞬时抖动假设 (3x15s 后仍 87, 且 off-pin 行星字节同时漂移) | 与前六轮不同路线——严格门禁 (determinism over availability): (a) 行星必需文件仅接受 era-pin 字节, off-pin 直接删除并试下一 tier, 无 era-pin 命中即按缺失报基础设施错误 (不再警告带病运行); (b) 小行星 short+long 由 best-effort 提升为必需, 缺失并入 missing_required 报基础设施错误 (调度重试, 不再以 87 伪装成测试失败)。健康网络首试即中、行为一致; 此后只有 on-pin 完整运行 (预期回 349 基线) 或具名 infra, 可证伪 (infra 带名=断网; 仍 516 且零 off-pin 拒绝=漂移假设错) |

| 13 | 第八轮 (本轮, 2026-09-19 infra 轮: pin 侧 SSL/读超时致连续失败 abort, 而 master/mirror 同轮可达却被严格门禁拒绝): 第七轮严格门禁与第五轮死主机熔断存在病态交互, pin 侧 2 次瞬时失败即把 raw 标死, 此后 pin 永不可达、mirror 永被拒绝; 再调逐文件超时/重试属原路线重复 | 换整包路线: 行星 39 个 .se1 改走单 commit tarball 整包预取 (github.com, source() 每轮已证可达), 1 次 TLS 握手替代约 39 次串行握手, 原子 era 一致; 成功则逐文件循环命中 size-check 跳过, 失败则原样回退逐文件逻辑; sat/小行星与 sefstars/seorbel 保持原逐文件逻辑与严格门禁不变, 套件口径与期望字节不变 |

| 14 | 第九轮 (2026-09-19, 149 失败轮: 01=112/02=0/04=3/05=1/07=12/08=5/09=10/10=6, 执行 12219/通过 12070): 第八轮整包 era-pin 生效, 行星 39 个 .se1 真正 on-pin (此前 349/516 轮仍有 off-pin 漂移): suite_10 135→6、suite_08 32→5、suite_02 8→0、suite_07 87→12 (优于 23 on-pin 基线, 小行星必需化+重试+整包共同作用)、suite_01 193→112。suite_09 保持 10 (calc_dip 数据无关, 侧证数据修复正交)。残留 149 驱动为代码行为漂移 (Delta-T/Vreijs/calc_dip/食阈值/split_deg/ayanamsa, 第三轮官方 diff 已核验) + DE441 重建 sat 覆盖 (lower-limit 2378496.5/2378861.5 vs 期望 2378491.5/2396759.5) + 小行星 MPC 根数漂移, 非数据缺失 (serr 直方图仅余少量 sepm 越界, top diffs 47.7/47.0/28.0 非 Moshier 回退量级, 无 not-found 回退)。12219 全绿仍不可达 (重生成期望=循环论证, 禁止) | 与前八轮不同路线: 不再调数据/镜像/夹具/容忍度 (数据侧已收敛), 改走确定性加固+诚实上报: (a) 整包 tarball 覆盖 seorbel.txt (三 pin 同字节 6063B, 与 sefstars 时代差异正交, 去掉一次 flaky 逐文件 strict-pin 抓取, 健康路径行为一致); (b) 本笔记+MANIFEST 豁免头同步到 149 分布, 不改套件口径、不删断言、不调精度; 可证伪 (若下轮 suite_02 回升或出现 not-found serr, 则为数据回退而非漂移 floor) |

| 17 | 第十二轮 (本轮, 2026-09-19, 149 失败轮第五次同指纹: 01=112/02=0/04=3/05=1/07=12/08=5/09=10/10=6, 按用例 1.1=93/1.3=15/1.5=4/4.1=3/5.4=1/7.3=12/8.3=1/8.7=3/8.9=1/9.3=8/9.4=1/9.5=1/10.8=6, 与 ledger 完全一致) | 上一方案 (第十/十一轮: 失败遥测+drift ledger 日志) 虽诚实上报但未解阻塞——日志 ledger-clean 无法机读复核, 且 MANIFEST 豁免仍残留旧分布描述 (suite_04 称残留 7、suite_10 称旧 156、头部残留 516 轮分析碎片), notes 通过率沿用 349 基线的 11870/12219=97.1% (正确应为 12070/12219=98.8%), 评审无法判定“同 floor” | 与前十一轮不同路线: 数据/镜像/夹具/容忍度/CFLAGS 零改动, 改走豁免文档同步+证据硬化——(a) MANIFEST 头部改写为 149 按用例台账并删 516 碎片, suite_04 改残留 3 (TESTCASE 4.1)、suite_10 旧虚高改 135~194、suite_07 补按用例 7.3=12; (b) notes 通过率改 12070/12219=98.8%; (c) 配方 _parse_setest_evidence 把 ledger 判定 (failed_by_case/drift_ledger/verdict) 写入 upstream_test_evidence.json 机读证据 (口径与 marker 不变, 仍诚实上报 failed); 可证伪 (下轮 evidence 缺新字段=本改动未生效; 新用例失败=NEW-REGRESSION; suite_02 回升/not-found serr=数据回退) |
| 16 | 第十一轮 (2026-09-19, 149 失败轮第四次同指纹) | 换路径: 不再调数据/镜像/夹具/容忍度/遥测计数, 改走漂移台账强制归因 (与前十轮均不同实现): conanfile _parse_setest_evidence 新增 ledger 校验——149 floor 的 13 个失败用例 (1.1/1.3/1.5/4.1/5.4/7.3/8.3/8.7/8.9/9.3/9.4/9.5/10.8) 为已知漂移台账, 全量执行与标记口径不变 (仍诚实上报 failed=149), 台账内失败记 ledger-clean, 台账外新失败记 NEW-REGRESSION loud warning 以区分“同 floor”与“新回归”。另核验: 库 CFLAGS -O2 与上游顶层 Makefile 第二行 CFLAGS (-O2) 一致, setest -O0 与上游 setest Makefile (无 -O 即 -O0) 一致, 故 FP 优化等级非漂移驱动, CFLAGS 本轮零改动; reader.c/testdata.c 通读确认 TEST-mode 输入与期望同节衍生、顺序消费, t_nojpl 派生配对成立 (执行数 12219 == 保留数)。可证伪 (下轮 ledger-clean=同 floor; NEW-REGRESSION 带名=新回归; suite_02 回升或 not-found serr 重现=数据回退) |
| 15 | 第十轮 (2026-09-19, 149 失败轮第三次同指纹) | 换路径: 不调镜像/数据/夹具/容差, 改走配方自证+失败分类可观测。(a) 对 v2.10.03 归档做配对审计: TEST-mode 只读 <collection>.exp, 输入与期望同节衍生, 排除配对纳错假设; (b) 新增脱钩护栏 (执行迭代数不等于派生保留数则报 infra); (c) 新增失败种类遥测 (WRONG_VALUE 按字段 top-8 + EXP_VALUE_MISSING + 按用例汇总); 可证伪 (若下轮 EXP_VALUE_MISSING>0 则为数据回退而非漂移) |

| 18 | 第十三轮 (本轮, 2026-09-19, 149 floor 第六次同指纹预期: 01=112/02=0/04=3/05=1/07=12/08=5/09=10/10=6, 按用例 1.1=93/1.3=15/1.5=4/4.1=3/5.4=1/7.3=12/8.3=1/8.7=3/8.9=1/9.3=8/9.4=1/9.5=1/10.8=6, ledger-clean 已连续 5 轮): 前十二轮已把数据/镜像/夹具/容差/CFLAGS/遥测/台账/文档路线做尽, 149 为上游标签内期望过期 + 绝版数据 floor, 非调用失误 | 换证伪硬化路线 (与前十二轮均不同实现): 配方加四处机器可检护栏——派生期望 t_nojpl.exp 非空下限 (5MB, 防空夹具假绿)、setest 二进制非空下限 (50KB, 防桩)、日志 Testmode 头 + 用例数==60 断言 (防静默跳过/作用域缩小); 健康路径 (12MB/真二进制/60 用例) 行为一致, 口径/容差/数据零改动, 仍诚实上报 failed; 可证伪 (护栏触发=infra, 未触发且仍 149=同 floor) |

| 19 | 第十四轮 (本轮, 2026-09-20, 同指纹第 2 次修复: 16:00 轮仍 149, 前轮四处证伪护栏静默通过无 infra, 分布/直方图/top-diffs 字节级一致, 确认同 floor; 新信息仅 HMBS_PLATFORM_CAPABILITIES (hardlink 0/chmod 0, 配方仅探针写无依赖无需适配) | 换归因诊断路线 (与前轮门禁式护栏不同, 无新通过/失败条件): _parse 的 EXP_VALUE_MISSING 计数附加迭代 id 归属 (# setest -s id 就近原则, 去重截断 10 个), 下轮日志直接出 EXP_VALUE_MISSINGx1 in [id] (猜测为 split_deg 新增 dsecfr 字段期望缺失, 待日志验证); 口径/数据/容差零改动, 仍诚实上报 failed; 可证伪 (id 落在 5.4=分支漂移证据; 落在其他=派生丢节需查) |

## 第三轮取证结论 (2026-09-19, 与前两轮不同路线: 先证伪, 不换镜像)

- t.exp 头部 `swisseph-version: 2.10.02a` (2022-08-27, 用户 alois 生成), 标签内未重生成; 且 t.fix 在 2.10.03 被改过 (suite_04 加 NONUT iephe、收紧精度 1e-5→1e-8) 而 t.exp 未同步, 标签内自相矛盾。
- 取回上游官方 v2.10.02...v2.10.03 全量 diff (17MB) 核验, 确认覆盖测试路径的行为变更: swephlib.c Delta-T 表更新 (2020-2028)、swecl.c 月亮星等 Vreijs 分段模型、calc_dip 273.16→273.15、lun_eclipse 阈值 2000000→2100000、split_deg dsecfr、ayanamsa 定长表 + NONUT 守卫; sweasp.c 仅排版变更 (suite_07 的 87 失败非代码漂移, 应为小行星密切根数更新)。
- sat/sepm 旧覆盖已绝版: t.exp 期望 lower-limit 2378491.5/2396759.5, DE441 重建文件实际 2378496.5/2378861.5 (真机 serr 直方图), 现存数据无解。
- 行星 pin 经核验真实有效: 41 个必需文件在 b51a0833 全部存在, 且抽查字节数与 master 不同 (如 seplm36 500226 vs 508266)。
- JPL 派生数经本地复算确认: 12757 小节中 538 个 iephe=1, 保留 12219, section-id 在 t.exp 内本就按用例连续, 无纯 JPL 用例。
- 结论: 在此标签下 12219 全绿不可达 (需重生成期望=循环论证, 禁止); 保持全量执行 + 诚实上报 + 精确豁免。套件失败分布: 01=191, 02=8, 03=0, 04=7, 05=5, 06=0, 07=87, 08=32, 09=10, 10=175。

## 第五轮证伪 (2026-09-19, 382 失败轮: 上一方案为何无效 + 不同路线)

- 上一方案 (第四轮: `_fix_suite04_fixture` 把 t.fix 2 处 NONUT eval 归一为单 SWIEPH、精度 1e-8 改回 1e-5) 无效: 真机 suite_04 仍为 7 (349→382 轮未动), 且 suite_01 +3、suite_10 +30 的波动指向数据 off-pin 回退而非夹具。对 v2.10.03 归档实数证伪: t.exp suite_04 期望小节按用例为 {1:8, 2:2, 3:1, 4:1} 共 12——TESTCASE 2 已含 iephe:2 与 iephe:66 双小节、TESTCASE 3 期望即 NONUT daya, 与 t.fix 双值展开 1:1 一致 (头部 2.10.02a 只是版本号未更新); 且 TESTCASE 3 代码根本不读 iephe, 加行无展开效应。归一化反而制造失衡并删除上游新增 NONUT 断言。
- 因此本轮整体删除该归一化 (调用+方法), 上游输入零改动、精度保持 1e-8; suite_04 豁免改写为 TESTCASE 1 值漂移 (ayanamsa 定长表/NONUT 守卫)。其余失败保持全量执行 + 诚实上报 + 豁免。

## 第四轮路线声明 (2026-09-19, 第 4 策略周期: 已被第五轮证伪, 保留备查)

- 上一方案 (第三轮: era-pin 加固 + 豁免实证重写) 部分有效: 真机从 515 收敛到 349 (suite_07 87→23、suite_01 191→132、suite_10 175→135), 证明行星 pin 生效; 但门禁仍为 failed, 因为剩余 349 里只有数据侧可解的部分被解掉, 剩下的驱动与镜像无关: (a) suite_04 的 7 个是 t.fix 改而 t.exp 未改的配对失衡 (eval 多值展开 vs 单期望小节, 任何数据都解不掉); (b) 其余 342 为编译进库的 Delta-T 表/月亮星等分段模型/calc_dip 常数/食阈值/split_deg/ayanamsa 守卫等代码行为漂移 + DE441 重建 sat 覆盖 (lower-limit 2378496.5/2378861.5 vs 期望 2378491.5/2396759.5), 数据文件无解。
- 因此禁止继续沿用镜像调优: 本轮对数据/镜像侧零改动, 改走夹具一致性路线——conanfile 新增 `_fix_suite04_fixture` (输入对齐已发布 oracle, 库零改动): 2 处 NONUT eval→单 SWIEPH、精度 1e-8→1e-5, 守卫 (2/1 计数) 失配则拒跑。预期下一轮 suite_04 7→0、总量 349→342, 可证伪 (若 suite_04 未归零则本假设错)。
- 其余 342 保持全量执行 + 诚实上报 + 豁免 (不做子集化造绿, 不重生成全量期望)。

## 源码修改

- patches/0001-clang-no-gcc-nested-functions.patch: harness 内嵌函数文件作用域化 (portability, 仅测试架)。
- patches/0002-m4-generated-setest-clang-compat.patch: m4 生成代码文件作用域化 (portability, 仅测试架)。
- 库源码 (swe*.c/h) 零修改。
- 上游测试输入 (setest/t.fix/t.exp) 零修改 (第五轮已删除 `_fix_suite04_fixture` 归一化)。

## 依赖版本

- 构建依赖: 无 (产出库仅链接 libc/libm/libdl)。
- 测试架构建依赖 (tool_requires, 不进 requires): m4/1.4.19, openssl/3.5.6.1 (setest.c 一处 SHA1 信息打印, 静态链接 libcrypto.a, 无运行时依赖)。

## 验证结果

```bash
# 真机预检 (HarmonyOS aarch64, 与官方 CI 同源), 2026-09-19 (最新)
./setest t_nojpl  # Total 10/60/12219 ... 384 failures in 149 iterations (01=112/02=0/04=3/05=1/07=12/08=5/09=10/10=6)
# 上轮: Total 10/60/12219 ... 1442 failures in 516 iterations
./test_swe        # 7/7 passed (6 断言 + 1 端到端出生盘用例)
# 上轮: Total 10/60/12219 ... 1532 failures in 552 iterations
# 上上轮: Total 10/60/12219 ... 829 failures in 382 iterations
# 上上上轮: Total 10/60/12219 ... 787 failures in 349 iterations (on-pin 基线)
# 上一轮 (2026-09-18): Total 10/60/12219 ... 1434 failures in 515 iterations
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libswe.a (默认) / lib/libswe.so (shared=True) | 静态/动态库 |
| include/swephexp.h, sweodef.h, swedll.h | 公开头文件 |
| licenses/LICENSE | 双许可文本 (AGPL-3.0 / Swiss Ephemeris 商业许可, 闭源商用需另购) |

## 注意事项

- 本库为 AGPL-3.0-only 双许可, 商业闭源使用需向 Astrodienst 购买 Professional Edition。
- `swetest/swemini/swevents` 仅构建验证, 不打包 (纯库包定位, 无 commands.json)。
- 上游测试通过率以真机预检日志为准 (本轮 12070/12219=98.8%, 2026-09-19; 上轮 11704/12219=95.8%), 不得改成 100%; 明细见 test_package/MANIFEST.yml upstream_test_exemptions。
- 申请人 (GitCode 用户名): sheepss, 队伍名称: 来都来了。
