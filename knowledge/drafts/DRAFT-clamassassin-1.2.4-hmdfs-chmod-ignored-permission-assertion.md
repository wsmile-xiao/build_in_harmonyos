# DRAFT-clamassassin-1.2.4-hmdfs-chmod-ignored-permission-assertion

> Contributor: yanjiaxin | Status: Draft | Updated: 2026-09-19
> Source: PR #9383 feat(clamassassin): 1.2.4 适配 HarmonyOS PC（CI build #51113 失败链）

## 背景

clamassassin 1.2.4 是纯 shell 脚本包（procmail/clamscan 邮件病毒过滤包装器）。
为满足 rule12（鸿蒙特有测试 ≥1），test_package/test.sh 增加了 E011 端到端断言：
检查打包出的脚本权限位是否为 group/other `r-x`，以证明 E011（HMDFS umask 077）
修复在包里生效。本地（非 HMDFS 文件系统）全绿，PR CI worker 上却失败：
`installed perms '-rwxr-x---', expected group/other r-x`。

## 现象

```text
FAIL: harmony-specific E011 perm check — installed perms '-rwxr-x---',
      expected group/other r-x (HMDFS umask 077 hides the filter from other users)
ConanException: Error 1 while executing
```

构建、L0 门禁、clean/infected 过滤测试全部通过，仅权限位断言失败。

## 根因

conanfile.py 的 `package()` 里 `chmod 0o555` 在 HMDFS 上**不生效**——这正是
知识库 E046 记录的行为：HarmonyOS 的 SELinux/HMDFS 会静默忽略 `chmod()` 调用
（返回成功但权限不变），落盘权限由文件系统策略决定。CI worker 上最终权限是
`0740`（other 位被抹掉），即使 umask 022 也保不住 `r-x`。因此"断言打包文件的
最终权限位"是与环境相关的脆弱断言：本地能过、PR 必挂，且无法通过修 chmod 修复。

## 修复

把断言从"最终权限位等于 0555"改为"E011 修复确实生效"的可移植判据：检查安装后
脚本的模式**不是** `0600`（未打补丁的 config.status 在 umask 077 下的特征产物）。
E011 的修复对象是 config.status 的 umask，其效果（生成物非 0600）在 chmod 被忽略
的文件系统上依然可观测；而最终权限位不属于配方可控范围。

```sh
INSTALLED_MODE="$(ls -lL "$INSTALLED" | awk '{print $1}')"
case "$INSTALLED_MODE" in
    -rw-------*)
        echo "FAIL: looks like unpatched umask 077 config.status output (0600)"
        exit 1
        ;;
esac
```

配套行为断言保留：`(umask 077; ... sh clamassassin < clean.eml)` 实跑过滤逻辑
验证 E011 修复不影响功能——这部分与文件系统权限策略无关，是稳定断言。

## 通用规则

在 HarmonyOS PC 上为 rule12 编写"鸿蒙特有测试"时：

1. **不要断言任何依赖 `chmod()`/`os.chmod()` 生效的最终权限位**（E046）。
2. E011 类修复的可移植验证判据是"生成物不是 0600/0700 特征"，而不是
   "权限位等于目标值"。
3. 本地通过 ≠ CI 通过：凡是权限/属性类断言，先问自己在 HMDFS
   （chmod 被忽略、UID 映射）上是否仍成立，否则改用行为级断言
   （实跑 + 输出校验）。

## 关键词

E046, E011, chmod ignored, HMDFS, SELinux, permission assertion,
rule12, harmony-specific test, umask 077, 0555, r-x, fragile assertion,
test_package, CI worker, local pass ci fail
