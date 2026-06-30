# libnet

## 软件描述

libnet 是一个用于构造和注入网络数据包的 C 库。它提供了一套简单而强大的 API，用于在链路层和网络层创建自定义数据包。

### 主要功能
- 构造各种网络协议数据包（ARP、IP、TCP、UDP、ICMP 等）
- 支持链路层和原始套接字注入
- 提供校验和计算功能
- 跨平台支持

### 官方网站
https://github.com/libnet/libnet

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 | 产物 |
|------|------|----------|--------|------|
| 1.2 | built | 2026-05-21 | 1 | ✅ |

## 编译要点

### 1. musl libc 类型兼容
鸿蒙系统使用 musl libc，不支持 GNU 扩展类型 `__int64_t`。
修改 `include/libnet/libnet-structures.h`，将 `__int64_t` 替换为标准的 `int64_t`。

### 2. autotools bootstrap
Git 克隆的源码缺少预生成的 configure 脚本，需运行 `autoreconf -W portability -vif`。

### 3. 配置选项
无特殊平台参数，仅使用 `--prefix=$DEFAULT_PREFIX`。

### 4. 无外部依赖
libnet 是独立的网络库，不依赖其他第三方库。

## 补丁说明

### 0001-fix-int64-type.patch
**用途**: 修复 musl libc 类型兼容问题
**文件**: include/libnet/libnet-structures.h
**修改**: 将 `__int64_t` 替换为 `int64_t`（第52-54行）

## 使用方法

### 通过 pkg-config 编译
```bash
pkg-config --cflags --libs libnet
```

### 示例代码
```c
#include <libnet.h>

int main() {
    libnet_t *l = libnet_init(LIBNET_RAW4, NULL, NULL);
    if (l == NULL) {
        fprintf(stderr, "libnet_init failed\n");
        return 1;
    }
    
    // 构造数据包...
    
    libnet_destroy(l);
    return 0;
}
```

## 注意事项

- 鸿蒙系统需要 root 权限才能使用原始套接字
- 部分网络功能可能需要特定的系统配置