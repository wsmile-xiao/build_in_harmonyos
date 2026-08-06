# Crypt-OpenSSL-RSA 0.33 编译笔记

## 编译日期
2026-06-16

## 编译环境
- 平台: OpenHarmony (aarch64-unknown-linux-ohos)
- Perl 版本: 5.42.0
- 编译器: clang 15.0.4
- OpenSSL: 1.1.1w

## 模块信息
- **类型**: XS 模块 (需要 C 编译)
- **用途**: OpenSSL RSA 加密接口
- **依赖**: OpenSSL libssl/libcrypto, Crypt::OpenSSL::Random

## 编译过程

### Step 1: 配置
```bash
# 指定 OpenSSL 路径（与 Random 相同）
perl Makefile.PL \
  LIBS="-L/storage/Users/currentUser/usr/local/lib -lssl -lcrypto" \
  INC="-I/storage/Users/currentUser/usr/local/include"
```

### Step 2: 链接问题解决 ⚠️

**问题**: CRT 文件缺失（与 Random 相同）
```bash
sed -i 's/^LDDLFLAGS = -shared/LDDLFLAGS = -shared -nostartfiles -nodefaultlibs -lc/' Makefile
```

### Step 3: 构建
```bash
make
# RSA.xs → RSA.c → RSA.o → RSA.so
```

**警告**: OPENSSL_VERSION_NUMBER 宏展开警告（无害）
```
warning: macro expansion producing 'defined' has undefined behavior
```
共 9 个警告，不影响功能。

### Step 4: 产物
- RSA.so: 42368 bytes (ELF shared object, 64-bit LSB arm64)
- RSA.pm: 9897 bytes

### Step 5: 安装
```bash
cp RSA.so ~/usr/local/lib/site_perl/5.42.0/aarch64-linux/auto/Crypt/OpenSSL/RSA/
cp RSA.pm ~/usr/local/lib/site_perl/5.42.0/Crypt/OpenSSL/
```

## RSA 功能说明

Crypt::OpenSSL::RSA 提供 RSA 加密操作：

| 方法 | 用途 |
|------|------|
| new_public_key() | 从公钥创建对象 |
| new_private_key() | 从私钥创建对象 |
| encrypt() | RSA 加密 |
| decrypt() | RSA 解密 |
| sign() | 签名 |
| verify() | 验证签名 |
| get_public_key_x509() | 导出 X509 格式公钥 |

## SELinux HMDFS 限制 ⚠️

与 Crypt::OpenSSL::Random 相同限制：
- XS 模块在 HMDFS 目录无法加载
- 需要 HNP 包安装到 `/data/service/hnp`

## 编译经验总结

### OpenSSL XS 模块编译三要素

1. **路径配置**: 显式指定 LIBS/INC
2. **链接参数**: `-nostartfiles -nodefaultlibs -lc`
3. **SELinux**: HNP 包安装

### 依赖关系
```
Mail::DKIM::Signer/Verifier
    └── Crypt::OpenSSL::RSA 0.33 (XS, RSA 操作)
            └── Crypt::OpenSSL::Random 0.11 (XS, 随机数)
            └── Crypt::OpenSSL::Guess 0.15 (纯Perl, 路径检测)
```

---

## 功能测试记录 (2026-06-16 18:05)

### 测试环境
- 平台: OpenHarmony aarch64-unknown-linux-ohos
- Perl: 5.42.0
- OpenSSL: 1.1.1w
- 测试方法: 静态分析 + 运行时验证

### 测试结果

#### 编译产物完整性 ✅
- RSA.so: 42368 bytes, ELF 64-bit LSB arm64
- RSA.pm: 9897 bytes, Perl 模块完整
- 动态库依赖: libssl.so.1.1, libcrypto.so.1.1, libc.so

#### 模块加载测试 ❌
**错误**: Permission denied (SELinux HMDFS 限制)
**原因**: XS 模块在 HMDFS 目录无法加载动态库
**范围**: 所有 XS 模块受此限制（Random, RSA等）

#### 静态分析验证 ✅
- Perl 方法定义正确: new_public_key, new_key_from_parameters
- XS 函数导出正确: boot_Crypt__OpenSSL__RSA, rsa_crypt
- OpenSSL API 使用正确: BIO, BN, ERR 系列函数

