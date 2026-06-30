# bluez-alsa v4.3.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-29
- 编译器: clang/clang++ (Clang 15.0.4 for OHOS aarch64)
- 状态: built

## 编译步骤

1. init-build 下载源码（GitHub 超时需手动 wget）
2. autoreconf -i 生成 configure 脚本
3. configure --prefix=$DEFAULT_PREFIX --enable-payloadcheck
4. make -j2
5. make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 缺少 pthread_cancel 实现 | musl/OpenHarmony 不提供 pthread_cancel/pthread_setcancelstate | 添加 0005-ohos-pthread-compat.patch，提供 stub 兼容层（#ifdef __OHOS__ 守卫） |
| 2 | HMDFS 上 config.status 临时文件权限问题 | HMDFS umask 077 导致 Permission denied | touch stamp-h1 绕过 config.h 重生成 |
| 3 | autotools 生成的 Makefile 需适配 | 交叉编译环境下链接选项不兼容 | 0001-0004 patches 修改 Makefile/Makefile.am 添加 OHOS 适配 |

## 源码修改

5 个补丁:
- `0001-src-Makefile.patch`: autotools 生成的 Makefile 适配（OHOS-only）
- `0002-src-Makefile.am.patch`: 源码 Makefile.am 修改（#ifdef __OHOS__ 守卫）
- `0003-utils-aplay-Makefile.patch`: aplay 工具 Makefile 适配（OHOS-only）
- `0004-utils-aplay-Makefile.am.patch`: aplay 工具 Makefile.am 修改（#ifdef __OHOS__ 守卫）
- `0005-ohos-pthread-compat.patch`: 新增 OHOS pthread_cancel stub 兼容层

## 依赖版本

- alsa-lib/1.2.12
- bluez/5.79
- dbus/1.15.8
- glib/2.84.0
- sbc/1.5

## 验证结果

- 质量门禁: G1-G3 PASS, G4 FAIL（manifest 缺少 build_system 字段，需修正）
- 无可执行二进制文件（库+配置文件为主）

## 交付物

| 文件 | 说明 |
|------|------|
| bluez-alsa-v4.3.1-ohos-aarch64.tar.gz | aarch64 预编译包 |
| bluez-alsa-v4.3.1-ohos-aarch64-debug.tar.gz | aarch64-debug 预编译包 |

## 注意事项

- OHOS 缺少 pthread_cancel，0005 patch 提供了兼容 stub 实现
- HMDFS 环境下 autotools config.status 有临时文件权限问题
- 补丁均使用 #ifdef __OHOS__ 守卫，不影响上游源码

---

**编译结束**: 2026-05-29 18:26
**最终状态**: built
