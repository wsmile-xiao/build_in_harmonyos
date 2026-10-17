# draft-cln-1.3.7-mktemp-0700-hmdfs

## 症状

cln 1.3.7 的 configure/config.status 报：

```
config.status: error: could not setup config files machinery
./config.status[1056]: can't create ./confHJe0QZ/subs1.awk: Permission denied
```

## 根因

cln 的 configure（autoconf 2.71 生成）创建临时目录用：

```sh
tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`
```

GNU mktemp -d **恒以 0700 权限创建目录，不经 umask**。HMDFS setgid 父目录
（属主 uid 20001006）下，SSH 登录 uid（20020084）对 0700 目录写文件被拒
（E011 家族 uid 错位语义）——config.status 无法写入 subs1.awk/config.h。

**为什么 E011 处方不够**：E011/a52dec/classads 的场景是 `(umask 077 && mkdir ...)`，
mkdir 尊重 umask，放宽为 022 即得 0755 可写。cln 是 mktemp -d，umask 无效——
放宽后目录仍是 0700（cln 实证：仅放宽 umask 的 r3/r4 依旧 machinery 失败）。

## 修复（cln/1.3.7 实证）

补丁放弃 mktemp，改用 shell 唯一名 + umask 000 创建（权限在创建时确定）：

```sh
tmp=./conf$$-$RANDOM
(umask 000 && mkdir "$tmp")
test -d "$tmp"
```

**失败方案存证**（两次 CI 实证）：
1. 仅 umask 放宽（mktemp -d 仍恒 0700）→ machinery 失败；
2. mktemp -d 后补 chmod 0777 → 设备（创建者==写入者）通过，但 CI worker 上
   chmod 被 HMDFS/SELinux 无视（E046），config.status 仍 Permission denied；
3. mkdir -m 0777 直接替换 mktemp → mkdir 无 stdout，命令替换后 tmp 恒空，
   autoconf 主分支死代码（AI 检视实证指出后废弃）。

最终方案用 $$-$RANDOM 唯一名 + umask 000 创建 0777 目录，设备与 CI 语义一致。

## 适用范围

- 所有 configure 临时目录经 mktemp -d 创建的 autotools 包（autoconf 2.68+ 常见）；
- 与 CONFIG_SHELL/getcwd（DRAFT-6487-classads-*）、TMPDIR 型问题可叠加出现，
  需逐项 grep configure 分辨。

## 反例/边界

- `(umask 077 && mkdir ...)` 型走 E011 umask 处方即可，无需本条；
- 非 HMDFS setgid 环境（如原生 Linux）0700 目录属主可写，无此问题。

## 触发实例

cln/1.3.7（2026-09-12，CI worker 两次失败方案实证后定型）。
