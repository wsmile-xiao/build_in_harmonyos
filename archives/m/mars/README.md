# mars

腾讯 Mars — 微信背后的跨平台基础组件库。本归档为 **Comm（公共组件）+ Xlog（高性能日志）+ 内嵌 boost 1.60 子集** 的 HarmonyOS PC (aarch64) 适配。

## 版本

- 1.3.0（上游最后正式 tag，2019）：`libmars-comm.a` / `libmars-xlog.a` / `libmars-boost.a` 三个静态库 + `include/mars/` 头文件树。

## 使用

```cmake
find_package(mars CONFIG REQUIRED)
target_link_libraries(app PRIVATE mars::mars)   # mars-comm + mars-xlog + mars-boost + zlib + pthread
```

```cpp
#include "mars/log/appender.h"          // xlog
#include "mars/comm/xlogger/xlogger.h"  // xlogger 宏
#include "mars/comm/autobuffer.h"       // comm 基础组件

appender_open(kAppednerAsync, "/path/to/logs", "myapp", "");
xlogger_SetLevel(kLevelInfo);
xinfo2("hello %_", 42);
```

## 适配说明

见 `1.3.0/notes.md`：musl 无 pthread_cancel（SIGUSR2 分支）、sysctl 裁剪、新增 comm/ohos 平台层（getNetInfo UDP 探测、ConsoleLog→xlogger）、zlib 依赖（log_buffer deflate）。
