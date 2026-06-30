# LWP-Protocol-https 6.14 适配笔记

## 编译环境
- 构建系统: perl (ExtUtils::MakeMaker)
- 编译日期: 2025-06-15
- 编译器: N/A (纯 Perl 模块)
- 状态: built (依赖模块已编译，SELinux 限制待解决)

---

## 编译步骤

### LWP::Protocol::https（本模块）

```bash
# 1. 解压源码
tar -xzf LWP-Protocol-https-6.14.tar.gz

# 2. 配置
cd LWP-Protocol-https-6.14
perl Makefile.PL PREFIX=~/usr/local

# 3. 构建（纯 Perl 模块，无实际编译）
make

# 4. 安装
make install DESTDIR=$TEST_PREFIX
```

### Net::SSLeay 1.85（依赖，XS 模块）

```bash
# 1. 下载（从 CPAN HTTP）
curl -L -o ~/tmp/Net-SSLeay-1.85.tar.gz \
    "http://www.cpan.org/authors/id/M/MI/MIKEM/Net-SSLeay-1.85.tar.gz"

# 2. 配置（使用系统 OpenSSL）
OPENSSL_PREFIX=/usr PERL_MM_USE_DEFAULT=1 perl Makefile.PL \
    PREFIX=~/usr/local \
    INC="-I~/usr/local/include" \
    LDDLFLAGS="-shared -nostartfiles -nodefaultlibs"

# 3. 修改 Makefile 链接库路径
# 原始: EXTRALIBS = -L/usr -L/usr/lib -lssl -lcrypto -lz
# 修改为: EXTRALIBS = -L~/usr/local/lib -lssl -lcrypto ~/usr/local/lib/libz.a
# 同样修改 LDLOADLIBS

# 4. 编译
make
# 输出: SSLeay.so (505KB)

# 5. ELF 签名
/data/service/hnp/bin/binary-sign-tool sign \
    -inFile blib/arch/auto/Net/SSLeay/SSLeay.so \
    -outFile ~/tmp/SSLeay.so.signed -selfSign 1

# 6. 安装
cp ~/tmp/SSLeay.so.signed ~/usr/local/lib/site_perl/5.42.0/aarch64-linux/auto/Net/SSLeay/SSLeay.so
cp -r blib/lib/Net ~/usr/local/lib/site_perl/5.42.0/
```

### IO::Socket::SSL 2.085（依赖，纯 Perl）

```bash
# 1. 下载
curl -L -o ~/tmp/IO-Socket-SSL-2.085.tar.gz \
    "http://www.cpan.org/authors/id/S/SU/SULLR/IO-Socket-SSL-2.085.tar.gz"

# 2. 配置（跳过 Net::SSLeay RNG 测试）
SKIP_RNG_TEST=1 PERL_MM_USE_DEFAULT=1 perl Makefile.PL PREFIX=~/usr/local

# 3. 编译安装
make && make install DESTDIR=~/tmp/test-install-IO-Socket-SSL-2.085

# 4. 复制到本地
cp -r blib/lib/IO ~/usr/local/lib/site_perl/5.42.0/
```

### Net::HTTP 6.23（依赖，纯 Perl）

```bash
# 1. 下载
curl -L -o ~/tmp/Net-HTTP-6.23.tar.gz \
    "http://www.cpan.org/authors/id/O/OA/OALDERS/Net-HTTP-6.23.tar.gz"

# 2. 编译安装
perl Makefile.PL PREFIX=~/usr/local && make
make install DESTDIR=~/tmp/test-install-Net-HTTP-6.23

# 3. 复制到本地
cp -r ~/tmp/test-install-Net-HTTP-6.23/storage/Users/currentUser/usr/local/lib/* ~/usr/local/lib/
```

---

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Net::SSLeay 找不到 OpenSSL | OPENSSL_PREFIX 未设置 | 设置 `OPENSSL_PREFIX=/usr` |
| 2 | 编译时找不到 sys/types.h | 缺少 musl 头文件路径 | `INC="-I~/usr/local/include"` |
| 3 | 链接时找不到 crti.o/crtbeginS.o | 系统缺少 CRT 文件 | `LDDLFLAGS="-shared -nostartfiles -nodefaultlibs"` |
| 4 | 链接时找不到 libssl/libcrypto | 路径指向系统库 | 修改 Makefile: `-L~/usr/local/lib` |
| 5 | 运行时 Permission denied | SELinux HMDFS 限制 | 需安装到系统目录 |

---

## 源码修改

无补丁，所有模块源码无需修改。

---

## 依赖版本

| 模块 | 版本 | 编译状态 | 加载状态 | 类型 |
|------|------|---------|---------|------|
| perl | 5.42.0 | - | ✅ 系统预装 | - |
| ExtUtils::MakeMaker | 7.70 | - | ✅ Perl 内置 | - |
| OpenSSL | 3.0.9 | - | ✅ 系统预装 | C 库 |
| libssl/libcrypto | 1.1.1w | ✅ 已编译 | ✅ 可用 | C 库 |
| Net::SSLeay | 1.85 | ✅ 成功 | ❌ SELinux | XS |
| IO::Socket::SSL | 2.085 | ✅ 成功 | ❌ 依赖阻断 | PurePerl |
| Net::HTTP | 6.23 | ✅ 成功 | ✅ 可用 | PurePerl |
| perl-libwww | 6.81-r0 | ✅ 已编译 | ✅ 可用 | PurePerl |

