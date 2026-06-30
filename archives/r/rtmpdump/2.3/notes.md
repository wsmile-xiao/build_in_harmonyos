# rtmpdump 2.3 编译笔记

## 编译日期
2026-05-20

## 版本说明
本次编译使用 rtmpdump 2.3 版本。

### 版本获取失败说明
尝试获取 rtmpdump 2.6 版本失败，原因如下：
1. git.ffmpeg.org SSL证书验证失败
2. Git克隆（跳过SSL验证）因系统库冲突失败
3. Cgit snapshot接口返回403 Forbidden
4. GitHub上无镜像仓库

因此使用 2.3 版本作为替代，该版本是唯一可用版本。

## 编译过程

### 环境设置
- 编译器: clang 15.0.4
- OpenSSL: 1.1.1w
- 目标平台: aarch64-unknown-linux-ohos

### 遇到的问题及解决方案

#### 问题1: OpenSSL 1.1+ API变化
**现象**: HMAC_CTX和DH结构体变为opaque，无法直接访问字段

**解决方案**:
- 使用 HMAC_CTX_new/free 替代栈声明
- 使用 DH_get0_p/dh_set0_pqg 等getter/setter函数
- 创建条件编译宏 HMAC_CTX_POINTER 和 DH_USE_GETTER

**受影响文件**:
- librtmp/handshake.h
- librtmp/dh.h
- librtmp/hashswf.c

#### 问题2: 鸿蒙头文件冲突
**现象**: sockaddr_storage结构体重定义冲突

**解决方案**:
- 使用 #ifndef __OHOS__ 跳过 linux/netfilter_ipv4.h 包含
- 使用条件编译跳过 SO_ORIGINAL_DST 相关代码

**受影响文件**:
- rtmpsrv.c
- rtmpsuck.c

## 源码修改清单

| 文件 | 原因 | 方式 |
|------|------|------|
| librtmp/handshake.h | OpenSSL 1.1+ HMAC适配 | 条件编译 |
| librtmp/dh.h | OpenSSL 1.1+ DH适配 | 条件编译 |
| librtmp/hashswf.c | OpenSSL 1.1+ HMAC适配 | 条件编译 |
| rtmpsrv.c | 鸿蒙头文件冲突 | 条件编译跳过 |
| rtmpsuck.c | 鸿蒙头文件冲突 | 条件编译跳过 |

## 编译结果
- 编译成功
- 所有二进制文件可执行
- librtmp库编译成功

## 补丁文件
- 0001-openssl-1.1-handshake.h.patch
- 0002-openssl-1.1-dh.h.patch
- 0003-openssl-1.1-hashswf.c.patch
- 0004-ohos-header-conflict-rtmpsrv.c.patch
- 0005-ohos-header-conflict-rtmpsuck.c.patch
