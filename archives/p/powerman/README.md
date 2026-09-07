# powerman

**PowerMan** — LLNL 开源的 HPC 集群远程电源管理（C client/server）。

powermand 守护进程通过设备协议脚本（`*.dev`，expect 风格）驱动 60+ 种电源设备
（baytech/icebox/cyclades/digital-loggers/openbmc/redfish/snmp/telnet…，亦支持
TCP 直连或 `cmd |&` 协程管道进程）；powerman 客户端提供 on/off/cycle/reset/
query/beacon/temperature 等命令，支持 hostlist 压缩表达式（`t[0-15]`）；另附
plmpower（并行多路控制）与 libpowerman（C API 客户端库）。

## 用法

```bash
# 服务端（默认前台运行；无 -f 选项，后台化用 shell &）
powermand -c /path/to/powerman.conf

# 客户端（默认端口 10101）
powerman --server-host=127.0.0.1:47913 -q          # 查询：on/off/unknown 三段
powerman --server-host=127.0.0.1:47913 -1 t[0-3]   # 开 t0..t3
powerman --server-host=127.0.0.1:47913 -0 t[0-3]   # 关
powerman --server-host=127.0.0.1:47913 -c t[0-3]   # cycle（off→delay→on）
powerman -l                                        # 节点列表

# 版本
powerman --version    # 2.4.4
```

最小配置（vpc 协程设备示例）：

```
listen "127.0.0.1:47913"
include "<prefix>/etc/powerman/vpc.dev"
device "test0" "vpc" "bash vpc-sim.sh |&"
node "t[0-15]" "test0"
```

## OHOS 适配说明（2.4.4）

- 可选设备守护进程 httppower/redfishpower/snmppower 按上游官方开关禁用
  （核心功能不受影响，免 libcurl/jansson/net-snmp 依赖）
- 适配细节见 [2.4.4/notes.md](2.4.4/notes.md)；上游测试套件真实结果与逐项
  归因见 [2.4.4/test_package/MANIFEST.yml](2.4.4/test_package/MANIFEST.yml)
- 已知限制：redfish 系设备协议依赖被禁用的 redfishpower 守护进程（如需使用
  须自行补 curl/jansson 依赖并去掉 --without-redfishpower）
