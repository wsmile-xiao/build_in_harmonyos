# perl-mail-dkim 1.20240923 编译笔记

## 编译日期
- 主模块: 2026-06-15
- 依赖编译: 2026-06-16

## 编译环境
- 平台: OpenHarmony (aarch64-unknown-linux-ohos)
- Perl 版本: 5.42.0
- 编译器: clang 18.1.8
- 构建工具: ExtUtils::MakeMaker
- OpenSSL: 1.1.1w (已安装)

## 主模块编译过程

### Step 1: 初始化
下载源码并解压：Mail-DKIM-1.20240923.tar.gz

### Step 2: 配置
```bash
perl Makefile.PL
```

**观察**:
- Mail::DKIM 是纯 Perl 模块，无 XS 组件
- 配置过程简单，无特殊依赖检查
- Makefile.PL 自动检测 Perl 环境

### Step 3: 构建
```bash
make
```

**结果**:
- 编译成功，无错误
- 无 C 代码编译，纯 Perl 文件生成

### Step 4: 测试
```bash
make test
```

**测试结果**:
- 总测试文件: 20
- 通过: 3 (基础加载测试)
- 失败: 16 (缺少运行时依赖)
- 跳过: 1

**失败分析**:
所有测试失败都是因为缺少运行时 Perl 模块依赖，不是编译错误：
- **Crypt::OpenSSL::RSA**: Mail::DKIM::PublicKey, PrivateKey, Signer, Verifier 需要
- **Crypt::PK::Ed25519**: ed25519 签名支持需要
- **Test::RequiresInternet**: policy.t 和 public_key.t 测试依赖

**结论**: 模块本身编译正确，测试失败是预期的依赖缺失。

### Step 5: 安装
```bash
make install DESTDIR=$TEST_PREFIX
```

**产物**:
- Mail/DKIM.pm 及子模块
- 无 XS 共享库（纯 Perl）
- 打包: perl-mail-dkim-1.20240923-ohos-aarch64.tar.gz (336KB)

### Step 6: 验证
```bash
perl -MMail::DKIM -e 'print $Mail::DKIM::VERSION'
# 输出: 1.20240923 ✅
```

---

## 运行时依赖编译（2026-06-16）

Mail::DKIM 签名/验证功能需要 Crypt::OpenSSL::RSA，其依赖链为：
```
Mail::DKIM
    └── Crypt::OpenSSL::RSA (XS)
            ├── Crypt::OpenSSL::Random (XS)
            └── Crypt::OpenSSL::Guess (纯Perl, 配置依赖)
```

### 依赖 1: Crypt::OpenSSL::Guess 0.15

**类型**: 纯 Perl 模块
**编译状态**: ✅ 成功
**加载状态**: ✅ 可用

```bash
# 下载源码
curl -k -L -o tmp/Crypt-OpenSSL-Guess-0.15.tar.gz \
  "https://cpan.metacpan.org/authors/id/A/AK/AKIYM/Crypt-OpenSSL-Guess-0.15.tar.gz"

# 初始化
python3 scripts/ohc-run.py init-build Crypt-OpenSSL-Guess 0.15 \
  --url=file:///storage/Users/currentUser/tmp/Crypt-OpenSSL-Guess-0.15.tar.gz

# 编译安装
source .build-context-Crypt-OpenSSL-Guess-0.15
cd $BUILD_SRC_DIR
perl Makefile.PL && make && make install DESTDIR=$TEST_PREFIX
```

**验证**:
```perl
use Crypt::OpenSSL::Guess qw(openssl_inc_paths openssl_lib_paths);
print "INC: " . openssl_inc_paths() . "\n";  # 输出正确路径
```

### 依赖 2: Crypt::OpenSSL::Random 0.11

**类型**: XS 模块（需要 C 编译）
**编译状态**: ✅ 成功
**加载状态**: ⚠️ SELinux HMDFS 限制

**编译过程**:
```bash
# 初始化
python3 scripts/ohc-run.py init-build Crypt-OpenSSL-Random 0.11 \
  --url=file:///storage/Users/currentUser/tmp/Crypt-OpenSSL-Random-0.11.tar.gz

# 配置（指定 OpenSSL 路径）
source .build-context-Crypt-OpenSSL-Random-0.11
cd $BUILD_SRC_DIR
perl Makefile.PL \
  LIBS="-L/storage/Users/currentUser/usr/local/lib -lssl -lcrypto" \
  INC="-I/storage/Users/currentUser/usr/local/include"

# ⚠️ 链接问题解决：修改 LDDLFLAGS
sed -i 's/^LDDLFLAGS = -shared/LDDLFLAGS = -shared -nostartfiles -nodefaultlibs -lc/' Makefile

# 编译
make
```

**链接问题**:
- 错误: `ld.lld: error: cannot open crti.o: No such file or directory`
- 原因: 鸿蒙平台 musl 不提供标准 CRT 文件
- 解决: 添加 `-nostartfiles -nodefaultlibs -lc` 绕过 CRT

**产物**:
- Random.so: 13696 bytes (ELF shared object, 64-bit LSB arm64)

### 依赖 3: Crypt::OpenSSL::RSA 0.33

**类型**: XS 模块（需要 C 编译）
**编译状态**: ✅ 成功
**加载状态**: ⚠️ SELinux HMDFS 限制

**编译过程**:
```bash
# 初始化（已在主模块编译时初始化）
source .build-context-Crypt-OpenSSL-RSA-0.33
cd $BUILD_SRC_DIR

# 配置（同 Random）
perl Makefile.PL \
  LIBS="-L/storage/Users/currentUser/usr/local/lib -lssl -lcrypto" \
  INC="-I/storage/Users/currentUser/usr/local/include"

# 修改链接参数
sed -i 's/^LDDLFLAGS = -shared/LDDLFLAGS = -shared -nostartfiles -nodefaultlibs -lc/' Makefile

# 编译
make
```

