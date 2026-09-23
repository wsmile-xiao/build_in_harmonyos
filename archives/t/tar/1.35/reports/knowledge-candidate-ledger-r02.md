# Knowledge Candidate Ledger — tar 1.35（R02）

**路径初判**: B（知识库扩展）— 三类候选经本轮实测确认、四范围查重未命中/仅弱相关，可跨库复用
**task**: tar-1.35-r02-pc3-13-20260913T113300Z
**日期**: 2026-09-13

## 候选台账

### C1: OHOS/HMDFS 执行环境 uid 空间超出 ustar/v7 头字段 21-bit octal 容量（UIDRANGE）

- **真实错误（本轮实测复现）**: `tar: value 20001006 out of uid_t range 0..2097151`（testsuite 中 78 项直接命中；`--format=v7|ustar` 创建归档 exit 2，`--format=gnu|posix|默认` exit 0）。
- **根因**: 执行端用户 euid=20020101 / 文件属主 uid=20001006（HMDFS UID 映射）> ustar/v7 头字段容量 2097151（2^21-1）；GNU tar 上游对超出字段容量的 uid 在 v7/ustar 格式下拒绝写入（create.c `UID_TO_CHARS` 失败），属格式规范 + 环境 uid 空间共同作用。
- **恢复路径实测**: 低 uid（uid<=2097151）切换 5 项真实尝试全部失败（`os.setuid(1000|2)` → EPERM；su/setpriv/runuser/chpst/fakeroot MISSING；sudo 无 tty exit 1；/etc/passwd 低 uid 用户 shell=/bin/false）——见 logs/39-uidrange-recovery-attempt.log。
- **验证**: 默认/gnu/posix 格式归档往返在本环境实测 PASS（鸿蒙专项测试），仅 v7/ustar 用例受环境 uid 空间阻塞。
- **适用范围**: 一切在 HMDFS 高 uid 映射执行端上运行强制 v7/ustar 归档的 GNU tar/类似工具上游 testsuite 的适配任务。
- **查重结果（四范围）**: 正式（graph/E*.kv + doc/E*.md）**未命中**（E086 为 ucred 结构体补丁，弱相关不同主题）；图谱 index.tsv **未命中**（关键词 uid range/2097151/ustar uid/base-256 全 0 命中）；草稿（drafts/）**未命中**。七轴：exact_duplicate=否 / causal_duplicate=否 / trigger_overlap=否 / solution_overlap=否 / combination_novelty=是 / boundary_novelty=是 / test_migration_novelty=是。
- **关系**: similar_to=(无) / caused_by=OHOS HMDFS 用户 uid 空间映射 / prerequisite_of=(无) / conflicts_with=(无)。

### C2: HMDFS 无完整 POSIX xattr 语义（目录 listxattr 暴露 security.* 但 getxattr 返回 EINVAL）

- **真实错误（本轮实测复现）**: `tar: dir: Warning: Cannot fgetxattr: Invalid argument` + `getfattr: getxattr failed: Invalid argument`；目录 listxattr=[security.hmmac, security.selinux]，`getxattr security.hmmac` → `[Errno 22] Invalid argument`（9 项 xattr 用例全部命中）。
- **根因**: HMDFS 目录 listxattr 暴露 security.hmmac 等条目，但 getxattr 对其返回 EINVAL；文件级 user.* xattr 可用（os.setxattr 实测 OK），目录级语义与 POSIX 不一致。
- **恢复路径实测**: 设备可写挂载点全部为 HMFS/tmpfs(HMDFS 语义)，无 ext4/ext2/f2fs 挂载；候选点写探针 + 目录 xattr 语义实测见 logs/40-xattr-recovery-attempt.log。
- **验证**: tar --xattrs 目录归档在 HMDFS 上 fgetxattr EINVAL（exit 0 但 xattr 读取失败），getfattr -d 复现 EINVAL。
- **适用范围**: 依赖完整 POSIX xattr（尤其目录级）的上游 testsuite/程序在 HMDFS 执行端的适配任务。
- **查重结果（四范围）**: 正式/graph **未命中**（E192 robust mutex 完全不同主题；E046/E047 为 HMDFS chmod/权限位而非 xattr 语义——弱相关，覆盖度不足）；草稿 **未命中**。七轴：exact_duplicate=否 / causal_duplicate=否 / trigger_overlap=否 / solution_overlap=否 / combination_novelty=是 / boundary_novelty=是 / test_migration_novelty=是。
- **关系**: similar_to=E046/E047（同属 HMDFS 平台语义差异族，但主题不同：权限位 vs xattr）/ caused_by=HMDFS xattr 实现 / prerequisite_of=(无) / conflicts_with=(无)。

### C3: OHOS toybox touch 不支持纳秒时间戳（GNU coreutils touch 缺失）

- **真实错误（本轮实测复现）**: `touch: bad date ...9999999999`（test 155 time01 命中）；`/usr/bin/touch -d 1970-01-01T00:00:00.0000000001` → exit 1（秒精度 `-d ...:01` exit 0）。
- **根因**: 设备唯一 touch 为 toybox 0.8.12（/usr/bin/touch -> ../../bin/toybox），无 GNU coreutils touch 或等价纳秒精度实现。
- **恢复路径实测**: 全设备搜索无 GNU coreutils touch；PATH 前端无其他 touch；恢复不可行见 logs/41-touch-v7-recovery-attempt.log。
- **验证**: toybox touch 纳秒日期实测 exit 1；155 重跑仍 FAILED。
- **适用范围**: 上游测试用纳秒 touch 设置 mtime 的适配任务（tar/time01 类）。
- **查重结果（四范围）**: 正式/graph **未命中**（E010 为 toybox sed/expr 工具链行为——弱相关不同工具）；草稿 **未命中**。七轴：exact_duplicate=否 / causal_duplicate=否 / trigger_overlap=否 / solution_overlap=否 / combination_novelty=是 / boundary_novelty=是 / test_migration_novelty=是。
- **关系**: similar_to=E010（toybox 工具链族）/ caused_by=OHOS toybox 替代 GNU coreutils / prerequisite_of=(无) / conflicts_with=(无)。

## 路径决定

- C1/C2/C3 均本轮实测确认、可跨库复用（OHOS 平台行为差异）、四范围查重未命中或仅弱相关且存在新增差异 → **满足路径 B 条件**。
- 判定 **路径 B**：建立 3 个同 stem 成对草稿（.kv + .md）：
  - `knowledge/drafts/DRAFT-tar-1.35-ohos-uid-range-ustar.kv` + `.md`（C1）
  - `knowledge/drafts/DRAFT-tar-1.35-hmdfs-dir-xattr-einval.kv` + `.md`（C2）
  - `knowledge/drafts/DRAFT-tar-1.35-toybox-touch-nanosecond.kv` + `.md`（C3）
- 不直接写正式 E###；草稿与三方库归档（archives/t/tar/）进入同一 PR。
