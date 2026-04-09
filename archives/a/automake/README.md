# GNU Automake 1.16.5 鸿蒙适配

> **编译日期**: 2026-04-09（首次适配: 2026-03-19）
> **测试环境**: HarmonyOS HongMeng Kernel aarch64
> **编译器**: clang + musl libc (HarmonyOS NDK)
> **Perl**: /data/service/hnp/bin/perl v5.42.0
> **测试结果**: ✅ 功能验证通过（官方测试套件因鸡生蛋问题不可用，手动全链路测试通过）

## 编译说明

### 特殊性说明

automake 是一个**纯 Perl 项目**（无需 C 编译），但它的构建存在**鸡生蛋问题**：
- automake 的 `make` 过程需要先构建 `bin/automake` 脚本
- 但 `bin/automake` 依赖 `lib/Automake/Config.pm`
- `Config.pm` 由 `config.status` 从 `Config.in` 生成
- `config.status` 由 `configure` 生成
- 但某些 `make` 规则会尝试用 `automake` 重新生成 `Makefile.in`，而此时 `automake` 还没构建好

因此采用**手动生成脚本 (gen-all.pl)** 的方式绕过标准 make 流程。

### 归档文件

| 文件 | 说明 |
|------|------|
| `patches/0001-port-for-ohos.patch` | config.guess (HarmonyOS 检测+输出) + config.sub (linux-ohos OS 识别, 3处) |
| `gen-all.pl` | 手动生成脚本：替换 @VAR@ 变量，生成 Config.pm / automake / aclocal |

### 编译步骤

```bash
# 1. 下载解压
curl -L -o automake-1.16.5.tar.xz https://ftp.gnu.org/gnu/automake/automake-1.16.5.tar.xz
tar -xf automake-1.16.5.tar.xz
cd automake-1.16.5

# 2. 应用 HarmonyOS 补丁（config.guess + config.sub）
patch -p1 < /path/to/0001-port-for-ohos.patch

# 3. 运行 configure
export TMPDIR=$HOME/tmp
./configure --prefix=$HOME/usr/local

# 4. 使用 gen-all.pl 手动生成所有文件
cp /path/to/gen-all.pl .
perl gen-all.pl

# 5. 修补残留变量
sed -i 's|@am_AUTOCONF@|autoconf|g' bin/automake
sed -i 's|@PACKAGE_URL@|https://www.gnu.org/software/automake|g' bin/automake bin/aclocal

# 6. 手动安装
PREFIX=$HOME/usr/local

# Perl 库
mkdir -p $PREFIX/share/automake-1.16/Automake
cp lib/Automake/*.pm $PREFIX/share/automake-1.16/Automake/

# 脚本
cp bin/automake bin/aclocal $PREFIX/bin/
cp bin/automake $PREFIX/bin/automake-1.16   # 版本化副本（符号链接受限时用复制）
cp bin/aclocal $PREFIX/bin/aclocal-1.16

# M4 宏文件
mkdir -p $PREFIX/share/automake-1.16/am
cp lib/am/*.am $PREFIX/share/automake-1.16/am/

mkdir -p $PREFIX/share/aclocal-1.16
mkdir -p $PREFIX/share/aclocal-1.16/internal
cp m4/*.m4 $PREFIX/share/aclocal-1.16/
cp m4/internal/*.m4 $PREFIX/share/aclocal-1.16/internal/

# 辅助脚本
cp lib/compile lib/install-sh lib/missing lib/depcomp lib/ar-lib \
   lib/mkinstalldirs lib/py-compile lib/tap-driver.sh \
   $PREFIX/share/automake-1.16/
```

### gen-all.pl 脚本

归档中的 `gen-all.pl` 负责执行 configure 本应完成的 `@VAR@` 替换，包括：
- `lib/Automake/Config.pm` — Perl 模块配置（路径、版本、API 版本等）
- `m4/amversion.m4` — automake 版本 m4 宏
- `bin/automake` — 主脚本（含 shebang 修正为鸿蒙 perl 路径）
- `bin/aclocal` — 宏索引脚本

需要额外手动修补的变量（未包含在 gen-all.pl 的 do_subst 中）：
- `@am_AUTOCONF@` → `autoconf`
- `@PACKAGE_URL@` → `https://www.gnu.org/software/automake`

### 验证

```bash
automake --version   # automake (GNU automake) 1.16.5
aclocal --version    # aclocal (GNU automake) 1.16.5

# 完整 Autotools 工作链测试
mkdir test && cd test
cat > configure.ac << 'EOF'
AC_INIT([test], [1.0])
AM_INIT_AUTOMAKE([foreign])
AC_PROG_CC
AC_CONFIG_FILES([Makefile])
AC_OUTPUT
EOF

cat > Makefile.am << 'EOF'
bin_PROGRAMS = hello
hello_SOURCES = hello.c
EOF

cat > hello.c << 'EOF'
#include <stdio.h>
int main() { printf("Hello!\n"); return 0; }
EOF

autoreconf --install --force
./configure && make && ./hello  # 输出: Hello!
```

## 已知限制

1. **官方测试套件无法运行**：`make check` 触发 automake 重新生成 Makefile.in，因 `@am_AUTOCONF@` 等变量未在 Makefile 层面正确替换导致失败
2. **make install 不可用**：同上原因，需手动安装或使用 install.sh
3. **辅助脚本路径依赖**：compile/missing/depcomp 等脚本硬编码安装到 `$pkgvdatadir`
4. **版本化符号链接受限**：部分文件系统不支持 ln -sf，改用 cp 创建版本化副本

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| Perl | 5.006+ (v5.42.0 ✅) | 运行时必需 |
| Autoconf | 2.72+ ✅ | 配合 autoreconf 使用 |
| GNU Make | 4.x ✅ | 构建 Autotools 项目 |
| musl libc | 系统自带 | C 程序链接 |
