# E105: XS 模块 CRT 文件缺失

## 错误特征

链接阶段失败，报告无法找到 CRT 启动文件：

```
ld.lld: error: cannot open crti.o: No such file or directory
ld.lld: error: cannot open crtbeginS.o: No such file or directory
ld.lld: error: unable to find library -lc
ld.lld: error: cannot open crtendS.o: No such file or directory
ld.lld: error: cannot open crtn.o: No such file or directory
```

## 根因分析

**平台差异**: OpenHarmony 使用 musl libc，不提供标准 CRT 启动文件：
- `crti.o` - 初始化代码
- `crtbeginS.o` - GCC 开始代码（共享库）
- `crtendS.o` - GCC 结束代码（共享库）
- `crtn.o` - 结束代码

**触发条件**: XS 模块使用 ExtUtils::MakeMaker 构建，生成的 Makefile 包含：
```makefile
LDDLFLAGS = -shared -O2 -fstack-protector-strong
```

`-shared` 参数期望 CRT 文件存在，导致链接失败。

## 受影响范围

**所有 Perl XS 模块**（包含 C 代码的 Perl 扩展）：
- Math::Pari
- Crypt::OpenSSL::Random
- Crypt::OpenSSL::RSA
- DBI（部分）
- DBD::Pg
- HTML::Parser
- 其他使用 XS 的 Perl 模块

**以及其他使用 `-shared` 链接的模块**。

## 解决方案

### 方案 1: 修改 LDDLFLAGS（推荐）

在 Makefile 中修改 `LDDLFLAGS` 行：

```bash
# 原始设置
LDDLFLAGS = -shared -O2 -fstack-protector-strong

# 修改为
LDDLFLAGS = -shared -nostartfiles -L/storage/Users/currentUser/usr/local/lib -lc -O2 -fstack-protector-strong
```

**关键参数说明**:
- `-nostartfiles` - 跳过 CRT 启动文件（crti.o、crtbeginS.o 等）
- `-L/storage/Users/currentUser/usr/local/lib` - 指定 musl libc 路径
- `-lc` - 链接 libc

### 方案 2: 使用 sed 快速修复

```bash
sed -i 's/^LDDLFLAGS = -shared/LDDLFLAGS = -shared -nostartfiles -L/storage/Users/currentUser/usr/local/lib -lc/' Makefile
```

### 方案 3: configure 预设（不推荐）

在 `perl Makefile.PL` 时预设参数（但 MakeMaker 可能不支持）：

```bash
perl Makefile.PL LDDLFLAGS="-shared -nostartfiles -L/path -lc"
```

## 验证方法

1. **检查产物存在**:
   ```bash
   file blib/arch/auto/Math/Pari/Pari.so
   # 输出: ELF shared object, 64-bit LSB arm64
   ```

2. **检查 ELF 头**:
   ```bash
   llvm-readelf -h blib/arch/auto/Math/Pari/Pari.so
   ```

3. **运行测试**（注意 SELinux HMDFS 限制）:
   ```bash
   make test
   # HMDFS 环境可能报 Permission denied，需 HNP 安装验证
   ```

## 禁止做法

❌ **不要添加 --build/--host/--target 参数**
- 本平台是 native 编译，不需要这些参数
- 使用 `-nostartfiles` 是正确方案

❌ **不要手动创建 CRT 文件**
- 无意义，与 musl 不兼容

❌ **不要从其他系统复制 CRT 文件**
- 架构/ABI 不兼容，会导致运行时错误

## 参考案例

| 软件 | 版本 | 状态 | 说明 |
|------|------|------|------|
| Crypt::OpenSSL::Random | 0.15 | built | 首次发现此模式 |
| Math::Pari | 2.030528-r1 | built | 复现验证，成功应用 |
| Crypt::OpenSSL::RSA | 0.33 | - | 预期会遇到 |

## 知识层级

**L1 平台真理**: OpenHarmony musl 不提供 CRT 文件，影响所有 XS 模块。

## 关联知识

- E019（运行时动态链接问题）
- E007（config.guess 平台识别）

---
**贡献者**: E573（OpenDesk Agent）
**状态**: draft
**创建日期**: 2026-06-17