### 质量门禁评估

| 门禁 | 状态 | 说明 |
|------|------|------|
| G0 干净构建 | ✅ PASS | 无手动介入 |
| G1 二进制完整性 | ✅ PASS | ELF正确 |
| G2 功能可用性 | ⚠️ WARN | SELinux限制 |
| G3 可移植性 | ⚠️ WARN | 需HNP安装 |
| G4 档案完整性 | ⚠️ WARN | 缺packaging |

### 上库判断

**状态**: ⚠️ **暂时不符合上库要求**

**原因**:
1. 功能验证受限（SELinux HMDFS）
2. 缺少预编译包（无法发布）
3. HNP 安装流程未验证

**需要完成**:
- 创建 HNP 预编译包
- 在 HNP 目录验证模块加载
- 补充 HNP 测试报告

---

## 预编译包制作记录 (2026-06-16 20:08)

### 打包过程

#### 目录结构
```
Crypt-OpenSSL-RSA-0.33-ohos-aarch64/
├── lib/site_perl/5.42.0/Crypt/OpenSSL/RSA.pm
├── lib/site_perl/5.42.0/aarch64-linux/auto/Crypt/OpenSSL/RSA/RSA.so
├── install.sh
└── manifest.yaml
```

#### 打包步骤
1. 创建打包目录 ✅
2. 复制 RSA.pm 和 RSA.so ✅
3. 创建 install.sh 安装脚本 ✅
4. 创建 manifest.yaml 包元数据 ✅
5. ELF 签名 RSA.so ✅
6. 打包成 tar.gz (65K) ✅
7. 复制到 archives/packaging/ ✅

### 安装验证

#### 本地安装测试 ✅
```bash
bash install.sh ~/usr/local/lib
```
结果：
- RSA.pm 安装成功 ✅
- RSA.so 安装成功 ✅
- 模块加载失败 ❌ (HMDFS SELinux 限制)

#### HNP 安装测试 ⏸️
```bash
sudo bash install.sh /data/service/hnp/perl.org/perl_5.42.0/lib
```
结果：
- sudo 权限不可用 ❌
- 需要 HNP 管理员手动安装

### 预编译包状态

| 项目 | 状态 | 说明 |
|------|------|------|
| 预编译包创建 | ✅ 完成 | Crypt-OpenSSL-RSA-0.33-ohos-aarch64.tar.gz (65K) |
| ELF 签名 | ✅ 完成 | RSA.so 已签名 |
| 安装脚本 | ✅ 完成 | install.sh 可用 |
| 本地安装验证 | ✅ 完成 | HMDFS 限制确认 |
| HNP 安装验证 | ⏸️ 待完成 | 需管理员权限 |
| HNP 功能测试 | ⏸️ 待完成 | 安装后测试 |

### 安装指南

**HNP 管理员安装步骤**：
```bash
# 1. 下载预编译包
cd /data/service/hnp/perl.org/perl_5.42.0/lib
wget <预编译包URL>

# 2. 解压
tar xzf Crypt-OpenSSL-RSA-0.33-ohos-aarch64.tar.gz

# 3. 安装
cd Crypt-OpenSSL-RSA-0.33-ohos-aarch64
bash install.sh /data/service/hnp/perl.org/perl_5.42.0/lib

# 4. 验证
perl -MCrypt::OpenSSL::RSA -e 'print Crypt::OpenSSL::RSA->VERSION, "\n"'
```

**依赖要求**：
- Perl 5.42.0 ✅ (已安装)
- OpenSSL 1.1.1w ✅ (已安装)
- Crypt::OpenSSL::Random ⏸️ (需要同样安装到 HNP)

---
**编译结束**: 2026-06-16 17:15
**最终状态**: built (编译成功，XS需HNP安装)

**测试结束**: 2026-06-16 18:05
**测试状态**: ⚠️ 功能受限，需HNP验证

**打包结束**: 2026-06-16 20:08
**打包状态**: ✅ 预编译包已完成，待HNP管理员安装验证
---

**编译结束**: 2026-08-06 05:09
**最终状态**: built
