# E112 — OpenHarmony SDK 缺少 musl libc 头文件导致 Perl XS 模块编译失败

## 错误特征

编译 Perl XS 模块（包含 C 代码的 Perl 模块）时，出现以下错误：

```
fatal error: bits/alltypes.h: No such file or directory
 #include <bits/alltypes.h>
          ^~~~~~~~~~~~~~~~~

fatal error: sys/types.h: No such file or directory
 #include <sys/types.h>
          ^~~~~~~~~~~~~
```

## 触发条件
- 构建系统: ExtUtils::MakeMaker（Perl XS 模块标准构建系统）
- 阶段: make（编译 C 代码阶段）
- 受影响软件: DateTime、所有 Perl XS 模块、其他依赖完整 musl libc 头文件的软件

## 根因分析

OpenHarmony SDK 提供的 musl libc 头文件集不完整，缺少以下关键文件：
- `bits/alltypes.h`：musl libc 核心类型定义（size_t、ptrdiff_t、wchar_t 等）
- 其他可能的系统头文件

**依赖链**：
1. Perl XS 模块的 C 代码（DateTime.xs → DateTime.c）依赖 Perl CORE 头文件
2. Perl CORE 头文件依赖标准 POSIX 头文件（sys/types.h）
3. sys/types.h 在 musl libc 中依赖 bits/alltypes.h
4. OpenHarmony SDK 缺少 bits/alltypes.h → 编译失败

**影响范围**：所有包含 C 代码的 Perl 模块（XS 模块），以及其他依赖完整 musl libc 头文件的软件。

## 解决方案

### 推荐方案

**标记为平台限制，跳过编译**

由于这是 OpenHarmony 系统层面的限制（SDK 不完整），无法通过修改源码解决。

**步骤**：
1. 在 notes.md 中记录平台限制：
   ```bash
   echo "Platform limitation: OpenHarmony SDK lacks musl libc headers (bits/alltypes.h)" >> notes.md
   ```
2. 更新 manifest.yaml 状态为 failed
3. 等待 OpenHarmony 完善系统头文件支持后再尝试编译

### 回退方案

**交叉编译**

在完整的 Linux 环境中（带有完整 musl libc 头文件）编译 Perl XS 模块，然后移植到 OpenHarmony。但这需要：
- 完整的交叉编译工具链
- 目标平台的 Perl 版本匹配
- 复杂的部署流程

### 禁止做法
- ❌ 手动创建 bits/alltypes.h 文件
  - 原因：musl 和 glibc 的类型定义不同，手动创建会导致 ABI 不兼容
  - 后果：编译成功但运行时崩溃、类型大小不匹配、内存访问违规

- ❌ 复制 glibc 的 bits/alltypes.h 到 musl
  - 原因：glibc 和 musl 的结构体布局、类型大小可能不同
  - 后果：运行时出现难以排查的 ABI 问题

## 验证

检查 OpenHarmony SDK 是否缺少 musl libc 头文件：
```bash
# 查找 bits/alltypes.h
find /usr/include -name "alltypes.h" 2>/dev/null | grep bits
# 如果返回空 → 确认缺少 musl libc 核心头文件
```

## 知识沉淀

**现象**：Perl XS 模块编译失败，缺少系统头文件

**原因**：
1. OpenHarmony SDK 头文件不完整（缺少 bits/alltypes.h 等）
2. Perl XS 模块依赖标准 POSIX 头文件
3. musl libc 头文件结构与 glibc 不同

**建议**：
1. 优先编译纯 Perl 模块（无 C 代码）
2. XS 模块需要等待 OpenHarmony 完善系统头文件支持
3. 或考虑交叉编译方式（在完整 Linux 环境编译）

## 关联条目
- 类似: E020（musl/glibc 不兼容）、E026（TLS 差异）、E078（musl 动态链接）
- 平台限制: 属于 OpenHarmony 系统层面的限制，非源码问题
