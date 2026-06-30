# perl-digest-sha3 1.01 编译笔记

## 编译环境
- 构建系统: Perl XS (Makefile.PL)
- 编译日期: 2026-06-10
- 编译器: clang 18.1.8
- Perl版本: 5.42.0
- 状态: built（功能未验证）

## 编译步骤

```bash
perl Makefile.PL \
  CCFLAGS="-D_GNU_SOURCE -I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include" \
  LDDLFLAGS="-nostartfiles -nodefaultlibs -L/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/lib/aarch64-linux-ohos"
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题

| 问题 | 解决方案 |
|------|---------|
| sys/types.h缺失 | 添加OHOS SDK头文件路径 |
| CRT文件缺失 | 使用-nostartfiles -nodefaultlibs |
| SELinux HMDFS限制 | 需管理员安装到系统目录 |

## ⚠️ 功能未验证风险

**阻塞原因**: SELinux HMDFS限制 + 无installs权限

**未验证项目**:
- ❌ SHA-3算法输出正确性
- ❌ API函数可用性
- ❌ 运行时链接库

**不承诺**: SHA-3功能可用

## 管理员验证要求

```bash
sudo -u installs unzip perl-digest-sha3-1.01-ohos-aarch64.hnp -d /data/service/hnp/perl.org/perl_5.42.0/
perl -MDigest::SHA3 -e 'print sha3_256_hex("test"), "\n"'
```

---

**编译结束**: 2026-06-10
**最终状态**: built（功能待验证）