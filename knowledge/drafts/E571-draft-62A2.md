# E571 — 科学计算库跨 libc/架构验证：从算法精度推导数值容差，禁止统一宽松 epsilon

> 状态: DRAFT（草稿，未正式索引；promote 决策权在人工主编）

## 错误特征

跨 libc / 架构（OHOS musl aarch64 vs glibc amd64 宿主）验证科学计算库（天文/大地测量类）时出现两类相反的假象：

1. **假阳性**：test_package 用统一的宽松 epsilon（如 `1e-3` 或 `1e-6` 一刀切），把 0.1 deg 量级的算法级错误全部吸收成 PASS，消费端冒烟测试保持绿色而底层 API 实际算错。
2. **假阴性**：上游自带测试（fixtures）中精度受限的天文例题被过紧容差误报为 FAIL —— 上游期望值可能冻结于旧版算法，"失败"不代表当前实现错误。

典型日志形态：`ok ... calc=... diff=... eps=...`（宽松容差吸收错误）、`[FAILED] ... Expected ... got ...`（陈旧期望值）、`assert(fabs(x) < 1e-6)`（一刀切断言）。

## 触发条件

- 构建系统: 任意（案例为 Autotools；Conan 2 test_package 消费门禁）
- 阶段: testing（上游测试执行与解析）+ test_package（消费者数值断言）
- 库类型: 数值/科学计算库（案例 libnova/0.16：儒略日、角度换算、恒星时、章动、VSOP87 行星、简化 ELP 月球、升落中天）

## 根因分析

单一 epsilon 无法同时覆盖算法精度相差 9 个量级的断言面：

| 算法类别 | 固有精度 | 依据 |
|---|---|---|
| 精确单位换算（hms/dms→deg） | ~1e-12 deg | 双精度舍入界 |
| 儒略日换算 | ~1e-9 day | 小整数精确算术 |
| 恒星时（打印值） | 1e-7 h | Meeus 例题打印粒度 |
| IAU-1980 章动级数 | ~1e-5 deg | 级数截断精度 |
| VSOP87 行星理论 | ~3e-4 deg（1″） | 截断版本精度 |
| 简化 ELP 月球理论 | ~1e-2 deg | 截断理论精度 |
| 升落/中天（RST） | 1e-3 day | 迭代收敛于分钟粒度断言 |

三个叠加因素：

1. 容差未按"算法固有精度"分级 —— 1e-3 一刀切在换算类断言上宽 9 个量级（掩盖错误），在月球类断言上又过紧（误报）。
2. 上游期望值可能陈旧 —— 但陈旧性必须逐项举证：第二套工具链构建（如 OHOS SDK clang/musl sysroot 原生构建）与交叉构建输出逐位一致只能证明失败平台无关，**不构成期望值错误的证明**。可用证据仅为：上游 master 提交历史中对该期望的实际修正（如 libnova 7b60adc，2016-09-12），权威文献打印值（Meeus《Astronomical Algorithms》），或历元正确的独立归算（libnova Pollux fixture：库值与 Meeus 22.2 平交角归算逐位一致，冻结期望才是离群值）。
3. 跨平台 libm 差异（musl vs glibc）仅 1-2 ULP，远小于算法容差 —— 不应把容差放宽到 libm 差异量级来"兜底"。

## 解决方案

### 推荐方案（derive-tolerance-from-algorithm-precision）

为每个被测 API 按其算法精度独立推导容差，并在测试源码注释中写明依据（见上表）。期望值来源分级：

1. 权威文献打印值（Meeus《Astronomical Algorithms》例题）—— 首选；
2. 上游 fixture 中已在本平台 PASSED 的向量；
3. 库自身输出 —— 仅当 (1)(2) 不可得时使用，必须注明并用独立归算交叉验证。

### 禁止做法

- ❌ 无依据的 `1e-6`/`1e-3` 一刀切 epsilon（假阳性掩盖真实回归）
- ❌ 门禁中放行已知失败（`failed > N` 阈值、静默 skip `FAILED` 行）—— 等于放弃整条回归轴；期望值修正必须走有来源披露的补丁，无法证明的失败必须如实保留并上报
- ❌ 默认"上游期望 = 真理"或"第二套工具链输出一致 = 期望陈旧" —— 必须逐项查期望值来源（上游提交历史、Meeus 打印值、独立归算），无证据即如实计失败

## 验证

```bash
# 容差分级是否落地（每个 EPS/TOL 都应有算法依据注释）
grep -nE "EPS|TOL" archives/l/libnova/0.16/test_package/test.c
# OHOS 目标完整门禁
conan create archives/l/libnova/0.16 -pr ci/conan/profiles/ohos-aarch64
```

实证：libnova/0.16 在 OHOS PC aarch64（musl, clang）上 —— test_package 39 项按算法分档容差检查在 static/shared 双产物全部通过；lntest 期望值修正仅限有上游提交、Meeus 权威值或独立归算逐项证明者（补丁中披露来源），无依据项如实计为失败，不以第二套工具链与交叉构建输出一致作为期望陈旧的证明。

## 关联条目

- 相似: E401（MLton 回归 golden 平台 oracle 变体 —— 同为"期望值 vs 平台数值行为"，彼为 1ULP 舍入差，此为算法精度分级）
- 相关: E540（can_run 误判致测试静默跳过 —— fail-closed 的对偶问题）
