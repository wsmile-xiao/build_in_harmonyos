# E543 — tacopie 类 select 驱动 TCP 库：connect() 超时路径 select() nfds 传 0，任何带超时的 connect 都必然抛 "connect() timed out"

## 错误特征

客户端带超时调用 `tcp_client::connect(host, port, timeout)` 时立即（等满超时后）抛出：

```
libc++abi: terminating due to uncaught exception of type tacopie::tacopie_error: connect() timed out
```

即使对端（tcp_server）已经 `accept()` 到该连接（服务端日志显示 new client），客户端仍报超时。
Python/普通 socket 的同机回环 connect 正常，排除环境网络问题。

## 触发条件

- 构建系统: cmake（库本体），任何消费 tacopie 的 CMake 工程
- 阶段: runtime（客户端 connect）
- 触发代码: `sources/network/unix/unix_tcp_socket.cpp` 的 `tcp_socket::connect()`，且 `timeout_msecs > 0`

## 根因分析

connect() 的非阻塞路径：

```c
fcntl(m_fd, F_SETFL, ... | O_NONBLOCK);      // 设非阻塞
ret = ::connect(m_fd, server_addr, addr_len); // 返回 EINPROGRESS
timeval tv = { timeout_msecs/1000, ... };
fd_set set; FD_ZERO(&set); FD_SET(m_fd, &set);
if (select(0, NULL, &set, NULL, &tv) == 1) { // ← BUG：nfds 传了 0
  // 连接成功
} else {
  __TACOPIE_THROW(error, "connect() timed out");
}
```

`select()` 的 `nfds` 参数是三个 fd_set 中最大 fd + 1。传入 0 表示**内核不监视任何文件描述符**，
`select()` 直接睡满整个超时并返回 0 → 代码永远走 `connect() timed out` 分支。
服务端确实 accept 到了连接（内核已完成三次握手），但用户态从未观察到 socket 可写。

修复：`select(m_fd + 1, NULL, &set, NULL, &tv)`。这是纯 POSIX 语义错误，与 OHOS 平台本身无关，
在桌面 Linux 同样必现；OHOS aarch64 适配时首次暴露。

## 解决方案

### 推荐方案

把 nfds 从 0 修正为实际 socket fd + 1：

```diff
-    if (select(0, NULL, &set, NULL, &tv) == 1) {
+    if (select(m_fd + 1, NULL, &set, NULL, &tv) == 1) {
```

补丁文件: `archives/t/tacopie/3.1.0/patches/0001-fix-connect-select-nfds.patch`（+1/-1）。

### 禁止做法

- ❌ 把超时参数改大/改 0（阻塞模式）来"绕过"——会掩盖真实 bug，且阻塞 connect 丢超时语义
- ❌ 直接改平台层 select 行为或加宏 hack 让 nfds=0 生效——POSIX 语义不可覆盖

## 验证

```bash
conan create . --profile=ohos-aarch64 --build=missing
# 输出: test_tacopie Passed + test_tacopie_hmos Passed（100% tests passed）
./test_tacopie   # 回环往返：服务端 async_read 收到 payload == "tacopie-consumer-ping"
```

独立诊断（修复版库源码直接编译运行）：
`diag_echo`（服务端 accept + read 回调打印 nbytes=16 data='diag-payload-123'）与
`diag_t5`（客户端按值捕获 client shared_ptr 后 read 回调触发、ok=1）均通过；
未修复版本 `diag_client` 连 Python 服务端（服务端 accept 成功）仍抛 connect() timed out。

## 关联条目

- 相关: E086（OHOS socket 平台差异：SO_PEERCRED/struct ucred 守卫）——同属 socket 层 OHOS 适配，但根因/方案不同
- 相关: E103（CMake 4.x 移除 <3.5 兼容）——同批次适配的另一类上游兼容问题
