# BIRD 3.1.6 鸿蒙适配笔记

## 软件简介
BIRD (BIRD Internet Routing Daemon) 是动态 IP 路由守护进程，支持 BGP、OSPF、RIP、Babel 等路由协议。
核心可执行文件：bird（守护进程）、birdcl（简易 CLI 客户端）、birdc（ncurses CLI 客户端）。

## 源码
- URL: https://gitlab.nic.cz/labs/bird/-/archive/v3.1.6/bird-v3.1.6.tar.gz
- 格式: tar.gz (GitLab archive, 非 release tarball)
- 构建系统: autotools (需要 autoconf + autoheader 生成 configure)

## 适配修改

### 1. 源码提取修复
- **问题**: init-build 的嵌套源码检测逻辑将 `client/` 子目录误识别为源码根目录，只提取了 client 部分
- **修复**: 手动解压完整 tarball 到 .orig 和 .work 目录

### 2. config.guess/config.sub 补丁 (E007)
- **问题**: config.guess (v2018-03-08) 不识别 HarmonyOS 平台
- **修复**:
  - 使用 `patch-autotools-ohos.pl` 添加 HarmonyOS 检测
  - 手动修复 config.guess: HarmonyOS case 缺少 `echo "$GUESS"; exit ;;` (只设置了 GUESS 变量但未输出和退出)
  - 手动修复 config.sub: 添加 `linux-ohos*` 到 OS 模式匹配列表和验证列表，添加 `-linux-ohos*` case 防止被 `-linux*` 的 `linux→linux-gnu` 转换规则错误处理

### 3. autoconf/autoheader 生成
- **问题**: tarball 是 GitLab archive，只包含 configure.ac，无预生成 configure 脚本
- **修复**: 运行 `autoheader` 生成 `sysdep/autoconf.h.in`，运行 `autoconf` 生成 `configure`

### 4. E114 HMDFS 临时目录权限修复
- **问题**: config.status 使用 mktemp -d 创建的临时目录在 HMDFS 上权限为 drwx--S---，无法在其中创建文件
- **修复**: 预创建固定临时目录，修改 configure 中 `ac_tmp=$tmp` 为 `ac_tmp=$TMPDIR/bird-config-fixed`

### 5. OHOS sysroot 头文件路径
- **问题**: OHOS SDK sysroot 包含 Linux 内核头文件但不在默认搜索路径
- **修复**: 设置 CFLAGS 添加 sysroot include 路径：
  - `-I$SYSROOT/usr/include` (linux/ 头文件)
  - `-I$SYSROOT/usr/include/aarch64-linux-ohos` (asm/ 头文件)
- SYSROOT: /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot

### 6. sockaddr_storage 重定义冲突
- **问题**: OHOS sysroot 的 `linux/socket.h` 定义 `struct sockaddr_storage`，与 `sys/socket.h` 冲突
- **影响**:
  - configure.ac 的 AC_CHECK_HEADER 检查失败（include 了 sys/socket.h）
  - netlink.c 编译失败（同时 include sys/socket.h 和 linux/rtnetlink.h→linux/netlink.h→linux/socket.h）
- **修复**:
  - configure.ac: 移除 AC_CHECK_HEADER 第四参数中的 `#include <sys/socket.h>`
  - 创建 `tools/ohos_compat.h`: 定义 `__kernel_sa_family_t` 和 `_K_SS_MAXSIZE`，然后定义 `_UAPI_LINUX_SOCKET_H` 跳过 linux/socket.h
  - Makefile CPPFLAGS 添加 `-include tools/ohos_compat.h`

### 7. ncurses 缺失 → --disable-client
- **问题**: birdc 客户端需要 ncurses 库，系统无 ncurses 且 Conan center 无法在 OHOS 构建
- **修复**: 使用 `--disable-client` 禁用 birdc（ncurses 客户端），birdcl（简易客户端）仍可构建
- **备注**: conan 配方中应添加 ncurses 作为可选依赖

## 编译参数
```
./configure --prefix=$DEFAULT_PREFIX --disable-client
make -j2
make install DESTDIR=$TEST_PREFIX
make check
```

## 环境变量
```
CC=clang
RANLIB=llvm-ranlib
AR=llvm-ar
CFLAGS=-I$SYSROOT/usr/include -I$SYSROOT/usr/include/aarch64-linux-ohos
LDFLAGS=-L$SYSROOT/usr/lib/aarch64-linux-ohos
CPPFLAGS += -include tools/ohos_compat.h
TMPDIR=/storage/Users/currentUser/tmp
```

## 编译结果
- bird (2.3MB, ELF 64-bit arm64, 动态链接 musl libc)
- birdcl (60KB, ELF 64-bit arm64)
- birdc: 未构建 (--disable-client)

## 测试结果
- make check: 20/20 测试全部通过 [OK]
- bird --version: "BIRD version 3.1.6" ✅
- birdcl: 可执行，显示用法信息 ✅

## 路由协议支持
aggregator bfd babel bgp l3vpn ospf pipe radv rip rpki static mrt bmp
---

**编译结束**: 2026-07-06 19:13
**最终状态**: built
