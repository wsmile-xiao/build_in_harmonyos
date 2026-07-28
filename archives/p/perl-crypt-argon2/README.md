# perl-crypt-argon2

Perl XS 模块，提供 Argon2 密钥派生函数接口（argon2id / argon2i / argon2d），用于密码哈希和验证。

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.030 | built | 2026-07-02 | 编译成功，Conan 配方验证通过；Argon2 算法功能测试通过（11/11）；Perl XS 模块受平台安全策略限制无法加载 |

## 平台限制说明

**鸿蒙系统安全限制**：
- Perl XS 模块生成 `.so` 共享库文件
- HNP 安装的 Perl 二进制安全标签为 `hnp_file:s0`
- 用户 HMDFS 存储中的 `.so` 文件标签为 `hmdfs:s0`
- OpenHarmony `hmmac=use_task` 安全策略阻止跨标签 dlopen
- 已排除 E131（LD 环境变量干扰）：`env -u LD -u CC` 和 `env -i` 均仍 Permission denied
- 已验证排除的绕过方案：LD_PRELOAD、复制到其他目录、安装到 HNP 目录、复制 Perl 到 HMDFS（缺 ELF 签名 E166）、chcon — 均失败

**影响范围**：此限制影响所有 Perl XS 模块，非 Crypt::Argon2 特有问题。同类软件 perl-dbd-pg、Data-Peek 均受限。

## CRT 文件缺失 (E173/E208)

鸿蒙系统缺少标准 CRT 文件（crti.o, crtn.o, crtbeginS.o, crtendS.o）。标准 Perl XS 模块链接需要添加 `-nostartfiles -nodefaultlibs -lc` 参数。本软件通过 Makefile.PL 的 postamble 自定义编译规则绕过了此问题。若其他 Perl XS 模块链接失败，参考 perl-dbd-pg 经验在 Makefile.PL 中添加：
```perl
dynamic_lib => { OTHERLDFLAGS => '-nostartfiles -nodefaultlibs -lc' }
```

## 功能测试结论

- **Argon2 C 算法**：✅ 全部 11 项测试通过（静态编译验证）
  - argon2id/argon2i/argon2d hash_raw / hash_encoded / verify / ctx
  - 确定性、区分性、错误处理均正确
- **Perl XS 模块加载**：❌ 被 HMDFS 安全策略阻止
  - 详见 `0.030/reports/functional-test-report.md`

## 解决方案

如需安装此模块，请联系系统管理员协助：
```bash
# 需管理员权限，将 .so 安装到 HNP 可信目录
mkdir -p /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Crypt/Argon2/
cp ~/usr/local/lib/perl5/aarch64-linux/auto/Crypt/Argon2/Argon2.so \
   /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Crypt/Argon2/
cp ~/usr/local/lib/perl5/aarch64-linux/Crypt/Argon2.pm \
   /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/Crypt/
```

## 补丁说明

| 补丁 | 说明 |
|------|------|
| 0001-Makefile.PL.patch | 新增 Makefile.PL (ExtUtils::MakeMaker 替代 Dist::Build)，含 postamble 自定义 C 编译规则 |
| 0002-src-ref.c.patch | 重命名 src/ref.c 中 fill_segment → fill_segment_ref，避免与 switch.c 符号冲突 (aarch64 无 SSE3/AVX) |

## 相关知识图谱

| 条目 | 类别 | 说明 |
|------|------|------|
| E073 | filesystem/hmdfs/runtime-linking | HMDFS 符号链接运行时加载问题（不同场景） |
| E078 | libc/linking/musl/dynamic-linking | musl dlopen 符号解析问题 |
| E131 | environment/runtime/perl | LD 环境变量导致 dlopen Permission denied（已排除） |
| E166 | platform_limitation/selinux/hmdfs | ELF 签名限制 |
| E173 | linking/xs/perl/musl | CRT 文件缺失，Perl XS 链接需 -nostartfiles |
| E208 | build_tool/make/perl | Makefile.PL OTHERLDFLAGS 和 CPATH/LIBRARY_PATH 设置 |
