# libverto 0.3.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-05
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 初始化编译环境
```bash
python3 ~/.opendesk/apps/skills/resources/openharmony-compile-agent/scripts/ohc-run.py init-build libverto 0.3.2
```

2. 配置
```bash
./configure --prefix=/storage/Users/currentUser/usr/local
```

3. 编译
```bash
make -j1
```

4. 安装
```bash
make install DESTDIR=/storage/Users/currentUser/test-install-libverto-0.3.2
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| E007 | config.guess无法识别HarmonyOS | 缺少系统识别分支 | 添加HarmonyOS case分支 |
| E072 | config.sub不支持ohos三元组 | 缺少操作系统白名单 | 添加3处修改（OS白名单等） |
| E011 | configure umask权限问题 | HMDFS UID映射限制 | 修改umask 077为022 |

## 源码修改

### patches/0001-config.guess.patch
添加 HarmonyOS 系统识别，输出 `aarch64-unknown-linux-ohos`

### patches/0002-config.sub.patch
添加 ohos 操作系统白名单（3处修改）

### patches/0003-configure.patch
修改 umask 077 为 umask 022

## 依赖版本

- glib 2.84.0
- libevent 2.1.12
- automake 1.16.5
- autoconf 2.72
- libtool 2.4.7

## 验证结果

```bash
pkg-config --modversion libverto
# 0.3.2

ls ~/usr/local/lib/libverto*.so*
# libverto.so.1.0.0
# libverto-glib.so.1.0.0
# libverto-libevent.so.1.0.0
```