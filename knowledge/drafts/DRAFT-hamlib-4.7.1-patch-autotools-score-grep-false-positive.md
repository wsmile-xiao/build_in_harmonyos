# draft-hamlib-4.7.1-patch-autotools-score-grep-false-positive

## 症状

`scripts/patch-autotools-ohos.pl <config.guess> <config.sub>` 输出 `Score: 5/5`、
`✅ Patching successful.`，但它的「验证」只是 grep：

```
config.guess: __OHOS__=1 HarmonyOS=1
config.sub:  ohos-linux=1 ohos*=0 linux-ohos=1
Score: 4/5        # 或 5/5，取决于 config.sub 原有内容
```

Score 通过 ≠ 需要的补丁。hamlib 4.7.1 官方 release 的 `config.sub`
**本来就支持 ohos**（OS 列表 `ohos*`、内核列表 `linux-ohos*-`），实测：

```bash
sh config.sub aarch64-unknown-linux-ohos   # -> aarch64-unknown-linux-ohos (rc=0)
```

脚本仍往里塞了一个 `ohos-linux)` 两段式简写分支（无用），适配者若不核验就会
把它当成必需补丁提交（本任务初版就误留成 `patches/0004`，后经实测删除）。

## 根因

1. 脚本的「验证」用 `grep` 判断字符串是否出现，而**正确的判据是执行**
   `sh config.sub <triplet>` / `sh config.guess` 是否返回期望三元组。
   `ohos*` 这类子串在别的代码路径（OS 列表）也会命中，导致假阳性。
2. 脚本无条件注入 `linux-uclibc*` 模式的 `linux-ohos*`（本版 config.sub 已有，
   报 `[skip] linux-ohos already present`）与 `ohos-linux` 简写（无条件下加），
   没有先判断该 config.sub 是否已原生支持。

## 建议修复

- 验证改为**执行式**：`sh config.sub aarch64-unknown-linux-ohos` 输出等于
  `aarch64-unknown-linux-ohos` 才算通过；`config.guess` 用受控 `uname` 桩
  （或至少检查 `*:HarmonyOS:*:*` 分支存在）。
- 打补丁前先「探测是否已支持」：已支持则不写文件、不报 Score，直接提示
  「该版本无需补丁」。
- 输出区分「注入的 change」与「原文件已有的能力」，避免把 no-op 计成成功。

## 验证

```bash
# hamlib 4.7.1 官方 release tarball（未打任何补丁）
tar xzf hamlib-4.7.1.tar.gz hamlib-4.7.1/build-aux/{config.guess,config.sub}
grep -c ohos hamlib-4.7.1/build-aux/config.sub        # 2 处（OS 列表 + 内核列表）
(cd hamlib-4.7.1/build-aux && sh config.sub aarch64-unknown-linux-ohos)  # rc=0
grep -c 'HarmonyOS\|ohos' hamlib-4.7.1/build-aux/config.guess            # 0 处 ← 真正需要补丁
```

结论：hamlib 4.7.1 只需修 `config.guess`；删掉 `config.sub` 补丁后
clean-verify（5 补丁）与 conan-verify G0–G4 全绿。

## 相关

- 触发实例：hamlib/4.7.1（2026-09-28）
- 相关知识：E007（HarmonyOS 三元组）
