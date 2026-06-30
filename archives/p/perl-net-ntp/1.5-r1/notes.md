# perl-net-ntp 1.5-r1 适配笔记

## 编译环境
- 构建系统: Perl Makefile.PL (ExtUtils::MakeMaker)
- 编译日期: 2026-06-26
- 编译器: N/A (纯 Perl 模块，无 C/XS 编译)
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: published

## 编译步骤

1. 下载源码: `Net-NTP-1.5.tar.gz` from CPAN
2. 解压源码到构建目录
3. `perl Makefile.PL` — 生成 Makefile
4. `make` — 构建模块（纯 Perl，仅处理 .pm 文件）
5. `make install DESTDIR=$TEST_PREFIX` — 安装到 staging 目录
6. Conan 打包: `conan create` + `conan-verify` (8 道门禁全部通过)

### Conan 配方

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init perl-net-ntp 1.5-r1
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify perl-net-ntp 1.5-r1
```

Conan 验证结果: 全部 8 道门禁 PASS (G0-G4 + L2/L4/L5)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `get_ntp_response()` 段错误 (SIGSEGV) | OHOS 平台 `getservbyname("ntp", "udp")` 实现有缺陷，调用即崩溃（C 级别段错误，eval 无法捕获） | 补丁 `0001-fix-ohos-getservbyname-segfault.patch`: 将默认端口从服务名 `'ntp'` 改为数字 `123` |
| 2 | 模块未安装到系统 Perl 路径 | Conan 包安装到 Conan 缓存，需手动安装或通过 HNP 包安装 | 纯 Perl 模块，可通过 `conan install` 或手动复制 `.pm` 文件到 `site_perl` 目录 |

## 源码修改

### 0001-fix-ohos-getservbyname-segfault.patch

修改文件: `lib/Net/NTP.pm`

将 `get_ntp_response` 函数中的默认端口从服务名 `'ntp'` 改为数字 `123`：

```diff
- my $port = shift || 'ntp';
+ my $port = shift || 123;
```

**原因**: OHOS 平台的 `getservbyname()` 函数对某些 UDP 服务名查询存在段错误缺陷。`IO::Socket::INET->new(PeerPort => 'ntp')` 内部调用 `getservbyname("ntp", "udp")` 导致进程崩溃。使用数字端口 123 绕过此问题，功能完全等价（NTP 服务标准端口为 123/udp）。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| Perl | 5.42.0 | 系统预装 (HNP) |
| Time::HiRes | 1.9764 (core) | Perl 核心模块 |
| IO::Socket | (core) | Perl 核心模块 |

## 验证结果

```bash
# Conan 验证
$ conan-verify perl-net-ntp 1.5-r1
→ G0: PASS | G1: PASS | G2: PASS | G3: PASS | G4: PASS
→ L2: PASS | L4: PASS | L5: PASS

# 功能测试
$ perl -I$NTP_LIB -MNet::NTP -e 'print $Net::NTP::VERSION'
→ 1.5

$ perl -I$NTP_LIB -e 'use Net::NTP qw(get_ntp_response); my %r = get_ntp_response("pool.ntp.org", 123); print "Stratum: $r{Stratum}\n"'
→ Stratum: 2
```

## 注意事项

1. **OHOS getservbyname 缺陷**: 此问题影响所有使用服务名（非数字端口）的网络模块。建议其他 Perl 网络模块适配时也注意此问题。
2. **纯 Perl 模块优势**: Net::NTP 是纯 Perl 实现，无 XS/C 编译，不受 SELinux HMDFS 限制影响（与 perl-dbd-pg 的 XS 模块不同），安装后可直接使用。
3. **补丁应用方式**: 通过 Conan 的 `apply_conandata_patches()` 自动应用，记录在 `conandata.yml` 中。

---

**编译结束**: 2026-06-29
**最终状态**: published
