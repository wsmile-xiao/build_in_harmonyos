# perl-params-validate 1.31 编译笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (Makefile.PL) — 替代源码的 Build.PL (Module::Build)
- 编译日期: 2026-07-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 CPAN 下载 Params-Validate-1.31.tar.gz
2. 在 build() 中生成 Makefile.PL (源码仅有 Build.PL, Module::Build 在 CI 不可用)
3. 运行 perl Makefile.PL INSTALLDIRS=site 生成 Makefile
4. 手动编译 XS: 内联传递 musl -I 路径和 CRT 修复标志给 clang (E137)
5. 运行 make -j1 编译 XS 和纯 Perl 模块
6. 运行 make install DESTDIR=... 安装到 staging

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI构建失败: Can't locate Module/Build.pm | CI worker Perl 未安装 Module::Build | 改用 ExtUtils::MakeMaker (Makefile.PL) 替代 Build.PL |
| 2 | 链接错误：ld.lld 拒绝 -fstack-protector-strong | Perl 5.42.0 的 lddlflags 包含该参数 | 内联 clang -shared -nostartfiles -nodefaultlibs -lc 编译 XS |
| 3 | 缺少 stdio.h 等 C 标准库头文件 | 鸿蒙系统默认搜索路径无 musl 头文件 | 内联 clang -I 传递 musl 头文件路径 |
| 4 | 链接找不到 libc | 系统库不在默认搜索路径 | 内联 clang -L 传递 ~/usr/local/lib 和 /system/lib64 |
| 5 | SELinux HMDFS 限制 XS 模块加载 | hishell_hap domain 只能加载 hnp_file 类型 | 需安装到系统目录 /data/service/hnp |
| 6 | patch 文件硬编码路径 | 0001-Build.PL.patch 使用 /storage/Users/currentUser/... | 删除 patch, 改用 Makefile PL + 内联 clang 编译 XS |

## 与其他 Perl XS 模块编译经验对比

| 维度 | perl-net-dns-sec | perl-params-validate |
|------|-----------------|---------------------|
| 构建系统 | ExtUtils::MakeMaker (Makefile.PL) | ExtUtils::MakeMaker (Makefile.PL, 自动生成) |
| 源码原始构建系统 | Makefile.PL (原生) | Build.PL (Module::Build, CI 不可用) |
| CRT 缺失修复 | LDDLFLAGS patch | LDDLFLAGS patch |
| 头文件路径 | CCFLAGS -isystem | INC -I |
| 库路径 | LDDLFLAGS -L | LDDLFLAGS -L |

### 关键差异
- perl-net-dns-sec 源码自带 Makefile.PL，直接使用
- perl-params-validate 源码只有 Build.PL (Module::Build)，需在 conanfile.py 中生成 Makefile.PL
- perl-net-dns-sec 通过 patch Makefile LDDLFLAGS 解决 E137，perl-params-validate 通过内联 clang 标志解决
- 两者都受 SELinux HMDFS 限制，XS 模块需安装到系统目录

## 依赖版本

### 已存在
- perl: 5.42.0 (系统安装, /data/service/hnp/perl.org/perl_5.42.0/)
- ExtUtils::MakeMaker: 随 perl 5.42.0 提供 (CI 可用)
- musl C 库头文件: ~/usr/local/include (371 个文件)
- clang 编译器 (/data/service/hnp/bin/clang)

## 编译产物

- **XS.so**: 50,688 bytes，ELF 64-bit AArch64 共享对象
  - 路径: blib/arch/auto/Params/Validate/XS/XS.so
  - 动态依赖: libc.so
  - ELF 安全: NX 栈不可执行 (RW), GNU_RELRO 启用
  - 关键符号: boot_Params__Validate, validate, validate_pos, validate_one_param
- **Validate.pm**: 26,713 bytes，Perl 模块文件 (主入口)
- **ValidatePP.pm**: 156 bytes，PP 实现入口
- **ValidateXS.pm**: 156 bytes，XS 实现入口
- **PP.pm**: 20,313 bytes，纯 Perl 实现细节
- **Constants.pm**: 552 bytes，常量定义

## 知识沉淀

### 平台发现
- Module::Build 不在 CI worker Perl 安装中 (本地有但 CI 无)
- ExtUtils::MakeMaker 随 Perl 核心提供，CI 可用
- Perl 5.42.0 on OHOS 的 lddlflags 包含 -fstack-protector-strong (E137)
- ExtUtils::MakeMaker 自动处理 .xs → .c → .so 编译流程
- 鸿蒙系统库在 /system/lib64
- musl C 库头文件需手动指定路径

### 编译建议
- Perl XS 模块编译需要完整的 C 库头文件支持 (musl)
- 源码只有 Build.PL 时，可在 conanfile.py 中生成 Makefile.PL 作为 fallback
- 需要 ELF 签名才能在鸿蒙系统执行

---

## 功能测试结果 (2026-07-06)

### PP (纯 Perl) 模式: 全部通过 (10/10)

| # | 测试项 | 状态 |
|---|--------|------|
| 1 | validate: 必需参数 (foo) | PASS |
| 2 | validate: 必需参数 (bar) | PASS |
| 3 | validate: 可选参数默认值 | PASS |
| 4 | validate: 缺少必需参数报错 | PASS |
| 5 | validate_pos: 位置参数 | PASS |
| 6 | validate_pos: 位置参数 | PASS |
| 7 | validate: 正则约束匹配 | PASS |
| 8 | validate: 正则约束失败报错 | PASS |
| 9 | validate_with 函数导出 | PASS |
| 10 | validate: ARRAYREF 类型 | PASS |

### XS 模式: SELinux 限制

- 直接加载 XS.so 失败: Permission denied (hmdfs:s0)
- Module::Implementation 自动降级到 PP 模式
- 需安装到系统目录 `/data/service/hnp` 才能使用 XS 模式
- XS.so 签名失败: 无 .codesign section

### 结论

PP 模式完全可用，XS 模式需管理员安装到系统目录。通过 Module::Implementation 自动降级机制确保功能可用性。

---
**编译结束**: 2026-07-03 16:58
**CI 修复**: 2026-07-08 (Module::Build → ExtUtils::MakeMaker)
**最终状态**: built (编译成功，PP 模式功能测试全部通过)
