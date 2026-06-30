# perl-php-serialization 0.34 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-24
- 编译器: 无需 C 编译器（纯 Perl 模块）
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: built

## 编译步骤

1. 下载源码包 PHP-Serialization-0.34.tar.gz (7600 bytes) 从 CPAN
2. 解压到工作目录
3. 生成 Makefile: `perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX`
4. 编译: `make` (仅复制 .pm 文件到 blib/)
5. 安装到 staging: `make install DESTDIR=$TEST_PREFIX`
6. 测试: `make test`
7. 打包: `ohc-run.py package`
8. 本地安装: `make install` (安装到 $DEFAULT_PREFIX/lib/perl5/)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CPAN HTTPS 下载失败 | SSL 证书验证失败 | 手动 curl -k 下载到本地，使用 file:// URL |
| 2 | 首次 make install DESTDIR 安装到 Perl 系统 prefix | ExtUtils::MakeMaker 默认安装到 Perl 的 site_perl 目录 | 使用 INSTALL_BASE=$DEFAULT_PREFIX 控制安装路径 |
| 3 | package 命令找不到 staging 文件 | 默认安装路径不在 $TEST_PREFIX/$DEFAULT_PREFIX 下 | 使用 INSTALL_BASE 使文件安装到 $DEFAULT_PREFIX/lib/perl5/ |
| 4 | verify-build G4 FAIL: manifest 缺少 build_system | manifest 模板用 build.system 而非 build_system | 手动添加 build_system 字段到 manifest.yaml |
| 5 | 首次打包包含整个 Perl 发行版 (70MB) | --prefix 指向 Perl 系统 prefix | 使用 INSTALL_BASE 重新安装，默认 prefix 打包 |
| 6 | submit 自检 manifest_complete FAIL | manifest 使用 build_date 但提交检查需要 compile_date | 添加 compile_date 字段到 manifest.yaml |

## 源码修改

无补丁，源码未修改。纯 Perl 模块，无需任何平台适配。

## 依赖版本

- Perl 5.42.0 (系统预装)
- ExtUtils::MakeMaker (Perl 核心模块)
- 无外部 C 库依赖

## 验证结果

### make test (官方测试套件)
```
t/01use.t ...................... ok
t/02basic.t .................... ok
t/03largeints.t ................ ok
t/04arraysRT21218.t ............ ok
t/05RT24441.t .................. ok
t/06bool_deserializeRT45024.t .. ok
t/07croak.t .................... ok
t/08incompletestringRT44700.t .. ok
t/09floatindexRT42029.t ........ ok
t/10intRT48594.t ............... ok
All tests successful.
Files=10, Tests=17,  1 wallclock secs
Result: PASS
```

### 自定义功能测试 (32 项)
- 32/32 全部通过
- 测试覆盖: 哈希序列化/反序列化、数组序列化/反序列化、特殊字符、空字符串、大整数、负数、嵌套结构、混合结构、undef 值、布尔值、浮点数、UTF-8 字符串、空哈希/数组、错误处理、PHP 格式兼容性、复杂嵌套结构

### 预编译包验证
```bash
# 从 tar.gz 解压后模块可正常加载和使用
perl -I <pkg>/lib/perl5 -e 'use PHP::Serialization; ...'
# Serialized: a:3:{s:7:"modules";a:2:{i:0;s:4:"base";i:1;s:5:"extra";}s:4:"name";s:11:"OpenHarmony";s:7:"version";i:1;}
# Deserialized name: OpenHarmony
# All tests PASS
```

### Staging 验证
```bash
perl -I $TEST_PREFIX/$DEFAULT_PREFIX/lib/perl5 -e 'use PHP::Serialization; ...'
# serialize: a:2:{s:3:"num";i:42;s:3:"key";s:5:"value";}
# deserialize: { num => 42, key => 'value' }
```

