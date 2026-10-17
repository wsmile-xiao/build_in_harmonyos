# libngtcp2 1.22.1 编译笔记

## 编译时间
- 开始: 2026-05-19 22:45
- 结束: 2026-05-20 11:06

## 状态
SUCCESS - 编译成功，质量门禁通过

## 遇到的问题

### 问题 1: config.guess 无法识别 HarmonyOS
**错误**: `./config.guess: unable to guess system type`
**根因**: config.guess 不包含 HarmonyOS 检测逻辑
**解决方案**: 添加 HarmonyOS 检测补丁 (patch 0001)

### 问题 2: HMDFS umask 权限问题 (E011)
**错误**: `./config.status: can't create ./confXXXXXX/subs1.awk: Permission denied`
**根因**: HMDFS 文件系统的 UID 映射机制导致 umask 077 创建的临时目录无法写入
**解决方案**: 修改 configure 中的 umask 077 为 umask 022 (patch 0002)

## 编译命令
```bash
sed -i 's/umask 077/umask 022/g' configure
./configure --prefix=$HOME/usr/local --enable-lib-only --without-openssl
make -j$(nproc)
make install DESTDIR=$HOME/tmp/install/ngtcp2-1.22.1
make check
```

## 测试结果
make check: PASS (1/1)

## 知识图谱匹配
- E011: HMDFS umask 077 权限问题

## 补丁文件
1. 0001-add-harmonyos-detection.patch - 添加 HarmonyOS 系统检测
2. 0002-fix-umask-for-hmdfs.patch - 修复 HMDFS umask 权限问题
---

**编译结束**: 2026-07-21 11:55
**最终状态**: built
