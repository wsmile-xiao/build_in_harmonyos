# DRAFT-liblockfile-1.17.1-link-oexcl-lockfile-creation - HMDFS 上 link() 原子锁创建失败改用 O_EXCL 回退

> **Contributor**: pc1-31 | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-05
> **Source event**: liblockfile 1.17.1 HarmonyOS PC adaptation（feat/liblockfile-1.17.1）

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。
本草稿与 E079（HMDFS 硬链接限制，shell 层 cp 替换）互补：E079 覆盖 `ln`、
make install、git clone 等命令层硬链接；本条目覆盖 **C 源码内 link(2) 作为
原子锁创建原语** 的场景与 O_EXCL 回退方案。

## 现象

在 OHOS 真机（$HOME 挂载 HMDFS）上运行 liblockfile 的上游测试：

- `dotlockfile -l testlock.lock` 静默失败，退出码 4（`L_MAXTRYS`）；
- `make test`（run-tests.sh）失败：第一个 `dotlockfile -l -r 1 testlock.lock`
  即返回非零；
- 手动验证：`ln t1 locktest.lock` 报 `Operation not permitted`；
  `open(lockfile, O_WRONLY|O_CREAT|O_EXCL, 0644)` 成功。

## 根因

liblockfile 的 `lockfile_create()` 用两段式原子锁算法：先以 `O_EXCL` 创建
临时锁文件并写入 PID，再 `link(tmplock, lockfile)` 把临时文件硬链接为目标
锁文件。`link()` 成功且 inode 一致即视为拿到锁（原子性来自 link 要么
成功要么 EEXIST 的语义）。HMDFS 分布式文件系统不支持硬链接（跨设备 inode
不具备唯一性），`link()` 返回 `EPERM`，代码按其“目标已存在”的失败分支反复
重试，最终返回 `L_MAXTRYS`。注意：`EPERM` 与 `EEXIST` 语义不同，前者是
文件系统能力缺失，不是“他人持锁”。

## 推荐方法

在不支持硬链接的文件系统（HMDFS、部分 NFS）上，把 `link(tmplock, lockfile)`
改为**运行时探测回退**：`link()` 失败且 `errno == EPERM|EOPNOTSUPP|ENOTSUP`
时，改用 `open(lockfile, O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC, 0644)` 直接
原子创建目标锁文件并写入 PID 内容（`O_EXCL` 本身就是“不存在才创建”的原子
原语，等价替代 link 的原子性），成功后丢弃临时文件返回 `L_SUCCESS`；
若 `open` 返回 `EEXIST` 则仍视为“他人持锁”走到原有 stale-lock 检查分支，
保持错误语义不变。

关键点：用运行时错误码探测而非 `#ifdef __OHOS__` 平台宏（R8 口径：补丁中
默认禁止平台宏），使同一补丁在 Linux/其他不支持硬链接的文件系统上同样生效；
`open` 需选择 `O_CLOEXEC` 与临时文件相同的权限位；写入失败时清理目标与
临时文件并返回 `L_TMPWRITE`，不污染锁状态。

## 验证

- 补丁后 `make`、`make test`（run-tests.sh）全部通过（tests OK）；
- `conan create` 干净构建通过（G2），test_package 消费者二进制真正调用
  `lockfile_create`/`lockfile_check`/`lockfile_remove` 断言锁生命周期；
- W3 本地 CI（build_and_test.sh）通过，L1e 破坏性反向验证确认 test 实质
  依赖被测包；
- 回退点在支持硬链接的环境不激活（link 成功路径不变）。

## 与已有知识的差异

- E079 只给 shell/命令层方案（cp 替换、env var、configure ln 探测），
  无法修复 **C 源码内 link(2) 锁原语**；
- E220（OHOS 复合适配）提到 hardlink 可能被拒，但方案是 perl 工具链专用
  copy-link wrapper，不含通用 O_EXCL 回退模式；
- 本条目给出可直接落进 C 库 source patch 的最小回退实现与错误语义约束
  （EEXIST≠EPERM 区分）。

## 适用边界

- 适用于以 link(2) 做“存在即锁”原子创建的 C/C++ 库（mail 锁、dotlock、
  各类 lockfile 库）；
- 回退只应在 link 因能力缺失失败时触发；其他 errno 保持原行为；
- 若后续目标锁语义依赖 inode/nlink 判定（如 lockfile 的 rdev/ino 校验），
  O_EXCL 成功分支直接返回，不进入 lstat 校验段。

## 反例与限制

- 不适用于依赖硬链接计数（nlink>1）暴露锁所有者信息的用法；
- 不支持硬链接 ≠ 不支持符号链接：无需把 symlink 一并改写；
- 不应把 O_EXCL 回退写成无条件替代 link（普通 Linux 上 link 语义仍优）。

## 证据来源

- `archives/l/liblockfile/1.17.1/patches/0002-lockfile.c.patch`
  （link→O_EXCL 运行时回退）
- `archives/l/liblockfile/1.17.1/reports/conan-verify-report.md`
- `archives/l/liblockfile/1.17.1/reports/w3-local-ci.log`
- 上游：https://github.com/miquels/liblockfile （tag v1.17, 9389848f70）