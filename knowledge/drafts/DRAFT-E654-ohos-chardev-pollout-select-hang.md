# DRAFT-E654-ohos-chardev-pollout-select-hang

## 问题

任何「先 poll/select stdout 写就绪、再写入」的运行时/工具，在 OHOS 上只要把
stdout 重定向到 /dev/null（或 /dev/zero）就**永久挂起**。radamsa 0.7 移植实测：
上游 README 的标准用法与上游测试套件的 `> /dev/null` 用例（tests/1k.sh 等 14 项）
全部无限期挂死（进程 State=S、CPU 时间不增长、`/proc/<pid>/wchan` 为 EVENTPOLL）。

```text
$ echo 'x' | radamsa --seed 42 -M tmp/meta -n 1000 -o - > /dev/null
（无输出、不退出；45s 超时强杀）
```

## 根因（一手 C 探针实测，2026-09-22）

OHOS（musl/内核）对**字符设备**的 poll(2)/select(2) **永不报告写就绪（POLLOUT）**：

```text
poll(fd=/dev/null, POLLOUT, timeout=0)    → r=0 revents=0   （不可写）
poll(fd=/dev/null, POLLOUT, timeout=100)  → r=0 revents=0   （超时，仍不可写）
poll(fd=/dev/null, POLLOUT, timeout=-1)   → 永不返回
select(写集={/dev/null}, timeout=NULL)    → 永不返回
poll(fd=/dev/zero, POLLOUT, ...)          → 同 /dev/null
而：管道写端（无限等待/有限等待）正常返回 POLLOUT；普通文件正常；
    /dev/null 的 POLLIN（读就绪）正常；write() 到 /dev/null 一直成功。
```

即 write(2) 实际可用，但就绪通知机制对字符设备失灵；无限超时的 select 调用
从此永不返回。Owl Lisp VM 的 `do_poll`（编译产物 radamsa.c 内 `select(nfds,…,NULL)`）
在向 stdout 端口写之前轮询写就绪，恰好踩中。同族风险面：任何带「非阻塞端口 +
poll-then-write」抽象的脚本语言 VM / 事件循环 / 自定义 IO 库。

## 修复（写就绪预检短路，保留原生语义面）

在 VM 的 poll 实现里，对**写集** fd 先 `fstat` 预检：`S_ISCHR(st.st_mode)`
（字符设备）直接判可写立即返回，不再进入 select；管道/套接字/普通文件保持
原生 poll 语义（它们在 OHOS 上报告正确，且管道需要真实背压）。radamsa 的落
点是 patches/0001-radamsa-do_poll-ohos-chardev-writable.patch（对构建期生成物
radamsa.c 的 do_poll 加 14 行）。修复后同一命令 rc=0、2.9s 完成。

## 验证

- 上游 tests/run 28 项：补丁前 1k.sh 等挂死（套件无法推进）；补丁后
  28/28 全通过（含 6 项 `> /dev/null` 形态用例）。
- test_package 8 项断言含 2 项回归：`stdout>/dev/null`、`stdout>/dev/zero`。
- 平台探针：上表 8 组读数（探针源码见任务留档 `run_upstream_tests.sh` 同目录
  sel-variants.c / sel-probe2.c / sel-probe3.c）。

## 适用范围

OHOS 上所有「poll/select 写就绪后写 fd」的自研运行时与移植工具：症状是
「输出重定向 /dev/null（或 /dev/zero）就挂、重定向到管道/文件就正常」。
排查顺序：`/proc/<pid>/wchan` 是否 EVENTPOLL + State=S + CPU 不增长 →
用上面的 3 行 poll 探针复现 → 对运行时的 poll/select 封装加 S_ISCHR 写集短路。

```text
复现命令（本机可执行；BIN 换成任一 poll-then-write 工具）：
printf 'x' | "$BIN" -n 3 -o - > /dev/null   # 挂起即命中
```
