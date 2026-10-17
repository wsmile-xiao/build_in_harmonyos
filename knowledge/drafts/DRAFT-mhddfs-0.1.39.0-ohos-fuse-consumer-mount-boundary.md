# DRAFT：OHOS PC 用户态 FUSE 消费端挂载可用性边界

- **id**: `DRAFT-mhddfs-0.1.39.0-ohos-fuse-consumer-mount-boundary`
- **来源**: mhddfs 0.1.39.0 适配（libfuse 2.9.9 消费端）
- **平台**: HarmonyOS PC / OpenHarmony aarch64，kernel 1.12.0，普通用户（Uid 20020085）
- **日期**: 2026-09-27

## 一类问题

任何"普通进程通过 /dev/fuse 挂载用户态文件系统"的软件（libfuse 消费端：
mhddfs、tmfs、mtpfs、securefs、kio-fuse 等同簇），在 OHOS PC 上运行时挂载会被
平台安全边界阻断。阻断不是单一 errno，而是三层叠加，探测顺序与判定树如下。

## 原始证据（设备实测，可复现）

```text
# 1) /dev/fuse 节点不可访问（stat 与 open 全部 EACCES）
stat  /dev/fuse: FAILED errno=13 (EACCES) Permission denied
open  /dev/fuse O_RDONLY: FAILED errno=13 (EACCES) Permission denied
open  /dev/fuse O_RDWR:   FAILED errno=13 (EACCES) Permission denied
read  /proc/filesystems:  FAILED errno=13 (EACCES) Permission denied

# 2) 无 fusermount；libfuse 制品自带的 fusermount 一执行即 SIGSYS
fusermount: (absent)   fusermount3: (absent)
<libfuse pkg>/bin/fusermount -u /tmp/mhprobe
Signal 31 (core dumped), rc=159

# 3) 直接 mount(2) 也被沙箱终止
libc.mount("none", "<dir>", "fuse", 0, "")
Signal 31 (core dumped)          # SIGSYS(31)，而非 EPERM

# 4) 内核 FUSE 能力存在，仅系统服务在用
/dev/fuse /data/storage/el2/media/Photo fuse rw,nosuid,nodev,noexec,noatime,... user_id=0,group_id=0,default_permissions,allow_other 0 0

# 5) 消费端可见错误（mhddfs 打包后二进制）
mhddfs: directory '<d1>' added to list
mhddfs: directory '<d2>' added to list
mhddfs: mount to: <mnt>
mhddfs: move size limit 67108864 bytes
fuse: failed to open /dev/fuse: Permission denied
rc=1
```

辅助事实：进程 `CapEff=0x2a`（无 CAP_SYS_ADMIN）；`id` 命令在 toybox 最小用户态缺失，
可用 `/proc/self/status` 观察 Uid/Gid/Cap。

## 判定树

```
用户态 FUSE 挂载可用？
├─ /dev/fuse open(O_RDWR) 失败(EACCES/EPERM/ENOENT) → 不可用（本平台现状：EACCES=13）
├─ fusermount/fusermount3 缺失或执行即 SIGSYS          → 不可用（本平台现状：缺失+SIGSYS）
├─ mount(2) 返回 EPERM                                  → 不可用（无 CAP_SYS_ADMIN）
├─ mount(2) 触发 SIGSYS                                 → 不可用（沙箱终止，本平台现状）
└─ 以上任一可用 → 可尝试 fuse_main 挂载（本平台不成立）
注意：/proc/mounts 里存在系统服务的 fuse 挂载 ≠ 普通进程可挂载（特权通道差异）。
```

## 与现有条目的差异化

- `DRAFT-composefs-1.0.8-hmfs-fsverity-ioctl-eacces` / `…-security-xattr-skip`：讲的是
  HMFS/fsverity/security xattr 的 **ioctl/xattr 语义**边界，不涉及挂载链。
- `DRAFT-ohos-syscall-capability-matrix-fork-probe`：进程/系统调用能力矩阵（fork 等），
  本条目聚焦 **FUSE 挂载链本身**（设备节点、辅助程序、mount(2)/SIGSYS）。
- 与 tmfs/mtpfs/securefs/kio-fuse 等 FUSE 消费端任务共享同一结论，可直接复用判定树与探针。

## 适配策略（一类问题级）

1. 能力探测三层（节点 errno / fusermount 可用性 / fuse_main 或 mount(2) 结果），原始输出
   归档到版本 `reports/`；
2. 交付物按"可构建 + CLI 可用"完成并如实标注挂载边界；
3. 消费者测试只对可确定行为做硬断言（版本、usage、目录校验、选项解析），挂载尝试做
   有界双向判定（见同批草稿 `DRAFT-mhddfs-0.1.39.0-fuse-consumer-test-construction`）；
4. 恢复条件：平台开放 /dev/fuse 给普通进程或提供系统级挂载服务后，原二进制无需改动即可挂载。

## draft-review 预审记录（2026-09-27）

```
相似正式条目 TOP3:
  E303 score=0.34  根因: hostfs 将宿主伪磁盘 opendir("/") 的 EACCES 当成坏文件名
  E008 score=0.25  根因: 鸿蒙 SELinux 限制对非普通文件(管道/终端/套接字)的 fstat()/lseek(), 返回 EACCES
  E031 score=0.20  根因: 鸿蒙 SELinux 限制普通用户访问 /proc 文件系统
预审建议: review-similar → E303（灰区，人工判断）
```

差异化：E303/E008/E031 均为 SELinux/EACCES 类，但资源与调用链不同——E303 是 hostfs
路径搜索（opendir）、E008 是非普通文件属性读取、E031 是 procfs 读取；本条目是 **FUSE
挂载链**（/dev/fuse 设备节点 open + fusermount 辅助程序 + mount(2) SIGSYS）。无同题命中。
