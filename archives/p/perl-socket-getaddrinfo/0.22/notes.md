# perl-socket-getaddrinfo 0.22 编译笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (EUMM, 从 Module::Build 重写)
- 编译日期: 2026-07-01
- 编译器: clang/clang++
- 状态: published

## 软件概述

Socket::GetAddrInfo 是 Perl 的地址解析 XS 模块，提供 getaddrinfo() 和 getnameinfo()
的 Perl 接口，支持 IPv4 和 IPv6 地址解析。

## 编译步骤

1. 从 CPAN 下载 Socket-GetAddrInfo-0.22.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-socket-getaddrinfo 0.22
3. 在 conanfile.py build() 中内联完成所有源码修改：
   - 手动生成 socket-gai-config.h（替代 ExtUtils::CChecker）
   - 重写 Makefile.PL（从 Module::Build::Compat 到 EUMM）
   - 添加链接参数 `-nostartfiles -nodefaultlibs -lc`
4. 运行 perl Makefile.PL 配置
5. 运行 make 编译（含 .o 文件路径修复）
6. 运行 make install DESTDIR 安装到 staging
7. 生成并验证 Conan 配方（conan-init + conan-verify）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Module::Build 不可用 | 鸿蒙系统未安装 Module::Build | 重写 Makefile.PL 使用 ExtUtils::MakeMaker |
| 2 | ExtUtils::CChecker 不可用 | 缺少该模块依赖 | 手动生成 socket-gai-config.h，定义 HAS_GETADDRINFO |
| 3 | 链接错误：缺少 crti.o, crtn.o | 鸿蒙系统缺少 CRT 文件 | 在 Makefile.PL 中添加 `dynamic_lib => { OTHERLDFLAGS => '-nostartfiles -nodefaultlibs -lc' }` |
| 4 | .o 文件路径不匹配 | EUMM 在 CWD 生成 .o，但链接器在 lib/Socket/ 查找 | 在 build() 中手动复制 .o 文件到正确路径 |
| 5 | SELinux HMDFS 限制 | 动态库加载受限 | 需安装到系统目录 /data/service/hnp |

## 依赖版本

### 已存在
- perl 5.42.0: /data/service/hnp/perl.org/perl_5.42.0/
- musl C 库头文件: ~/usr/local/include

### 编译依赖
- musl C 库头文件（提供 stdio.h, sys/types.h, netdb.h 等）
- perl 5.42.0（提供 ExtUtils::MakeMaker, xsubpp 等）

## 编译产物

- **GetAddrInfo.so**: 17KB，ELF 64-bit ARM64 共享对象
- **GetAddrInfo.pm**: 13KB，Perl 模块文件
- **GetAddrInfo.xs**: 7.6KB，XS 源文件
- **Core.pm**: 704B，Core 实现
- **Emul.pm**: 10KB，Emulation 实现
- **Socket6api.pm**: 3.8KB，Socket6 API 兼容
- **Strict.pm**: 2.7KB，Strict 模式
- **XS.pm**: 586B，XS 实现入口
- **.packlist**: 1.3KB，安装清单

共 11 个文件，安装路径: lib/site_perl/5.42.0/aarch64-linux/

## 知识沉淀

### 平台发现
- 鸿蒙系统缺少 CRT 文件（crti.o, crtn.o 等），Perl XS 模块链接需要 `-nostartfiles -nodefaultlibs -lc`
- Module::Build 在鸿蒙系统不可用，需将基于它的 Makefile.PL 重写为 ExtUtils::MakeMaker
- ExtUtils::CChecker 在鸿蒙系统不可用，需手动生成配置头文件
- EUMM 的 .o 文件路径行为与标准 Perl 不同，需要手动修正
- SELinux HMDFS 限制动态库加载到用户目录

### 编译建议
- Perl XS 模块编译需要完整的 C 库头文件支持
- 对于依赖 Module::Build 的 Perl 模块，需重写为 EUMM
- 对于依赖 ExtUtils::CChecker 的模块，需手动生成配置头文件
- 需要 ELF 签名才能在鸿蒙系统执行

## 与 perl-dbd-pg 编译经验对比

| 对比项 | perl-dbd-pg | perl-socket-getaddrinfo |
|--------|-------------|------------------------|
| 构建系统 | Makefile.PL (EUMM) | Makefile.PL (从 Module::Build 重写为 EUMM) |
| CRT 缺失修复 | -nostartfiles -nodefaultlibs -lc | 同上 |
| 配置检测 | pg_config 包装器 | 手动生成 socket-gai-config.h |
| 补丁方式 | 外部 .patch 文件 | conanfile.py build() 内联 |
| 特殊问题 | DBI::DBD 加载失败 | .o 文件路径不匹配 |

---
**编译结束**: 2026-07-01
**conan-verify**: 2026-07-02 全部门禁通过 (G0-G4, L2, L4, L5)
**功能测试**: 2026-07-02 11 项功能测试全部通过
**最终状态**: published (conan-verify 通过，功能测试通过)
