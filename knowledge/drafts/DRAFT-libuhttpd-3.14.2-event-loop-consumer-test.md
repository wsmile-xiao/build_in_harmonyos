# DRAFT：事件循环服务器库的 L1 消费者测试防死锁模式

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `testing` | Updated: 2026-09-27
> 对应: `knowledge/drafts/DRAFT-libuhttpd-3.14.2-event-loop-consumer-test.kv`

---

**匹配关键词**：event loop, test_package, recv timeout, SO_RCVTIMEO, client thread, watchdog, chunked

## 错误签名（error_signature）

```text
test hang|no output.*timeout|client.*recv.*block|EVBREAK|watchdog timeout fired|Server: .*Transfer-Encoding: chunked
```

## 根因（root_cause）

libuhttpd 类基于单线程事件循环（libev/libuv）的服务器库，test_package 若在主线程先发起客户端 HTTP 请求再 run loop，客户端 recv 阻塞时会卡死事件循环无法 accept，形成死锁；且 chunked + Connection: close 响应在 recv 端可能不返回 EOF（连接保持打开），无 SO_RCVTIMEO 时 recv 无限期阻塞。

## 推荐方案（rec_approach）

事件循环服务器库的 L1 消费者测试：
1. 服务器在主线程创建并 `ev_run`，客户端请求放进独立 pthread（libev 允许跨线程 ev_break）
2. connect 前对候选端口循环重试（最多 50 次 × 100ms）
3. socket 设 `SO_RCVTIMEO` 5s，recv 遇 `EAGAIN/EWOULDBLOCK` 视为响应已收完
4. `ev_run` 前挂 20s watchdog 定时器，未通过即 `ev_break` 并报 watchdog 超时，防测试无限挂起

## 验证（verification）

libuhttpd 3.14.2 test_package：独立线程客户端 + SO_RCVTIMEO + watchdog，`conan create` 全绿（CONAN_RC=0），HTTP/1.1 200 + 响应体 "Hello from libuhttpd 3.14.2" 校验通过，测试约 5s 内自然结束。

## 适用边界（applicable_library_types）

http-server、event-loop、libev、libuv、libevent 类库的 test_package。

## 反例（counter_examples）

- 纯客户端库（无需 accept）的测试不涉及此死锁
- 上游已自带集成测试框架时可直接复用，无需自造回环

## 限制（limitations）

- 跨线程 `ev_break` 依赖 libev 线程语义（libev 文档明确允许）；其他事件循环需核对
- fork 场景需重算 loop 状态，不建议与线程方案混用
- chunked 响应校验应基于原始字节包含（strstr），不依赖 EOF

---

*本文件由 `knowledge/drafts/DRAFT-libuhttpd-3.14.2-event-loop-consumer-test.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
