# E113: Perl XS 模块编译链接参数缺失

## 问题描述

Perl XS 模块编译时遇到以下错误：
- `ld.lld: error: unable to find library -lc`
- `clang: error: linker command failed with exit code 1`
- `fatal error: 'sys/types.h' file not found`

## 根因分析

Perl XS 模块使用 ExtUtils::MakeMaker 构建系统，默认链接参数不适合 musl 平台：
1. 缺少 CPATH 环境变量，找不到 musl 头文件
2. 缺少 LIBRARY_PATH 环境变量，找不到 musl 库文件
3. 默认链接参数会尝试链接不存在的 CRT 文件

## 受影响范围

所有 Perl XS 模块（使用 Makefile.PL 构建的 Perl 扩展模块），包括：
- Devel::Caller
- DBD::Pg
- PadWalker
- 其他使用 XS 代码的 Perl 模块

## 解决方案

### 步骤 1：设置环境变量

```bash
export CPATH=/storage/Users/currentUser/usr/local/include
export LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib
```

### 步骤 2：修改 Makefile.PL

在 Makefile.PL 的 `WriteMakefile()` 中添加：

```perl
dynamic_lib => { OTHERLDFLAGS=>q[-nostartfiles -nodefaultlibs -lc] },
```

### 步骤 3：构建

```bash
perl Makefile.PL PREFIX=/storage/Users/currentUser/usr/local
make
```

## 验证命令

```bash
ls -la blib/arch/auto/*/模块名.so
```

## 补丁示例

```diff
--- a/Makefile.PL
+++ b/Makefile.PL
@@ -23,4 +23,5 @@
         license     => 'http://dev.perl.org/licenses/',
     },
+    dynamic_lib => { OTHERLDFLAGS=>q[-nostartfiles -nodefaultlibs -lc] },
 );
```

## 相关案例

- perl-dbd-pg/3.18.0
- Devel-Caller/2.07

## 知识层次

L1（平台真理）：所有 Perl XS 模块在鸿蒙平台都需要此修改