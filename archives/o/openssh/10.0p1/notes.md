# openssh 10.0p1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 下载源码
wget https://cdn.openbsd.org/pub/OpenBSD/OpenSSH/portable/openssh-10.0p1.tar.gz

# 解压到 ~/builds/openssh-10.0p1.work

# 配置环境变量（HMDFS 限制）
export TMPDIR=/storage/Users/currentUser/tmp
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
export CFLAGS="-I/storage/Users/currentUser/usr/local/include"
export LDFLAGS="-L/storage/Users/currentUser/usr/local/lib"
export LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib

# 运行 configure
./configure --prefix=/storage/Users/currentUser/usr/local --with-ssl-dir=/storage/Users/currentUser/usr/local

# 编译
make -j1

# 安装
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure umask 077 失败 | HMDFS 不支持严格权限模式 | 修改 configure: `sed -i 's/umask 077/umask 022/g' configure` |
| 2 | getspnam 函数未定义 | 鸿蒙无 shadow password API | 禁用 HAVE_SHADOW_H in config.h |
| 3 | sockaddr_storage 重定义 | SDK linux/socket.h 与 sys/socket.h 冲突 | 使用 #ifdef __OHOS__ 守卫，替换 linux/if.h 为 net/if.h |
| 4 | seccomp-filter sandbox 编译失败 | SDK linux/net.h 头文件冲突 | 禁用 SANDBOX_SECCOMP_FILTER，使用 SANDBOX_NULL |

## 源码修改

### 补丁文件
- configure: umask 077 → umask 022
- config.h: 禁用 HAVE_SHADOW_H, 启用 SANDBOX_NULL
- openbsd-compat/port-net.c: OHOS 头文件冲突守卫
- sandbox-seccomp-filter.c: OHOS 头文件冲突守卫（已禁用）

### 运行时依赖
- 需要 `LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib` 指向 OpenSSL 库

## 依赖版本

| 软件 | 版本 | 来源 |
|------|------|------|
| OpenSSL | 3.5.6 | Conan 包 (静态链接) |
| zlib | 系统 | musl |

## 验证结果

```bash
# 二进制文件检查
file ~/usr/local/bin/ssh
# ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

# 依赖检查
readelf -d ~/usr/local/bin/ssh | grep NEEDED
# Shared library: [libc.so]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ssh | 1.4MB | SSH 客户端 |
| sshd | 748KB | SSH 服务端 |
| ssh-keygen | 727KB | 密钥生成工具 |
| scp | 313KB | 文件复制工具 |
| sftp | 321KB | SFTP 客户端 |

## 注意事项

1. 运行时需设置 `LD_LIBRARY_PATH` 或将 OpenSSL 库复制到系统库目录
2. `/var/empty` 目录需手动创建或修改 sshd 配置
3. 鸿蒙系统执行二进制可能需要特殊权限配置
---

**编译结束**: 2026-07-22 21:55
**最终状态**: built
