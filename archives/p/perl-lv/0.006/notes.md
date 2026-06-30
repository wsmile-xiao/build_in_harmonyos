# LV 0.006 适配笔记

## 编译环境
- 构建系统: perl-module (ExtUtils::MakeMaker)
- 编译日期: 2026-06-15
- 编译器: 无（纯 Perl 模块）
- 状态: built（功能受限）
- 源码 sha256: `fa88c2d4af0b1126d46401e6355a65496d033cfc2a6a944653011a638adfa75c`

## 编译步骤

LV 是一个纯 Perl 模块，编译过程非常简单：

```bash
# 1. 下载源码（从 CPAN MetaCPAN 镜像）
curl -fsSL "https://cpan.metacpan.org/authors/id/T/TO/TOBYINK/LV-0.006.tar.gz" -o LV-0.006.tar.gz

# 验证 sha256
sha256sum LV-0.006.tar.gz
# 输出: fa88c2d4af0b1126d46401e6355a65496d033cfc2a6a944653011a638adfa75c

# 2. 解压源码
tar -xzf LV-0.006.tar.gz
cd LV-0.006

# 3. 生成 Makefile
perl Makefile.PL

# 4. 编译（实际上只是检查依赖）
make

# 5. 测试
make test
# 结果：
# t/01basic.t ..... ok
# t/02tie.t ....... ok
# t/03sentinel.t .. skipped: LV::Backend::Sentinel not usable
# t/04magic.t ..... skipped: LV::Backend::Magic not usable
# All tests successful.
# Files=4, Tests=8,  0 wallclock secs
# Result: PASS
#
# ⚠️ 注意：Perl 测试套件判定 PASS 是因为 skipped 测试不计为失败
# 但实际上有两个后端不可用（需要 XS 支持），这是功能限制

# 6. 安装
make install
# 安装位置：
# /storage/Users/currentUser/usr/local/lib/perl5/site_perl_merge/5.42.0/LV.pm
# /storage/Users/currentUser/usr/local/lib/perl5/site_perl_merge/5.42.0/LV/Backend/Magic.pm
# /storage/Users/currentUser/usr/local/lib/perl5/site_perl_merge/5.42.0/LV/Backend/Sentinel.pm
# /storage/Users/currentUser/usr/local/lib/perl5/site_perl_merge/5.42.0/LV/Backend/Tie.pm
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 模块无法直接加载 | 安装路径为 site_perl_merge，不在 Perl 默认搜索路径中 | 设置 PERL5LIB 包含安装路径 |
| 2 | Sentinel/Magic 后端不可用 | 这两个后端需要 XS 扩展支持（Sentinel.pm、Variable::Magic），鸿蒙平台未安装 | 使用 Tie 后端（纯 Perl，兼容性好），但性能较低 |
| 3 | Savannah 下载源 404 | Savannah Nongnu 下载链接失效 | 使用 CPAN MetaCPAN 镜像替代 |

## 源码修改

无。LV 是纯 Perl 模块，源码无需任何修改即可在鸿蒙平台编译和使用。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| perl | 5.42.0 | OpenHarmony 预装的 Perl 版本 |

可选依赖（未满足）：
- Sub::Name（用于命名匿名函数，改善堆栈跟踪）- 可用
- Sentinel（Sentinel 后端需要 XS）- ❌ 不可用
- Variable::Magic（Magic 后端需要 XS）- ❌ 不可用

## 功能测试

### 官方测试套件结果

| 测试文件 | 结果 | 说明 |
|----------|------|------|
| t/01basic.t | ✅ PASS | 基本功能测试通过 |
| t/02tie.t | ✅ PASS | Tie 后端测试通过 |
| t/03sentinel.t | ⚠️ skipped | Sentinel 后端不可用（需要 XS 扩展） |
| t/04magic.t | ⚠️ skipped | Magic 后端不可用（需要 XS 扩展） |

**官方测试判定**: PASS（Perl 测试套件将 skipped 视为非失败）

**实际功能状态**: ⚠️ 功能受限
- 核心功能可用（通过 Tie 后端）
- 高性能后端不可用（Sentinel/Magic 需要 XS）
- Tie 后端性能较低，但兼容性好

### 扩展功能测试

```bash
# 设置 PERL5LIB 后进行功能测试
PERL5LIB="/storage/Users/currentUser/usr/local/lib/perl5/site_perl_merge/5.42.0:$PERL5LIB" perl -e '
use strict;
use warnings;
use LV qw( lvalue get set );

