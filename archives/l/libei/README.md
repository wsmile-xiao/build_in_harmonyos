# libei

## 简介
libei 是 freedesktop.org 的输入仿真协议（Emulated Input）参考实现，
为远程桌面、输入注入等场景提供进程间输入事件传输协议：

- **libei**：客户端库（sender/receiver 双模式）——应用侧发送或接收输入事件
- **libeis**：服务端库——合成器/会话侧接收或下发输入事件
- **liboeffis**：RemoteDesktop portal DBus 助手（OHOS 适配已裁剪）

协议基于 Unix socket + 自有 brei 序列化格式（XML 协议定义经 ei-scanner
生成 C 绑定），支持 pointer/keyboard/touch/scroll/button/region 等
输入能力与 seat/device/region 语义。

## OHOS 适配
- **构建系统**: meson
- **裁剪**: liboeffis（sd-bus 依赖 OHOS 无）；核心 libei/libeis 零外部依赖
- **测试**: munit 单元/集成测试 vendor 内嵌（CI 离线可跑）；
  pytest 协议套件（本地实测）
- **平台补丁**: tmpfile() → $TMPDIR 兜底（musl /tmp 只读）
- 上游测试实测 175/176（socket_overflow 受 OHOS socket 缓冲区语义影响豁免）

## 依赖
核心库无运行时依赖。工具链可选：
- libxkbcommon（eis-demo-server --layout / ei-demo-client 键盘映射）
- libevdev（eis-demo-server --uinput / ei-debug-events 事件名）

## 使用
```cmake
find_package(libei REQUIRED)
target_link_libraries(app libei::libei)   # libei.so + libeis.so
```
头文件：`#include <libei.h>` / `#include <libeis.h>`（libei-1.0 目录）
