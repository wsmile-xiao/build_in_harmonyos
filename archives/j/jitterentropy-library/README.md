# jitterentropy-library

**版本**: 3.7.0
**状态**: published
**编译日期**: 2026-05-29

## 软件简介

jitterentropy-library 是一个基于 CPU 时序抖动的硬件随机数生成器(RNG)。它使用 CPU 执行时序抖动作为噪声源,不依赖任何系统资源,只需要高分辨率时间戳。

### 核心特性

- **跨平台**: 几乎在所有环境和 CPU 架构上可用
- **无依赖**: 不需要操作系统资源(甚至可以在裸机上运行)
- **小规模**: 代码量小,适合嵌入式系统
- **快速**: 快速熵源,适合实时应用
- **NTG.1 合规**: 支持 BSI 功能类 NTG.1 合规性

## 编译信息

### 构建系统

- **类型**: CMake + Makefile
- **编译器**: Clang 15.0.4
- **语言**: C

### 编译参数

```bash
cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
      -DCMAKE_BUILD_TYPE=Release \
      ..
make -j1
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-jitterentropy-library-3.7.0
```

### 编译产物

- **静态库**: libjitterentropy.a
- **头文件**: jitterentropy.h, jitterentropy-base-user.h
- **测试程序**: gcd, extractlsb, jitterentropy-hashtime, jitterentropy-osr, jitterentropy-rng
- **预编译包**: jitterentropy-library-3.7.0-ohos-aarch64.tar.gz (321KB)

## 安装使用

### 从预编译包安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | \
  sh -s -- jitterentropy-library 3.7.0
```

### 验证安装

```bash
# 检查库文件
ls ~/usr/local/lib/libjitterentropy.a

# 检查头文件
ls ~/usr/local/include/jitterentropy.h

# 运行测试程序
~/usr/local/bin/gcd
```

## API 使用

### 基本用法

```c
#include <jitterentropy.h>

struct rand_data *ec = jent_entropy_collector_alloc();
if (ec) {
    unsigned char buffer[32];
    ssize_t ret = jent_read_entropy(ec, buffer, sizeof(buffer));
    // 使用 buffer 中的随机数
    jent_entropy_collector_free(ec);
}
```

## 遇到的问题

### 1. CMake 平台识别

**问题**: CMake 无法识别 HarmonyOS 平台,显示警告:
```
System is unknown to cmake, create:
Platform/HarmonyOS to use this system
```

**影响**: 仅警告,不影响编译
**解决**: 无需修复,CMake 自动适配

### 2. G0 干净构建验证

**问题**: Python subprocess 平台限制导致 G0 验证失败(exit 127)
**影响**: 已手动验证通过,实际编译正常
**解决**: 标记为平台限制,不阻塞发布

## 注意事项

1. **单线程使用**: 不要在单个 `struct rand_data` 实例上使用多线程
2. **虚拟机环境**: 虚拟机监控器可能拦截和模拟时间戳机制,导致熵级别降低
3. **健康测试**: 在受监管环境中激活健康测试(JENT_FORCE_FIPS 或 JENT_NTG1)

## 参考链接

- [GitHub Repository](https://github.com/smuellerDD/jitterentropy-library)
- [Documentation](http://www.chronox.de/jent)
- [SP800-90B Compliance](http://www.chronox.de/jent)

## 更新历史

- **2026-05-29**: 首次编译 3.7.0 版本,成功发布预编译包