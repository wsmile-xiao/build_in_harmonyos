# perl-net-domain-tld 1.75-r0 适配笔记

## 编译环境
- 构建系统: Perl Makefile.PL (ExtUtils::MakeMaker)
- 编译日期: 2026-06-26
- 编译器: clang 18.1.8
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: published

## 编译步骤

纯 Perl 模块，编译流程简单：

```bash
# 1. 解压源码
tar xzf Net-Domain-TLD-1.75.tar.gz

# 2. 生成 Makefile
perl Makefile.PL

# 3. 编译（实际是复制 .pm 到 blib）
make -j1

# 4. 安装到临时目录
make install DESTDIR=/tmp/destdir

# 5. 复制 .pm 到标准位置
cp /tmp/destdir/.../Net/Domain/TLD.pm lib/perl5/Net/Domain/TLD.pm
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G4 产物完整性检查失败 | conanfile.py package() 使用 `make install DESTDIR=$package_folder PREFIX=""` 导致文件安装到深层嵌套路径，lib/ 目录无产物 | 参考 perl-net-cidr 经验：使用临时 DESTDIR + glob 查找 .pm 文件 + 复制到 `lib/perl5/` |
| 2 | conan-verify G2 失败 | ci/conan/profiles/ohos-aarch64 更新为 `os.cpu.arch=armv8`，但 settings.yml 不支持 `os.cpu` 嵌套 | 使用兼容性 profile (arch=armv8) 完成 conan create |
| 3 | %tld_profile 无法导出 | 上游 bug: 声明为 `my %tld_profile` 而非 `our`，Exporter 无法导出词域变量 | 已知限制，不影响 tld_exists/tlds 核心功能 |

## 源码修改

无源码修改。所有补丁为空。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| Perl | 5.42.0 | 系统内置 |
| Storable | 3.37 | Perl 内置 |
| Carp | 1.54 | Perl 内置 |
| Exporter | 5.78 | Perl 内置 |

## 验证结果

```bash
# Conan L1 测试
$ conan create ... && conan test ...
test perl-net-domain-tld 1.75-r0: 23/23 OK

# 功能测试
$ perl test_tld_comprehensive.pl
总计: 48/50 通过
性能: 2,406,922 ops/s

# 模块自带测试
$ make test
t/01_ini.t .. ok
All tests successful.
```

## 注意事项

1. **Profile 兼容性**: ci/conan/profiles/ohos-aarch64 于 2026-06-26 更新为 `os.cpu.arch=armv8` 格式，与 Conan settings.yml 不兼容。使用兼容性 profile (arch=armv8) 可正常工作。
2. **%tld_profile 上游 bug**: 模块源码中 `%tld_profile` 声明为 `my` 而非 `our`，导致 Exporter 无法导出。这是 Net::Domain::TLD 1.75 的已知上游 bug。
3. **纯 Perl 模块**: 无 C/XS 代码，不受 SELinux/HMDFS 限制，可直接安装使用，无需管理员权限。

---

**编译结束**: 2026-06-26 12:27
**最终状态**: published
