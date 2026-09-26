# pcapplusplus

PcapPlusPlus 是一个跨平台 C++ 网络数据包捕获、解析与构造库，把 libpcap 的原始
API 封装为面向对象的协议分层模型，广泛用于网络工具、流量分析器与协议模糊测试。

## 功能概述

- 报文解析：Ethernet / ARP / IPv4 / IPv6 / TCP / UDP / DNS / HTTP / SSL / BGP /
  GTP / SIP / LDAP / Modbus / SOME-IP / WireGuard / VXLAN 等 60+ 协议分层
- 报文构造：逐层 `addLayer()` + `computeCalculateFields()` 生成可上线的字节流
- 抓包与收发：`PcapLiveDevice` / `PcapLiveDeviceList`（基于 libpcap）
- 离线文件：`PcapFileReaderDevice` / `PcapFileWriterDevice`（pcap / pcapng，含 zstd 压缩）
- BPF 过滤：`BPFStringFilter` 等过滤器，编译期与运行期均可匹配
- 会话重组：`TcpReassembly`、`IPReassembly`

## OHOS 适配

- 构建系统：CMake；第三方抓包后端使用制品仓已发布的 `libpcap/1.10.6`
  （armv8 / OHOS / clang 15 / 静态）
- 上游用自带 `cmake/modules/FindPCAP.cmake`（`find_path`/`find_library`）而不是
  CMake config 包，配方把 Conan libpcap 包的 `include/` 与 `lib/libpcap.a` 直接写进
  `PCAP_INCLUDE_DIR` / `PCAP_LIBRARY` 缓存变量
- `CMAKE_SYSTEM_NAME` 强制为 `Linux`（CMake 无 `Platform/HarmonyOS.cmake`），否则
  `if(UNIX)` 分支不成立，`LinuxNicInformationSocket.cpp` 会被静默丢弃
- 未改动上游任何源码，无补丁
- 详见各版本 `notes.md`

### 已知问题

- 无

## 使用方式

```cpp
#include "EthLayer.h"
#include "IPv4Layer.h"
#include "TcpLayer.h"
#include "Packet.h"

int main() {
    pcpp::EthLayer eth(pcpp::MacAddress("00:11:22:33:44:55"),
                       pcpp::MacAddress("66:77:88:99:aa:bb"));
    pcpp::IPv4Layer ip(pcpp::IPv4Address("192.168.10.7"), pcpp::IPv4Address("10.0.0.1"));
    pcpp::TcpLayer tcp(44321, 80);

    pcpp::Packet packet(100);
    packet.addLayer(&eth);
    packet.addLayer(&ip);
    packet.addLayer(&tcp);
    packet.computeCalculateFields();
    return 0;
}
```

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [26.07](./26.07/) | built | 2026-09-24 |

## 参考资料

- 官网: https://pcapplusplus.github.io/
- 源码: https://github.com/seladb/PcapPlusPlus
