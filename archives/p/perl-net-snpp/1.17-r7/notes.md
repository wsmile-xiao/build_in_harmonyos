# perl-net-snpp 1.17-r7 适配笔记

## 编译环境
- 构建系统: custom (ExtUtils::MakeMaker / perl Makefile.PL)
- 编译日期: 2026-06-26
- 编译器: clang/clang++ (未使用，纯 Perl 模块)
- 状态: built

## 编译步骤

Net::SNPP 是纯 Perl 模块，使用 ExtUtils::MakeMaker 构建系统。

```bash
# 1. 下载源码
curl -LO https://cpan.metacpan.org/authors/id/T/TO/TOBEYA/Net-SNPP-1.17.tar.gz

# 2. 解压
tar xzf Net-SNPP-1.17.tar.gz
cd Net-SNPP-1.17

# 3. 生成 Makefile
perl Makefile.PL

# 4. 构建（纯 Perl，无 C 编译）
make

# 5. 安装到 staging 目录
make install DESTDIR=$TEST_PREFIX

# 6. Conan 打包
conan create . perl-net-snpp/1.17-r7@ohpcd/stable
```

构建过程中无需修改源码，Makefile.PL 正常识别系统 Perl 5.42.0。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | 纯 Perl 模块，编译顺利 | 无需修复 |

无编译错误。模块为纯 Perl 实现，不涉及 C/XS 编译，无需平台适配补丁。

## 源码修改

无修改。源码未经任何改动即可在鸿蒙平台编译运行。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| Perl | 5.42.0 | 系统安装 (aarch64-linux) |
| Net::Cmd | 3.15 | Perl 核心库 (libnet) |
| ExtUtils::MakeMaker | 7.70 | Perl 核心库 |

## 验证结果

### Conan 验证 (conan-verify)

```
G0: ✅ PASS  构建系统识别
G1: ✅ PASS  配方完整性 (conanfile.py + conandata.yml + test_package/)
G2: ✅ PASS  conan create 成功
G3: ✅ PASS  系统同名库隔离 (纯 Perl，无 .so)
G4: ✅ PASS  产物完整性 (3 .pm 文件)
L2: ✅ PASS  smoke test (无 bin/，跳过)
L4: ✅ PASS  安全扫描 (无 ELF 文件)
L5: ✅ PASS  产物基线 (5 个文件一致)
```

### 功能测试

```
Net::SNPP loaded OK, version: 1.17
Net::SNPP::Server loaded OK
Net::SNPP::HylaFAX loaded OK, version: 1.01
parse_response: 7/7 passed
SNPP API methods: 24/24 available
RFC 1861 Level 1-3 commands: all present
Example scripts syntax: 3/3 OK
Total: 16 PASS, 1 FAIL (platform limitation)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/perl5/Net/SNPP.pm | 14495 bytes | 主模块 |
| lib/perl5/Net/SNPP/Server.pm | 26213 bytes | SNPP 服务器模块 |
| lib/perl5/Net/SNPP/HylaFAX.pm | 2270 bytes | HylaFAX 扩展模块 |

## 注意事项

1. **纯 Perl 模块优势**: Net::SNPP 是纯 Perl 实现，不依赖任何 C/XS 扩展。在 HMDFS 上不受 SELinux 限制，可直接通过 `PERL5LIB` 环境变量加载。这与 perl-dbd-pg 不同（后者需要 XS 模块和 HNP 安装）。

2. **Server socket bind 限制**: `Net::SNPP::Server->new()` 需要绑定端口监听，受 SELinux HMDFS 限制（`Permission denied`）。这是平台限制，非模块缺陷。如需运行 SNPP 服务器，需将 Perl 安装到系统目录（`/data/service/hnp/`）或获得相应权限。

3. **PERL5LIB 使用方式**: 消费者安装此包后，Conan 会自动设置 `PERL5LIB` 指向 `lib/perl5` 目录，Perl 可直接 `use Net::SNPP`。

---

**编译结束**: 2026-06-26 18:04
**功能测试**: 2026-06-30
**最终状态**: built
