# net-tools 2.1 真机手动实跑取证（2026-09-26）

设备: 华为 PC 真机（aarch64，uid 20020084 普通应用 uid）
包位置: ~/.conan2/p/b/net-t7fc8af8274f93/p/{bin,sbin}

## ifconfig -a（真实接口枚举成功）

```
Warning: cannot open /proc/net/dev (Permission denied). Limited output.
lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
        inet 127.0.0.1  netmask 255.0.0.0
        unspec 00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00  txqueuelen 1000  (UNSPEC)

wlan0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 192.168.43.14  netmask 255.255.255.0  broadcast 192.168.43.255
        unspec 00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00  txqueuelen 1000  (UNSPEC)
```

结论：接口枚举（lo/wlan0 真实状态 flags/地址/mtu）成功；仅 /proc/net/dev
统计面受限，ifconfig 有降级路径（Limited output 提示）。

## hostname

```
localhost
```

## /proc/net 文件级权限矩阵（普通 uid 实测）

目录列举 `ls /proc/net/` 成功（70+ 条目可见）；文件内容读取 **12/12 全拒**：

| 文件 | head 读取 | 影响工具 |
|---|---|---|
| route | Permission denied | netstat -rn / route -n |
| arp | Permission denied | arp -n |
| dev | Permission denied | ifconfig 统计面 |
| tcp / udp | Permission denied | netstat -t / -u |
| unix | Permission denied | netstat -x |
| sockstat / stat | Permission denied | netstat -s |
| wireless | Permission denied | iwconfig 类 |
| protocols | Permission denied | — |
| netstat | Permission denied | netstat -s 内部 |
| if_inet6 | Permission denied | ifconfig IPv6 面 |

结论：OHOS 沙箱对 /proc/net 文件内容全线 EACCES（目录列举可读），
网络状态查询类工具的"读表"面全部受限，"列举"面（接口名/主机名）正常。

## 实跑结论

- 工具在 OHOS 真机正常执行、参数解析正确、对受限资源如实报 EACCES，
  行为与 Linux 一致；差异在平台权限模型。
- 消费者测试 36 断言：33 passed / 3 restricted / 0 skipped / 0 failed
  （conan-verify G0-G4/L1-L5 全绿，判定可标记 status: published）。
- 知识草稿：knowledge/drafts/DRAFT-5919-net-tools-proc-net-route-arp-
  permission-denied.{kv,md}（E434）。
