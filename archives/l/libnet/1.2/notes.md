# libnet 1.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### Phase 0: 源码获取
1. 从 GitHub 克隆源码: `git clone --depth 1 --branch v1.2 https://github.com/libnet/libnet.git`
2. 打包为 tar.gz 格式，排除 .git 目录

### Phase 1: Bootstrap
1. 运行 `autoreconf -W portability -vif` 生成 configure 脚本
2. 手动复制 ltmain.sh 到源码目录（libtoolize 复制路径问题）

### Phase 2: Configure
```bash
./configure --prefix=/storage/Users/currentUser/usr/local
```

Configure 参数:
- `--prefix=/storage/Users/currentUser/usr/local` (R20 DESTDIR 模式)
- 无特殊平台参数

耗时: ~2 分钟

### Phase 3: Make
```bash
make -j1
```

编译成功，生成静态库和动态库。

### Phase 4: Install (DESTDIR 模式)
```bash
make install DESTDIR=/storage/Users/currentUser/test-install-libnet-1.2
```

安装产物:
- bin: libnet-config
- lib: libnet.so.9.0.0, libnet.a, libnet.la
- include: libnet.h, libnet/*.h
- pkgconfig: libnet.pc

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 脚本不存在 | Git 克隆的源码缺少预生成的 configure | 运行 `autoreconf -W portability -vif` |
| 2 | ltmain.sh 找不到 | libtoolize 复制到错误的目录 | 手动复制 `~/usr/local/share/libtool/build-aux/ltmain.sh` |
| 3 | `__int64_t` 类型未定义 | musl libc 不定义 `__int64_t` | 修改 libnet-structures.h，将 `__int64_t` 替换为 `int64_t` |

## 源码修改

### 文件: include/libnet/libnet-structures.h

```c
// 修改前 (第52-54行)
struct libnet_stats
{
    __int64_t packets_sent;
    __int64_t packet_errors;
    __int64_t bytes_written;
};

// 修改后
struct libnet_stats
{
    int64_t packets_sent;
    int64_t packet_errors;
    int64_t bytes_written;
};
```

**原因**: musl libc（鸿蒙系统使用的 C 库）不定义 `__int64_t` 类型，应使用标准的 `int64_t`。

## 依赖版本

无外部依赖，libnet 是独立的网络库。

## 验证结果

```bash
# 检查库文件
ls -la /storage/Users/currentUser/usr/local/lib/libnet.*
# 输出: libnet.so.9.0.0, libnet.a, libnet.la, libnet.so.9, libnet.so

# 检查 pkg-config
pkg-config --modversion libnet
# 输出: 1.2

# 检查头文件
ls /storage/Users/currentUser/usr/local/include/libnet/
# 输出: libnet-asn1.h, libnet-functions.h, libnet-headers.h, libnet-macros.h, libnet-structures.h, libnet-types.h
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libnet-1.2-ohos-aarch64.tar.gz | 1420KB | 预编译包（含动态库、静态库、头文件、pkg-config） |
| libnet-1.2-ohos-aarch64-debug.tar.gz | ~ | 调试符号包 |

## 注意事项

1. **musl libc 类型兼容**: 鸿蒙系统使用 musl libc，某些 GNU 扩展类型（如 `__int64_t`）不存在，需替换为标准类型。
2. **autotools bootstrap**: Git 克隆的源码需要运行 autoreconf 生成 configure 脚本。
3. **libtool ltmain.sh**: 某些情况下 libtoolize 复制路径错误，需手动复制。

---
**编译结束**: 2026-05-21 23:59
**最终状态**: built