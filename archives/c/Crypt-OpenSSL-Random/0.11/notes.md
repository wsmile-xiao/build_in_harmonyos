# Crypt-OpenSSL-Random 0.11 编译笔记

## 编译日期
2026-06-16

## 编译环境
- 平台: OpenHarmony (aarch64-unknown-linux-ohos)
- Perl 版本: 5.42.0
- 编译器: clang 18.1.8
- OpenSSL: 1.1.1w

## 模块信息
- **类型**: XS 模块 (需要 C 编译)
- **用途**: OpenSSL 随机数生成器接口
- **依赖**: OpenSSL libssl/libcrypto

## 编译过程

### Step 1: 配置
```bash
# 指定 OpenSSL 路径
perl Makefile.PL \
  LIBS="-L/storage/Users/currentUser/usr/local/lib -lssl -lcrypto" \
  INC="-I/storage/Users/currentUser/usr/local/include"
```

### Step 2: 链接问题解决 ⚠️

**问题**: CRT 文件缺失
```
ld.lld: error: cannot open crti.o: No such file or directory
ld.lld: error: cannot open crtbeginS.o: No such file or directory
```

**原因**: 鸿蒙平台 musl 不提供标准 CRT 启动文件

**解决**: 修改 LDDLFLAGS
```bash
sed -i 's/^LDDLFLAGS = -shared/LDDLFLAGS = -shared -nostartfiles -nodefaultlibs -lc/' Makefile
```

### Step 3: 构建
```bash
make
# Random.xs → Random.c → Random.o → Random.so
```

**警告**: endian.h 宏展开警告（无害）
```
warning: operator '<<' has lower precedence than '+'; '+' will be evaluated first
```

### Step 4: 产物
- Random.so: 13696 bytes (ELF shared object, 64-bit LSB arm64)
- Random.pm: 3132 bytes

### Step 5: 安装
```bash
# 手动安装（系统目录权限问题）
cp Random.so ~/usr/local/lib/site_perl/5.42.0/aarch64-linux/auto/Crypt/OpenSSL/Random/
cp Random.pm ~/usr/local/lib/site_perl/5.42.0/Crypt/OpenSSL/
```

## SELinux HMDFS 限制 ⚠️

**问题**: XS 模块无法加载
```
Can't load '.../Random.so': Permission denied
```

**原因**:
| 文件位置 | SELinux type | 加载结果 |
|---------|-------------|----------|
| `/data/service/hnp` | `hnp_file:s0` | ✅ 可加载 |
| `~/usr/local/lib` (HMDFS) | `hmdfs:s0` | ❌ Permission denied |

**解决方案**: 创建 HNP 包，管理员安装到系统目录

## XS 编译经验总结

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| CRT 文件缺失 | musl 无标准 CRT | `-nostartfiles -nodefaultlibs -lc` |
| OpenSSL 路径 | pkg-config 检测 | 显式指定 LIBS/INC |
| SELinux 限制 | HMDFS domain | HNP 包安装 |

---
**编译结束**: 2026-06-16 17:13
**最终状态**: built (编译成功，XS需HNP安装)