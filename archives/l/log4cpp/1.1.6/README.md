# log4cpp 1.1.6 — OpenHarmony 预编译包

## 软件信息

- **名称**: log4cpp
- **版本**: 1.1.6
- **描述**: C++ logging library patterned after log4j
- **许可证**: LGPL-2.1
- **构建系统**: autotools
- **平台**: aarch64-unknown-linux-ohos (OpenHarmony)

## 功能特性

- 多级日志级别（DEBUG、INFO、WARN、ERROR、FATAL 等）
- 线程安全日志记录
- 自定义日志格式
- 多种输出方式：
  - 控制台输出
  - 普通文件输出
  - 按大小滚动文件
  - 按日期滚动文件
  - syslog 输出
  - IDSA 输出
- 无外部依赖

## 编译配置

- **编译器**: clang 15.0.4 / clang++ 15.0.4
- **配置选项**: `--prefix=/storage/Users/currentUser/usr/local --disable-shared`
- **说明**: 因 OpenHarmony 平台不支持 RUNPATH，按铁律 R4 使用 `--disable-shared` 编译为纯静态库

## 预编译包内容

```
bin/log4cpp-config          — 配置脚本（查询版本、编译参数）
include/log4cpp/*.hh        — 42 个 C++ 头文件
include/log4cpp/threading/*.hh — 6 个线程相关头文件
lib/liblog4cpp.a            — ELF64 aarch64 静态库 (1,018,084 字节)
lib/liblog4cpp.la           — libtool 影文件
lib/pkgconfig/log4cpp.pc    — pkg-config 配置文件
share/aclocal/log4cpp.m4    — autoconf 宏文件
```

## 使用方法

### 编译链接

```bash
# 使用 log4cpp-config
g++ -o myapp myapp.cpp $(log4cpp-config --libs --cflags)

# 使用 pkg-config
g++ -o myapp myapp.cpp $(pkg-config --libs --cflags log4cpp)

# 直接指定
g++ -o myapp myapp.cpp -I$PREFIX/include -L$PREFIX/lib -llog4cpp
```

### 基本示例

```cpp
#include <log4cpp/Category.hh>
#include <log4cpp/OstreamAppender.hh>

int main() {
    log4cpp::OstreamAppender* appender =
        new log4cpp::OstreamAppender("console", &std::cout);
    log4cpp::Category& root = log4cpp::Category::getRoot();
    root.addAppender(appender);
    root.info("Hello, log4cpp!");
    log4cpp::Category::shutdown();
    return 0;
}
```

## 测试结果

全部 12 个测试通过（详见 test-report.md）：

| 测试 | 结果 |
|------|------|
| testCategory | ✅ PASS |
| testFixedContextCategory | ✅ PASS |
| testNDC | ✅ PASS |
| testPattern | ✅ PASS |
| testErrorCollision | ✅ PASS |
| testPriority | ✅ PASS |
| testFilter | ✅ PASS |
| testProperties | ✅ PASS |
| testSimpleConfig | ✅ PASS |
| testPropertyConfig | ✅ PASS |
| testRollingFileAppender | ✅ PASS |
| testDailyRollingFileAppender | ✅ PASS |

## 平台适配说明

1. **E007/E072**: config.guess 和 config.sub 需补丁以识别 `aarch64-unknown-linux-ohos` 三元组
2. **E080**: HMDFS 上 `umask 077 && mktemp -d` 创建的临时目录不可写，需移除 umask
3. **R4**: OpenHarmony 不支持 RUNPATH，必须 `--disable-shared` 编译为静态库

## 原始上游信息

- **上游源码**: https://sourceforge.net/projects/log4cpp/
- **GitHub**: https://github.com/log4cpp/log4cpp
- **许可证**: LGPL-2.1（见源码 COPYING 文件）