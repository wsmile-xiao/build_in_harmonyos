# DRAFT-socat-1.8.1.3-ohos-chardev-write-pollout

OHOS 字符设备写端 POLLOUT 永不就绪导致 select/poll 数据循环挂起

## 基本信息

- **草稿 ID**: DRAFT-socat-1.8.1.3-ohos-chardev-write-pollout
- **关联库**: socat 1.8.1.3（r01，OHOS aarch64 实测）
- **严重度**: 2
- **类别**: platform, ohos, poll, chardev
- **触发**: `socat /dev/null /dev/null` 进入数据转移循环后永久挂起

## 错误特征

```
socat /dev/null /dev/null hangs
data transfer loop hangs
select write fd never writable
POLLOUT never ready
character device write
```

## 根因分析

OHOS 内核 poll/select 对字符设备（/dev/null、/dev/zero）的 O_WRONLY fd 从不返回
POLLOUT/可写（对照：普通文件、socketpair 立即可写，实测 select 3 秒不返回）。
依赖 select/poll 等待写端就绪后再写入的程序（如 socat 双向数据转移循环）会
永久阻塞在 poll/select。该问题在 test.sh:191 的健全性检查 `$SOCAT /dev/null /dev/null`
处卡死整个测试套件。

## 推荐方案

**方法**: skip-pollout-for-non-socket-write-fd

对非 socket 写端 fd（fstat 后 S_ISREG/S_ISCHR，含普通文件/字符设备）视为始终可写：
不加入 poll 集合（fd=-1）并直接置 maywr=true，跳过 POLLOUT 等待。写普通文件/
字符设备不会阻塞，等待 POLLOUT 本就不必要。

**r02 细化（实测修正）**：
1. 仅对 S_ISREG/S_ISCHR 生效，管道/FIFO 排除——STALL 等地址故意填满写管道，
   若误判"始终可写"会导致 write 阻塞且循环死等（test599 STALL_WR 实测复现后收窄）。
2. 当转移循环 4 个 poll fd 全部禁用且某方向 mayrd&&maywr 已就绪时（如 readbytes
   消耗后 EOF 待处理），跳过 poll 直接进入 transfer 评估（retval=1 模拟就绪），
   避免 select 空 fd 集 + NULL 超时永久阻塞（test149 READBYTES 实测复现后修复）。

```c
/* socat.c 数据转移循环，两处对称分支（sock1->sock2、sock2->sock1） */
if (!maywr2) {
    fd2out->fd = XIO_GETWRFD(sock2);
    fd2out->events = POLLOUT;
    struct stat st;
    if (fd2out->fd >= 0 && fstat(fd2out->fd, &st) == 0 &&
        (S_ISREG(st.st_mode) || S_ISCHR(st.st_mode))) {
        fd2out->fd = -1;
        maywr2 = true;
    }
}
/* fd 全部禁用且方向已就绪时跳过 poll： */
if (fd1in->fd < 0 && fd2in->fd < 0 && fd1out->fd < 0 && fd2out->fd < 0 &&
    ((mayrd1 && maywr2) || (mayrd2 && maywr1))) {
    retval = 1;  /* simulated ready */
} else {
    retval = xiopoll(fds, 4, to);
}
```

## 验证/命令

```
timeout 10 socat /dev/null /dev/null; echo $?   # 修复前挂起(RC=124)，修复后 RC=0
./test.sh -n 149    # READBYTES: OK（readbytes EOF 不再死等）
./test.sh -n 599    # STALL_WR: OK（填满管道仍按 -T 超时退出）
python3 -c "import os,select; fd=os.open('/dev/null',os.O_WRONLY); print(select.select([],[fd],[],3))"
# r02 鸿蒙专项测试全部 PASS（READBYTES/STALL_WR/UDP4/PIPE/FILE/TCP4/UNIX 7 项）
```

## 适用范围

任何在 OHOS 上使用 select/poll 等待非 socket 写端就绪的 C 程序（autotools/手动
socket 程序、数据中继/代理类工具），尤其以 /dev/null 或字符设备为写端时。

## 回退方案

无法改源码时可用 `-T` 总超时兜底（`socat -T N /dev/null /dev/null` 可退出），
但会截断正常长任务，仅作应急。

## 关键词

POLLOUT, select, poll, /dev/null, /dev/zero, char device, character device,
writable, data transfer loop, socat, hang, never ready, O_WRONLY
