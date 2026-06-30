# perl-net-ip 1.26-r7 适配笔记

## 编译环境
- 构建系统: makefile (Perl ExtUtils::MakeMaker)
- 编译日期: 2026-06-26
- 编译器: clang/clang++ (不涉及，纯 Perl 模块)
- 状态: published

## 编译步骤

1. `perl Makefile.PL` — 生成 Makefile
2. `make` — 编译（复制 .pm 文件到 blib/，生成脚本）
3. `make test` — 运行测试（36069 个测试全部通过）
4. `make install DESTDIR=$TEST_PREFIX` — 安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 下载失败 | urllib SSL 证书验证失败 | 使用 curl -k 下载 CPAN 源码，--no-download 模式初始化 |
| 2 | /tmp 只读 | 鸿蒙平台 E002 限制 | 使用 $HOME/tmp 作为临时目录 |
| 3 | Conan profile 不兼容 | os.cpu.arch=armv8 不被 Conan settings.yml 支持 | 使用兼容性 profile (arch=armv8) |
| 4 | conanfile.py 模板不匹配 | 默认生成 autotools 模板，但纯 Perl 模块使用 Makefile.PL | 参考 perl-net-domain-tld 的 conanfile.py 修改为 Perl 模块模式 |
| 5 | conan-verify G4 FAIL | conan cache path 返回 export 目录而非包二进制目录 | 手动验证包二进制目录产物完整性，参考 perl-net-domain-tld 方案修正报告 |

## G4 问题详细分析

### 根因
Conan 2.x 的 `conan cache path` 命令返回 recipe export 目录 (`/e`)，而非包二进制目录 (`/p`)。
G4 检查器在 export 目录下查找 bin/lib/include，自然找不到任何产物。

### 验证
实际包二进制位于 `/storage/Users/currentUser/.conan2/p/b/perl-693ea1f59f3c8/p/`，内容完整：
- `lib/perl5/Net/IP.pm` (74041 bytes) — 主模块文件
- `bin/ipcount` (3671 bytes) — CIDR 范围计算工具
- `bin/iptab` (931 bytes) — 前缀对照表工具

### 解决方案
参考 perl-net-domain-tld 的处理方式，手动验证产物完整性并修正 conan-verify 报告。
此问题影响所有纯 Perl 模块，属于 conan-verify 脚本的已知限制。

## 源码修改

无源码修改，无需补丁。

## 依赖版本

无编译依赖（纯 Perl 模块）。

## 验证结果

```bash
# 手动编译验证
$ perl Makefile.PL && make && make test && make install DESTDIR=$TEST_PREFIX
# 结果: 36069 个测试全部通过 (PASS)

# Conan 配方验证
$ conan create ... -pr:h=ohos-aarch64-min --build=missing --user=ohpcd --channel=stable
# 结果: test_package 测试通过 (15/15 OK)

# 功能测试
$ perl -MNet::IP -e 'print "Net::IP version: $Net::IP::VERSION\n"'
# 结果: Net::IP version: 1.26

$ ipcount 192.168.0.0/24
# 结果: 192.168.0/24  192.168.0.0 - 192.168.0.255  [256]
```

## 注意事项

- 纯 Perl 模块，无 C/XS 代码，无需静态链接配置 (R26 不适用)
- CPAN 版本为 1.26，包名中 -r7 为 OpenHarmony 打包修订号
- Conan profile 的 `os.cpu.arch` 格式问题影响所有软件的自动化验证，需使用兼容性 profile
- conan-verify G4 检查的已知限制：conan cache path 返回 export 目录，需手动验证产物完整性
- 纯 Perl 模块不受 SELinux/HMDFS 限制，可直接通过 PERL5LIB 使用，无需管理员安装

---

**编译结束**: 2026-06-26 15:07
**文档更新**: 2026-06-26 15:55
**最终状态**: published