**产物**:
- RSA.so: 42368 bytes (ELF shared object, 64-bit LSB arm64)

---

## XS 模块编译经验总结

### 问题 1: CRT 文件缺失

**现象**:
```
ld.lld: error: cannot open crti.o: No such file or directory
ld.lld: error: cannot open crtbeginS.o: No such file or directory
ld.lld: error: cannot open crtendS.o: No such file or directory
ld.lld: error: cannot open crtn.o: No such file or directory
```

**原因**: 鸿蒙平台使用 musl C 库，不提供标准 CRT 启动文件

**解决方案**（参考 perl-dbi 经验）:
```bash
# Makefile 中修改 LDDLFLAGS
sed -i 's/^LDDLFLAGS = -shared/LDDLFLAGS = -shared -nostartfiles -nodefaultlibs -lc/' Makefile
```

**参数说明**:
- `-nostartfiles`: 不使用标准启动文件 (crti.o, crtn.o)
- `-nodefaultlibs`: 不链接默认库
- `-lc`: 仅链接 C 库

### 问题 2: OpenSSL 路径

**现象**: Makefile.PL 找不到 OpenSSL 库

**解决方案**:
```bash
# 使用 pkg-config 获取路径
pkg-config --cflags openssl  # -I/storage/Users/currentUser/usr/local/include
pkg-config --libs openssl    # -L/storage/Users/currentUser/usr/local/lib -lssl -lcrypto

# 或直接指定
perl Makefile.PL \
  LIBS="-L$OPENSSL_PREFIX/lib -lssl -lcrypto" \
  INC="-I$OPENSSL_PREFIX/include"
```

### 问题 3: SELinux HMDFS 限制

**现象**:
```
Can't load '.../Random.so': Permission denied
```

**原因**:
| 文件位置 | SELinux type | 加载结果 |
|---------|-------------|----------|
| `/data/service/hnp` (系统目录) | `hnp_file:s0` | ✅ 可加载 |
| `~/usr/local/lib` (HMDFS) | `hmdfs:s0` | ❌ Permission denied |

**根本原因**: `hishell_hap` SELinux domain 只能加载 `hnp_file` 类型文件

**解决方案**（参考 perl-dbd-pg）:
1. 创建 HNP 安装包
2. 管理员安装到 `/data/service/hnp/perl.org/perl_5.42.0/`
3. 使用 binary-sign-tool 重新签名

---

## 依赖模块安装位置

```
/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/
├── Crypt/OpenSSL/
│   ├── Guess.pm    (7804 bytes, 纯 Perl, ✅ 可加载)
│   ├── Random.pm   (3132 bytes)
│   └── RSA.pm      (9897 bytes)
└── aarch64-linux/auto/Crypt/OpenSSL/
    ├── Random/Random.so (13696 bytes, XS, ⚠️ SELinux限制)
    └── RSA/RSA.so       (42368 bytes, XS, ⚠️ SELinux限制)
```

---

## 功能可用性

### ✅ 当前可用功能
- 模块加载和版本查询
- Mail::DKIM 基础类 (Common, Policy, DNS)
- Crypt::OpenSSL::Guess (OpenSSL 路径检测)

### ⚠️ 需管理员安装 XS 模块后可用
- DKIM 签名验证 (Mail::DKIM::Verifier)
- DKIM 签名生成 (Mail::DKIM::Signer)
- RSA 密钥操作 (PublicKey, PrivateKey)
- 随机数生成 (Crypt::OpenSSL::Random)

### HNP 安装包建议

为 XS 模块创建 HNP 包，供管理员部署：

```bash
# 创建目录结构
mkdir -p ~/tmp/hnp/Crypt-OpenSSL/lib/site_perl/5.42.0/Crypt/OpenSSL
mkdir -p ~/tmp/hnp/Crypt-OpenSSL/lib/site_perl/5.42.0/aarch64-linux/auto/Crypt/OpenSSL

# 复制文件
cp -r ~/usr/local/lib/site_perl/5.42.0/Crypt/OpenSSL/* \
  ~/tmp/hnp/Crypt-OpenSSL/lib/site_perl/5.42.0/Crypt/OpenSSL/
cp -r ~/usr/local/lib/site_perl/5.42.0/aarch64-linux/auto/Crypt/OpenSSL/* \
  ~/tmp/hnp/Crypt-OpenSSL/lib/site_perl/5.42.0/aarch64-linux/auto/Crypt/OpenSSL/

# 打包
cd ~/tmp/hnp/Crypt-OpenSSL && zip -r Crypt-OpenSSL.hnp .
```

---

## 编译状态总结

| 模块 | 版本 | 类型 | 编译 | 加载 | 备注 |
|------|------|------|------|------|------|
| Mail::DKIM | 1.20240923 | 纯 Perl | ✅ | ✅ | 主模块 |
| Crypt::OpenSSL::Guess | 0.15 | 纯 Perl | ✅ | ✅ | 配置依赖 |
| Crypt::OpenSSL::Random | 0.11 | XS | ✅ | ⚠️ | SELinux限制 |
| Crypt::OpenSSL::RSA | 0.33 | XS | ✅ | ⚠️ | SELinux限制 |

**结论**: 所有模块编译成功。XS 模块的 SELinux 限制是平台特性，可通过 HNP 包安装解决。

---
**编译结束**: 2026-06-16 17:16
**最终状态**: published (依赖已编译，XS模块需HNP安装)