# perl-net-dns 1.53-r0 适配笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-25
- 编译器: clang/clang++ (纯 Perl 模块，无 C 编译)
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: published

## 编译步骤

1. 从 CPAN 下载源码: `Net-DNS-1.53.tar.gz`
2. 解压源码到构建目录
3. 执行 `perl Makefile.PL` 生成 Makefile
4. 执行 `make` 构建模块
5. 执行 `make install DESTDIR=...` 安装到 staging 目录
6. 从 staging 目录提取 `Net/` 目录树到 Conan 包的 `lib/perl5/` 目录
7. 设置 `PERL5LIB` 环境变量指向包的 lib 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conanfile.py package() 方法包含硬编码本地路径 | 自动生成的 conanfile.py 中 package() 方法引用了 `/storage/Users/currentUser/` 路径，无法在 CI 环境中使用 | 重写 package() 方法，使用 DESTDIR + glob 模式递归查找并复制 Net/ 目录树 |
| 2 | conandata.yml 源码 URL 为本地 file:// 路径 | 初始编译使用本地 tarball，URL 未更新为 CPAN 地址 | 更新为 `https://cpan.metacpan.org/authors/id/N/NL/NLNETLABS/Net-DNS-1.53.tar.gz` |
| 3 | conan-verify G4 失败: 无任何产物 | package() 方法因硬编码路径失败，未将 .pm 文件复制到包目录 | 修复 package() 方法后，正确复制 Net/ 目录树到 lib/perl5/ |
| 4 | conanfile.py settings 包含 compiler 和 build_type | 纯 Perl 模块不需要编译器设置，Conan profile os=Linux 在 settings.yml 中没有 cpu 子属性 | 简化为 `settings = "os", "arch"` |

## 源码修改

无补丁。Net::DNS 是纯 Perl 模块，源码无需任何修改即可在鸿蒙平台编译和运行。

## 依赖版本

- Perl 5.42.0 (系统自带)
- ExtUtils::MakeMaker (Perl 自带)
- 无其他运行时依赖

## 验证结果

### conan create + test_package

```bash
$ conan create . --profile=ohos-aarch64
perl-net-dns/1.53-r0@ohpcd/stable: Exported package recipe
perl-net-dns/1.53-r0@ohpcd/stable: Test package: Running test()
perl-net-dns/1.53-r0@ohpcd/stable: RUN: perl -e "use Net::DNS; print Net::DNS->version"
1.53
```

### 模块功能验证

```perl
use Net::DNS;
my $resolver = Net::DNS::Resolver->new();
my $reply = $resolver->query("example.com", "A");
print "DNS query successful\n" if $reply;
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (修复 settings 和 package() 方法) |
| conandata.yml | 源码 URL + SHA256 (CPAN 地址) |
| test_package/conanfile.py | Conan 测试包 (验证 Net::DNS 可加载) |

## 注意事项

1. **纯 Perl 模块无 SELinux 限制**: Net::DNS 不加载 .so 文件，不受 HMDFS/SELinux 权限限制
2. **多文件复制**: Net::DNS 包含 DNS.pm + DNS/ 子目录（含 RR/ 下大量资源记录类），package() 需递归复制整个 Net/ 树
3. **settings 简化**: 纯 Perl 模块的 conanfile.py 只需 `"os", "arch"`，与 perl-net-cidr 等同类模块一致

---

**编译结束**: 2026-06-25 15:44
**最终状态**: published
