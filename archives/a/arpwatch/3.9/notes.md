# arpwatch 3.9 编译笔记

## 编译环境
- 日期: 2026-06-18
- 平台: OpenHarmony (OHOS) aarch64
- 构建系统: autotools (手动模式B)
- 编译器: cc (clang)
- 目标: aarch64-unknown-linux-musl

## 依赖
- libpcap 1.10.5 ✓ 已安装
- libresolv ✓ 系统提供

## 编译流程

### Step 1: 初始化
- 源码下载: https://ee.lbl.gov/downloads/arpwatch/arpwatch-3.9.tar.gz
- 解压位置: ~/builds/arpwatch-3.9.work

### Step 2: 编译（遇到多个问题）

#### 问题1: config.guess无法识别HarmonyOS
- **原因**: HarmonyOS是新系统，config.guess不支持
- **解决**: 修改config.guess添加HarmonyOS识别
- **补丁**: 0001-config.guess-harmonyos.patch

#### 问题2: sendmail缺失
- **原因**: configure要求sendmail，但HarmonyOS无此工具
- **解决**: 创建假sendmail脚本（只记录日志）
- **影响**: 邮件通知功能不完整（可在未来集成msmtp）

#### 问题3: configure临时文件权限
- **原因**: config.status无法在当前目录创建临时文件
- **解决**: 修改config.status使用$TMPDIR
- **备注**: HarmonyOS限制当前目录临时文件创建

#### 问题4: _res未定义 (dns.c)
- **原因**: musl libc不提供全局_res变量
- **解决**: 添加条件编译，在OHOS下跳过DNS选项设置
- **补丁**: 0004-dns.c-musl.patch

#### 问题5: time.h缺失 (report.c)
- **原因**: report.c缺少<time.h>头文件
- **解决**: 添加#include <time.h>
- **补丁**: 0005-report.c-timeh.patch

#### 问题6: 宏引号问题
- **原因**: Makefile DEFS中字符串引号在HarmonyOS下转义失败
- **解决**: 在源码中硬编码字符串值
- **补丁**: 0002-arpwatch.c-fixes.patch, 0003-arpsnmp.c-fixes.patch, 0006-util.c-fixes.patch

### Step 2.5: Staging安装
- DESTDIR: ~/test-install-arpwatch-3.9
- 文件: sbin/arpwatch, sbin/arpsnmp, man8/*.8

### Step 3: 预编译包
- 文件: arpwatch-3.9-ohos-aarch64.tar.gz (128KB)
- 内容: sbin/, share/man/man8/

### Step 4: 本地安装验证
- 安装位置: ~/usr/local/sbin/
- 验证结果: ✓ Version 3.9，命令可执行

## 编译结果
- 状态: built
- 可执行文件: arpwatch (59KB), arpsnmp (51KB)
- 测试: ✓ 通过（见 reports/test-report.md）

## 编译开始: 2026-06-18 15:07
## 编译结束: 2026-06-18 15:29
## 最终状态: built
---

**编译结束**: 2026-06-18 15:44
**最终状态**: built