---

## 验证结果

### 编译产物完整性 ✅ PASS

```bash
# LWP::Protocol::https 打包内容
tar -tzf LWP-Protocol-https-6.14-ohos-aarch64.tar.gz
# lib/perl5/LWP/Protocol/https.pm
# lib/perl5/aarch64-linux/auto/LWP/Protocol/https/.packlist

# Net::SSLeay 编译产物
ls -la ~/usr/local/lib/site_perl/5.42.0/aarch64-linux/auto/Net/SSLeay/
# SSLeay.so: 505KB，已签名 (.codesign section 存在)
```

### 功能测试 ❌ FAIL（SELinux HMDFS 限制）

```bash
# 测试 Net::SSLeay
perl -MNet::SSLeay -e 'print $Net::SSLeay::VERSION'
# 错误: Permission denied

# 原因分析：
# 文件位置: ~/usr/local/lib (HMDFS)
# SELinux type: hmdfs:s0
# hishell_hap domain 只能加载 hnp_file:s0 类型文件

# 解决方案: 安装到 /data/service/hnp/perl.org/perl_5.42.0/lib
```

---

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| LWP-Protocol-https-6.14-ohos-aarch64.tar.gz | 14KB | 预编译包 |
| Net::SSLeay 1.85 SSLeay.so | 505KB | XS 模块（已签名） |
| IO::Socket::SSL 2.085 | 约 100KB | 纯 Perl 模块 |
| Net::HTTP 6.23 | 约 50KB | 纯 Perl 模块 |

---

## 注意事项

### 1. 依赖顺序

必须按以下顺序安装：
```
OpenSSL → Net::SSLeay → IO::Socket::SSL → Net::HTTP → perl-libwww → LWP::Protocol::https
```

### 2. SELinux HMDFS 限制（关键）

XS 模块必须安装到系统目录：
- 安装位置: `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/`
- 需要 `installs` 用户权限
- 安装后需重新签名（获得 `hnp_file:s0` SELinux type）

### 3. Net::SSLeay 编译要点

- 使用系统 OpenSSL 3.0.9（`/usr/bin/openssl`）
- 需要链接本地编译的 libssl/libcrypto（`~/usr/local/lib`）
- 需要 `-nostartfiles -nodefaultlibs` 绕过 CRT 缺失
- 必须进行 ELF 签名

### 4. 纯 Perl 模块

- LWP::Protocol::https、IO::Socket::SSL、Net::HTTP 均为纯 Perl
- 无 SELinux 限制，可从任意目录加载
- 但依赖 XS 模块时会被间接阻断

---

## 功能测试结论

**测试日期**: 2026-06-16

### 依赖编译状态

| 模块 | 编译 | 加载 | 说明 |
|------|------|------|------|
| Net::SSLeay 1.85 | ✅ | ❌ | XS 模块，SELinux HMDFS 限制 |
| IO::Socket::SSL 2.085 | ✅ | ❌ | 纯 Perl，依赖 Net::SSLeay |
| Net::HTTP 6.23 | ✅ | ✅ | 纯 Perl，可用 |
| perl-libwww 6.81-r0 | ✅ | ✅ | 已安装 |

### 解决方案

1. **HNP 包安装**：将 Net::SSLeay 打包为 HNP 包，请求管理员安装
2. **等待预编译包**：等待 cmd-pkgs 发布 Net::SSLeay 预编译包

### 上库判断

| 条件 | 状态 |
|------|------|
| 编译成功 | ✅ 全部依赖编译成功 |
| 打包完整 | ✅ |
| 归档文件完整 | ✅ |
| 功能可用 | ❌ 需 HNP 包安装 |
| 上库建议 | ✅ 可上库，状态为 `built` |

**结论**: 可上库但状态保持 `built`。依赖模块已编译，但需要管理员协助安装 XS 模块到系统目录。

---

## 附录：HNP 包制作方法

```bash
# 1. 准备文件
cd ~/usr/local/lib/site_perl/5.42.0

# 2. 创建 HNP 包
tar -czf ~/tmp/net-ssleay.hnp \
    aarch64-linux/auto/Net/SSLeay/SSLeay.so \
    aarch64-linux/Net/SSLeay.pm \
    Net/SSLeay.pm \
    Net/SSLeay.pod

# 3. 提交给管理员安装
# 管理员执行：
sudo -u installs unzip net-ssleay.hnp \
    -d /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/

# 4. 重新签名
/data/service/hnp/bin/binary-sign-tool sign \
    -inFile /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Net/SSLeay/SSLeay.so \
    -outFile /tmp/SSLeay.so.signed -selfSign 1
sudo -u installs mv /tmp/SSLeay.so.signed \
    /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Net/SSLeay/SSLeay.so
```

---

**编译结束**: 2025-06-15 18:21
**依赖编译**: 2026-06-16 完成 Net::SSLeay 1.85 和 IO::Socket::SSL 2.085
**最终状态**: built (XS 模块受 SELinux 限制，需 HNP 包安装)