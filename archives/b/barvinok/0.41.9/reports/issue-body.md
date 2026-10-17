【申请人账号】Awstme
【队伍名称】gogogo
【申请日期】2026/08/28
【库名称】知识库扩展（无新增库；知识来源软件为 barvinok 0.41.9，其路径 A 交付见 PR !6848）

## 关联 PR

PR：!7076
PR 链接：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/7076
分支信息：feat/kb-ohos-worker-dlopen-boundary → main
当前提交：e5860e7d3f
PR 状态：开放中

## 申请路径 B 的理由

本申请不是孤立 bug 修复或单个编译 patch，而是一条**平台加载器边界的诊断模式 + 一种可复制的配方组合方案**：

OHOS CI worker 对进程启动后新增映射的用户目录共享库（`dlopen()`、`LD_PRELOAD`）实施与签名无关的统一拒载——新自签文件与制品仓**发布签名件**同样被拒（#33869 三向探针矩阵实证），而同一批文件经 `DT_NEEDED` 在 exec 时加载完全正常（#33895 中 14/15 C 测试通过）。该边界对所有"上游测试含 ctypes/FFI/插件动态加载"的库是**通用必遇阻断**，且存在配方级正解：嵌入式 Python 启动器把被测库经 exec 路径注入进程全局符号域，上游测试零改动执行真实计算（不 skip、不 stub）。

推广价值：任何含 `ctypes.CDLL` / `cdll.LoadLibrary` / dlopen 类上游测试的软件（Python 绑定库、自动加载插件宿主、FFI 套件）在 CI 上的同类失败可直接套用 E2166 判据定位、E2167 模式换路；E2167 含 `prescan_pattern`，合入后 PreScanner 在选型阶段即可预警。

## 知识库查重与新增价值

新增 draft：knowledge/drafts/E2166-draft-7A4A.kv、knowledge/drafts/E2167-draft-7A4A.kv（各带配对 .md）
拟提升编号：E2166、E2167（最终编号由知识库主编确认）
条目主题：
- E2166 — OHOS CI worker 拒载一切用户目录 .so 的 dlopen/LD_PRELOAD（与签名无关），仅 exec-NEEDED 放行；含 musl 报错形态判据（绝对路径=顶层被拒 / `soname (needed by ...)`=依赖被拒 / `so=主程序`=CDLL(None) 空域）、诊断输出禁整体截断纪律、conan 缓存写红线与恢复命令
- E2167 — 上游 dlopen/ctypes 测试的嵌入式 Python 启动器配方模式（launcher NEEDED 直链自签被测库；`make check PYTHON=<launcher>` 必须 make 命令行参数形式；`Py_DecodeLocale` argv 编组；`python3-config --embed` 静态回退；符号链接别名实体化提示）

查重关键词：dlopen、Permission denied、LD_PRELOAD、needed by、PY_LOG_COMPILER、embedded python、ctypes、.codesign、CI worker、exec-time loading

覆盖判断：已有条目 E135 仅覆盖"本机未签名 .so 拒载→自签解决"，未覆盖 worker 侧更严边界（自签在该路径上无解，E135 方案照抄进 CI 配方会产生 13 轮无效重试）；E2164/E2165 覆盖任务私有副本重签与实体化（exec 路径前提），未覆盖 dlopen 禁制本身与测试路由方案；E077 仅约束签名操作顺序。本增量在于：①"双拒+唯一放行路径"的完整策略画像与取证判据；②与之配套的测试换路配方模式；③两条配套反模式红线（[:N] 截断多行诊断；objcopy/签名误写 `~/.conan2` 缓存伪造出"签名时效"假政策，真实事故与恢复法已记录）。

## 证据材料

