# mono 6.12.0.122 编译笔记

## 编译状态：built（部分编译成功）

## 编译日期：2026-05-27（更新）

## 遇到的问题

### 问题 1：HMDFS 权限问题 (E011) ✅
- **症状**：`./config.status: can't create ./confXXX/subs1.awk: Permission denied`
- **原因**：HMDFS 文件系统的 UID 映射不匹配，umask 077 创建的临时目录权限为 0700，但 owner 不是当前进程
- **解决方案**：修改 configure 中的 `umask 077` 为 `umask 022`
- **状态**：已解决 ✅

### 问题 2：config.guess 不识别 HarmonyOS (E007) ✅
- **症状**：`config.guess: unable to guess system type`
- **原因**：mono 的 config.guess 版本过旧（2015-08-20），不包含 HarmonyOS 检测
- **解决方案**：替换为 automake-1.16 的 config.guess/config.sub，运行 patch-autotools-ohos.pl
- **状态**：已解决 ✅

### 问题 3：CMake 版本兼容性 ✅
- **症状**：BTLS 模块的 CMakeLists.txt 版本要求过低（2.8.10），与当前 CMake 4.1.2 不兼容
- **解决方案**：使用 `--disable-btls` 禁用 BTLS 模块
- **状态**：已解决 ✅

### 问题 4：OpenHarmony SDK 头文件冲突 (E081) ✅ 已修复
- **症状**：`sockaddr_storage` 在 `linux/socket.h` 和 `sys/socket.h` 中重复定义
- **文件**：`external/corefx/src/Native/Unix/System.Native/pal_maphardwaretype.c`
- **原因**：OpenHarmony SDK 的系统头文件组织问题，`linux/socket.h` 和 `sys/socket.h` 都定义了相同的结构体
- **修复方案**：
  ```c
  #ifdef __OHOS__
  // On OpenHarmony, sys/socket.h defines sockaddr_storage
  // linux/socket.h also defines it, causing redefinition
  // We need to prevent sockaddr_storage redefinition from linux/socket.h
  // but linux/netlink.h (included via linux/if_arp.h chain) needs __kernel_sa_family_t
  // Solution: define _UAPI_LINUX_SOCKET_H to skip linux/socket.h entirely,
  // and manually define __kernel_sa_family_t (typedef unsigned short)
  #define _UAPI_LINUX_SOCKET_H
  typedef unsigned short __kernel_sa_family_t;
  #endif
  ```
- **关键点**：
  - 使用 `#ifdef __OHOS__` 守卫（符合 R8 源码"四不"准则）
  - 定义 `_UAPI_LINUX_SOCKET_H` 跳过 linux/socket.h
  - 手动定义 `__kernel_sa_family_t` 以满足 linux/if_arp.h 的需求
  - 在 `#include <sys/socket.h>` 后、`#include <linux/if_arp.h>` 前插入
- **状态**：已解决 ✅

### 问题 5：C# 类库编译速度极慢 ⚠️
- **症状**：mscorlib.dll, Mono.Security.dll, System.dll 编译完成（约4个 dll），但 System.Xml.dll 编译进程卡住
- **原因**：
  - mono 使用 bootstrap 方式编译 C# 类库（使用 mono + roslyn csc.exe）
  - 编译过程需要大量内存和计算资源
  - 系统内存不足（多次遇到 "Out of memory" 错误）
- **状态**：部分完成 ⚠️ - 需要更多资源和时间完成全部类库

### 问题 6：系统资源限制 ❌
- **症状**：多次遇到 "fork failed: out of memory" 错误
- **影响**：
  - make check 无法执行
  - 部分安装步骤失败（Error 127）
  - 无法创建新的进程进行验证
- **状态**：环境限制 ❌ - 需要在资源充足的环境下完成完整编译

## 编译配置

```
./configure --prefix=$DEFAULT_PREFIX --without-x --disable-btls CC=clang CXX=clang++
```

## 编译进度（2026-05-27）

### 第一阶段：修复与编译
- ✅ configure 成功（修复 sockaddr_storage 问题后）
- ✅ C/C++ 编译成功，mono-sgen 可执行文件生成（16M）
- ⚠️ C# 类库编译中断（编译速度极慢，进程卡住）

### 第二阶段：收尾工作
- ✅ staging 安装成功（DESTDIR 模式，安装到 test-install-mono-6.12.0.122）
- ✅ 安全弹窗验证（R7）：mono-sgen --version 正常运行，无弹窗（HongMeng Kernel 1.12.0 已解决）
- ❌ make check 因系统内存不足失败（Out of memory）
- ⚠️ make install 因 C# 类库未完成而失败（Error 127）
- ✅ 手动复制 mono-sgen 到 ~/usr/local/bin（16M）
- ✅ staging 目录验证成功（mono-sgen --version 正常）

## 编译产物

- **mono-sgen**: 16M ELF 可执行文件（arm64, dynamic linked）
- **libmonosgen-2.0.so**: 共享库
- **部分 C# 类库**: mscorlib.dll, Mono.Security.dll, System.dll, PEAPI.dll等（约4-6个）
- **staging 安装目录**: /storage/Users/currentUser/test-install-mono-6.12.0.122

## 遵循的 SKILL 铁律

- ✅ R6: 只改源文件（pal_maphardwaretype.c），不改生成文件
- ✅ R7: 安全弹窗验证（mono-sgen --version 正常运行）
- ✅ R8: 源码"四不"准则（使用 `#ifdef __OHOS__` 守卫）
- ✅ R20: DESTDIR 模式（staging 安装成功）
- ⚠️ R22: 干净构建验证（因资源限制无法完整执行）
- ⚠️ R25: notes.md 防重复（finish 前更新记录）

## 知识提取记录（R17）

### E081: sockaddr_storage 重复定义 ✅ 新条目需创建
- **分类**：L1 平台真理（OpenHarmony SDK 特性）
- **影响范围**：所有使用 `linux/socket.h` 和 `sys/socket.h` 的软件
- **解决方案**：见上方"问题4"详细说明
- **建议创建知识条目**：使用 `ohc-run.py graph add E081 --draft`

### E011: HMDFS umask 问题
- 已在知识图谱中存在
- 本次验证了 `sed -i 's/umask 077/umask 022/g' configure` 方案有效

## 平台限制总结

mono 是一个复杂的 .NET 运行时，在 OpenHarmony 上编译存在以下平台限制：

1. **sockaddr_storage 重复定义**（E081）✅ 已修复
   - OpenHarmony SDK 的头文件组织问题
   - 修复方案：使用宏定义跳过 linux/socket.h，手动定义必要类型

2. **C# 类库编译速度极慢** ⚠️
   - bootstrap 编译方式需要大量资源
   - 系统内存不足会导致编译失败

3. **系统资源限制** ❌
   - 当前测试环境内存不足（多次 fork failed）
   - make check 无法执行
   - 部分安装步骤失败

## 建议

- **当前状态**：mono-sgen（JIT 编译器）已可用，可运行基本的 .NET 程序（需要类库支持）
- **完整编译**：建议在资源充足的环境下继续（推荐 ≥4GB 内存）
- **发布状态**：当前标记为 `built`（部分编译成功），完整编译后可升级为 `published`
---

**编译结束**: 2026-05-27 14:11
**最终状态**: built
---

**编译结束**: 2026-05-27 14:16
**最终状态**: built
