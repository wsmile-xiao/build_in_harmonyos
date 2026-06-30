# libindi

**INDI 协议天文仪器库 - Implementation of the INDI protocol for astronomical instruments**

## 简介

libindi 是 INDI (Instrument Neutral Distributed Interface) 协议的实现，用于天文仪器的控制和通信。INDI 协议允许天文软件与望远镜、相机、焦点器等设备进行通信。

## 功能

- **indiserver**: INDI 服务器，管理驱动程序和客户端连接
- **libindiclient**: INDI 客户端库，用于构建天文软件
- **设备驱动**: 支持多种天文设备的驱动程序
- **XML 通信**: 基于 XML 的设备属性通信协议

## 编译版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 2.1.5.1-r1 | published | 2026-06-08 | 当前版本 |

## 依赖关系

**构建依赖**:
- libnova (REQUIRED) - 天文动力学计算库
- cfitsio - FITS 文件格式库
- zlib - 压缩库
- libev - 事件循环库

## 安装方法

使用预编译包安装:
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libindi 2.1.5.1-r1
```

**先安装依赖**:
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libnova 0.14.0
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- cfitsio 4.6.4
```

## 使用示例

启动 INDI 服务器:
```bash
indiserver -v /path/to/driver
```

默认监听端口: 7624

编译 INDI 客户端程序:
```cpp
#include <libindi/baseclient.h>

class MyClient : public INDI::BaseClient {
public:
    MyClient() : INDI::BaseClient() {}
};

int main() {
    MyClient client;
    client.connectServer();
    return 0;
}
```

编译命令:
```bash
clang++ -o my_client my_client.cpp \
    -I$PREFIX/include \
    -L$PREFIX/lib \
    -lindiclient -lnova -lc++_shared \
    -Wl,-rpath,$PREFIX/lib
```

## 平台适配说明

### CMake UNIX 变量问题

HarmonyOS CMake 不识别 `UNIX` 变量，需修改判断条件:
```cmake
# 原始: if(UNIX)
# 修改: if(CMAKE_HOST_UNIX OR UNIX OR NOT WIN32)
```

### select.h 头文件缺失

`fd_set` 和 `struct timeval` 需要显式包含:
```c
#include <sys/select.h>
#include <sys/time.h>
```

## 许可证

GPL-2.0+

## 项目主页

- GitHub: https://github.com/indilib/indi
- 官网: https://indilib.org/

## 相关软件

- libnova: 天文动力学计算库（依赖）
- Stellarium: 天文软件（使用 INDI）
- KStars: KDE 天文软件（使用 INDI）