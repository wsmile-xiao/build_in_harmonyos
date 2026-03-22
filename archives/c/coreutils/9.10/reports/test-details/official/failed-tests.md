# GNU Coreutils 9.10 失败测试用例详细列表

**生成时间**: 2026-03-17  
**测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64

---

## 一、FAIL 状态测试用例 (66个)

### 1. 符号链接/硬链接相关

| 序号 | 测试用例 | 说明 |
|------|----------|------|
| 1 | `link` | 硬链接创建失败 |
| 2 | `ln` | 符号链接创建失败 |
| 3 | `readlink` | 读取符号链接失败 |
| 4 | `tests/cp/link` | cp 链接操作失败 |
| 5 | `tests/cp/no-deref-link1` | cp 不解引用链接测试1 |
| 6 | `tests/cp/no-deref-link2` | cp 不解引用链接测试2 |
| 7 | `tests/cp/no-deref-link3` | cp 不解引用链接测试3 |
| 8 | `tests/cp/same-file` | 同文件复制测试 |
| 9 | `tests/ln/backup-1` | ln 备份测试 |
| 10 | `tests/ln/relative` | ln 相对路径测试 |
| 11 | `tests/ln/target-1` | ln 目标测试 |
| 12 | `tests/touch/dangling-symlink` | 悬空符号链接 touch |
| 13 | `tests/truncate/truncate-dangling-symlink` | 悬空符号链接 truncate |

### 2. 权限/用户相关

| 序号 | 测试用例 | 说明 |
|------|----------|------|
| 14 | `whoami` | 用户名解析失败 |
| 15 | `tests/chgrp/basic` | 基本组修改失败 |
| 16 | `tests/chgrp/no-x` | 无执行权限目录的组修改 |
| 17 | `tests/chgrp/recurse` | 递归组修改失败 |
| 18 | `tests/chmod/equal-x` | chmod 等号权限测试 |
| 19 | `tests/chmod/equals` | chmod 等号测试 |
| 20 | `tests/chmod/no-x` | 无执行权限目录的 chmod |
| 21 | `tests/chmod/setgid` | setgid 位设置失败 |
| 22 | `tests/chown/preserve-root` | chown 保留根目录测试 |
| 23 | `tests/chroot/chroot-fail` | chroot 失败测试 |
| 24 | `tests/id/uid` | UID 解析测试 |
| 25 | `tests/id/zero` | id -z 测试 |
| 26 | `tests/install/basic-1` | install 基本测试 |
| 27 | `tests/install/strip-program` | install strip 测试 |

### 3. 文件系统/删除相关

| 序号 | 测试用例 | 说明 |
|------|----------|------|
| 28 | `tests/rm/cycle` | rm 循环删除测试 |
| 29 | `tests/rm/empty-inacc` | 空不可访问目录删除 |
| 30 | `tests/rm/inaccessible` | 不可访问文件删除 |
| 31 | `tests/rm/rm1` | rm 测试1 |
| 32 | `tests/rm/rm2` | rm 测试2 |
| 33 | `tests/rm/rm3` | rm 测试3 |
| 34 | `tests/rm/unread2` | 不可读文件删除2 |
| 35 | `tests/rm/unreadable` | 不可读文件删除 |
| 36 | `tests/shred/shred-remove` | shred 删除测试 |
| 37 | `tests/mkdir/p-3` | mkdir -p 测试3 |
| 38 | `tests/mkdir/special-1` | mkdir 特殊测试1 |
| 39 | `tests/du/inacc-dest` | du 不可访问目标 |
| 40 | `tests/du/inacc-dir` | du 不可访问目录 |
| 41 | `tests/du/no-x` | du 无执行权限测试 |

### 4. 进程/信号相关

| 序号 | 测试用例 | 说明 |
|------|----------|------|
| 42 | `tests/misc/close-stdout` | 关闭标准输出测试 |
| 43 | `tests/misc/nohup` | nohup 测试 |
| 44 | `tests/timeout/timeout` | timeout 测试 |

### 5. 并行处理相关

| 序号 | 测试用例 | 说明 |
|------|----------|------|
| 45 | `tests/wc/wc-parallel` | wc 并行测试 |
| 46 | `tests/wc/wc-files0-from` | wc 从文件读取测试 |
| 47 | `tests/cksum/md5sum-parallel` | md5sum 并行测试 |
| 48 | `tests/sort/sort-compress` | sort 压缩测试 |
| 49 | `tests/sort/sort-debug-keys` | sort 调试键测试 |
| 50 | `tests/sort/sort-exit-early` | sort 早退出测试 |

### 6. 其他功能

