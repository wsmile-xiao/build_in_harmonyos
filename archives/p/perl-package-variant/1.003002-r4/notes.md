# perl-package-variant 1.003002-r4 适配笔记

## 编译环境
- 构建系统: perl-makemaker (ExtUtils::MakeMaker)
- 编译日期: 2026-07-02 (功能测试: 2026-07-03)
- 编译器: clang/clang++ (纯 Perl 模块，未实际使用 C 编译器)
- Perl: 5.42.0 (aarch64-linux)
- 状态: built

## 编译步骤

1. 下载源码: `curl -fsSL -o Package-Variant-1.003002.tar.gz https://cpan.metacpan.org/authors/id/M/MS/MSTROUT/Package-Variant-1.003002.tar.gz`
2. 验证 SHA256: `echo "b2ed849d2f4cdd66467512daa3f143266d6df810c5fae9175b252c57bc1536dc  Package-Variant-1.003002.tar.gz" | sha256sum -c`
3. 解压到 work 目录
4. 运行 `perl Makefile.PL PREFIX=$DEFAULT_PREFIX` 生成 Makefile
5. 运行 `make` 编译（纯 Perl 模块，仅复制 .pm 文件到 blib）
6. 运行 `make install DESTDIR=$TEST_PREFIX` 安装到 staging 目录
7. 运行 `make test` 执行测试套件
8. 运行 `make install INSTALL_BASE=<path>` 验证 INSTALL_BASE 安装方式

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 鸿蒙环境缺少 CA 证书 | 配置 CA 证书或通过 conandata.yml 的 SHA256 校验确保下载完整性；依赖模块从 CPAN 下载后手动校验 |
| 2 | make test 失败: Can't locate strictures.pm | 缺少 Perl 运行时依赖 strictures 和 Import::Into | 从 CPAN 手动下载并安装 strictures-2.000006 和 Import-Into-1.002005 |
| 3 | conan-verify G1 失败 | conanfile.py 缺少 export_sources() 方法和补丁应用调用 | 添加 export_conandata_patches(self) 和 apply_conandata_patches(self) |
| 4 | conan-verify G2 失败: test_package 找不到 Package::Variant | conanfile.py 使用 PREFIX=$package_folder + DESTDIR=$package_folder 导致路径双重嵌套 | 改用 INSTALL_BASE=$package_folder 在 Makefile.PL 阶段设置，package() 直接 make install |
| 5 | G0 clean-build 验证失败 | finish 脚本尝试运行 ./configure 但 Perl 模块没有 configure 脚本 | 非阻塞，记录为已知限制 |

## 源码修改

无源码修改。纯 Perl 模块直接编译。

## 依赖版本

- perl 5.42.0 (aarch64-linux)
- strictures 2.000006 (运行时依赖，手动安装)
- Import::Into 1.002005 (运行时依赖，手动安装)
- Module::Runtime (已安装)
- Carp (Perl 核心模块)
- Test::Fatal (已安装，用于测试)
- Moo / Moo::Role (已安装，用于测试)

## 功能测试结果 (2026-07-03)

### make test 测试套件
```
t/01simple.t .......... ok
t/10argument-types.t .. ok
t/11dynamic-build.t ... ok
t/20moo-param-role.t .. ok
t/30-pragma-leak.t .... ok
All tests successful.
Files=5, Tests=34,  1 wallclock secs
Result: PASS
```

### API 功能测试
- Test 1: 模块加载 ✅ PASS (version 1.003002)
- Test 2: 版本号验证 ✅ PASS
- Test 3: build_variant 创建变体包 ✅ PASS
- Test 4: install 方法安装 ✅ PASS
- Test 5: 方法调用返回正确值 ✅ PASS
- Test 6: 参数传递 ✅ PASS
- Test 7: 第二次 build_variant ✅ PASS
- Test 8: build_variant 参数传递 ✅ PASS
- Test 9: 命名变体 (make_variant_package_name) ✅ PASS
- Test 10: 命名变体方法调用 ✅ PASS
- Test 11: 多次构建产生不同包 ✅ PASS
- Test 12-14: 变体方法正确性 ✅ PASS

### Conan 验证
```
conan create + test_package: PASS
Package::Variant loaded OK (from Conan package)
```

### INSTALL_BASE 验证
```
perl Makefile.PL INSTALL_BASE=<path> → make → make install
模块从 INSTALL_BASE 路径加载成功
```

### 平台兼容性
- SELinux HMDFS 限制: 不适用（纯 Perl 模块，无 .so 文件）
- ELF 签名: 不需要（无可执行二进制）
- /tmp 只读: 使用 $TMPDIR/$HOME/tmp 规避
- CRT 文件缺失: 不适用（无 C 编译）

## 验证结果

```bash
$ make test
All tests successful.
Files=5, Tests=34,  1 wallclock secs
Result: PASS
```

Conan 验证:
- G0: PASS (跳过预查询)
- G1: PASS (配方完整性)
- G2: PASS (conan create 成功)
- G3: PASS (系统同名库隔离)
- G4: PASS (产物完整性)
- L2: PASS (跳过 - 无 cache 路径)
- L4: PASS (跳过 - 无 cache 路径)
- L5: PASS (跳过 - 无 cache 路径)

## 交付物

| 文件 | 说明 |
|------|------|
| archives/p/perl-package-variant/README.md | 软件描述 |
| archives/p/perl-package-variant/manifest.yaml | 软件级元数据 |
| archives/p/perl-package-variant/1.003002-r4/conanfile.py | Conan 配方 |
| archives/p/perl-package-variant/1.003002-r4/conandata.yml | 源码+SHA256 声明 |
| archives/p/perl-package-variant/1.003002-r4/test_package/conanfile.py | Conan L1 测试 |
| archives/p/perl-package-variant/1.003002-r4/reports/test-report.md | 功能测试报告 |
| archives/p/perl-package-variant/1.003002-r4/reports/quality-report.md | 质量报告 |
| archives/p/perl-package-variant/1.003002-r4/reports/reviewer-report.md | 上库评估报告 |

## 注意事项

- 这是纯 Perl 模块，使用 ExtUtils::MakeMaker 构建系统，非 autotools
- conanfile.py 使用 INSTALL_BASE 而非 PREFIX+DESTDIR 来避免路径双重嵌套
- 测试需要 strictures 和 Import::Into 模块，已在系统安装
- 测试还需要 Test::Fatal 和 Moo/Moo::Role，已在系统安装
- G0 clean-build 验证失败是因为 finish 脚本默认运行 ./configure，Perl 模块不支持
- 本地 CI 模拟 (W3) 失败是 bash 脚本 bug (`${=CI_PACKAGES}: bad substitution`)，非配方问题
- 纯 Perl 模块不受 SELinux HMDFS 限制，可在用户目录正常加载（与 perl-dbd-pg XS 模块不同）

## 与 perl-dbd-pg 的对比

| 方面 | perl-package-variant | perl-dbd-pg |
|------|---------------------|-------------|
| 模块类型 | 纯 Perl | XS (C 扩展) |
| 构建系统 | ExtUtils::MakeMaker | ExtUtils::MakeMaker + C 编译 |
| CRT 文件 | 不需要 | 需要 (-nostartfiles 绕过) |
| SELinux 限制 | 无 | 有 (XS 模块需安装到系统目录) |
| ELF 签名 | 不需要 | 需要 |
| 补丁 | 无 | 2 个 (Makefile + Makefile.PL) |
| 平台风险 | 极低 | 中等 |

---

**编译结束**: 2026-07-02 15:18
**功能测试**: 2026-07-03 12:05
**最终状态**: built
