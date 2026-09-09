# E543 — HMDFS 上 umask 077 创建的 0700 属主目录连属主都不可写

## 错误特征
configure/config.status/config.guess 执行中报 `cannot create temp file ... Permission denied` 或
`mktemp: failed to create file ... Permission denied`，随后 config.status 报
`error: could not make confXXXXXX`。观察目录权限为 `drwx-----`（0700，属主即当前进程），
但属主进程无法在其中创建文件。

## 触发条件
- 构建系统: autotools（任何内含 `umask 077` + mktemp 的生成脚本：configure、config.status、config.guess）
- 阶段: configuration（configure 首跑 / config.status 重跑 / config.guess 探测）
- 文件系统: HMDFS（鸿蒙分布式文件系统）
- 平台: HarmonyOS PC (aarch64)

## 根因分析
HMDFS 的 UID 映射机制：目录属主 UID 被映射为文件系统侧账号（如 20001006），而进程实际 UID 不同
（如 20020083），0700 权限目录中 "user" 权限位对实际进程无效——**连属主都不可写**。
复现实验 3/3 全部命中：
1. `umask 077; d=$(mktemp -d); touch $d/f` → `Permission denied`
2. `chmod 0777 $d` 返回成功，但 `touch $d/f2` 依然 `Permission denied`（chmod 在 HMDFS 上不生效，E046 同源）
3. `umask 022; d2=$(mktemp -d); touch $d2/f` → 成功

pmix 5.0.11 实测命中 5 处：config.guess ×3（umask 077）+ configure 内嵌 config.status 模板 ×2。

## 解决方案

### 推荐方案
全局替换 `umask 077` → `umask 022`：
```bash
sed -i 's/umask 077/umask 022/g' configure config/config.guess config/config.sub
```
固化进 conandata.yml 补丁（per-file diff），umask 022 创建 0755 目录属主可写，单用户构建场景安全。

### 回退方案
固定工作目录替代 mktemp：`mkdir -p tmp_work` + 替换 mktemp 调用（见 E011 极端方案）。

### 禁止做法
- ❌ 试图 `chmod 777` 恢复已创建 0700 目录的可写性——HMDFS 上 chmod 不生效，白费排障时间
- ❌ 用 `--build=/--host=` 交叉参数绕过（E011 forbid 同理）

## 验证
```bash
umask 077 && d=$(mktemp -d) && touch $d/probe; echo "exit=$?"   # → Permission denied
umask 022 && d2=$(mktemp -d) && touch $d2/probe; echo "exit=$?" # → 0
```

## 关联条目
- 相关: E011（umask 077 现象与 sed 修法原始条目）、E046（chmod 在 HMDFS/SELinux 上不生效）
