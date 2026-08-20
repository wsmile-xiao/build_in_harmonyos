# E332 — 上游 golden 由 glibc 生成，OHOS musl 正确舍入导致 real 回归 ±1ULP

## 错误特征

MLton `make check` 的 real 回归报 diff，典型日志如下：

```
real: difference with -type-check true
expected: 1.570796251 (0x3fc90fda)
actual:   1.570796371 (0x3fc90fdb)
real.ok: FAIL
```

C 探针与最小 SML（Basis `Real32.Math.atan2` 与 FFI `atan2f`）逐位一致，证明无包装/类型提升/格式化参与；差异 100% 来自上游默认 oracle 生成平台的 libm 舍入特性。

## 触发条件

- 在 OHOS（musl 正确舍入）上运行 MLton `make check` 的 real 回归；
- 上游 golden 由 amd64-linux（glibc）平台生成；
- 输入为 `Real32.atan2`/`atan2f` 的 x<0 有限输入（±1ULP 边界）；
- 未放置 `{arch}-{os}` 平台 oracle 变体时触发。

## 根因分析

MLton 回归框架 `bin/regression` 的 oracle 选择逻辑默认回退到通用 `real.ok`（等价于 `real.amd64-linux.ok`），该 golden 由上游在 amd64-linux（glibc）上生成：对 `Real32.atan2`/`atan2f` x<0 有限输入记录 `0x3fc90fda`（低 1 ULP 舍入）。OHOS 由 clang + musl libm 对相同输入返回正确舍入 `0x3fc90fdb`，与上游自带的 `real.x86-linux.ok` / `real.amd64-darwin.ok` 一致。两者 bit 级差恰好 1 ULP（expected 1.570796251 vs actual 1.570796371），`make check` 的 real 回归因此报 "real: difference"。

属平台精度机制差异，非 MLton 缺陷、非格式化缺陷。

## 解决方案

### 推荐方案

新增 `regression/real.{arch}-{os}.ok` 平台 oracle 变体（OHOS 为 `real.arm64-ohos.ok`，25884 行，行数与 `real.ok` 一致，值取自 OHOS 实际输出且与上游 x86-linux/darwin 变体语义一致），并在 conandata.yml 注册该补丁。`bin/regression` 的 oracle 选择循环依次探测 `$OBJPTR_REP/a$ALIGN/$TARGET_OS/$TARGET_ARCH/$TARGET_ARCH-$TARGET_OS`，`real.{arch}-{os}.ok` 命中最后一项、优先级最高，其它平台不受影响。

```bash
# 新增 regression/real.arm64-ohos.ok（diff --git a/regression/real.arm64-ohos.ok，new file）
# 并在 conandata.yml 注册该补丁
bin/regression -test-reg real
# rc=0 且无 "real: difference"，完整 CI real 差异计数=0
diff regression/real.arm64-ohos.ok regression/real.ok
# 确认差异仅限 atan2f x<0 相关行的 ±1ULP
```

### 回退方案

若 `{arch}-{os}` 变体需从零生成，可先以上游自带且与 OHOS 输出 bit 级一致的 `real.x86-linux.ok` 为语义参照交叉校验 OHOS 实际输出，再以 OHOS 输出生成变体，确保无遗漏平台行。

### 禁止做法 ❌

- 禁止 `patch regression/real.ok` / `sed` 修改通用 `real.ok`、禁止放宽容差、禁止跳过 real 测试——通用 `real.ok` 是上游 amd64-linux/glibc 生成的 golden，修改它或放宽容差会污染所有平台、掩盖真实平台差异；跳过 real 测试则彻底放弃该回归轴，atan2f x<0 等边界输入在 OHOS 上永久失去回归保护。
- 禁止伪造 PASS、吞掉失败、把 "real: difference" 改成 "skipped"——把真实 difference 伪造成 PASS/skipped 违反测试真实性原则，掩盖平台 oracle 缺陷。

## 验证

```bash
# C 探针：atan2f(FLT_MAX, ±x/±0) 返回 0x3fc90fdb 且 errno=0、round=FE_TONEAREST
# 最小 SML 验证 Basis 与 FFI bits 逐位一致
# 放置变体后：
bin/regression -test-reg real
grep "real: difference"
```

`bin/regression -test-reg real` rc=0 且无 "real: difference"，完整 CI real 差异计数=0。

## 关联条目

- 原则：P013
- 状态：draft
- 正式文档：doc/E332.md
- 相似条目：无（similar_to: []）
- 事件源：MLton 20241230 Round 13 real_difference_count=1（real: difference with -type-check true，期望 0x3fc90fda vs 实际 0x3fc90fdb，1ULP）；Round 14 新增 regression/real.arm64-ohos.ok + conandata.yml 注册后 real 差异清零；Round 17/18 完整 CI real 差异=0

---
*draft/E332-draft-MLTN.md · knowledge graph draft · MLTN*