print "=== LV 模块功能测试 ===\n\n";

# 测试 1: 模块加载和版本
print "1. 模块加载测试:\n";
print "   LV 版本: $LV::VERSION\n";
print "   当前后端: ", LV->implementation, "\n";
print "   PASS\n\n";

# 测试 2: lvalue 子程序基本功能（使用 Tie 后端）
print "2. lvalue 子程序测试 (Tie 后端):\n";
my $counter;
sub counter :lvalue {
    lvalue
        get { $counter }
        set { $counter = $_[0] }
}

counter() = 10;
print "   设置 counter = 10\n";
print "   当前 counter = ", counter(), "\n";
counter() = counter() + 5;
print "   增加 5 后 counter = ", counter(), "\n";
print "   PASS\n\n";

# 测试 3: 多个 lvalue 变量
print "3. 多变量测试:\n";
my ($x, $y);
sub x_val :lvalue { lvalue get { $x } set { $x = $_[0] } }
sub y_val :lvalue { lvalue get { $y } set { $y = $_[0] } }

x_val() = 100;
y_val() = 200;
print "   x = ", x_val(), ", y = ", y_val(), "\n";
print "   PASS\n\n";

# 测试 4: get/set 函数
print "4. get/set 函数测试:\n";
my $z;
sub z_val :lvalue {
    lvalue
        get { $z }
        set { $z = $_[0] }
}

z_val() = 42;
print "   z = ", z_val(), "\n";
print "   PASS\n\n";

print "=== 测试完成 ===\n";
print "注意: 所有测试使用 Tie 后端（性能较低但兼容性好）\n";
print "Sentinel/Magic 高性能后端不可用（需要 XS 扩展）\n";
'
```

**测试输出**：
```
=== LV 模块功能测试 ===

1. 模块加载测试:
   LV 版本: 0.006
   当前后端: LV::Backend::Tie
   PASS

2. lvalue 子程序测试 (Tie 后端):
   设置 counter = 10
   当前 counter = 10
   增加 5 后 counter = 15
   PASS

3. 多变量测试:
   x = 100, y = 200
   PASS

4. get/set 函数测试:
   z = 42
   PASS

=== 测试完成 ===
注意: 所有测试使用 Tie 后端（性能较低但兼容性好）
Sentinel/Magic 高性能后端不可用（需要 XS 扩展）
```

### 功能限制说明

**可用功能**:
- ✅ lvalue 子程序创建和使用（Tie 后端）
- ✅ get/set 自定义回调
- ✅ 多变量 lvalue 操作

**不可用功能**:
- ❌ LV::Backend::Sentinel（高性能，需要 XS）
- ❌ LV::Backend::Magic（高性能，需要 XS）

**性能影响**:
- Tie 后端使用 Perl tie 机制，性能较低
- Sentinel/Magic 后端使用 XS 扩展，性能更高
- 在鸿蒙平台只能使用 Tie 后端

## 预编译包制作

由于 LV 是纯 Perl 模块，预编译包制作流程不同于 XS 模块：

```bash
# 1. 创建打包目录
PKG_NAME="perl-lv-0.006-ohos-aarch64"
INSTALL_BASE="/storage/Users/currentUser/usr/local/lib/perl5/site_perl_merge/5.42.0"
TMP_DIR="$HOME/tmp/pkg-perl-lv"

mkdir -p "$TMP_DIR/lib/site_perl/5.42.0"

