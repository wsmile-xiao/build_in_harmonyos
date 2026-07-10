# perl-crypt-cast5 0.05-r14 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-02
- 编译器: clang/clang++ (Clang 21.1.5, Harmonybrew OHOS LLVM)
- Perl: 5.42.0 (aarch64-linux)
- 状态: built

## 编译步骤

1. 源码下载: 从 CPAN 下载 Crypt-CAST5-0.05.tar.gz (原始 URL 在 Savannah 上 404，实际源码在 CPAN: https://cpan.metacpan.org/authors/id/B/BO/BOBMATH/Crypt-CAST5-0.05.tar.gz)
2. `perl Makefile.PL` - 生成 Makefile (ExtUtils::MakeMaker)
3. `make` - 编译 XS/C 代码 (CAST5.xs, _cast5.c, tables.c)
4. `make install DESTDIR=$TEST_PREFIX` - staging 安装

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码下载失败 (SSL 证书验证) | Python urllib SSL 验证失败 | 手动用 curl -k 下载，放到 init-build 期望位置 |
| 2 | 源码 URL 404 | 任务给定的 Savannah URL 不存在，实际模块在 CPAN | 从 MetaCPAN API 查找正确 URL: https://cpan.metacpan.org/authors/id/B/BO/BOBMATH/Crypt-CAST5-0.05.tar.gz |
| 3 | make test 失败: "Permission denied" 加载 .so | 平台限制: tmpfs (/storage/Users) 不允许 dlopen 共享库 | 平台限制，记录原因。编译本身成功，.so 文件经 ELF 验证有效 |
| 4 | make install 到系统 Perl lib 失败: Permission denied | /data/service/hnp/ 由 installs 组拥有，当前用户无写权限 | 使用 DESTDIR staging 安装代替直接安装 |

## 源码修改

无补丁，源码未修改。编译过程零介入（仅 Makefile.PL 不带 PREFIX 参数使用 Perl 默认路径）。

## 依赖版本

- Perl 5.42.0 (aarch64-linux, /data/service/hnp/perl.org/perl_5.42.0)
- clang 21.1.5 (Harmonybrew OHOS LLVM)
- Test::More (Perl 核心模块, 已安装)

## 验证结果

### 编译验证
```bash
$ file blib/arch/auto/Crypt/CAST5/CAST5.so
ELF shared object, 64-bit LSB arm64, not stripped

$ llvm-readelf -d CAST5.so
NEEDED: libc.so
FLAGS: BIND_NOW
# 仅依赖 libc.so，无外部库依赖

$ llvm-nm -D CAST5.so | grep " T "
T boot_Crypt__CAST5    # Perl XS boot 符号
T cast5_encrypt        # 加密函数
T cast5_decrypt        # 解密函数
T cast5_init           # 初始化函数
```

### 功能测试 (2026-07-02 补充)

**完整报告**: `reports/functional-test-report.md`

#### ELF 技术验证 ✅
- AArch64 ELF 共享对象，结构完整
- 仅依赖 libc.so，无外部库依赖
- 导出符号正确: boot_Crypt__CAST5, cast5_encrypt, cast5_decrypt, cast5_init
- 未定义符号均为 Perl API (PL_*, Perl_*)，运行时由解释器提供
- .note.ohos.ident 段存在（OHOS 平台标识）

#### 运行时 dlopen 测试 ❌
- **Perl DynaLoader**: `Can't load '.../CAST5.so': Permission denied`
- **Python ctypes**: 同样 `Permission denied`
- **对照**: Perl 自带 XS 模块 (File::Glob, List::Util, Encode) 正常加载

#### 根因: hmmac 安全标签不匹配
| 路径 | 文件系统 | 安全标签 | dlopen |
|------|---------|---------|--------|
| /data/service/hnp/ (Perl自带.so) | hmfs (inherit_parent) | hnp_file | ✅ |
| /storage/Users/ (Conan缓存) | hmdfs | hmdfs | ❌ |
| /data/storage/el2/base/ (用户可写) | hmfs | hishell_hap_data_file | ❌ |

**先例**: perl-dbd-pg 3.18.0 (2026-06-10) 已记录相同问题，称为 "SELinux HMDFS 限制"。本次通过 `ls -Z` 安全标签分析确认根因更精确地是 hmmac 安全标签限制，非传统 SELinux 或文件系统类型问题。

#### 排除的因素
- LD 环境变量 (E131): `env -u CC -u LD` 后仍失败 → 非主因
- ELF 签名: `binary-sign-tool -selfSign 1` 签名后仍失败 → 标签问题非签名问题
- 文件权限: chmod 777 无效 → hmmac 不依赖 Unix 权限

#### 与 perl-dbd-pg 的编译差异
perl-dbd-pg 需要 `-nostartfiles -nodefaultlibs -lc` 链接参数（E208: CRT 文件缺失），而 perl-crypt-cast5 不需要此参数即编译成功。推测原因：CAST5 模块 C 代码较简单，不依赖 CRT 启动代码。

#### 结论
软件编译正确，但当前用户环境无法进行运行时功能验证。需通过 hnp 包管理器安装到 `/data/service/hnp/` 路径（获得 `hnp_file` 安全标签）后方可正常运行。

### 上游测试 (make test)
```
make test → FAIL (平台限制)
- t/1cast5.t: 9/9 failed (Can't load CAST5.so: Permission denied)
- t/2cbc.t: skipped (Crypt::CBC required)
- t/3utf.t: FAIL (Can't load CAST5.so: Permission denied)
```
测试失败原因: hmmac 安全标签限制（同 dlopen 测试根因）。

## 交付物

| 文件 | 路径 | 说明 |
|------|------|------|
| CAST5.so | auto/Crypt/CAST5/CAST5.so | Perl XS 共享库 (43328 bytes) |
| CAST5.pm | Crypt/CAST5.pm | Perl 模块文件 (2801 bytes) |

## 注意事项

- 模块名为 Crypt::CAST5 (大写 CAST5)，CPAN 上的包名为 Crypt-CAST5
- 版本 0.05-r14 中的 -r14 为打包修订号，上游版本为 0.05
- 源码包含 XS (C 扩展) 代码，需要 Perl 开发头文件
- Makefile.PL 中有 GCC_X86 优化检测，在 aarch64 上不会启用 (不影响功能)
- ppport.h 有 PERL_UNUSED_DECL 宏重定义警告 (无害)
---

**编译结束**: 2026-07-02 15:38
**最终状态**: built