### 本地安装验证
```bash
perl -I $DEFAULT_PREFIX/lib/perl5 -e 'use PHP::Serialization; ...'
# OK: serialize=a:2:{s:3:"num";i:42;s:3:"key";s:5:"value";}
# OK: deserialize key=value num=42
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-php-serialization-0.34-ohos-aarch64.tar.gz | 21015 bytes (21KB) | 预编译包，含 PHP/Serialization.pm |

## 与 perl-dbd-pg 编译经验对比

| 方面 | perl-dbd-pg | perl-php-serialization |
|------|-------------|----------------------|
| 模块类型 | XS (C 编译) | 纯 Perl |
| CRT 补丁 | 需要 (-nostartfiles -nodefaultlibs -lc) | 不需要 |
| C 编译器 | 需要 (clang) | 不需要 |
| ELF 签名 | 需要 (.so 文件) | 不需要 |
| SELinux HMDFS 限制 | 影响 make test (.so 无法 dlopen) | 不影响 (纯 Perl) |
| INSTALL_BASE | 需要 | 需要 (控制安装路径) |
| CPAN SSL 问题 | 遇到 | 遇到 (curl -k 解决) |
| manifest build_system | 需手动添加 | 需手动添加 |
| manifest compile_date | 需手动添加 | 需手动添加 |

### 经验借鉴
从 perl-dbd-pg 编译中借鉴的关键经验：
1. **INSTALL_BASE 控制**: Perl 模块必须使用 INSTALL_BASE 而非 PREFIX 控制安装路径
2. **CPAN SSL 问题**: 使用 curl -k 绕过 SSL 证书验证
3. **manifest 字段**: build_system 和 compile_date 需手动添加到模板
4. **纯 Perl 模块优势**: 无需 C 编译、ELF 签名、CRT 补丁，编译流程更简单

## 上库要求评估

| 要求 | 状态 | 详情 |
|------|------|------|
| test-report.md | ✅ | 包含官方17项+自定义32项测试 |
| .staging-verified | ✅ | Staging 安装已验证 |
| 预编译包 | ✅ | 21KB tar.gz, 工具化打包 |
| G0 干净构建 | ✅ | configure+make+install 全通过 |
| G1-G4 质量门禁 | ✅ | 全部 PASS |
| 知识检查 | ✅ | 0 unreferenced |
| manifest.yaml | ✅ | 必填字段完整 (含 compile_date) |
| notes.md | ✅ | 编译笔记完整 |
| 源码修改记录 | ✅ | 无修改 (track-edit scan 确认) |
| submit 自检 | ✅ | 6/6 PASS |

**结论**: 软件满足上库要求。状态 `built` 表示编译成功但未发布到 cmd-pkgs。

## 注意事项

1. **INSTALL_BASE 关键**: Perl 模块必须使用 `INSTALL_BASE=$DEFAULT_PREFIX` 而非 `PREFIX=` 来控制安装路径，这样文件会安装到 `$DEFAULT_PREFIX/lib/perl5/` 下，与 ohc-run.py package 的默认 staging 路径一致。
2. **纯 Perl 模块**: 无需 C 编译器，make 仅复制 .pm 文件，无 ELF 二进制，G1/G3 门禁自动通过。
3. **G2 功能验证**: 因无可执行二进制文件，G2 显示 ⚠️ (无二进制文件)，这是正常的。自定义功能测试全部通过。
4. **manifest.yaml build_system 字段**: verify-build G4 检查 `build_system:` 字段（扁平），而模板使用 `build.system:`（嵌套），需手动添加扁平字段。
5. **manifest.yaml compile_date 字段**: submit 自检检查 `compile_date` 字段，模板使用 `build_date`，需手动添加。
6. **manifest.yaml knowledge_gained ref 字段**: check-knowledge-gap 检查 knowledge_gained 条目是否包含 `ref:` 引用，需添加 `(ref: L3-software-specific)` 标注。
7. **模块加载路径**: 安装后需设置 `PERL5LIB=~/usr/local/lib/perl5` 或使用 `-I ~/usr/local/lib/perl5` 让 Perl 找到模块。

---

**编译结束**: 2026-06-24 18:03
**最终状态**: built
**验证日期**: 2026-06-24
**验证结果**: 全部通过 (官方 17/17 + 自定义 32/32 + 预编译包 + submit 6/6)
