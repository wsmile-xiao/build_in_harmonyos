# DRAFT-ohos-hmdfs-owner-check-fails：OHOS HMDFS 目录 owner 强制 20001006:file_manager，[[ -O dir ]] 必然失败→[[ -w dir ]] 可写性检查

> Contributor: blesh-0.4.0-git20250806.8060b7a 适配 | Status: Draft | Updated: 2026-08-24
> Source: archives/b/blesh/0.4.0-git20250806.8060b7a（make check 实测 + 本地验证）

## 现象

ble.sh 初始化用 bash 的 `[[ -O $dir ]]` 判断目录 owner 是否为当前用户
（缓存目录 `_ble_base`、运行时目录 `$XDG_RUNTIME_DIR`、home 目录等），
OHOS 上全部走失败分支（目录创建逻辑异常、初始化路径不正确）。

原因：OHOS 的 `$HOME` 等目录挂载 HMDFS（HarmonyOS Distributed File
System），目录 owner 被强制为 `20001006:file_manager`，与进程实际 euid
（应用沙箱用户）不同——bash 的 `-O` 测试按 st_uid == geteuid() 判断，
HMDFS 上必然返回假。

## 主从根因

- **主根因**：HMDFS 强制目录 owner 为 20001006:file_manager，`[[ -O dir ]]`
  必然失败（平台权限模型差异，归轴 1 平台能力边界）。
- **附加 note（非主根因）**：`$XDG_RUNTIME_DIR` 等运行时目录在 OHOS 上
  可能不可写或不存在——切换为可写性检查后需确保目录确实可写（mkdir -p
  成功 + `[[ -w dir ]]`），不可只改检查不验证实际可写性。

## 与现有知识的关系

- 现有 DRAFT-hmdfs-script-exec-interpreter（HMDFS 禁止直接执行脚本）覆盖
  HMDFS 的"执行"限制，不覆盖"owner 归属"语义——机制不同。
- 现有 E074（make -j FIFO jobserver）不涉及 owner 检查——本主题无覆盖。
- 跨库可复用：任何用 bash `[[ -O ]]`/`test -O` 判断目录归属的脚本/库
  （缓存目录初始化、运行时目录管理、用户目录探测）在 OHOS 都会命中。

## 方案

把 owner 归属检查改为可写性检查（环境适配，不改上游测试断言）：

```bash
# 适配（配方内生成 out/ble.sh 时做文本替换，不改上游测试用例）：
s = s.replace('if ! (umask 077; ble/bin/mkdir -p "$dir" && [[ -O $dir ]]); then',
              'if ! (umask 077; ble/bin/mkdir -p "$dir" && [[ -w $dir ]]); then')
s = s.replace('elif [[ ! -O $dir ]]; then',
              'elif [[ ! -w $dir ]]; then')
# …… 其余 [[ -O ... ]] 出现处同理（XDG_RUNTIME_DIR / _ble_base / home 等）
```

目录初始化前提从"目录归我"放宽为"目录可写"——mkdir -p 成功且可写即满足
初始化需求（OHOS 上 HMDFS 目录归属不可变更，可写性才是真实约束）。

## 验证证据

- 本地 OHOS 环境 make check：替换后初始化路径正常，7830/7830 全过（100%）。
- CI 日志（ci_blesh6186b.log）：JC pass、7830/7830、L0/L1/L4/L5 pass、
  Success 1 100%。

## 适用场景

- 纯 Bash 脚本库/工具在 OHOS 上做目录归属判断（`[[ -O ]]`/`test -O`）。
- 任何依赖"目录归当前用户"语义的初始化逻辑在 HMDFS 上的适配。

## 禁止做法

- 不要尝试 chown 目录去迎合 `[[ -O ]]`——HMDFS 强制 owner 不可变更，
  会直接失败。
- 不要删掉目录检查只留 mkdir（无检查会掩盖不可写/不可创建的失败）——
  应保留可写性校验。
