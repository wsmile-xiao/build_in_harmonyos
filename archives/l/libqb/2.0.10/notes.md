# libqb 2.0.10 编译笔记

## 编译信息

- 软件名: libqb
- 版本: 2.0.10
- 构建系统: autotools
- 编译日期: 2026-06-11
- 状态: 编译成功

## 编译流程

### 1. 源码获取

从 GitHub ClusterLabs 下载：
```
https://github.com/ClusterLabs/libqb/releases/download/v2.0.10/libqb-2.0.10.tar.xz
```

### 2. 平台适配

#### 问题 1: config.guess 无法识别 HarmonyOS

原始 config.guess 不支持 HarmonyOS 系统，导致 configure 失败。

**解决方案**: 修改 build-aux/config.guess 和 build-aux/config.sub，添加 HarmonyOS 支持。

补丁内容：
- 0001-config.guess-harmonyos.patch: 修改 config.guess 识别 HarmonyOS
- 0002-config.sub-harmonyos.patch: 修改 config.sub 支持 linux-ohos target

#### 问题 2: config.status 临时目录权限问题

config.status 使用 `umask 077 && mktemp -d` 创建临时目录，导致目录权限过于严格（只有 owner 可写），而进程的 primary GID 与目录的 GID 不匹配，无法在其中创建文件。

**解决方案**: 修改 config.status 中的 umask 077 为 umask 000，允许组用户写入。

### 3. Configure 参数

```
./configure --prefix=/storage/Users/currentUser/usr/local --disable-man
```

注意: --disable-examples 参数不被支持，examples 和 tests 会被编译但不会安装。

### 4. 依赖

- glib-2.0 >= 2.0 (已安装: 2.88.0)
- libsystemd (可选，未安装)
- check >= 0.9.4 (用于测试，已安装)

### 5. 编译产物

- libqb.so.100.3.3 (共享库)
- libqb.a (静态库)
- libqb.pc (pkg-config 文件)
- qb-blackbox (工具)
- 头文件: qbhdb.h, qblist.h, qbdefs.h, qbatomic.h, qbloop.h, qbrb.h, qbutil.h, qbarray.h, qbipcc.h, qbipcs.h, qbipc_common.h, qblog.h, qbconfig.h, qbmap.h

### 6. 安装位置

- 库文件: ~/usr/local/lib/
- 头文件: ~/usr/local/include/qb/
- pkg-config: ~/usr/local/lib/pkgconfig/
- 工具: ~/usr/local/sbin/

## 关键发现

### 平台问题

1. **umask + setgid 目录**: 当目录设置了 setgid 位（继承父目录 GID），使用 umask 077 创建子目录会导致进程无法写入，即使进程属于相同的 supplementary group。

2. **HarmonyOS 平台检测**: 需要在 config.guess 中添加 HarmonyOS 特殊处理，因为 `uname -s` 返回 "HarmonyOS" 而不是 "Linux"。

## 知识提取

- [E007] config.guess 平台适配问题
- [新发现] umask + setgid 目录权限问题

---

**编译结束**: 2026-06-11 18:58
**最终状态**: success