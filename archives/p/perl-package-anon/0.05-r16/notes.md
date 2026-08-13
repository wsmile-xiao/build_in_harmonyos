# perl-package-anon 0.05-r16 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-02
- 编译器: clang 18.1.8
- 状态: built

## 编译步骤

1. 源码来自 CPAN: Package-Anon-0.05 (https://cpan.metacpan.org/authors/id/A/AU/AUGGY/Package-Anon-0.05.tar.gz)
2. `perl Makefile.PL` 生成 Makefile
3. 修改 Makefile 的 CCFLAGS 和 LDDLFLAGS 添加 OHOS SDK sysroot 路径
4. `make` 编译 XS 扩展 (Anon.xs → Anon.c → Anon.o → Anon.so)
5. `make install DESTDIR=$TEST_PREFIX` 安装到 staging 目录
6. `make test` 测试（因平台限制失败，见下文）

### 关键修改
- CCFLAGS 添加: `-isystem $SYSROOT/usr/include -isystem $SYSROOT/usr/include/aarch64-linux-ohos`
- LDDLFLAGS 添加: `--sysroot=$SYSROOT -L$SYSROOT/usr/lib/aarch64-linux-ohos -L$LLVM_LIB/aarch64-linux-ohos`
- 其中 SYSROOT=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot
- LLVM_LIB=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败，无法下载源码 | 鸿蒙Python/OpenSSL未配置CA证书 | 设置 SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem |
| 2 | `sys/types.h` not found | clang 18.1.8 无 OHOS sysroot，Perl Config 中的 incpth 指向不存在的路径 | Makefile CCFLAGS 添加 -isystem 指向 OHOS SDK sysroot include |
| 3 | `unable to find library -l:libunwind.a` 和 `-lc` | clang 18.1.8 无 OHOS sysroot 和 LLVM lib 路径 | Makefile LDDLFLAGS 添加 --sysroot 和 -L 指向 sysroot lib 和 LLVM lib |
| 4 | `make test` 失败: Permission denied 加载 Anon.so | OHOS SELinux 限制 (E046)，HMDFS 上的 .so 不可加载 | 平台限制，不阻塞编译。需安装到 /data/service/hnp 系统目录 (hnp_file:s0) |
| 5 | CRT 文件缺失 (crti.o, crtn.o 等) | 鸿蒙系统缺少 CRT 文件 | 参考 perl-dbd-pg 经验，LDDLFLAGS 添加 -nostartfiles -nodefaultlibs -lc |

### perl-dbd-pg 经验引用

本次编译参考了 perl-dbd-pg 3.18.0 的编译经验：
1. **CRT 链接修复**: perl-dbd-pg 在 Makefile.PL 中添加 `dynamic_lib => { OTHERLDFLAGS => '-nostartfiles -nodefaultlibs -lc' }`，本次在 conanfile.py 的 `_patch_makefile()` 中将相同参数添加到 LDDLFLAGS
2. **SELinux HMDFS 限制**: 与 perl-dbd-pg 相同，XS 模块在 HMDFS 上无法加载 (hmdfs:s0)，需安装到 /data/service/hnp (hnp_file:s0)
3. **HNP 包安装方案**: 参考 perl-dbd-pg 的 HNP 包方案，创建了 perl-package-anon.hnp 供管理员安装
4. **binary-sign-tool 签名**: 使用 /data/service/hnp/bin/binary-sign-tool 对 Anon.so 进行签名

## 源码修改

无源码修改，仅修改生成的 Makefile（编译参数调整）。

## 依赖版本

- Perl: 5.42.0 (aarch64-linux)
- clang: 15.0.4 (OHOS SDK, Conan profile) / 18.1.8 (系统, 探索阶段)
- OHOS SDK: 26.0.0.18 (sysroot)
- ExtUtils::MakeMaker: 6.30+

## 验证结果

```bash
# 编译成功
$ make
clang -c ... Anon.c
clang -shared ... Anon.o -o blib/arch/auto/Package/Anon/Anon.so
chmod 755 blib/arch/auto/Package/Anon/Anon.so

# 安装成功
$ make install DESTDIR=$TEST_PREFIX
Installing .../auto/Package/Anon/Anon.so
Installing .../Package/Anon.pm

# Conan 验证通过
$ ohc-run.py conan-verify perl-package-anon 0.05-r16
✅ G0: PASS  ✅ G1: PASS  ✅ G2: PASS  ✅ G3: PASS  ✅ G4: PASS
✅ L2: PASS  ✅ L4: PASS  ✅ L5: PASS
✅ 配方验证通过: perl-package-anon 0.05-r16

# test_package 测试
✅ Found: .../Package/Anon.pm
✅ Found: .../auto/Package/Anon/Anon.so
✅ ELF check passed: ELF shared object, 64-bit LSB arm64
✅ Dynamic deps check passed (libc.so dependency verified)
⏭️ Perl XS module loading: SKIPPED (SELinux HMDFS restriction, E046)

# 签名
$ binary-sign-tool sign -inFile Anon.so -outFile Anon.so.signed -selfSign 1
✅ add codesign section success

# HNP 包
$ hnpcli pack -i ... -o ... -n perl-package-anon -v 0.05-r16
✅ PackHnp end. ret=0

# 测试失败（平台限制，非编译缺陷）
$ make test
Can't load '.../Anon.so': Permission denied  # SELinux 限制，E046
# 解决方案：安装 HNP 包到 /data/service/hnp 系统目录
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/Anon.so | 13568 bytes | XS 共享库 (已签名) |
| packaging/Anon.so.unsigned | 13568 bytes | XS 共享库 (未签名) |
| packaging/Anon.pm | 4888 bytes | Perl 模块 |
| packaging/perl-package-anon.hnp | 9441 bytes | HNP 安装包 |
| packaging/perl-package-anon-0.05-r16-ohos-aarch64.tar.gz | 31255 bytes | tar.gz 预编译包 |
| packaging/perl-package-anon-0.05-r16-ohos-aarch64-debug.tar.gz | 21015 bytes | tar.gz 调试包 |
| conanfile.py | 3.4KB | Conan 配方 |
| conandata.yml | 271 bytes | 源码+补丁声明 |
| test_package/ | - | 测试包 (文件+ELF+依赖+加载) |
| reports/test-report.md | - | 功能测试报告 |
| reports/reviewer-report.md | - | 上库评估报告 |
| reports/conan-verify-report.md | - | Conan 验证报告 |
| 安装路径: /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/ | - | 系统安装目录 |

## 注意事项

1. **OHOS sysroot 路径**: Perl 5.42.0 的 Config 中 incpth 指向 `/opt/llvm-21.1.5-ohos-arm64/` (不存在)，实际 sysroot 在 `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot`
2. **libunwind.a**: 位于 OHOS SDK LLVM lib 目录，非 sysroot
3. **CRT 文件缺失**: 鸿蒙系统缺少 crti.o, crtn.o 等，使用 -nostartfiles -nodefaultlibs -lc 绕过 (perl-dbd-pg 经验)
4. **测试限制**: OHOS 平台 SELinux 阻止 HMDFS 上加载 .so (hmdfs:s0)，需安装到 /data/service/hnp (hnp_file:s0)
5. **纯 Perl 模块说明**: 本模块含 XS 组件 (Anon.xs)，非纯 Perl，需要 C 编译器
6. **Conan 配方**: conan-verify 8 道门禁全部通过，可标记 published
---

**编译结束**: 2026-07-02 16:55
**最终状态**: built (conan-verify 通过，可提交 PR)
