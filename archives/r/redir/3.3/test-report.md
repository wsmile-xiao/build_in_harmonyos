# redir 3.3 功能测试报告

**测试日期:** 2026-09-21
**测试环境:** HarmonyOS PC aarch64
**编译器:** clang 15.0.4

## 1. 编译测试

### 1.1 编译状态
✅ 编译成功（conan create 干净构建通过，G2 门禁）

### 1.2 构建配置
- `autoreconf -fi` 生成 configure（git archive 快照无 configure）
- configure 参数：`--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos --with-libwrap=no`
- make -j1（E074 HMDFS jobserver fifo 限制）

### 1.3 源码修改
无补丁（纯配方层适配：tool_requires 引导 + config.status umask 077 修复）

## 2. 安装产物

- 可执行文件: `bin/redir`
- 手册页: `man/man1/redir.1`
- 文档: `share/doc/redir/`（README.md、transproxy.txt、ChangeLog.md）

## 3. 功能测试（test_package 消费者验证）

### 3.1 CLI 冒烟测试
```bash
$ redir -h
Usage: redir [-hinspv] [-b IP]  [-f TYPE] [-I NAME] [-l LEVEL] [-t SEC]
                       [-x STR] [-m BPS] [-o FLAG] [-w MSEC] [-z BYTES]
                       [SRC]:PORT [DST]:PORT
```
✅ 退出码 0，usage 正常输出

### 3.2 端到端 TCP 重定向测试（R34 消费者用例）
测试脚本：`test_package/test_redir.sh`（Python 驱动，仅使用已安装的公开 `redir` 二进制）

```bash
# 1) 启动本机回显服务（模拟上游业务服务）
# 2) 以 -n（前台）运行安装的 redir：127.0.0.1:<SRC> -> 127.0.0.1:<SRV>
# 3) 客户端连接 SRC 端口，发送负载，断言经隧道往返的数据逐字节匹配
```

```python
payload = b"redir-consumer-e2e-payload"
sock.sendall(payload)
echo_back = sock.recv(4096)
assert echo_back == payload
```

✅ 结果：`OK: E2E TCP redirect round-trip matched (26 bytes)`
✅ `ALL TESTS PASSED`

### 3.3 公开 API 调用（消费者视角）
- 调用的公开接口：`redir [-h]`、`redir -n [SRC]:PORT [DST]:PORT`（上游 CLI 用法）
- 可观察结果：usage 输出、真实 TCP 端口监听、连接转发、数据往返一致

## 4. 上游测试统计（双口径）

| 口径 | 数量 | 说明 |
|------|------|------|
| source_declared_total | 0 | 上游无独立测试源：单文件 redir.c，Makefile.am 仅 bin_PROGRAMS，无 check/测试目标 |
| configured_executable_total | 2 | test_package 消费者测试 2 项（CLI 冒烟 + E2E 重定向） |
| executed_passed_total | 2/2 | 两项全部通过 |
| 未运行/未实例化 | 0 | 无 |

> 上游 `distcheck`（release 目标）是发行自检而非针对库功能的独立用例，不计入。
> 该统计与 MANIFEST.yml 声明一致（assertion_count: 2）。

## 5. 结论

✅ 全部测试通过，交付状态：built（本地 conan create 验证通过，制品未 upload）