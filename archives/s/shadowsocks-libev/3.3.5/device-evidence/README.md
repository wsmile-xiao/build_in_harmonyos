# 真机端到端证据（DAYU200 · rule12）

设备：润和 DAYU200-RK3568 · OpenHarmony 6.0.0.47 (API20, aarch64, 64bit)
序列号：`450100445634303332018f3e7d2dba00`
执行器：`automation/device_runner.sh`（Windows hdc 直连，D 盘中转）

## 用例

`test_package/test_shadowsocks_e2e.c` —— **消费者端到端回环**，不是纯断言：

1. 进程内 fork 出**内建 HTTP 源站**（纯 socket，无第三方依赖）
2. fork/exec 包内**真实** `ss-server` 与 `ss-local` 二进制
3. 自己实现最小 SOCKS5 客户端，穿过加密隧道向源站发 HTTP GET
4. **逐字节校验**取回的载荷（`OHPC_SHADOWSOCKS_E2E_PAYLOAD_0123456789`）

覆盖 AEAD（aes-256-gcm、chacha20-ietf-poly1305）与流密码
（aes-256-cfb、rc4-md5）两条加解密代码路径。

## 真机执行结果

```
# 设备上执行
$ sh run_on_device.sh

=== env ===
Linux localhost 6.6.101 #1 SMP Mon Sep 28 19:29:42 CST 2026 aarch64
=== libs ===
-rwxr-xr-x 63808  libev.so
-rwxr-xr-x 906328 ss-local
-rwxr-xr-x 1133424 ss-server
-rwxr-xr-x 863328 test_shadowsocks_e2e
=== run consumer e2e ===
  [PASS] SOCKS5 tunnel round-trip           aes-256-gcm (payload matched)
  [PASS] SOCKS5 tunnel round-trip           chacha20-ietf-poly1305 (payload matched)
  [PASS] SOCKS5 tunnel round-trip           aes-256-cfb (payload matched)
  [PASS] SOCKS5 tunnel round-trip           rc4-md5 (payload matched)

E2E summary: 4 passed, 0 failed (ciphers=4)
__RC__=0
```

采集到的 `_device_evidence.json`：

```json
{
  "job": "ssx_e2e",
  "device_serial": "450100445634303332018f3e7d2dba00",
  "system": "OpenHarmony 6.0.0.47 (API20, aarch64, 64bit)",
  "command": "sh run_on_device.sh",
  "exit_code": 0,
  "result_json_received": true,
  "timestamp": "2026-10-01T19:28:47+08:00"
}
```

## 复现步骤

```bash
# 1) 用 conan 构建（交叉）
conan create . -pr:h=ohos-aarch64 -pr:b=default --build=missing

# 2) 取包内二进制
PKG=$(conan cache path shadowsocks-libev/3.3.5)   # 注意：这是导出目录
#    实际包目录形如 /root/.conan2/p/b/<hash>/p

# 3) 编译静态测试二进制（设备无运行库依赖）
aarch64-unknown-linux-ohos-clang --sysroot=<sysroot> -O2 -static \
  -o test_shadowsocks_e2e test_package/test_shadowsocks_e2e.c

# 4) 打包（ss-local/ss-server/ss-tunnel + libev.so + 测试二进制 + run_on_device.sh）
#    ss-* 唯一的动态依赖是 libev.so，与其放在同一目录并设 LD_LIBRARY_PATH

# 5) 推送并执行
bash automation/device_runner.sh run ssx_e2e <payload_dir> "sh run_on_device.sh"
```

> 说明：qemu + OHOS musl 运行根下的同一用例亦 4/4 通过（CI 门禁口径），
> 真机结果与之一致。
