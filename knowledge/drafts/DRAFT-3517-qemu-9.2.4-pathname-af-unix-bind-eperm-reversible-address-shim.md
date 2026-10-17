# DRAFT-3517-qemu-9.2.4-pathname-af-unix-bind-eperm-reversible-address-shim

> HarmonyOS PC（aarch64-linux-ohos，HongMeng Kernel 1.12.0）上
> **路径名 AF_UNIX `bind(2)` 全域返回 EPERM**，抽象命名空间却可用。
> 本条目给出可逆地址改写垫片的实现要点，以及「只做正向改写会修好一批、
> 弄坏另一批」这一必备反向映射。来自 qemu 9.2.4 适配（Issue #3517 / PR !13119）。

## 现象

qemu 的 qtest 传输层两侧都是**路径名** unix socket：libqtest 监听某路径，并把
**同一路径**经 `-qtest unix:PATH` 交给它 spawn 的 QEMU；QMP 侧也是路径名
chardev。在本机上，每个用例在 **0.15s 内 SIGABRT**：

```
socket_accept failed: Resource temporarily unavailable
ERROR:../src/tests/qtest/libqtest.c:497:qtest_init_internal:
      assertion failed (s->fd >= 0 && s->qmp_fd >= 0)
```

失败得极快、且报错落在 socket 层，容易误判为「QEMU 没起来」或「参数错」。

## 根因

实测地址能力矩阵（同一进程、同一目录）：

| 地址形式 | `bind` |
|---|---|
| 路径名（`$HOME/...`、`$TMPDIR/...`、任意可写目录） | **EPERM** |
| 抽象命名空间（`sun_path[0] == '\0'`） | **OK** |
| AF_INET `127.0.0.1:0` | **OK** |

即：**不是 socket 被禁用**，而是**路径名地址这一形式**被拒。换目录无解
（已在 `$HOME`、`$TMPDIR`、`/dev/shm`、`/data/local/tmp` 等多处验证）。

### 关键陷阱：地址回显

只改写 `bind`/`connect` **不够**。软件会**回报**自己的 socket 地址：

- QEMU 的 `info network` 会打印 socket 地址；
- 上游 `tests/qtest/netdev-socket.c` 断言**配置的路径被原样回报**。

只做正向改写时，该断言会失败——表现为「垫片修好了一批用例、又弄坏了另一批，
且新失败与地址字符串有关」。这正是本条目最重要的判据。

## 修复

用 LD_PRELOAD 把路径名地址改写为**由路径纯函数派生**的抽象名，并**实现反向
映射**：

1. **正向**（`bind`/`connect`）：`sun_path` → `PREFIX + path`（过长则退化为
   `PREFIX + hash`）。纯函数派生是**多进程免协调**的关键：被 spawn 的 QEMU
   继承同一垫片后能独立算出同一名字，无需任何通信。
2. **反向**（`getsockname`/`getpeername`）：把抽象名还原为原路径，使地址
   回显与日志保持真实。抽象名的长度取自 `addrlen`（名字**不以 NUL 结尾**），
   且 `sun_path[0]` 是 NUL 标记——解析须从 `sun_path[1]` 起比前缀、按
   `addrlen` 算实际长度。

### 两个必须避开的实现错误（本包实测踩到）

| 错误 | 后果 | 正确做法 |
|---|---|---|
| 用 `addrlen - offsetof(struct sockaddr_un, sun_path)` 当路径长度 | 调用方普遍传 `sizeof(struct sockaddr_un)`，于是把尾部 NUL 填充一并复制进抽象名，且生成的 addrlen 越过结构体边界 → 内核 **EINVAL**，**全部 bind 失败** | 用 `strnlen(sun_path, sizeof sun_path)` 取**字符串**长度 |
| 把名字写在 `sun_path[0..]` | 变成**相对路径名**，恰好回到被拒的那条路 | `sun_path[0] = 0`，名字从 `sun_path[1]` 起写；`addrlen = offsetof(...) + 1 + namelen` |

### 顺带：抽象套接字没有 inode

抽象套接字不对应文件，故对被改写路径的 `chmod()` 会 `ENOENT`。有调用方
（如 **swtpm**）在 `bind` 自身控制套接字后 `chmod` 该路径，并把失败当**致命
错误**退出——于是守护进程在 QEMU 连接前就死了，测试以 socket 超时收场，报错
里完全没有 TPM 字样。

处置：**只对垫片自身重定向过的路径**（在 `bind` 成功时登记）应答
`chmod`/`fchmodat` 成功；未被改写的路径原样透传（这样垫片绝不会替它没碰过的
文件撒谎）。

## 验证

| 项 | 结果 |
|---|---|
| 基线（无垫片） | 每个 qtest 用例 0.15s SIGABRT |
| 仅正向改写 | 多数用例通过，`netdev-socket` 失败（地址回显不符） |
| 正向 + 反向 | `qtest` 66 项 **0 FAIL**；`netdev-socket` **2/2**（各 10 项子测试） |
| swtpm 场景 | 补 `chmod` 容忍后 `tpm-tis-device-swtpm-test` **2/2** 通过 |

## 适用边界

- 垫片是**本地验证 harness，不随配方发布**；补偿的是宿主沙箱限制，不改变软件本身。
- 语义不变：仍是 stream AF_UNIX 套接字，只是地址**命名空间**从路径名换到抽象名；
  被测的字节流与协议帧完全一致。
- 边界：哈希形式的抽象名**不可逆**（路径超长时回显会变成哈希名）；若软件有
  「把地址写给另一个不知道垫片的进程」的需求，该协商会失败。
