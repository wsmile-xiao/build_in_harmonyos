# udpping

**描述**: Simple ping with UDP - 通过 UDP 协议测试网络可达性的工具

**功能**:
- UDP 端口探测：测试 UDP 端口是否开放
- 响应延迟测量：测量 UDP 包的往返时间
- 服务器模式：可以作为 UDP echo server 运行
- 客户端模式：发送 UDP 包并接收响应

**项目来源**: GitHub - emanuele-f/udpping

**构建系统**: CMake

**编译版本**: 0.0.2

**平台适配要点**:
- 需要 `#include <sys/time.h>` 修复 `struct timeval` 定义缺失
- 需要 `install(TARGETS ...)` 修复 CMakeLists.txt 安装规则缺失
- 链接 pthread 库

**使用方式**:
```bash
# 服务器模式
udpping -s -p 6000

# 客户端模式
udpping -c <server_ip> -p 6000
udpping -c 127.0.0.1 -p 6000 -n 10 -i 500
```

**依赖**: 无额外依赖（仅需 pthread）