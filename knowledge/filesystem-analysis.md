# 鸿蒙文件系统架构与差异分析

> **检测环境**: HarmonyOS / HongMeng Kernel 1.11.0 / aarch64 / UID 20020081  
> **检测时间**: 2026-03-23  
> **检测方式**: 实机探索，/proc/mounts 全量分析、stat 验证、功能测试

**相关文档**:
- 文件系统限制对编译的直接影响 → `environment.md` §5
- 软链接处理规范 → `environment.md` §9
- procfs 访问限制 → `harmonyos-specifics.md` §11
- SELinux 域转换 → `harmonyos-specifics.md` §7

---

## 1. 文件系统类型全景

| 文件系统 | 类型 | Linux 对标 | 主要挂载点 | 开发者关注点 |
|----------|------|-----------|-----------|-------------|
| **HMFS** | 自研可读写 | ext4/f2fs | /data 下大量子挂载 | ⭐ 主力文件系统，见 §2 |
| **EROFS** | 只读压缩 | squashfs | /tmp, 系统镜像 | /tmp 只读，见 `environment.md` §5.1 |
| **HMDFS** | 自研分布式 | 无 | 用户主目录、云盘 | ⭐ 分布式文件系统，见 §3 |
| **ShareFS** | 自研共享 | 无 | 应用间数据 | 跨应用数据交换 |
| **OverlayFS** | 联合挂载 | 同 Linux | /system, /vendor 等 | ⭐ 重度使用，见 §4 |
| **tmpfs** | 内存 FS | 同 Linux | /, /storage/*, /dev/shm | 基本一致 |
| **ext4** | 只读 | 同 Linux | /sys_prod, /module_update | 只读辅助分区 |
| **devfs** | 设备 FS | devtmpfs | /dev | 见 §5 |
| **procfs** | 进程信息 | 同 Linux | /proc | 权限收紧，见 `harmonyos-specifics.md` §11 |
| **configfs** | 配置 FS | 同 Linux | /config | 新增 `transfs` 选项 |

---

## 2. HMFS — 鸿蒙主文件系统

HMFS (HarmonyOS Mutable File System) 承担传统 Linux 中 ext4/xfs 的角色，是鸿蒙系统中数据持久化的核心。

### 2.1 标准挂载选项

从 /proc/mounts 提取的 HMFS 挂载参数模板：

```
hmfs rw,nosuid,nodev,noatime,
  hmmac=inherit_parent,        # 鸿蒙特有 MAC（见 §6）
  user_xattr,                  # 扩展属性
  inline_xattr,                # xattr 内联存储
  inline_data,                 # 小文件数据内联
  inline_dentry,               # 目录项内联
  discard,                     # TRIM 支持
  noflush_merge,               # 禁用 flush 合并
  acl,                         # POSIX ACL
  usrquota, grpquota, prjquota,# 三级配额（用户/组/项目）
  fsync_mode=nobarrier,        # 无屏障 fsync
  reserve_root=32768,          # root 预留 32MB
  errors=panic,                # 错误时 panic（非 remount-ro）
  seclabel                     # SELinux 标签
```

### 2.2 与 ext4 关键差异

| 特性 | HMFS | ext4 | 编译影响 |
|------|------|------|---------|
| `inline_data` | ✅ 默认开启 | 需手动启用 | 大量小文件（.o、.a）I/O 更快 |
| `inline_dentry` | ✅ 默认开启 | ❌ 不支持 | 小目录 ls 更快 |
| `inline_xattr` | ✅ 默认开启 | ❌ 不支持 | xattr 读取零开销 |
| `prjquota` | ✅ 默认开启 | 仅 xfs | 可按项目限制磁盘 |
| `fsync_mode=nobarrier` | ✅ 默认 | 需手动 | 编译速度更快，掉电风险 |
| `errors=panic` | ✅ 默认 panic | 默认 remount-ro | 磁盘错误 = 系统崩溃 |
| `noflush_merge` | ✅ 默认 | ❌ | 写入顺序保证更强 |

### 2.3 inline 机制对编译的实际影响

- 小文件（< 几 KB）直接存储在 inode 中，跳过数据块寻址
- 编译产物中大量 .o 文件（通常几 KB～几十 KB）受益于 inline_data
- `stat()` 返回 `Blocks: 0` 是正常的（inline 数据不占独立块），脚本不应依赖块计数判断文件大小
- `du` 对小文件报告的磁盘占用可能偏低

---

## 3. HMDFS — 用户主目录分布式文件系统

用户的 $HOME (`/storage/Users/currentUser`) 挂载于 HMDFS：

```
/data/service/el2/100/hmdfs/account → /storage/Users/currentUser
  文件系统: hmdfs
  选项: rw,nodev,relatime,hmmac=genfs
  总容量: ~926GB (底层 hmfs)
  inode 总数: ~48M
  块大小: 4096
```

### 3.1 与本地文件系统的差异

| 特性 | 本地 FS (ext4/hmfs) | HMDFS | 编译影响 |
|------|--------------------|---- |---------|
| `stat -f` Type | 正确报告类型 | `unknown` | ❌ 文件系统检测脚本失效 |
| `nodev` | 可选 | 默认开启 | 无法创建设备文件 |
| inode 数量 | 有限 | ~48M | 大量小文件无压力 |
| `flock`/`fcntl` 锁 | 完整 POSIX 语义 | ⚠️ 分布式语义 | make 并行编译的锁可能不同 |
| xattr | 完整支持 | ⚠️ 部分支持 | `getfattr` 可能返回 Not supported |
| SGID 目录 | 可选 | 默认 `drwxrws--x` | 新文件继承 file_manager 组 |

### 3.2 权限特征

```
$HOME 所有者: 20001006:file_manager (非当前用户 20020081)
$HOME 权限: drwxrws--x (SGID)
新建文件组: file_manager (继承 SGID)
```

部分 `.so` 文件在 `du` 扫描时出现 `Permission denied`，原因可能是 hmmac 或 hmdfs 的细粒度访问控制，但不影响正常编译流程。

---

## 4. OverlayFS 的重度使用

鸿蒙对 OverlayFS 的使用远超典型 Linux 发行版。

### 4.1 挂载模式

约 **20+ 个 overlay 挂载点**，覆盖 `/system`、`/vendor`、`/cust`、`/version`、`/chip_prod` 的子路径：

```
overlay /system/bin       lowerdir=/system,  upperdir=/mnt/overlay/usr/upper
overlay /system/lib64     lowerdir=/system,  upperdir=/mnt/overlay/usr/upper  ← 同一 upper!
overlay /system/etc       lowerdir=/system,  upperdir=/mnt/overlay/usr/upper  ← 同一 upper!
overlay /vendor/lib64     lowerdir=/mnt/lower/vendor, upperdir=/mnt/overlay/vendor/upper
overlay /cust             lowerdir=/mnt/lower/cust,   upperdir=/mnt/overlay/cust/upper
```

选项: `rw,relatime,hmmac=genfs,override_creds=off,seclabel`

### 4.2 对编译的影响

- 对 `/system` 下的任何写入都反映在所有子挂载中（共享 upperdir）
- 系统头文件、库文件均通过 overlay 访问
- `make install` 写入 overlay upperdir，实际存储在 hmfs 分区
- 系统升级/OTA 基于 overlay 层切换实现

---

## 5. devfs — 设备文件系统

```
devfs /dev devfs rw,relatime,hmmac=genfs
```

| 特性 | Linux devtmpfs | 鸿蒙 devfs | 影响 |
|------|---------------|-----------|------|
| 自动设备创建 | ✅ | ✅ | 一致 |
| /dev/null, /dev/zero | ✅ | ✅ | 一致 |
| /dev/stdin, /dev/fd | ✅ | ✅ | 一致 |
| /dev/pts | ✅ 可访问 | ❌ Permission denied | 无法创建新 PTY |
| /dev/console | ✅ 可访问 | ❌ Permission denied | 无法访问控制台 |
| IO Block | 通常 4096 | **512** | stat 结果差异 |

**编译影响**: 无法使用 `script` 命令（需要 /dev/pts），某些测试套件依赖 PTY 的功能会跳过。

---

## 6. Hmmac — 鸿蒙特有 MAC 层

Hmmac (HarmonyOS MAC) 是独立于 SELinux 的文件系统级强制访问控制，所有挂载点均携带 `hmmac=` 参数。

| hmmac 模式 | 适用 FS | 含义 |
|------------|--------|------|
| `use_task` | tmpfs | 使用进程的 hmmac 标签 |
| `inherit_parent` | hmfs, erofs | 继承父目录标签 |
| `genfs` | overlay, hmdfs, sharefs | 按文件系统类型生成 |
| `namefs:shmfs` | /dev/shm | 共享内存命名空间 |

**对编译的影响**: 软链接的创建和访问可能被 hmmac 拦截，无法通过 `chmod` 绕过。详见 `environment.md` §9。

---

## 7. 根目录布局差异

### 7.1 鸿蒙特有的目录

| 目录 | 用途 | 文件系统 |
|------|------|---------|
| `/storage` | 用户/外部存储根 | tmpfs 挂载点 |
| `/storage/Users/currentUser` | 用户主目录 | hmdfs |
| `/chip_prod` | 芯片产品化配置 | ext4 (ro) |
| `/sys_prod` | 系统产品化配置 | ext4 (ro) |
| `/cust` | 运营商定制 | overlay |
| `/preload` | 预装资源 | overlay |
| `/version` | 版本/OTA 管理 | overlay |
| `/config` | 内核配置 | configfs (transfs) |
| `/module_update` | 模块热更新 | ext4 (ro) |

### 7.2 缺失的标准 Linux 目录

| 目录 | FHS 用途 | 鸿蒙替代 |
|------|---------|---------|
| `/usr` | 二级层次结构 | 不存在，内容在 `/system` |
| `/var` | 可变数据 | `/data/log`, `/data/storage` |
| `/run` | 运行时数据 | 无明确替代 |
| `/home` | 用户主目录 | `/storage/Users/{userName}` |
| `/root` | root 主目录 | 不存在 |
| `/sbin` | 系统管理命令 | `/system/bin`（合并） |
| `/opt` | 第三方软件 | 无标准替代 |
| `/boot` | 启动文件 | 不暴露 |
| `/srv`, `/media`, `/snap` | 服务/介质/包 | 不存在 |

### 7.3 关键符号链接

```
/bin     -> /system/bin     # 系统命令（非 /usr/bin）
/etc     -> /system/etc     # 系统配置
/lib     -> /system/lib     # 32 位库
/lib64   -> /system/lib64   # 64 位库
/d       -> /sys/kernel/debug  # 调试入口
```

---

## 8. IO Block 大小异常

所有文件系统统一报告 IO Block = **512**（标准 Linux 通常为 4096）：

```
/       : IO Blocks: 512  (tmpfs)
/tmp    : IO Blocks: 512  (erofs)
/system : IO Blocks: 512  (overlay)
$HOME   : IO Blocks: 512  (hmdfs)
/dev    : IO Blocks: 512  (devfs)
```

**影响**: 依赖 `stat` 中 IO Blocks 计算磁盘使用量的脚本（如 `du` 的某些实现）会得到偏大 8 倍的结果。编译脚本中应使用 `stat --format=%s` 获取精确文件大小，而非依赖块计数。

---

## 9. 文件系统类型识别能力

`stat -f` 对鸿蒙自研文件系统返回 `unknown`：

| 挂载点 | `stat -f` Type | 实际 FS | 可识别 |
|--------|---------------|---------|--------|
| / | tmpfs | tmpfs | ✅ |
| /data (根视图) | tmpfs | tmpfs | ✅ |
| /tmp | **unknown** | erofs | ❌ |
| $HOME | **unknown** | hmdfs | ❌ |
| /system/bin | **unknown** | overlay (底层 erofs) | ❌ |

**影响**: 基于 `stat -f` 类型判断的 configure 脚本或构建工具可能行为异常。

---

## 10. 详细影响场景与实机验证

> 以下所有场景均基于 2026-03-23 实机验证，标注 ✅/❌ 的为实际测试结果。

### 10.1 HMDFS 不支持硬链接 — ⚠️ 隐蔽且影响广泛

**触发条件**: 在 $HOME（HMDFS）上执行 `ln` 不带 `-s` 参数

**实测**:
```bash
$ echo "original" > ~/tmp/hl_src
$ ln ~/tmp/hl_src ~/tmp/hl_dst
ln: cannot create hard link: Operation not permitted   # ❌ 失败
```

**根因**: HMDFS 挂载选项包含 `nodev`（禁用设备文件），同时不支持硬链接 inode 共享。这是分布式文件系统的固有限制——跨设备 inode 不具备唯一性。

**连锁影响场景**:

| 场景 | 受影响软件 | 表现 | 解决方案 |
|------|-----------|------|---------|
| `make install` 安装 man 页 | GNU autotools 生态 | man 页安装失败（make 用 ln 硬链接 man1→man8 等别名） | `make install DESTDIR=` 后手动复制；或安装 GNU coreutils 的 `ginstall` |
| git 仓库操作 | git | `git clone --local`（硬链接优化）失败；`git fsck` 报告对象问题 | 避免 `--local`，使用 `--no-hardlinks` |
| 构建缓存 | ccache, sccache | 可能依赖硬链接做原子替换 | 配置缓存目录到 HMFS 之外的路径 |
| cargo/rustc 编译 | Rust 工具链 | 编译缓存硬链接失败，退化为复制 | 性能下降但功能正常 |
| npm/pnpm | Node.js 包管理 | pnpm 的 content-addressable store 依赖硬链接 | 设置 `store-dir` 到非 HMDFS 路径 |
| 文件去重工具 | fdupes, rdfind | 无法通过硬链接合并重复文件 | 仅报告，不执行链接 |

**但 `mv`（rename）和 `rename()` 系统调用正常**:
```bash
$ echo "new" > ~/tmp/src && echo "old" > ~/tmp/dst
$ mv ~/tmp/src ~/tmp/dst   # ✅ OK（使用 rename，不需要硬链接）
```

**对 SQLite 的影响**: 测试表明 SQLite 默认 `journal_mode=delete` 和 WAL 模式均正常工作，因为 SQLite 的原子写入依赖 rename 而非硬链接。

---

### 10.2 HMDFS 不支持 FIFO/命名管道 — ⚠️ IPC 方案受限

**触发条件**: 在 $HOME（HMDFS）上执行 `mkfifo`

**实测**:
```bash
$ mkfifo ~/tmp/test_pipe
mkfifo: cannot create fifo: Operation not permitted   # ❌ 失败

$ mknod ~/tmp/test_node c 1 3
mknod: Operation not permitted                       # ❌ 失败
```

**连锁影响场景**:

| 场景 | 受影响软件 | 表现 | 解决方案 |
|------|-----------|------|---------|
| 进程间通信 | 自定义脚本 | `mkfifo` 创建失败 | 使用 `/dev/shm` 下的 FIFO（tmpfs，支持） |
| 测试框架 | autotests, Go test | 依赖 FIFO 的并行测试跳过 | 在 `$TMPDIR`（HMDFS）下跳过，改用 socket |
| 管道式构建 | 某些 Makefile | FIFO 并行管道失败 | 改用普通管道 |
| X11/Wayland socket | 桌面应用 | socket 文件创建行为可能异常 | N/A（鸿蒙桌面有自己的机制） |

**替代方案**: `/dev/shm` 是 tmpfs，完全支持 FIFO 和 mmap：
```bash
$ mkfifo /dev/shm/my_pipe     # ✅ OK
$ python3 -c "import mmap; ... mmap /dev/shm/test ..."  # ✅ OK
```

---

### 10.3 HMDFS 的 chown 静默无效 — ⚠️ 非常隐蔽的权限陷阱

**触发条件**: 在 $HOME（HMDFS）上对文件执行 `chown`

**实测**:
```bash
$ echo "x" > ~/tmp/own_test
$ chown 0:0 ~/tmp/own_test   # exit code 0 ✅ 看似成功！
$ ls -la ~/tmp/own_test
-rw-rw---- 1 20001006 file_manager 2 ...  # ⚠️ 所有者未变！仍是 20001006:file_manager
```

**根因**: HMDFS 的所有者由 `file_manager` 服务统一管理，`chown` 调用返回成功但不执行任何操作（静默忽略）。

**影响场景**:

| 场景 | 表现 | 风险等级 |
|------|------|---------|
| `make install` 中的 chown | 安装后 chown root:root 静默失败，文件仍是 file_manager:file_manager | 🟡 中（通常不影响使用） |
| 测试脚本验证权限 | 脚本检查 chown 返回码为 0，但实际未生效 | 🔴 高（测试假通过） |
| setuid/setgid 位 | 需 chown root 才能生效的场景全部失败 | 🟢 低（鸿蒙不用 setuid） |

---

### 10.4 /tmp 只读的连锁反应 — 🔴 影响面最广

**根因**: `/tmp` 挂载于 EROFS（只读压缩文件系统），完全不可写。

**实测**:
```bash
$ touch /tmp/test          # ❌ Read-only file system
$ mktemp /tmp/test.XXXX   # ❌ failed to create file via template
$ TMPDIR=/home/user/tmp mktemp /tmp/test.XXXX  # ❌ 仍然失败！
#                                ^^^ mktemp 优先使用模板路径而非 $TMPDIR

$ python3 -c "import tempfile; print(tempfile.mkdtemp())"
/storage/Users/currentUser/tmp/tmpwse0ibk1  # ✅ Python 尊重 $TMPDIR
```

**⚠️ 重要发现**: `mktemp /tmp/...` 即使设置了 `TMPDIR` 也会失败，因为 mktemp 的命令行参数会覆盖环境变量。只有不传路径参数时 mktemp 才使用 `$TMPDIR`。

**连锁影响场景（按严重程度排序）**:

| 严重度 | 场景 | 具体表现 | 解决方案 |
|--------|------|---------|---------|
| 🔴 | autotools configure | 崩溃，无法生成 Makefile | `export TMPDIR=$HOME/tmp` |
| 🔴 | Python 临时文件 | 默认会用 `$TMPDIR`，但如果代码硬编码 `/tmp` 则失败 | 检查代码中的硬编码路径 |
| 🔴 | 编译器中间文件 | clang/cc 内部临时文件失败 | `export TMPDIR=$HOME/tmp` |
| 🟡 | shell 脚本 `<<<` here-string | 某些 shell 实现在 /tmp 创建临时文件 | 使用 `echo ... \| cmd` 替代 |
| 🟡 | `mktemp /tmp/...` 显式路径 | 即便设了 TMPDIR 仍失败 | 改用 `mktemp $TMPDIR/...` 或 `mktemp`（无参数） |
| 🟡 | heredoc `cat << EOF > /tmp/file` | 直接写 /tmp 失败 | 写 `$TMPDIR` |
| 🟢 | Docker/容器工具 | 不适用于鸿蒙 | N/A |

---

### 10.5 /usr/bin/env 不存在的连锁反应

**实测**:
```bash
$ ls /usr/bin/env
ls: /usr/bin/env: No such file or directory  # ❌ 整个 /usr 目录不存在
```

**影响场景**:

| 场景 | 受影响 | 表现 | 修复 |
|------|--------|------|------|
| 脚本 shebang `#!/usr/bin/env python3` | 所有使用 env 的脚本 | `bad interpreter: No such file or directory` | `sed -i 's|#!/usr/bin/env |#!/|' script` |
| libtoolize | autotools 工具链 | 生成的 libtool 脚本包含 env shebang | 安装后批量修复 |
| npm 全局安装的包 | Node.js | 包的 bin 脚本使用 env shebang | 安装后修复 |
| pip 安装的包 | Python | 同上 | 同上 |
| cargo 安装的工具 | Rust | 同上 | 同上 |

**批量修复**:
```bash
# 安装后扫描所有使用 env shebang 的脚本
grep -rl '#!/usr/bin/env' $HOME/usr/local/bin/ 2>/dev/null | while read f; do
    sed -i 's|#!/usr/bin/env \([^ ]*\)|#!/\1|' "$f"
done
```

---

### 10.6 procfs hidepid=invisible 的影响 — 🔴 系统级调试几乎不可用

**挂载选项**: `procfs /proc procfs rw,relatime,hmmac=genfs,gid=3009,hidepid=invisible`

**实测**:
```bash
$ cat /proc/stat                  # ❌ Permission denied
$ cat /proc/version               # ❌ Permission denied
$ cat /proc/cmdline               # ❌ Permission denied
$ cat /proc/filesystems           # ❌ Permission denied
$ cat /proc/cpuinfo               # ✅ OK
$ cat /proc/meminfo               # ✅ OK
$ cat /proc/self/status           # ✅ OK（自身进程）
$ cat /proc/1/cmdline             # ❌ Permission denied（其他进程）
$ dmesg                           # ❌ klogctl: Operation not permitted
$ ls /sys/fs/selinux              # ❌ Permission denied
```

**连锁影响场景**:

| 场景 | 工具 | 表现 | 替代方案 |
|------|------|------|---------|
| 进程监控 | htop, top | 启动后无法获取 CPU/内存数据 | `sudo -E TERM=xterm-256color htop` |
| CPU 监控 | mpstat, vmstat | 无数据输出 | `sudo mpstat` |
| 系统调用追踪 | strace | 无法 attach 到其他进程 | `sudo strace -p <pid>` |
| 性能分析 | perf | 无法访问内核事件 | 不可用 |
| 构建系统优化 | make -j 决策 | 无法读取 /proc/loadavg 获取 CPU 数 | 依赖 `nproc`（可用） |
| 编译器信息 | `uname -v` equivalent | 无法通过 /proc/version 获取详细内核信息 | `uname -r` 可用（仅版本号） |
| 构建缓存 | ccache | 正常（不依赖 proc） | N/A |
| 日志分析 | `journalctl` | 不存在 | 查看 `/data/log/` |
| 文件系统信息 | `df -Th` | 基本正常（不依赖 proc） | N/A |

**注意**: `nproc` 和 `uname -m` 等通过 syscall 而非 /proc 获取的信息正常可用。

---

### 10.7 软链接的 Hmmac 三层陷阱

鸿蒙的软链接问题不仅是 SELinux，还有 Hmmac 叠加，形成三层陷阱：

**陷阱 1: ln -sf 产生随机后缀残留文件**
```bash
$ touch target_a target_b
$ ln -s target_a mylink        # ✅ 创建: mylink -> target_a
$ ln -sf target_b mylink       # ❌ 不覆盖！产生: mylink_pAleJB -> target_b
$ ls -la mylink*
lrwxrwxrwx 1 20001006 file_manager 10 ... mylink -> target_a       # 未变
lrwxrwxrwx 1 20001006 file_manager 10 ... mylink_pAleJB -> target_b  # 垃圾文件
```
**修复**: `rm -f mylink && ln -s target_b mylink`

**陷阱 2: 软链接存在但无法执行**
```bash
$ ls -la cc -> /data/service/hnp/bin/clang   # 看起来正常
$ cc --version
/bin/sh: cc: No such file or directory        # ❌ 执行失败
```
**原因**: SELinux context 阻止了 follow symlink。文件存在但不可访问。
**修复**: 用 wrapper 脚本替代，详见 `environment.md` §9。

**陷阱 3: 软链接的创建本身也可能失败**
```bash
$ ln -s /system/lib/libncursesw.so.6 ~/usr/local/lib/libncursesw.so.6
ln: cannot create symbolic link: Permission denied   # ❌ Hmmac 拦截
```
**修复**: `cp` 复制或 wrapper 脚本。

**对编译安装的全面影响**:

| 阶段 | 软链接操作 | 命中陷阱 | 影响 |
|------|-----------|---------|------|
| configure | 检测编译器 | 陷阱2 | `./configure` 找不到 cc/clang |
| make | 编译过程 | 通常无 | 代码编译不依赖软链接 |
| make install | 创建 bin 软链接 | 陷阱1+3 | 安装的命令可能不可执行 |
| make install | 创建 lib 软链接 | 陷阱1+3 | `.so.1 -> .so.1.2.3` 等版本链接失败 |
| make install | 头文件软链接 | 陷阱3 | `ln -s ../include/foo.h foo.h` 失败 |
| 验证 | 检查安装结果 | 陷阱2 | 二进制存在但无法执行 |

---

### 10.8 无 /etc/passwd 用户条目 — ⚠️ 用户身份识别系统失效

**实测**:
```bash
$ whoami
cannot find name for user ID 20020081  # ❌ 无用户名

$ python3 -c "import pwd; pwd.getpwuid(20020081)"
KeyError: 'getpwuid(): uid not found: 20020081'  # ❌ Python 也找不到

$ python3 -c "import os; os.getlogin()"
# 空字符串                                # ⚠️ 返回空而非用户名

$ getent passwd currentUser
zsh: command not found: getent            # ❌ 命令不存在
```

**连锁影响场景**:

| 场景 | 表现 | 解决方案 |
|------|------|---------|
| Git commit 作者 | `git config user.name` 可配置，不影响 | 使用 git config |
| SSH config 解析 | `~/.ssh/config` 正常工作 | N/A |
| Python logging | `logging.handlers.SysLogHandler` 可能找不到用户 | 用 `HANDLER = '%(name)s'` 替代用户名 |
| 构建日志记录 | 编译日志中用户名显示为 UID 数字 | 使用 `id -u` 获取数字 ID |
| sudo/su | 鸿蒙沙箱中不适用 | 使用 hdc shell（调试模式） |
| cron/at | 不存在 | 不适用 |
| pip install --user | 可正常工作 | N/A |

---

### 10.9 IO Block = 512 导致的脚本计算偏差

**实测**:
```bash
# 创建 1 字节文件
$ echo "x" > ~/tmp/tiny     # 实际内容 2 bytes

# stat 报告
$ stat ~/tmp/tiny
  Size: 2  Blocks: 16  IO Blocks: 512   # ⚠️ IO Blocks=512
                                     # Blocks=16 = ceil(2/512)*8 = 8 个 512 字节块 = 4096 字节
                                     # 但 du 报告:
$ du -b ~/tmp/tiny
2    /storage/Users/currentUser/tmp/tiny   # -b 模式用 stat size，准确

$ du ~/tmp/tiny
8.0K    /storage/Users/currentUser/tmp/tiny  # 默认模式报告 8K（实际 2 bytes）
```

**影响场景**:
- `du` 默认显示的磁盘占用与实际文件大小差距巨大（2 bytes → 8K）
- 依赖 `du` 做磁盘空间预估的脚本会高估
- `stat --format=%b` 返回的块数按 512 字节计算

**安全做法**: 统一使用 `stat --format=%s` 获取精确字节数，或 `du -b`：

```bash
# ✅ 正确获取文件大小
stat --format=%s file        # 精确字节数
du -b file                   # 精确字节数

# ⚠️ 不准确
du file                      # 报告块占用（偏大）
stat --format=%b file        # 512 字节块数
```

---

### 10.10 toybox flock 与 GNU flock 不兼容

**实测**:
```bash
# toybox flock 不支持 -c 参数（GNU flock 的核心用法）
$ flock -c "echo hello" /tmp/lock
flock: Unknown option 'c'

# toybox 语法: flock [-sxun] fd（需要先打开文件描述符）
$ exec 9>$HOME/tmp/lock
$ flock 9   # 但 HMDFS 上 9<> 打开会先失败
```

**同时**: HMDFS 上打开文件用于 flock 会因前面的硬链接限制产生连锁失败。

**影响**: 依赖 `flock -c "command" file` 的 Makefile 并行控制脚本需要改写。用 Python 的 `fcntl.flock()` 替代：
```python
import fcntl, os
f = os.open('lockfile', os.O_CREAT | os.O_RDWR)  # ✅ Python fcntl 正常工作
fcntl.flock(f, fcntl.LOCK_EX)                       # ✅ OK
```

---

### 10.11 du 在 HMDFS 上的 Permission denied 风暴

**实测**: 对 `$HOME` 执行 `du` 会产生大量 Permission denied 输出：
```bash
$ du -sh ~/python/libffi-3.4.4/aarch64-unknown-linux-ohos/.libs/
du: cannot access '.../libffi.so': Permission denied
du: cannot access '.../libffi.so.8': Permission denied
du: cannot access '.../libffi.la': Permission denied
```

**根因**: 编译产物中某些 `.so` 文件和 `.la` 文件的 hmmac 标签与当前用户不匹配。

**影响**: `du -sh` 估计磁盘使用时返回值不准确；脚本中 `2>/dev/null` 过滤是常见做法。

---

## 11. 安全模型三层叠加

| 层 | 机制 | Linux 对标 | 状态 |
|----|------|-----------|------|
| DAC | 传统 rwx | 同 | ✅ 正常 |
| MAC | SELinux | 同 | ✅ 强制启用 |
| Hmmac | 文件系统级 MAC | **无对标** | ✅ 独有 |

根目录权限收紧为 `0711`（标准 Linux 为 `0755`），普通用户无法 `ls /`。

---

## 11. 开发者影响速查

### 🔴 必须处理

| 问题 | 解决方案 | 详见 |
|------|---------|------|
| `/tmp` 只读 | `export TMPDIR=$HOME/tmp` | `environment.md` §5.1 |
| `/usr/bin/env` 不存在 | `sed -i 's|#!/usr/bin/env \|#!/|'` | `environment.md` §5.2 |
| 软链接受限 | wrapper 脚本替代 | `environment.md` §9 |
| procfs 大部分不可读 | sudo 或 HarmonyOS API | `harmonyos-specifics.md` §11 |

### 🟡 需要适配

| 问题 | 影响 | 建议 |
|------|------|------|
| 无 /var, /run | 日志/PID/socket 路径 | 自建目录或写入 $HOME |
| 无 /etc/passwd 条目 | `whoami` 失败 | 使用 `id -u` 替代 |
| HMDFS 的 flock 语义 | 并行编译锁 | make -j 可能需要调低 |
| /dev/pts 不可访问 | PTY 依赖的测试 | 标记跳过 |
| IO Block = 512 | 磁盘用量计算 | 用 `stat --format=%s` |
| `stat -f` 返回 unknown | FS 类型检测 | 用 `grep /proc/mounts` 替代 |

---

*文档版本: 1.0*  
*最后更新: 2026-03-23*  
*检测方法: 实机 /proc/mounts 全量分析 + stat 验证 + 功能测试*
