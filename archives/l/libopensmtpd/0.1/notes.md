# libopensmtpd 编译笔记

**软件**: libopensmtpd
**版本**: 0.1 (from GitHub murty2/libopensmtpd main branch)
**构建系统**: Makefile.gnu (自定义 Makefile)
**编译日期**: 2026-06-11

---

## 编译过程

### 依赖处理

**缺失依赖**: libevent

**解决方案**:
- 从 GitHub 克隆 libevent 2.1.12-stable
- 使用 autotools 编译安装到 ~/usr/local
- 禁用 OpenSSL 支持 (--disable-openssl)

### 编译命令

```bash
cd ~/tmp/libevent-2.1.12-stable
git clone --depth=1 --branch=release-2.1.12-stable https://github.com/libevent/libevent.git
autoreconf -fi
./configure --prefix=/storage/Users/currentUser/usr/local --disable-openssl
make
make install

cd /storage/Users/currentUser/builds/libopensmtpd-.work
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
export LOCALBASE=/storage/Users/currentUser/usr/local
export CFLAGS="-I... -I.../openbsd-compat -I$LOCALBASE/include -Wall -Wstrict-prototypes -Wmissing-prototypes -Wmissing-declarations -Wshadow -Wpointer-arith -Wcast-qual -Wsign-compare -fPIC -DNEED_RECALLOCARRAY=1 -DNEED_STRLCAT=1 -DNEED_STRLCPY=1 -DNEED_STRTONUM=1"
make -f Makefile.gnu LOCALBASE=$LOCALBASE CFLAGS="$CFLAGS" LDLIBS="-levent" LDFLAGS="-L$LOCALBASE/lib -shared -Wl,-soname=libopensmtpd.so.0"
```

### 安装命令

```bash
export DESTDIR=/storage/Users/currentUser/test-install-libopensmtpd-0.1
make -f Makefile.gnu install LOCALBASE=$LOCALBASE DESTDIR=$DESTDIR MANFORMAT=""
```

---

## 遇到的问题

### 1. 缺少 event.h

**错误**: `fatal error: 'event.h' file not found`

**原因**: libevent 未安装

**解决**: 手动编译安装 libevent 2.1.12

### 2. 缺少 sys/tree.h

**错误**: `fatal error: 'sys/tree.h' file not found`

**原因**: Makefile.gnu 的 CFLAGS 未正确包含 openbsd-compat 目录

**解决**: 在 CFLAGS 中添加 `-I.../openbsd-compat`

### 3. 链接错误 - undefined symbol: main

**错误**: `ld.lld: error: undefined symbol: main`

**原因**: 链接器尝试创建可执行文件而不是共享库

**解决**: 在 LDFLAGS 中显式添加 `-shared -Wl,-soname=libopensmtpd.so.0`

### 4. 缺少 mandoc

**错误**: `/bin/sh: mandoc: inaccessible or not found`

**原因**: Makefile.gnu 尝试使用 mandoc 生成手册页

**解决**: 设置 MANFORMAT="" 跳过手册页转换

---

## 产物

**共享库**: libopensmtpd.so.0.1.0
**头文件**: opensmtpd.h
**手册页**: osmtpd_run.3

**依赖**:
- libevent-2.1.so.7
- libc.so

---

## 备注

- 这是一个小型库，用于 OpenSMTPD 的扩展开发
- 源码来自 GitHub murty2/libopensmtpd (fork of imperialat.at/dev/libopensmtpd)
- 无正式版本号，使用 shlib_version 中的 major=0, minor=1
---

**编译结束**: 2026-06-11 14:17
**最终状态**: built
