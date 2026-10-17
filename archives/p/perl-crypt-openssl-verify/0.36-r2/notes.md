# perl-crypt-openssl-verify 0.36-r2 适配笔记

## 编译环境
- 构建系统: custom (Perl XS / ExtUtils::MakeMaker)
- 编译日期: 2026-07-06
- 编译器: clang/clang++ 15.0
- 状态: published

## 编译步骤

1. 下载源码: CPAN Crypt-OpenSSL-Verify-0.36.tar.gz (sha256: deefdae6b14877f590f08c4eb50e3cd3710aa3ee62412c08d183f55b3af73e9e)
2. 应用补丁: 0001-Makefile.PL.patch (绕过 Crypt::OpenSSL::Guess, 动态检测 OpenSSL)
3. perl Makefile.PL (配置)
4. make -j1 (编译)
5. make install DESTDIR=... (staging 隔离安装)
6. conan-verify 全部门禁通过

## 源码修改

### Makefile.PL (0001-Makefile.PL.patch)
- 移除 `use Crypt::OpenSSL::Guess;` 依赖
- 内联检测 OpenSSL 版本 (运行 `openssl version` 命令, 回退默认 3.0.0)
- 使用 `$ENV{OPENSSL_PREFIX} || '/usr/local'` (通用默认值)
- 添加 LDFLAGS: `-Wl,-z,noexecstack -Wl,-z,relro -Wl,-z,now` (显式安全标志)
- 移除 CONFIGURE_REQUIRES 中的 Crypt::OpenSSL::Guess

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Crypt::OpenSSL::Guess 缺失 | CPAN 不可用 | 补丁内联检测 OpenSSL 版本和路径 |
| 2 | .so 无法 dlopen (Permission denied) | OHOS SELinux: tmpfs 文件上下文为 hmdfs, 策略阻止 dlopen | 部署到 /data/service/hnp/ 获得 hnp_file 上下文 (见测试报告 §7) |
| 3 | L4 扫描报告 NX=disabled | 误报: readelf 确认 GNU_STACK=RW (NX 实际已启用) | 添加 -z noexecstack LDFLAGS 显式标记; 记录为扫描器误报 |
| 4 | patch 硬编码用户路径 | 初始补丁使用 /storage/Users/currentUser/usr/local | 改为通用 /usr/local, 通过 OPENSSL_PREFIX 环境变量覆盖 |

## OHOS SELinux 限制 (E073)

OHOS SELinux 策略阻止 dlopen() 加载 tmpfs (/storage/Users/) 上的 .so 文件:
- tmpfs 文件上下文: `u:object_r:hmdfs:s0` → dlopen ❌
- hmfs 系统目录 (/data/service/hnp/): `u:object_r:hnp_file:s0` → dlopen ✅

**部署方案**: 安装 .so 到系统 Perl lib 目录 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64/`

## 安全标志

| 标志 | 值 | 状态 |
|------|-----|------|
| GNU_STACK | RW | ✅ NX 已启用 |
| GNU_RELRO | 存在 | ✅ RELRO 启用 |
| FLAGS | BIND_NOW | ✅ Full RELRO |
| PIE | DYN | ✅ PIE 启用 |

## 依赖版本

- Perl 5.42.0
- OpenSSL 3.5.6 (libssl, libcrypto)
- Crypt::OpenSSL::X509 2.1.2 (运行时依赖)
- Crypt::OpenSSL::Guess 0.015 (配置依赖, 已通过补丁绕过)

## 验证结果

### conan-verify 8 道门禁
- G0-G4: ✅ 全部 PASS
- L2 (smoke test): ✅ PASS (perl -v)
- L4 (安全扫描): ✅ PASS (ELF 检查通过)
- L5 (产物基线): ✅ PASS (9个文件)

### test_package 测试
- 包结构: ✅ Verify.pm + Verify.so 存在
- ELF 结构: ✅ valid AArch64 ELF shared object
- 动态依赖: ✅ libssl.so.3 + libcrypto.so.3 + libc.so
- 导出符号: ✅ boot_Crypt__OpenSSL__Verify
- 安全标志: ✅ GNU_STACK=RW, RELRO=full, BIND_NOW
- 运行时加载: ⏭️ 跳过 (OHOS SELinux, 需部署到系统目录)

## 交付物

| 文件 | 路径 | 说明 |
|------|------|------|
| Verify.so | lib/perl5/aarch64-linux/auto/Crypt/OpenSSL/Verify/Verify.so | Perl XS 共享库 |
| Verify.pm | lib/perl5/Crypt/OpenSSL/Verify.pm | Perl 模块文件 |
| 0001-Makefile.PL.patch | patches/0001-Makefile.PL.patch | OHOS 适配补丁 |
| test-report.md | reports/test-report.md | 功能测试报告 |

## 注意事项

1. 版本 0.36-r2 中的 -r2 是打包修订号, 上游版本为 0.36
2. 运行时需要 Crypt::OpenSSL::X509 模块已安装
3. OHOS 上 .so 运行时加载需部署到系统 Perl 目录 (SELinux 限制)
4. 详细测试结果见 reports/test-report.md

---

**编译结束**: 2026-07-06 14:56
**最终状态**: published
