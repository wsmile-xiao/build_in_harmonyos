# DRAFT-cdb-20251021-hmdfs-shebang-script-exec-refusal：hmdfs 用户分区拒绝 #! 脚本 exec（ELF 不受限）

> **Contributor**: gcw_6YxinkyD | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-08
> **Source event**: cdb 20251021 HarmonyOS PC 适配真机验证（PR #8907，设备 10.62.134.118:2222）
> 对应：knowledge/drafts/DRAFT-cdb-20251021-hmdfs-shebang-script-exec-refusal.kv

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。只进入 `knowledge/drafts/**`，
不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则；是否提升由知识库
维护者和赛事评审决定。

## 现象

真机（OHOS 6.0，设备 10.62.134.118）在用户可写路径 `/storage/Users/currentUser`
（hmdfs 挂载）构建 djbware 包时：

```text
make: ./compile: Permission denied
```

对照实验（同一目录）：

```sh
printf '#!/system/bin/sh\nexit 42\n' > t.sh && chmod 755 t.sh && ./t.sh
# → rc=126，stderr: Permission denied
# 同逻辑 C 程序经 /data/service/hnp/bin/clang 编译为 ELF 后执行 → rc=42 正常
```

chmod 777 无效；shebang 改为任何存在的解释器（/system/bin/sh、bash 绝对路径）无效。

## 根因

`/storage/Users/currentUser` 为 hmdfs 挂载并带 hmmac 安全标签（与 E212 中
dlopen 按路径标签受限同源的机制）。该标签路径上：

- `#!` 脚本 exec 按"文件类型 + 路径标签"一律拒绝（EACCES → shell rc=126），
  与 shebang 指向的解释器是否存在、文件权限位无关；
- 同目录 ELF 二进制 exec 正常。

djbware 的 `./compile`/`./load`/`./makelib` 全是 `#!/bin/sh` 脚本，make 直接
exec 即触发；上游 rts 测试套件经 PATH 调用的 `cdbmake-12`/`cdbmake-sv` 等
脚本工具同理。`/data/local/tmp` 可 exec 但 root-only，普通用户无替代路径。

## 修复（真实证据）

1. **构建期**：补丁 `0002-makefile-invoke-build-scripts-via-sh.patch` 把 Makefile
   中 68 处 `\t./compile|./load|./makelib` 调用改为 `\tsh ./xxx`（正则
   `^(\t)(\./(?:compile|load|makelib) )` → `\1sh \2`），对 Linux 行为完全等价。
   应用后 `make prog` 14 个二进制 + 5 个静态库全部产出。
2. **测试期 PATH 工具**：编译微型 ELF shim（`main` 中
   `execvp("sh", ["sh", <脚本绝对路径>, argv...])`），shim 目录放 PATH 首位——
   上游 `rts.tests` 字节级原样执行，实测 47/55（8 个失败均为错误注入型平台
   限制，与本条目无关）。

## 与已有知识的差异（查重关键）

- **DRAFT-gnustep-gui-0.31.1-shebang-bash-fix**：根因是 shebang 解释器路径
  不存在/受限 → 改写解释器路径即解决。本条目解释器路径有效仍被拒，
  gnustep 方案在本机型**完全无效**——区分判据：`./<script>; echo $?`，
  126 = 本条目（exec 拒绝），127/not found = 解释器路径问题（gnustep 条目）。
- **E212**：同为 hmmac 路径标签机制，但作用点是 `dlopen(.so)`；本条目作用点
  是 `execve(#! 脚本)`。两者互为佐证：hmmac 按文件类型 + 路径标签做执行类管控。
- **E112**：同真机的 `/tmp` 只读 → TMPDIR 注入，与本条目常一起出现但独立成立。

## 禁止做法

- chmod 755/777 当修复——权限位与限制无关；
- 改写 shebang 指向"可用解释器"——本机型限制与 shebang 内容无关；
- 把构建目录挪到 `/data/local/tmp`——root-only，普通用户不可写。

## 适用边界

- 仅真机用户分区（hmdfs 标签路径）；CI worker（x86 容器）不受影响；
- ELF 二进制不受限，无需签名即可 exec（与 E2xx 重签名类问题正交）。
