# librelp 1.12.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-11
- 编译器: gcc (clang 15.0.4)
- 状态: published

## 编译步骤

1. 源码下载：https://download.rsyslog.com/librelp/librelp-1.12.0.tar.gz
2. 修复 config.guess/config.sub：
   - 使用 patch-autotools-ohos.pl 打补丁（识别 HarmonyOS）
   - 手动修改 config.sub 添加 linux-ohos* 和 ohos* 支持（修复 E072）
3. 重新生成 configure（autoreconf -fvi）
4. configure --prefix=/storage/Users/currentUser/usr/local
5. make -j2
6. make install DESTDIR=/storage/Users/currentUser/test-install-librelp-1.12.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统 | HarmonyOS 未识别 | 使用 patch-autotools-ohos.pl |
| 2 | config.sub 拒绝 linux-ohos | E072: kernel-os 白名单缺少 | 手动修改 config.sub 添加 linux-ohos* |
| 3 | configure 失败 (Permission denied) | config.status 使用 ./confXXXXXX 临时目录失败 | autoreconf -fvi 重新生成 configure |
| 4 | 缺少 openssl 依赖 | PKG_CONFIG_PATH 未设置 | export PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig |

## 源码修改

修改文件：
- config.guess: 添加 HarmonyOS 识别
- config.sub: 添加 linux-ohos* 和 ohos* 到 kernel-os 白名单（第 145 行和第 1781 行）

## 依赖版本

- openssl: 已安装（系统）
- gnutls: 已安装（系统）

## 验证结果

```bash
# 门禁检查
G1: PASS (二进制完整性)
G2: PASS (功能可用性) ⚠️1 (无二进制可执行文件)
G3: PASS (可移植性)
G4: PASS (档案完整性)
总体: PASS

# 预编译包
librelp-1.12.0-ohos-aarch64.tar.gz: 9838067 bytes (9.4MB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| librelp-1.12.0-ohos-aarch64.tar.gz | 9838067 bytes (9.4MB) | 预编译包 |
| librelp-1.12.0-ohos-aarch64-debug.tar.gz | 8061152 bytes (7.7MB) | 调试符号包 |

## 注意事项

1. librelp 是库文件，无可执行二进制文件，G2 门禁会有警告
2. 需要 openssl 和 gnutls 依赖
---

**编译结束**: 2026-06-11 18:12
**最终状态**: built
