# NymphRPC

NymphRPC 是一个轻量级的 C++ RPC（远程过程调用）库，专为微服务和分布式应用程序设计。

## 功能概述

- **轻量级设计**：最小化依赖，适合嵌入式和资源受限环境
- **异步通信**：支持异步 RPC 调用，不阻塞主线程
- **类型安全**：使用 C++ 类型系统确保接口安全性
- **跨平台**：支持 Linux、Windows、MacOS，现已适配 OpenHarmony

## OHOS 适配要点

### 关键问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `nullptr_t` 未定义 | HarmonyOS SDK libc++ bug + musl stddef.h 缺失 | 创建 `ohos_fix.h` 预包含头 |
| `__promote` 未声明 | libc++ `<cmath>` 缺少内部模板包含 | 包含 `__type_traits/promote.h` |
| musl 头文件干扰 | `~/usr/local/include/` 中残留 musl 头文件 | 移除干扰头文件 |
| C++14 不兼容 | HarmonyOS SDK libc++ 需要 C++17 | 升级编译标准 |

### 修复头文件

编译时需要使用 `-include ~/usr/local/include/preinclude/ohos_fix.h` 选项：

```cpp
// ohos_fix.h 内容摘要
#ifndef __OHOS_FAMILY__
#define __OHOS_FAMILY__ 1
#endif

typedef decltype(nullptr) nullptr_t;
#include <__type_traits/promote.h>
```

### 编译命令

```bash
make CXX=clang++ \
    CXXFLAGS="-std=c++17 -include ~/usr/local/include/preinclude/ohos_fix.h \
    -I ~/usr/local/include \
    -I $OHOS_SDK/llvm/include/libcxx-ohos/include/c++/v1"
```

## 依赖关系

```
nymphrpc
  │
  ├── POCO C++ Libraries 1.15.3（必需）
  │   ├── PocoNet
  │   ├── PocoUtil
  │   ├── PocoFoundation
  │   └── PocoJSON
  │   │
  │   └── OpenSSL 3.0.13（可选，POCO 依赖）
```

## 安装使用

### 通过 cmd-pkgs 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- nymphrpc v0.1.1
```

### 手动编译

1. 安装依赖：POCO 1.15.3
2. 下载源码：`https://github.com/MayaPosch/NymphRPC/archive/refs/tags/v0.1.1.tar.gz`
3. 应用补丁：`0001-Makefile.patch`
4. 执行编译命令

## API 使用示例

```cpp
#include <nymphrpc/nymph_listener.h>
#include <nymphrpc/nymph_message.h>

// 定义 RPC 方法
NymphMessage* handle_request(NymphMessage* msg, void* data) {
    // 处理请求并返回响应
    return msg;
}

// 启动服务器
NymphListener listener;
listener.start(5000, handle_request);
```

## 参考资料

- **源码仓库**：https://github.com/MayaPosch/NymphRPC
- **作者**：Maya Posch
- **许可证**：MIT License