# 2. 复制 Perl 模块文件（保持目录结构）
cp "$INSTALL_BASE/LV.pm" "$TMP_DIR/lib/site_perl/5.42.0/"
cp -r "$INSTALL_BASE/LV" "$TMP_DIR/lib/site_perl/5.42.0/"

# 3. 创建 tar.gz 包
cd "$TMP_DIR" && tar czvf "$ARCHIVE_DIR/$PKG_NAME.tar.gz" lib/

# 4. 验证包内容
tar tzvf "$ARCHIVE_DIR/$PKG_NAME.tar.gz"
# 输出:
# lib/site_perl/5.42.0/LV.pm
# lib/site_perl/5.42.0/LV/Backend/Tie.pm
# lib/site_perl/5.42.0/LV/Backend/Magic.pm
# lib/site_perl/5.42.0/LV/Backend/Sentinel.pm
```

**说明**：纯 Perl 模块预编译包不需要 ELF 签名、RPATH 设置、strip 等步骤，只需打包 Perl 源码文件即可。

## 交付物

### 预编译包

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-lv-0.006-ohos-aarch64.tar.gz | 13K | 包含所有 Perl 模块文件 |
| INSTALL.md | 1.4K | 安装说明文档 |

### 预编译包内容

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/site_perl/5.42.0/LV.pm | 4.2KB | 主模块文件 |
| lib/site_perl/5.42.0/LV/Backend/Tie.pm | 746B | Tie 后端（✅ 可用） |
| lib/site_perl/5.42.0/LV/Backend/Magic.pm | 651B | Magic 后端（❌ 不可用） |
| lib/site_perl/5.42.0/LV/Backend/Sentinel.pm | 429B | Sentinel 后端（❌ 不可用） |

### 安装方式

用户可通过以下方式安装预编译包：

```bash
# 方法 1: 使用 cmd-pkgs 公共安装脚本
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-lv 0.006

# 方法 2: 手动安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/perl-lv-0.006-ohos-aarch64.tar.gz -o perl-lv-0.006-ohos-aarch64.tar.gz
tar xzf perl-lv-0.006-ohos-aarch64.tar.gz -C /usr/local/lib/perl5/site_perl/5.42.0/
```

## 注意事项

1. **PERL5LIB 配置**：使用 LV 模块前需要设置 PERL5LIB 包含 site_perl_merge 目录
2. **后端限制**：只能使用 Tie 后端，性能较低；Sentinel/Magic 后端不可用（需要 XS）
3. **无二进制产物**：纯 Perl 模块不需要 ELF 签名
4. **测试覆盖**：核心功能测试通过，但高性能后端不可用
5. **下载源**：推荐使用 CPAN MetaCPAN 镜像，Savannah 源可能不可用
6. **性能影响**：Tie 后端比 Sentinel/Magic 性能低，但在大多数应用场景下足够使用

## 与 perl-dbd-pg 编译经验对比

| 项目 | perl-dbd-pg (XS 模块) | perl-lv (纯 Perl 模块) |
|------|----------------------|------------------------|
| 模块类型 | XS 扩展 | 纯 Perl |
| 二进制产物 | Pg.so (77KB) | 无 |
| 编译依赖 | pg_config, libpq, musl | 仅 perl |
| 平台适配 | 需要 SELinux/HMDFS 处理 | 无需修改源码 |
| ELF 签名 | 必须 | 不需要 |
| RPATH 设置 | 必须 | 不需要 |
| 预编译包 | 需要 XS 处理 | 仅打包 .pm 文件 |
| 功能限制 | XS 模块加载受 SELinux 限制 | 高性能后端不可用（需要 XS） |
| 官方测试 | PASS（有跳过） | PASS（有跳过） |

---

**编译开始**: 2026-06-15
**编译结束**: 2026-06-15
**预编译包制作**: 2026-06-16
**功能测试完成**: 2026-06-16
**最终状态**: built（功能受限：高性能后端不可用，核心功能可用）