# Texinfo 7.3 - 鸿蒙系统编译指南

## 软件简介

Texinfo 是 GNU 项目用于编写文档的系统，可以生成 Info、HTML、PDF 等多种格式的文档。

**版本**: 7.3
**编译日期**: 2026-04-01
**目标系统**: OpenHarmony (HongMeng Kernel 1.12.0)

## 编译环境

- **编译器**: clang
- **构建系统**: autotools (autoconf/automake)
- **Perl**: /data/service/hnp/bin/perl
- **安装路径**: $HOME/usr/local

## 编译步骤

### 1. 解压源码

```bash
tar -xf texinfo-7.3.tar.xz
cd texinfo-7.3
```

### 2. 准备临时目录（关键步骤）

鸿蒙系统上 `config.status` 创建临时目录时会失败，需要提前准备：

```bash
mkdir -p .config_tmp
chmod 777 .config_tmp
```

### 3. 配置

```bash
./configure \
  --prefix=$HOME/usr/local \
  --disable-nls \
  --build=aarch64-unknown-linux-gnu \
  --host=aarch64-unknown-linux-gnu \
  CC=clang \
  CFLAGS="-I$HOME/usr/local/include" \
  LDFLAGS="-L$HOME/usr/local/lib"
```

**重要配置说明**:
- `--disable-nls`: 禁用国际化支持，避免编译问题
- `--build` 和 `--host`: 必须指定为 aarch64-unknown-linux-gnu，因为 config.guess 无法识别 HarmonyOS
- `CC=clang`: 使用 clang 编译器

### 4. 修改 config.status（关键步骤）

由于鸿蒙系统的临时目录权限问题，需要修改 `config.status` 文件：

```bash
# 修改主目录的 config.status
sed -i 's|(umask 077 && mktemp -d "\./confXXXXXX")|mktemp -d "./.config_tmp/confXXXXXX"|g' config.status

# 修改 tta 子目录的 config.status
cd tta
mkdir -p .config_tmp
chmod 777 .config_tmp
sed -i 's|(umask 077 && mktemp -d "\./confXXXXXX")|mktemp -d "./.config_tmp/confXXXXXX"|g' config.status
cd ..
```

### 5. 编译

```bash
make
```

### 6. 安装

```bash
make install
```

## 已知问题与解决方案

### 问题 1: config.status 创建临时目录失败

**错误信息**:
```
./config.status[2501]: can't create ./confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**原因**: 鸿蒙系统上 `mktemp -d` 配合 `umask 077` 创建的临时目录权限不足。

**解决方案**:
1. 提前创建 `.config_tmp` 目录并设置 777 权限
2. 修改 `config.status` 中的 mktemp 路径为 `./.config_tmp/confXXXXXX`

### 问题 2: config.guess 无法识别 HarmonyOS

**错误信息**:
```
./build-aux/config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one
```

**解决方案**: 使用 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu` 显式指定系统类型。

### 问题 3: tta 子目录需要单独配置

**错误信息**:
```
make[1]: *** No rule to make target 'tta/perl/Texinfo/ModulePath.pm'. Stop.
```

**原因**: tta 子目录有自己的 configure 脚本，需要单独配置。

**解决方案**: 进入 tta 目录，执行 configure 并修改 config.status。

## 安装后的工具

编译成功后，以下工具将被安装到 `$HOME/usr/local/bin/`:

- `texi2any` - Texinfo 转换工具（主程序）
- `makeinfo` - texi2any 的软链接
- `install-info` - 安装 info 文档的工具
- `texindex` - Texinfo 索引工具
- `pod2texi` - Perl POD 到 Texinfo 的转换器
- `texi2pdf`, `texi2dvi`, `pdftexi2dvi` - 其他转换工具

## 安装位置

- **可执行文件**: `$HOME/usr/local/bin/`
- **Perl 模块**: `$HOME/usr/local/share/texi2any/`
- **Info 文档**: `$HOME/usr/local/share/info/`
- **Man 手册**: `$HOME/usr/local/share/man/`

## 核心功能验证

```bash
# 检查版本
texi2any --version
makeinfo --version
install-info --version

# 创建测试文档
cat > test.texi << 'EOF'
\input texinfo
@node Top
@top Test Document
This is a test Texinfo document.
@bye
EOF

# 转换为 info 格式
makeinfo test.texi -o test.info
```

## 兼容性评估

**兼容性等级**: 高

**核心功能状态**:
- ✅ texi2any - 正常工作
- ✅ makeinfo - 正常工作
- ✅ install-info - 正常工作
- ✅ texindex - 正常工作
- ✅ Info 文档生成 - 正常工作

## 参考资料

- GNU Texinfo 官方网站: https://www.gnu.org/software/texinfo/
- GNU Texinfo 下载: https://ftp.gnu.org/gnu/texinfo/
