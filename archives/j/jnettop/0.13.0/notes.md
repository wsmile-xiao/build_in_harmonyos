# jnettop 0.13.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 1. 在~/tmp目录编译（绕过HMDFS限制）
mkdir -p ~/tmp/jnettop-build
cd ~/tmp/jnettop-build
cp -r ~/builds/jnettop-0.13.0/* .

# 2. 修改configure umask设置
sed -i 's/umask 077/umask 022/g' configure

# 3. 设置环境变量
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig"
export CFLAGS="-I$HOME/usr/local/include"
export LDFLAGS="-L$HOME/usr/local/lib"
export LD_LIBRARY_PATH="$HOME/usr/local/lib"

# 4. Configure
./configure --prefix=/storage/Users/currentUser/usr/local

# 5. Make
make -j2

# 6. Install to staging
make install DESTDIR=/storage/Users/currentUser/test-install-jnettop-0.13.0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libpcap链接失败 | Alpine预编译包缺少ether_hostton符号 | 手动编译libpcap 1.10.5 |
| 2 | sockaddr_storage重复定义 | linux/socket.h与sys/socket.h冲突 | 定义_UAPI_LINUX_SOCKET_H宏 |
| 3 | configure临时文件创建失败 | HMDFS文件系统限制 | 在~/tmp目录编译+修改umask |

## 源码修改

### libpcap补丁 (libpcap-libpcap-1.10.5/pcap-linux.c)

```c
/* HarmonyOS: avoid sockaddr_storage redefinition */
#define _UAPI_LINUX_SOCKET_H
typedef unsigned short __kernel_sa_family_t;
#include <linux/if.h>
... 其他linux头文件 ...
#undef _UAPI_LINUX_SOCKET_H
```

## 依赖版本

- libpcap 1.10.5 (手动编译)
- ncurses 6.4 (预编译包)
- glib-2.0 2.88.0 (系统预装)

## 验证结果

```bash
$ file jnettop
jnettop: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ ls -la ~/test-install-jnettop-0.13.0/storage/Users/currentUser/usr/local/bin/
-rwxrwx--- 2730496 jnettop
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| jnettop | 2.7MB | 主程序 |
| jnettop.8 | 6KB | man手册 |
| jnettop-lookup-nmb | 1KB | NetBIOS查询辅助脚本 |

## 注意事项

1. **运行时库路径**: 需要设置`LD_LIBRARY_PATH=$HOME/usr/local/lib`
2. **网络权限**: 需要root或CAP_NET_RAW权限捕获流量
3. **HMDFS限制**: G0干净构建验证需要在标准Linux环境重新运行

---

**编译结束**: 2026-06-12 10:56
**最终状态**: built（待验证和打包）