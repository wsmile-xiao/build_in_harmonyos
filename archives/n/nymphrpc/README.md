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
| C++14 不兼容 | HarmonyOS SDK libc++ 需要 C++17 | 通过 Conan profile 的 compiler.cppstd=17 传入 |
| make jobserver 失败 | SELinux 禁 FIFO（HMDFS） | make 以 `-j1` 单线程执行 |

### 构建方式

本库通过 Conan recipe（`conanfile.py`）管理构建，依赖由 Conan 解析：

1. **依赖管理**：POCO C++ Libraries 1.15.3（PocoNet/PocoUtil/PocoFoundation/PocoJSON）由 Conan 自动获取与链接，无需手动安装。
2. **编译器与标准**：使用 Conan profile 指定的 clang++（aarch64-unknown-linux-ohos），构建时传入 `-std=c++17`；编译器与归档器从 Conan conf `tools.build:compiler_executables`（dict）读取。
3. **include 路径**：POCO 与 libc++ include 路径由 conanfile.py 自动拼接（libc++ 路径通过 `_libcxx_include()` 从 OHOS SDK 自动发现）。
4. **无应用补丁**：conandata.yml 无 patches 段；官方 v0.1.1/patches/0001-Makefile.patch 为手工编译时代遗留产物，文件保留但不被引用。

### 编译命令（Conan 方式）

```bash
conan create archives/n/nymphrpc/v0.1.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

> 仓库内实际构建入口为 `ci/conan/build_and_test.sh`，会执行 conan create 并运行消费测试。

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

1. 安装依赖：POCO 1.15.3（PocoNet/PocoUtil/PocoFoundation/PocoJSON）
2. 下载源码：`https://github.com/MayaPosch/NymphRPC/archive/refs/tags/v0.1.1.tar.gz`
3. 执行 `make lib`，指定 CXX/AR，并传入 POCO 与 libc++ include 路径及 `-std=c++17`（构建细节见 `conanfile.py`）

> 推荐直接使用 Conan recipe 构建，Conan 自动管理 POCO 依赖、include 路径与 C++17 标准。

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
- **许可证**：BSD-3-Clause
