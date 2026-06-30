# fbida 2.14 适配笔记

## 编译环境
- 构建系统: custom (GNUmakefile + mk/Autoconf.mk)
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### 1. 初始化构建
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build fbida 2.14 --url=https://www.kraxel.org/releases/fbida/fbida-2.14.tar.gz
```

### 2. 安装依赖（预编译包）
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libexif 0.6.26
```

### 3. 配置和编译
```bash
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
make config prefix=$DEFAULT_PREFIX
make exiftran prefix=$DEFAULT_PREFIX JPEG_VER=62
```

### 4. 手动安装到 staging
由于 make install 会尝试构建所有目标（包括 fbi、fbpdf），而我们只需要 exiftran，所以手动安装：
```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin $TEST_PREFIX/$DEFAULT_PREFIX/share/man/man1
cp exiftran $TEST_PREFIX/$DEFAULT_PREFIX/bin/
chmod 755 $TEST_PREFIX/$DEFAULT_PREFIX/bin/exiftran
cp man/exiftran.1 $TEST_PREFIX/$DEFAULT_PREFIX/share/man/man1/
chmod 644 $TEST_PREFIX/$DEFAULT_PREFIX/share/man/man1/exiftran.1
```

### 5. 用户验证
```bash
cp exiftran $DEFAULT_PREFIX/bin/
export LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH
$DEFAULT_PREFIX/bin/exiftran -h
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 找不到 libexif 头文件 | GNUmakefile 中没有为 exiftran 添加 libexif CFLAGS | 修改 GNUmakefile 第 149 行，添加 libexif 到 pkg-config --cflags |
| 2 | JPEG_VER 为空导致编译失败 | jpeg-version.sh 脚本需要 cpp，系统无 cpp | 手动设置 JPEG_VER=62（系统安装的是 libjpeg-turbo，JPEG_LIB_VERSION=62） |
| 3 | thumbnail.cgi 编译失败 | 同样缺少 libexif CFLAGS 和 LDLIBS | 修改 GNUmakefile，为 thumbnail.cgi 也添加 libexif 的 pkg-config 选项 |
| 4 | exiftran 动态链接失败 | LD_LIBRARY_PATH 未设置 | 设置 LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib |
| 5 | make install 尝试编译 fbi/fbpdf | HAVE_LINUX_FB_H=yes 导致 TARGETS 包含 fbi/fbpdf | 手动安装 exiftran 到 staging，跳过不需要的目标 |

## 源码修改

- GNUmakefile: 添加 libexif 的 pkg-config 选项
  - 第 149 行: `exiftran      : CFLAGS += $(shell $(PKG_CONFIG) --cflags pixman-1 libexif)`
  - 第 150 行: `exiftran      : LDLIBS += $(shell $(PKG_CONFIG) --libs   pixman-1 libexif)`
  - 第 151-153 行: 为 thumbnail.cgi 也添加 libexif 的 pkg-config 选项

## 依赖版本

- libexif: 0.6.26
- libjpeg (libjpeg-turbo): 3.1.4.1 (JPEG_LIB_VERSION=62)
- pixman: 0.46.4

## 验证结果

```bash
$ exiftran -h
usage: exiftran [ options ] file

transform options:
  -a         automatic (using exif orientation tag)
  -9         rotate by 90 degrees clockwise
  -1         rotate by 180 degrees clockwise
  -2         rotate by 270 degrees clockwise
  ...
--
(c) 2002-2012 Gerd Hoffmann <gerd@kraxel.org> [SUSE Labs]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| exiftran | 707K | JPEG EXIF 转换工具 |
| exiftran.1 | man page | 手册页 |

## 注意事项

1. exiftran 不支持 --version 选项，只能通过 -h 或直接运行来验证
2. JPEG_VER 必须设置为 62（与系统 libjpeg-turbo 的 JPEG_LIB_VERSION 一致）
3. 需要 PKG_CONFIG_PATH 设置为 /storage/Users/currentUser/usr/local/lib/pkgconfig
4. 需要设置 LD_LIBRARY_PATH 或使用 RPATH 来找到动态库
5. fbida 包含多个工具（fbi、fbpdf、ida），但我们只编译了 exiftran，因为其他工具需要额外的依赖（libdrm、freetype、fontconfig、poppler-glib 等）

## 命名决策

- **源码包名称**: fbida-2.14.tar.gz（项目名称）
- **归档目录**: archives/f/fbida/2.14/（基于源码包名称）
- **预编译包名称**: exiftran-2.14-ohos-aarch64.tar.gz（基于用户实际需要的工具）
- **包内内容**: 只包含 exiftran 相关文件（bin/exiftran、man page、依赖库）

**原因**: 用户请求编译 exiftran，而 exiftran 没有独立的源码包，它是 fbida 项目的一部分。为避免用户混淆，预编译包使用 exiftran 名称，归档目录使用 fbida 名称（反映真实源码来源）。
---

**编译结束**: 2026-06-12 14:30
**最终状态**: built
