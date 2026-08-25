# DRAFT-ohos-gawk-gensub-global-capture-bug：OHOS gawk 5.4.0 gensub 全局替换捕获组 bug→IS_GAWK=0 兼容路径

> Contributor: blesh-0.4.0-git20250806.8060b7a 适配 | Status: Draft | Updated: 2026-08-24
> Source: archives/b/blesh/0.4.0-git20250806.8060b7a（make check 实测 + 本地修复验证）

## 现象

ble.sh 上游测试 `ble/util/writearray --nlfix` 用例失败（1 个 fail）。用例依赖
gawk 的 `gensub` 全局替换（g 标志）+ 捕获组引用做多行文本变换：

```bash
# 期望：对 "a1b2c3" 全局替换数字为 "X\1"（保留捕获组）
# gawk 5.4.0（OHOS 自带）：a1b2c3 → aX1bXcX（第二、三个捕获组为空）
# 预期行为：                        aX1bX2cX3
```

OHOS 自带 gawk 5.4.0 在 `gensub(re, "\\1X", "g", str)` 场景下，从第二个匹配
起捕获组内容为空——非 ble.sh 自身 bug，也非沙箱/权限限制，是 gawk 5.4.0
特定版本行为差异。

## 主从根因

- **主根因**：gawk 5.4.0 的 gensub 全局替换（g 标志）带捕获组引用时，第二个
  匹配起捕获组为空（工具链版本行为差异，归轴 1 平台能力边界）。
- 无附加从因：非编译问题、非权限问题、非路径问题。

## 与现有知识的关系

- knowledge/graph 现有条目（E032 gawk 编译兼容 / E061 gnulib / E074 make
  FIFO jobserver）均不覆盖 gawk 运行时 gensub 行为差异——本主题无覆盖。
- 跨库可复用：任何依赖 gawk `gensub(/re/, repl, "g", str)` 且替换串含
  `\\1` 捕获组引用的脚本/工具（文本变换、模板生成、日志处理）在 OHOS
  gawk 5.4.0 下都会命中此行为差异。

## 方案

ble.sh 检测到 AWKTYPE=gawk 时会走 gensub 快路径（`IS_GAWK = AWKTYPE == "gawk"`），
OHOS 上强制走 gsub 兼容路径（`IS_GAWK = 0`），gsub 的全局替换 + 捕获组行为
正确：

```bash
# 适配（不改上游测试用例，仅配方内做环境适配）：
s = s.replace('      IS_GAWK = AWKTYPE == "gawk";',
              '      IS_GAWK = 0;')
```

gsub 兼容路径输出正确（本地实测：`a1b2c3` → `aX1bX2cX3`，测试全绿）。

## 验证证据

- 本地 OHOS 环境 make check：修复前 writearray --nlfix 1 个 fail；强制
  IS_GAWK=0 后 7830/7830 全过（100%）。
- CI 日志（ci_blesh6186b.log）：JC pass、7830/7830、L0/L1/L4/L5 pass、
  Success 1 100%。

## 适用场景

- 纯 Bash/POSIX 工具链库在 OHOS 上的上游测试，测试依赖 gawk gensub
  全局替换 + 捕获组。
- 任何把 gawk 当文本变换引擎的配方（ble.sh、awk 批处理脚本）。

## 禁止做法

- 不要盲目修改上游测试用例断言去"适配"（环境适配应改配方/运行路径，
  不改测试）。
- 不要假设 gawk 5.4.0 的 gensub 行为与 Linux 发行版 gawk 一致——OHOS
  自带版本存在全局替换捕获组差异，需实测确认。
