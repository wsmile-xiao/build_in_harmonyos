# DRAFT-shmux-1.0.3-config-guess-pre2018-echo-idiom-fallback

## 一句话
老版（≤2016-10）config.guess 的分支以 `echo <triplet>` + `exit` 结尾、文件内**没有** GUESS 变量；
把 2018+ 习语的 `GUESS=${MACHINE}-…` 补丁块（zile 2.6.4 补丁 0001 同款）移植到老文件时，
分支会被命中并赋值、但 `;;` 后执行流直接落进文件尾的 `cat >&2` fallback ⇒ 仍报
"unable to guess" / configure "cannot guess build type"。补丁块必须按目标文件的输出习语自适应。

## 稳定症状（本次实证，shmux 1.0.3）
- `grep HarmonyOS config.guess` 有命中（补丁"看起来在"）；
- `sh -x config.guess` 可见 `+ GUESS=aarch64-unknown-linux-ohos` 赋值执行；
- 紧接 `+ >&2` / `+ <<EOF` 的 fallback dump，stdout 为空、rc=1；
- configure 侧：`configure: error: cannot guess build type; you must specify one`。

## 根因
GNU config 在 2018-01 前后重构了 config.guess 输出协议：老版各分支 `echo` 后立即 `exit`，
新版改为 `GUESS=` 赋值 + 文件尾统一 `echo "$GUESS"`。OHOS/HarmonyOS 识别块都是社区后补，
补丁常以新版文件为底稿反向移植——赋值式分支在老文件上没有"出口"，落空进 fallback。
因补丁确实在文件里，极易误诊为"补丁未应用"或"uname 未识别"而空转重试。

## 最小复现与验证
```sh
# 复现（2016 版 config.guess + GUESS= 块）
sh -x config.guess 2>&1 | grep -E "GUESS=|unable"   # 可见赋值 + fallback
# 修复后（老习语：分支尾 echo + exit）
sh config.guess        # → aarch64-unknown-linux-ohos，rc=0
sh config.sub aarch64-linux-ohos   # → aarch64-unknown-linux-ohos（config.sub 双点同步补）
```
对照证据：shmux 1.0.3 `reports/conan-create.log`（修复前）与 `_patch_config_ohos` 习语自适应实现
（修复后）；本地产物 `~/tmp/uc2/DS-32/`。

## 推荐方案（配方侧，CI 安全）
build() 内 Python 读改写，自包含、不依赖 OHC_SKILL_ROOT、不产生 patches/*.patch（规避 PF5 对
`__OHOS__` 宏的拦截）：
1. 插入前判习语：`grep 'echo "$GUESS"'` 命中＝2018+（用 GUESS= 块）；未命中＝≤2016（echo+exit 块）；
2. config.sub 同步加 `linux-ohos*`（KERNEL-OS 拆分）与 `-linux-ohos*`（OS 校验列表）；
3. 改写后断言锚点存在，锚点缺失即抛错（防静默半补丁）；
4. 铁律：改写 shell 框架文件后**必须直接运行并断言 stdout**，不能只验"补丁存在"。

## 边界
- 2018+ config.guess：GUESS= 块是正确习语，本条不适用（反例即 zile 2.6.4 自身，2024 快照）；
- 文件压根没补（grep 无命中）属 E007 常规形态，不在本条范围。

## 查重与申报
- similar_to: **E007**（patch-autotools-script）——同族但 E007 未覆盖①输出习语按年代分野
  ②CI 安全交付形态（无 perl 脚本依赖、无补丁文件）。依 AGENTS §6.2 hit 条件 2
  （既有条目未写的另一条解法与适用面）申报 **create**。
- 载体 PR：shmux 1.0.3 交付 PR（随 PR 原子提交）。
