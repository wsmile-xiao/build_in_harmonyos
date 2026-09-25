# DRAFT: OHOS musl struct msghdr.msg_iovlen 为 int+pad——glibc 风格位置初始化器错位，须用 C99 指定初始化器

- **草稿 ID**: DRAFT-musl-msghdr-msg-iovlen-int-layout
- **来源库**: l2tpns 2.5.0（OHOS PC aarch64, clang 15.0.4 / OHOS SDK 26.0.0.18；musl libc）
- **状态**: 草稿（待主编 promote 为正式 E 条目）
- **严重度**: L1（musl 目标上确定性编译失败，且若压警告则转为运行期内存布局破坏）

## 问题（真机实测）

l2tpns 2.5.0 的 netlink 发送/接收封装以 glibc 成员布局书写位置初始化器：

```c
msg = (struct msghdr){ (void *)&nladdr, sizeof(nladdr), &iov, 1, NULL, 0, 0 };
```

OHOS musl 的 `struct msghdr`（`sys/socket.h`）为 64 位可移植性改写为
`int msg_iovlen` 并按字节序插入 `int __pad1`（aarch64 小端在 iovlen 之后）：

```c
struct msghdr {
    void *msg_name;
    socklen_t msg_namelen;
    struct iovec *msg_iov;
    int msg_iovlen;        /* glibc 为 size_t */
    int __pad1;            /* 64 位小端下存在 */
    void *msg_control;
    socklen_t msg_controllen;
    int msg_flags;
};
```

第 5 个初始化器 `NULL` 落到 `__pad1`（int），clang 报
`error: incompatible pointer to integer conversion initializing 'int' with an
expression of type 'void *'`。真机命中 `l2tpns.c:1931`（sendmsg 封装）与
`l2tpns.c:1963`（recvmsg 封装）两处。
证据：本 run 设备日志
`/storage/Users/currentUser/tmp/oh-device-porting-v2/l2tpns-2.5.0/manual-make3.log`。

## 根因

`struct msghdr` 的成员类型是 libc 实现细节（POSIX 只约束语义）：
glibc 用 `size_t msg_iovlen`（无 pad），OHOS musl 用 `int msg_iovlen` +
`int __pad1`（保持 32/64 位二进制兼容的历史决策）。**任何针对特定 libc
成员序列的位置初始化器/位置聚合赋值都是不可移植的**——成员数量或类型一变，
初始化器整体错位：轻则编译错（int←void*），重则（压警告后）把指针写进 pad、
把控制缓冲长度写进 flags 等，运行期布局破坏。

## 方案（推荐：C99 指定初始化器）

```c
msg = (struct msghdr){ .msg_name = (void *)&nladdr,
                       .msg_namelen = sizeof(nladdr),
                       .msg_iov = &iov,
                       .msg_iovlen = 1 };
```

- 与成员顺序解耦，未提及成员按标准零初始化（pad/flags/controllen 归零，
  语义与上游意图一致）；
- glibc/musl 双栈可移植，编译期不再依赖布局巧合。

l2tpns 落地：`patches/0003-msghdr-designated-init.patch`（两处同文替换）。

### fallback（结构体多处复用、不便改初始化器时）

`memset` 归零 + 逐成员赋值：

```c
memset(&msg, 0, sizeof(msg));
msg.msg_name = (void *)&nladdr;
msg.msg_namelen = sizeof(nladdr);
msg.msg_iov = &iov;
msg.msg_iovlen = 1;
```

同样与布局解耦；代价是代码量与遗漏字段静默为零的风险（对 flags/controllen
恰好无害，但需逐字段复核）。

## 验证（编译探针 + sysroot 布局核对，musl 目标下执行）

```sh
grep -n -A9 'struct msghdr {' ${OHOS_SDK_SYSROOT:-/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot}/usr/include/sys/socket.h   # 期望看到 int msg_iovlen 与 int __pad1
printf '#include <sys/socket.h>\nint main(void){struct msghdr m = {0,0,0,1,NULL,0,0}; return m.msg_iovlen;}\n' | ${CC:-clang} -x c - -c -o /dev/null   # 期望失败: incompatible pointer to integer conversion initializing 'int' with an expression of type 'void *'
```

第二条即本条目的判别特征：第 5 个位置初始化器撞上 int 成员；
改指定初始化器后通过。

## 适用边界

- 一切对 libc 内部布局敏感的聚合类型位置初始化：`struct msghdr`、
  `struct iovec` 之外的 `cmsghdr`、`sockaddr_storage` 补齐字段、
  `stat`/`statvfs` 等 musl 与 glibc 布局差异族；
- 32→64 位兼容层（含显式 pad 成员）的 libc 衍生版（OHOS musl 即此类）是
  高发环境；`getopt`/`aiocb` 等同模式。

## 反例与限制

- **禁止**以关闭/降级诊断的方式"消除"该错误（`-Wno-error=int-conversion`
  或更宽的 `-w`）：错位仍在，编译通过后指针被截断写入 int pad、控制缓冲
  与 flags 错位，运行期破坏内存布局且难复现；
- **禁止**按"成员序号 + 手算 pad"重排位置初始化器来适配 musl：把 libc
  实现细节固化进源码，libc 升级即碎；
- **禁止**手写本地 `struct msghdr` 替代定义绕开系统头（ABI 双源）。

## 查重差异

- 与 **E102/E148**（musl socket 族头/类型与 glibc 差异）同族：均源于
  OHOS musl 对 socket 相关结构/接口的布局与类型改写；本条增量是
  **聚合初始化器错位**这一具体失效模式（编译期 int←void* 指纹）与
  "指定初始化器优先、memset+逐成员赋值兜底、禁止压警告"的处置链；
- 与 E119（uapi 头类型重复冲突）方向相反：E119 是"重复定义要跳过"，
  本条是"成员类型改写要解耦"，互不覆盖。

## 参考

- OHOS SDK sysroot `usr/include/sys/socket.h`（struct msghdr 定义）
- glibc `socket/bits/types/struct_msghdr.h`（size_t msg_iovlen 对照）
- 本仓库归档：`archives/l/l2tpns/2.5.0/patches/0003-msghdr-designated-init.patch`
