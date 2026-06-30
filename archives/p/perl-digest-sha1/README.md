# Digest::SHA1

Digest::SHA1 是 Perl 的 SHA-1 算法接口模块，提供 SHA-1 哈希计算功能，使用 Perl XS 实现高性能计算。

## 功能概述

- SHA-1 哈希计算
- 支持增量哈希计算
- 兼容 Digest 接口规范

## OHOS 适配

### 适配要点

1. **链接参数**：Perl XS 模块必须使用 `-nostartfiles -nodefaultlibs` 参数，因为鸿蒙系统缺少标准 CRT 文件（crti.o, crtn.o）

2. **头文件路径**：必须添加 `-I~/usr/local/include` 参数，指定 musl 头文件路径，因为 Perl CORE 头文件依赖系统头文件

3. **Makefile.PL 修改示例**：
   ```perl
   WriteMakefile(
       'INC'          => '-I/storage/Users/currentUser/usr/local/include',
       'LDDLFLAGS'    => '-shared -O2 -nostartfiles -nodefaultlibs -L/storage/Users/currentUser/usr/local/lib',
   );
   ```

### 已知问题

- **SELinux 限制**：编译产物在 HMDFS 目录（用户目录）下无法直接加载，需要安装到系统目录或使用 HNP 包

### 与 Linux 的差异

- Linux 下 Perl XS 模块可使用默认链接参数
- OHOS 下必须显式指定 `-nostartfiles -nodefaultlibs` 和 musl 头文件路径

## 依赖

### 编译依赖

- Perl 5.42.0
- musl headers 1.2.5
- CRT files (crti.o, crtn.o, crtbeginS.o)

### 运行依赖

- Perl 5.42.0

## 功能验证

### 测试结果（2026-06-10）

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 模块加载 | ✅ PASS | XS 模块已正确编译签名 |
| SHA-1 算法 | ✅ PASS | hello/world/空字符串均正确 |
| 增量哈希 | ✅ PASS | add() 方法正常工作 |
| Base64 编码 | ✅ PASS | b64digest 可用 |
| ELF 结构 | ✅ PASS | 64-bit ARM64，签名正确 |

**结论**: ✅ **可用于生产环境**

### 使用建议

⚠️ **重要**: XS 模块因 SELinux HMDFS 限制，需安装到系统目录：

1. **推荐方式**: 通过 HNP 包安装到 `/data/service/hnp`
2. **备选方式**: 通过 cmd-pkgs 公共安装脚本部署
3. **安装后验证**:
   ```bash
   perl -e 'use Digest::SHA1; print Digest::SHA1->new->add("hello")->hexdigest'
   # 应输出: aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d
   ```

### 测试示例

```perl
#!/usr/bin/perl
use Digest::SHA1;

# 基本使用
my $sha1 = Digest::SHA1->new;
$sha1->add("hello");
print $sha1->hexdigest, "\n";
# 输出: aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d

# 增量哈希
$sha1 = Digest::SHA1->new;
$sha1->add("hel")->add("lo");
print $sha1->hexdigest, "\n";

# Base64 编码
print $sha1->b64digest, "\n";

# 文件哈希
open my $fh, "<", "file.txt" or die;
$sha1 = Digest::SHA1->new;
$sha1->addfile($fh);
print $sha1->hexdigest, "\n";
```

## 参考

- 官网: https://metacpan.org/pod/Digest::SHA1
- 源码: https://cpan.metacpan.org/authors/id/G/GA/GAAS/Digest-SHA1-2.13.tar.gz

## 相关软件

- perl-dbd-pg 3.18.0 - 编译经验可参考