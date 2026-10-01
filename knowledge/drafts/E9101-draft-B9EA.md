# E9101 — libshout 源客户端消费者测试：假 Icecast 服务器必须模拟 TLS 探测与 401 挑战

> Status: DRAFT | 实例: oggfwd 0.2-git20150412.506088e（HarmonyOS PC 构建 OHOS AArch64）
> severity 🟡 2 | category: testing, network, socket, ohos

## 错误特征

test_package 里起一个本地假 Icecast 服务器、用被测 CLI（oggfwd）作客户端时，客户端**无输出、不退出**，
服务器只看到：

```
OPTIONS * HTTP/1.1
Host: 127.0.0.1:36437
User-Agent: libshout/2.4.6
Connection: Upgrade
Upgrade: TLS/1.0, HTTP/1.1
```

或（加 `-T disabled` 后）第一个连接是不带凭据的：

```
SOURCE /test.ogg HTTP/1.0
Host: 127.0.0.1:48003
User-Agent: libshout/2.4.6
Content-Type: application/ogg
Content-Length: 0
Connection: Keep-Alive
Prefer: return=minimal
```

服务器直接回 `HTTP/1.0 200 OK` 后，`qemu -strace` 可见客户端 `close(3)` 后重新 `connect` 并停在 `pselect6`。

## 触发条件

- 构建系统: 任意（本例为纯 Makefile）
- 阶段: test_package / 消费者用例运行
- 形态: 被测包是 libshout 的源客户端（oggfwd、ezstream、darkice……），测试用本地假服务器验证握手

## 根因分析

libshout 2.4.x 的 HTTP 源协议握手是多步的：

1. 默认 TLS 模式为 `AUTO`：先发 `OPTIONS * HTTP/1.1` + `Upgrade: TLS/1.0` 探测服务器是否支持升级；
   普通 TCP 假服务器不回应 OPTIONS，客户端一直等待。
2. `-T disabled` 后，首个 `SOURCE` 请求**不带 `Authorization`**；收到 `401` + `WWW-Authenticate: Basic` 后
   关闭连接、**重新连接**并带 `Authorization: Basic base64(source:password)` 重试（与真实 Icecast 行为一致）。
   假服务器对首个无凭据请求就回 200，会让客户端与假服务器错位（首连接已被客户端关闭，服务器却在等第二连接的后续数据）。

这不是被测包或 OHOS 的缺陷，而是消费者测试对协议的建模不足。

## 识别方式（输入）

- 日志/抓包里出现 `OPTIONS * HTTP/1.1` + `Upgrade: TLS/1.0` 且客户端无后续输出
- `qemu-aarch64 -strace` 停在 `pselect6`，且有两次 `connect`
- 服务器侧首个 `SOURCE` 请求缺少 `Authorization`

## 解决方案

### 推荐方案

假服务器按 Icecast 行为建模（本例 `test_package/test_fake_icecast.c`）：

- 循环 `accept`：请求无 `Authorization: Basic` → 回 `HTTP/1.0 401 Unauthorized` + `WWW-Authenticate: Basic realm="Icecast"` 并关闭；
  带凭据 → 回 `HTTP/1.0 200 OK`；
- 先跑 `oggfwd -h`，用法含 `[-T ` 时（libshout 带 TLS）客户端加 `-T disabled` 避开 OPTIONS 探测；
- 所有等待处 `alarm()` 设上限，stdout 行缓冲（`setvbuf(stdout, NULL, _IOLBF, 0)`），超时被杀也保留已通过的断言输出；
- 元数据文件写到 `$TMPDIR`（OHOS `/tmp` 只读，E002）。

可断言的可观测行为：挂载点、`Authorization: Basic c291cmNlOmhhY2ttZQ==`（`source:hackme`）、`ice-name` / `ice-genre` / `ice-description`、
`Connected to server`、`Total bytes read: 0`、退出码。

### 回退方案

假服务器建模成本不可接受时，仅断言无需握手的行为（`-h` 用法、缺参报错、连接被拒 `Error connecting` + 退出 1），
并在 notes 中如实说明握手路径未覆盖。

### 禁止做法

- ❌ 用 `sleep … && kill`、`|| true` 吞掉卡死，或只 `grep` 符号名当作握手通过（rule12 不认"只是断言"）
- ❌ 为迁就测试去 patch libshout 的 TLS 探测 / 认证流程，或改被测客户端源码

## 验证

```bash
# x86 runner：静态重链 oggfwd（E544），消费者用 -static 编译，经 qemu 实跑
qemu-aarch64 ./test_fake_icecast_static ./oggfwd-wrap.sh   # 11/11 PASS，退出码 0
```

## 关联条目

- 相关: E544（x86 runner 上动态 OHOS 产物无法运行，需静态重链副本验证）
