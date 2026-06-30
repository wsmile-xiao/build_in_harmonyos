# Data-UUID 1.227 编译笔记

## 编译状态：built

## 编译进度追踪

### Phase 1: 初始分析（2026-06-09）

**问题**：平台缺少基本的 C 标准库头文件，无法编译 Perl XS 模块。

### Phase 2: 头文件修复（2026-06-09）

**解决方案**：在 ~/usr/local/include 目录创建缺失的标准 C 头文件 stub：

**已创建的头文件（共 40+ 个）：**

**标准 C 头文件：**
- ctype.h, locale.h, langinfo.h, setjmp.h, stdlib.h
- unistd.h, inttypes.h, wchar.h, netdb.h

**系统头文件：**
- sys/types.h, sys/param.h, sys/mode.h, sys/times.h
- sys/ipc.h, sys/sem.h, sys/shm.h, sys/msg.h
- sys/_types.h（核心类型定义）

**关键技术点：**
- 统一类型定义避免冲突（sys/_types.h）
- wchar_t 使用编译器内置类型，避免与 stddef.h 冲突
- 添加 off64_t 别名支持 Perl 的 Off_t 宏
- 添加 gethostid 函数声明

### Phase 3: 编译结果（2026-06-09）

**编译成功 ✅**：
- UUID.o 成功生成
- 所有 Perl XS C 代码编译通过
- 只有 14 个宏重定义警告（可忽略）

**链接失败 ❌**：
```
ld.lld: error: cannot open crti.o: No such file or directory
ld.lld: error: cannot open crtbeginS.o: No such file or directory
ld.lld: error: unable to find library -l:libunwind.a
ld.lld: error: unable to find library -lc
ld.lld: error: cannot open crtendS.o: No such file or directory
ld.lld: error: cannot open crtn.o: No such file or directory
```

### 根本原因分析

**平台限制**：OpenHarmony 缺少完整的 C 运行时库（musl libc 或 glibc）

链接阶段需要的文件：
1. **crt*.o 启动文件** - C 运行时初始化/终止代码
2. **libc** - C 标准库（malloc, printf 等）
3. **libunwind.a** - 异常处理/栈展开库

**现状**：
- 头文件问题已解决（创建 stub）
- 编译阶段通过（UUID.o 生成）
- 链接阶段无法通过（缺少运行时库）

---

## 编译修复过程（2026-06-10）

### 问题诊断
1. **根本原因**：链接阶段缺少 CRT 文件（crti.o, crtbeginS.o 等）和 libc
2. **关键发现**：perl-dbd-pg 成功使用了 `-nostartfiles -nodefaultlibs` 参数绑过 CRT 文件缺失问题
3. **依赖**：musl 1.2.5 已编译，提供 libc.so（~/usr/local/lib/libc.so）

### 解决方案
1. **手动链接**：使用 `clang -shared -nostartfiles -nodefaultlibs ~/usr/local/lib/libc.so -o UUID.so UUID.o`
2. **ELF 签名**：使用 binary-sign-tool 对 UUID.so 签名
3. **HNP 包制作**：创建 perl-data-uuid-1.227.hnp（16KB），包含 UUID.pm 和 UUID.so

### 编译结果
- **UUID.so 已生成**：25KB，已 ELF 签名
- **HNP 包已创建**：~/tmp/perl-data-uuid-1.227.hnp（16KB）

### SELinux 限制分析（与 perl-dbd-pg 相同）

**问题**：HMDFS 文件系统上的 .so 文件无法加载（Permission denied）

**解决方案**：需要管理员将 HNP 包安装到 `/data/service/hnp` 目录获得正确的 SELinux 标签

### 功能测试（2026-06-10）

**静态分析结果**：
- ✅ ELF 结构正确（AArch64 shared object）
- ✅ 代码签名段存在（.codesign 4096 bytes）
- ✅ XS 接口符号正确链接 Perl 运行时
- ✅ 功能接口完整（create, create_str, create_hex, create_b64, create_from_name, to_string, from_string, compare）

**运行测试限制**：
- ❌ SELinux HMDFS 限制阻止模块加载（`hmdfs:s0` 标签）
- 需要管理员安装到 `/data/service/hnp` 目录获得 `hnp_file:s0` 标签

**功能完整性评估**：PASS（静态分析验证）

---
**编译结束**: 2026-06-10
**最终状态**: built（编译成功，功能验证通过静态分析，等待管理员安装运行测试）