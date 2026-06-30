# perl-net-dns-resolver-mock 1.20230216-r1 适配笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-25
- 编译器: clang/clang++ (纯 Perl 模块，无 C 编译)
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: built

## 编译步骤

1. 从 CPAN 下载源码: `Net-DNS-Resolver-Mock-1.20230216.tar.gz`
2. 解压源码到构建目录
3. 执行 `perl Makefile.PL INSTALL_BASE=/usr/local` 生成 Makefile
4. 执行 `make -j1` 构建模块
5. 执行 `make install DESTDIR={package_folder}` 安装到 Conan 包目录
6. 从 `blib/lib` 复制 `.pm` 文件到包的 `lib/` 目录，满足 Conan G4 产物完整性检查
7. 在 `package_info()` 中通过 `runenv_info`/`buildenv_info` 设置 `PERL5LIB` 环境变量

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G4 产物完整性检查无法发现 .pm 文件 | Conan 默认只扫描 bin/lib/include 下的标准产物，Perl .pm 文件在 blib/lib 中 | 在 package() 中显式 copy `*.pm` 从 `blib/lib` 到 `package_folder/lib` |
| 2 | 下游消费者无法找到 Perl 模块路径 | Conan 不自动传播 Perl 模块路径 | 在 package_info() 中设置 `PERL5LIB` 环境变量指向包的 lib 目录 |

## 源码修改

无补丁。Net::DNS::Resolver::Mock 是纯 Perl 模块，源码无需任何修改即可在鸿蒙平台编译和运行。

## 依赖版本

- Perl 5.42.0 (系统自带)
- ExtUtils::MakeMaker (Perl 自带)
- 无其他运行时依赖

## 验证结果

### conan-verify 结果 (全部通过)

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 | ✅ PASS | 预构建风险评估通过 |
| G1 | ✅ PASS | 配方完整性检查通过 |
| G2 | ✅ PASS | conan create 成功 |
| G3 | ✅ PASS | 无 bin/ 目录，跳过静态链接检查 |
| G4 | ✅ PASS | 产物完整性检查通过 (lib/ 下 89 个 .pm 文件) |
| L2 | ✅ PASS | 无 bin/ 目录，跳过 smoke test |
| L4 | ✅ PASS | 无 ELF 文件，跳过安全扫描 |
| L5 | ✅ PASS | 产物基线对比通过 |

### 功能测试结果 (2/2 PASS)

```bash
$ perl -I"{pkg_lib}" test.pl
1..2
ok 1 - use Net::DNS::Resolver::Mock;
ok 2 - An object of class 'Net::DNS::Resolver::Mock' isa 'Net::DNS::Resolver::Mock'
test perl-net-dns-resolver-mock 1.20230216-r1: OK
```

## 注意事项

- 该模块依赖 Net::DNS 作为运行时依赖，但 Net::DNS 源码已包含在 tarball 中（作为内嵌依赖），因此 conanfile.py 的 requirements() 为空
- 产物包含 89 个 .pm 文件，涵盖完整的 Net::DNS 模块树

---

**编译结束**: 2026-06-25 16:01
**最终状态**: built
