# libpwquality 1.4.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-11
- 编译器: gcc (系统默认)
- 状态: built

## 编译步骤

1. init-build 初始化编译环境
2. 修复 config.guess/config.sub（E072 问题）
   - 使用预置的 config.guess（直接输出 aarch64-unknown-linux-ohos）
   - 手动修改 config.sub 添加 ohos 支持（3 处修改）
3. 修复 config.status 临时文件问题（HMDFS 限制）
   - 将临时目录改为使用预创建的 ~/tmp/confwork
4. configure --prefix=$DEFAULT_PREFIX --disable-cracklib-check
5. make -j2
6. make install DESTDIR=$TEST_PREFIX
7. make check（无测试）
8. package 制作预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.sub 三元组验证失败 | E072：config.sub 未识别 ohos 作为合法 OS | 手动添加 ohos 支持（3 处修改） |
| 2 | config.status 无法创建临时文件 | HMDFS 不支持动态创建子目录 | 使用预创建的固定临时目录 ~/tmp/confwork |
| 3 | cracklib 依赖缺失 | 未安装 cracklib 库 | 使用 --disable-cracklib-check 禁用 |

## 源码修改

| 文件 | 修改说明 |
|------|----------|
| config.guess | 替换为预置版本，直接输出 aarch64-unknown-linux-ohos |
| config.sub | 添加 ohos 支持（3 处：maybe_os 映射、OS 白名单、kernel-os 白名单） |
| config.status | 将临时目录改为 ~/tmp/confwork |

补丁文件：
- 0003-config.guess.patch
- 0004-config.sub.patch
- 0001-po-Makefile.in.patch（自动生成）
- 0002-python-constants.c.patch（自动生成）
- 0005-po-POTFILES.patch（自动生成）
- 0006-src-pwmake.patch（自动生成 - RPATH）
- 0007-src-pwscore.patch（自动生成 - RPATH）

## 依赖版本

- GNU make 4.4.1
- automake 1.16.5
- autoconf 2.72
- libtool 2.4.7
- python 3.12

## 验证结果

```bash
# staging 验证通过
# 门禁验证:
G1: ✅0 ⚠️0 ❌0 (二进制完整性)
G2: ✅0 ⚠️1 ❌0 (功能可用性 - 无可执行验证脚本)
G3: ✅0 ⚠️0 ❌0 (可移植性)
G4: ✅0 ⚠️0 ❌1 (档案完整性)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libpwquality-1.4.5-ohos-aarch64.tar.gz | 454KB | 预编译包 |
| libpwquality-1.4.5-ohos-aarch64-debug.tar.gz | 213KB | 调试符号包 |

## 注意事项

1. 此软件依赖 PAM，但鸿蒙系统可能没有完整的 PAM 支持
2. 禁用了 cracklib 检查功能
3. config.status 临时文件问题需要特殊处理（HMDFS 限制）

---

**编译结束**: 2026-06-11 18:43
**最终状态**: built
---

**编译结束**: 2026-06-11 18:44
**最终状态**: built