| 项目 | 内容 |
|---|---|
| 原始失败 | CI #32474：`FAIL: isl_test_python.py`（14/15）；#33025 探针定位到 `LoadLibrary(.../libisl.so.23.5.0): Permission denied`；此后 13 轮取证受阻元凶为配方自身 `probe_output[:400]` 截断（非机器人截断）|
| 边界定案 | #33869（CI-006）三向探针：新自签 `.libs/libgmp.so.10`、发布签名 `p/gmpaa.../libgmp.so.10`、新自签 `libisl.so.23.5.0` 全部 `Permission denied`；#33895（CI-004）：`LD_PRELOAD` 被静默忽略，同轮 14 个 exec-NEEDED C 测试通过；#33918：env 前缀 `PYTHON=` 被 Makefile 赋值压制（launcher 未生效实锤）|
| 修复方案 | PR !6848 提交 `c7569dcbc`（NEEDED 链 dereference 复制+构建期逐个自签+结构化探针+test_package signed-libs 闭包）、`7a1c16925`（LD_PRELOAD 尝试，已被证据否决）、`d184422a9` + `b9c42101e`（嵌入式启动器 + make 命令行 `PYTHON` 参数覆盖），文件：`archives/b/barvinok/0.41.9/conanfile.py`、`test_package/conanfile.py`、`test_package/CMakeLists.txt`（配方级实现，非源码补丁，12 个上游补丁不变）|
| 构建验证 | HarmonyOS PC aarch64（HongMeng Kernel 1.12.0）+ Conan 2.29.1（os=OHOS profile），`conan create --build=missing`；worker 终裁 CI 构建 #33932（CI-003）|
| 上游测试 | 25/25 PASS（根级 10/10 + 内嵌 isl 15/15，含曾失败的 `isl_test_python.py`，经启动器执行真实 isl 计算）|
| 消费者验证 | test_package 2/2 PASS（CMake `test_barvinok` 1/1 + `test_iscc.sh` 1/1，OHOS 下 NEEDED 闭包 signed-libs 实体化+自签）|
| 审查证据 | W4 独立审计 verdict=pass（P0=0/P1=0）；AI review：首轮"✅ 未发现问题"，第二轮（#33932 后）同结论，检视线程已回复闭环（note 187085822）|
| 当前 CI | !6848 最新构建 #33932 校验通过（head b9c42101e，全部门禁绿）；本申请 !7076 CI **校验通过**（全部构建步骤 ✅，纯知识 PR 无包构建），AI 代码检视结论"✅ 未发现问题" |

## 申请分值

路径 B 贡献创新：10 分候选
理由：将一次 barvinok 适配中反复出现的 worker 加载器拒载，系统化为"边界画像 + 报错形态判据 + 取证纪律 + 可复制测试换路配方"两条配对知识；后续任何带 dlopen/ctypes 测试的库可跳过本任务付出的 4 轮 CI 试错成本（约 3 小时 worker 时间与一整条错误假设链）。E2167 的 prescan 派生规则使知识合入即转化为选型期自动预警能力。
测试框架/工具链验证作为路径 B 证明材料，不重复申报额外分值。最终以官方审核为准。

## 其他说明

- 路径 A（barvinok 0.41.9 本身）由 PR !6848 单独申报，本申请**只申报路径 B**，两者不重复计分素材：!6848 交付归档与配方，!7076 交付跨库知识条目。
- 路径合规说明：!7076 仅新增 `knowledge/drafts/` 四个草稿文件，未改动 `knowledge/graph/`、`knowledge/doc/`、`index.tsv`、`SUMMARY.md` 等框架/正式索引；拟提升编号 E2166/E2167 为前占位段（避免并行 PR 撞号），最终以主编 promote 结果为准。
- CI 特殊状态说明：!7076 为纯知识 PR，若 CI 机器人对"无 archives 变更"给出特殊结论，属预期，不构成失败原因。
- 已知限制：结论绑定 HongMeng Kernel 1.12.0 + CI 专用 HNP python 组合；平台代际升级后按 E2166 验证方法重测。
- 本知识库扩展与 !6848 存在交叉引用（notes.md 第 7 条含完整过程记录），如需在 E135 正式条目上回链"worker 边界见 E2166"，由主编在 promote 时决定，本 PR 未改正式条目。

## 需要官方确认的问题

1. 是否认可本 PR 按路径 B（贡献创新，10 分候选）评审
2. 是否认可该诊断模式 / 组合方案属于可跨库复用的适配知识
3. 是否认可修复 + 验证证据，并允许草稿在主编审核时确定最终编号