| 序号 | 测试用例 | 说明 |
|------|----------|------|
| 51 | `tests/help/help-version` | 帮助版本测试 |
| 52 | `tests/cp/existing-perm-dir` | cp 现有权限目录 |
| 53 | `tests/cp/fail-perm` | cp 权限失败 |
| 54 | `tests/cp/proc-short-read` | cp proc 短读 |
| 55 | `tests/cp/reflink-perm` | cp reflink 权限 |
| 56 | `tests/cp/sparse` | cp 稀疏文件 |
| 57 | `tests/dd/fail-ftruncate-fstat` | dd ftruncate 失败 |
| 58 | `tests/ls/color-dtype-dir` | ls 彩色目录类型 |
| 59 | `tests/misc/time-style` | 时间样式测试 |
| 60 | `tests/mktemp/mktemp` | mktemp 测试 |
| 61 | `tests/mv/childproof` | mv 子目录保护 |
| 62 | `tests/mv/i-1` | mv 交互测试1 |
| 63 | `tests/mv/i-2` | mv 交互测试2 |
| 64 | `tests/mv/i-4` | mv 交互测试4 |
| 65 | `tests/mv/mv-exchange` | mv 交换测试 |
| 66 | `tests/mv/perm-1` | mv 权限测试1 |
| 67 | `tests/od/od` | od 测试 |
| 68 | `tests/tac/tac` | tac 测试 |
| 69 | `tests/tail/follow-stdin` | tail 跟踪标准输入 |
| 70 | `tests/tail/inotify-hash-abuse2` | tail inotify 测试 |

---

## 二、ERROR 状态测试用例 (83个)

### 1. 符号链接相关 (大量)

```
tests/chmod/ignore-symlink
tests/chmod/symlinks
tests/chmod/thru-dangling
tests/chown/deref
tests/chown/separator
tests/cp/abuse
tests/cp/attr-existing
tests/cp/cp-HL
tests/cp/cp-deref
tests/cp/deref-slink
tests/cp/dir-rm-dest
tests/cp/keep-directory-symlink
tests/cp/link-deref
tests/cp/link-no-deref
tests/cp/link-preserve
tests/cp/link-symlink
tests/cp/preserve-link
tests/cp/preserve-slink-time
tests/cp/r-vs-symlink
tests/cp/slink-2-slink
tests/cp/symlink-slash
tests/cp/thru-dangling
tests/df/df-symlink
tests/du/deref
tests/du/deref-args
tests/du/hard-link
tests/du/long-sloop
tests/du/no-deref
tests/du/trailing-slash
tests/ln/hard-to-sym
tests/ln/misc
tests/ln/sf-1
tests/ls/classify
tests/ls/dangle
tests/ls/dired
tests/ls/follow-slink
tests/ls/infloop
tests/ls/inode
tests/ls/symlink-loop
tests/ls/symlink-quote
tests/ls/symlink-slash
tests/mkdir/p-thru-slink
tests/mv/force
tests/mv/hard-2
tests/mv/hard-3
tests/mv/hard-4
tests/mv/i-link-no
tests/mv/into-self-4
tests/mv/symlink-onto-hardlink
tests/mv/symlink-onto-hardlink-to-self
tests/readlink/can-e
tests/readlink/can-f
tests/readlink/can-m
tests/readlink/multi
tests/readlink/readlink-fp-loop
tests/readlink/readlink-posix
tests/readlink/readlink-root
tests/readlink/rl-1
tests/rmdir/ignore
tests/rmdir/symlink-errors
tests/stat/stat-slash
tests/tail/symlink
tests/touch/no-dereference
```

### 2. 权限相关

```
tests/chgrp/default-no-deref
tests/chgrp/posix-H
tests/rm/fail-eacces
```

### 3. 其他

```
tests/cat/cat-self           # 文件描述符操作
tests/date/reference         # 日期引用
tests/dd/misc                # dd 杂项
tests/du/inodes              # du inode 统计
tests/env/env                # 环境变量测试
tests/ls/getxattr-speedup    # xattr 加速
tests/ls/group-dirs          # 组目录
tests/ls/hyperlink           # 超链接
tests/ls/ls-time             # ls 时间
tests/ls/no-arg              # ls 无参数
tests/ls/selinux-segfault    # SELinux
tests/ls/stat-dtype          # stat dtype
tests/ls/stat-failed         # stat 失败
tests/misc/realpath          # 路径解析
tests/pwd/pwd-option         # pwd 选项
tests/tail/inotify-hash-abuse # inotify
```

---

## 三、统计摘要

| 类别 | FAIL | ERROR | 合计 |
|------|------|-------|------|
| 符号链接/硬链接 | 13 | 56 | 69 |
| 权限/用户管理 | 14 | 3 | 17 |
| 文件系统操作 | 14 | 0 | 14 |
| 进程/信号 | 3 | 0 | 3 |
| 其他功能 | 22 | 24 | 46 |
| **总计** | **66** | **83** | **149** |

---

## 四、根本原因分析

### 主要问题

1. **符号链接不支持** (占失败总数约 46%)
   - 鸿蒙系统默认禁止普通用户创建符号链接
   - 影响大量依赖符号链接的测试

2. **权限模型差异** (占失败总数约 11%)
   - 用户/组管理机制不同
   - 特殊权限位受限

3. **文件系统特性** (占失败总数约 9%)
   - 部分文件系统操作受限
   - 临时文件权限问题

---

*报告生成时间: 2026-03-17*