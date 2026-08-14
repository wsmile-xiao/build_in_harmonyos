# perl-net-snmp 6.0.1 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-26
- 编译器: N/A (纯 Perl 模块，无 C 编译)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build perl-net-snmp 6.0.1` 初始化编译环境
2. `source .build-context-perl-net-snmp-6.0.1` 加载上下文
3. `cd $BUILD_SRC_DIR` 进入源码目录
4. `perl Makefile.PL` 生成 Makefile
5. `make` 编译 Perl 模块
6. `ohc-run.py conan-init perl-net-snmp 6.0.1` 生成 Conan 配方
7. `ohc-run.py conan-verify perl-net-snmp 6.0.1` 验证配方 (全部通过)
8. `ohc-run.py finish perl-net-snmp 6.0.1 built` 归档收尾

## 可选依赖解决

### 问题

Net::SNMP 的 SNMPv3 USM 和 IPv6 传输依赖三个可选 Perl XS 模块，XS .so 文件在 OpenHarmony 上受 SELinux HMDFS 限制无法从用户目录加载。

### 解决方案：纯 Perl 兼容包装器

创建了三个纯 Perl 包装器，绕过 XS .so 的 SELinux 限制：

| 包装器 | 后端 | 位置 |
|--------|------|------|
| Crypt::DES | Crypt::DES_PP (CPAN 纯 Perl DES) | ~/usr/local/lib/site_perl/5.42.0/Crypt/DES.pm |
| Digest::SHA1 | Digest::SHA (核心模块 v6.04) | ~/usr/local/lib/site_perl/5.42.0/Digest/SHA1.pm |
| Socket6 | Socket (核心模块 v2.038) | ~/usr/local/lib/site_perl/5.42.0/Socket6.pm |

Crypt::DES_PP 来源: https://mirrors.tuna.tsinghua.edu.cn/CPAN/authors/id/G/GU/GUIDO/Crypt-DES_PP-1.00.tar.gz

### Crypt::DES XS 编译尝试记录

尝试了 XS 编译但最终因 SELinux 限制未能使用：
1. 下载 Crypt-DES-2.07 (作者 DPARIS, 非 DAPM)
2. 修复 DES.xs: `perl_des_expand_key` → `_des_expand_key`, `perl_des_crypt` → `_des_crypt`
3. 添加 musl 头文件路径: `CCFLAGS="-I~/usr/local/include"`
4. 编译成功: `clang -c DES.c` + `clang -c _des.c`
5. 链接: `clang -shared -L~/usr/local/lib DES.o _des.o -o DES.so -lc -l:libunwind.a`
6. .so 生成成功 (26KB ELF64 AArch64)
7. **加载失败**: SELinux HMDFS Permission denied
8. 系统目录无写入权限
9. **结论**: 改用纯 Perl 包装器

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SNMPv3 USM 不可用 | Crypt::DES 未安装 | 创建 Crypt::DES 纯 Perl 包装器 (Crypt::DES_PP 后端) |
| 2 | IPv6 Transport 不可用 | Socket6 未安装 | 创建 Socket6 纯 Perl 包装器 (核心 Socket 后端) |
| 3 | Digest::SHA1 未安装 | XS 模块未预装 | 创建 Digest::SHA1 包装器 (Digest::SHA 后端) |
| 4 | Crypt::DES XS .so 加载失败 | SELinux HMDFS 限制 | 放弃 XS, 使用纯 Perl 包装器 |
| 5 | Crypt::DES XS 编译缺 sys/types.h | musl 头文件不在默认路径 | 添加 -I~/usr/local/include |
| 6 | Crypt::DES XS 函数名错误 | DES.xs 使用旧 perl_ 前缀 | 修改为 _des_ 前缀 |
| 7 | PERL5LIB 覆盖丢失路径 | export PERL5LIB= 覆盖已有值 | 使用 PERL5LIB=$NEW:$PERL5LIB 追加 |

## 源码修改

Net::SNMP 无需补丁。所有适配通过纯 Perl 包装器实现，不修改 Net::SNMP 源码。

## 依赖版本

- Perl: 5.42.0 (系统预装)
- 无 C/C++ 依赖
- 可选依赖 (通过纯 Perl 包装器解决):
  - Crypt::DES → Crypt::DES_PP 1.00 (CPAN 纯 Perl)
  - Digest::SHA1 → Digest::SHA 6.04 (Perl 核心)
  - Socket6 → Socket 2.038 (Perl 核心)
  - Digest::HMAC 1.05 (已安装)
  - Digest::MD5 2.59 (已安装)

## 验证结果

```bash
# Conan create 验证
$ conan create . 6.0.1@ohpcd/stable
Net::SNMP version: v6.0.1

# conan-verify 8 道门禁全部 PASS
G0-G4 + L2/L4/L5: ALL PASS

# 功能测试 (25项全部 PASS)
- SNMPv1/v2c: 会话+操作+异步 全部正常
- SNMPv3 USM: SHA+DES, MD5+DES, noAuth 全部可用
- IPv4/IPv6 Transport: UDP/TCP 全部加载
- 所有 15 个子模块加载: OK
```

## 注意事项

- 纯 Perl 模块，不受 OpenHarmony SELinux HMDFS 限制
- 通过 `PERL5LIB` 环境变量加载，无需安装到系统目录
- SNMPv3 需要安装 Crypt::DES_PP 和 Digest::SHA1 包装器
- IPv6 需要安装 Socket6 包装器
- PERL5LIB 设置需追加而非覆盖: `export PERL5LIB=$CONAN_LIB:$PERL5LIB`

---

**编译结束**: 2026-06-26 18:09
**可选依赖解决**: 2026-06-30
**最终状态**: built (功能完全可用)
