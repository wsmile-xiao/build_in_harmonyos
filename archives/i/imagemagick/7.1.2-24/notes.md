# imagemagick 7.1.2-24 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-30
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **初始化**: 使用 ohc-run.py init-build 初始化编译环境
2. **configure**: 使用交叉编译模式绕过 SELinux 限制
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX --disable-docs --disable-shared --disable-openmp --without-modules --host=aarch64-unknown-linux-ohos CC="clang -fuse-ld=bfd" CXX="clang++ -fuse-ld=bfd"
   ```
3. **修改 Makefile**: 手动删除 -fopenmp 选项（configure 的 --disable-openmp 没生效）
   ```bash
   sed -i 's/-fopenmp//g' Makefile
   ```
4. **编译**: make -j2
5. **手动链接**: 由于 libtool 在交叉编译模式下异常，手动链接静态库
   ```bash
   clang -fuse-ld=bfd utilities/magick.o MagickWand/.libs/libMagickWand-7.Q16HDRI.a MagickCore/.libs/libMagickCore-7.Q16HDRI.a $DEFAULT_PREFIX/lib/libbz2.a $DEFAULT_PREFIX/lib/libjpeg.a -lm -lpthread -ldl -o utilities/magick-static
   ```
6. **ELF 签名**: 使用 ohc-run.py sign-elf 签名可执行文件
7. **安装**: 复制到 ~/usr/local/bin/magick 并创建 wrapper scripts

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SELinux 限制 configure 执行测试程序 | 鸿蒙 SELinux 阻止未签名二进制执行 | 使用 --host 交叉编译模式绕过 |
| 2 | umask 077 权限问题 (E011) | HMDFS 文件系统 UID 映射问题 | sed 修改 configure 中的 umask 077 为 umask 022 |
| 3 | OpenMP 未被禁用 | configure 检测到 omp 支持 | 手动 sed 删除 Makefile 中的 -fopenmp |
| 4 | libtool 链接异常 | 交叉编译模式下 libtool 找不到 .so | 手动链接静态库 |
| 5 | 缺少 bz2/jpeg 符号 | 静态库依赖未自动链接 | 手动添加静态库到链接命令 |
| 6 | Permission denied 执行 | ELF 未签名 | 使用 ohc-run.py sign-elf 签名 |

## 源码修改

- configure: `umask 077` → `umask 022` (E011 补丁)
- Makefile: 删除 `-fopenmp` 选项

## 依赖版本

- bz2: 1.0.8 (已安装预编译包)
- jpeg: 10 (已安装预编译包)

## 验证结果

```bash
$ magick --version
Version: ImageMagick 7.1.2-24 Q16-HDRI aarch64 24116 https://imagemagick.org
Copyright: (C) 1999 ImageMagick Studio LLC
License: https://imagemagick.org/license/
Features: Cipher DPC HDRI 
Delegates (built-in): bzlib jpeg
Compiler: clang (15.0.4)

$ identify --version
Version: ImageMagick 7.1.2-24 Q16-HDRI aarch64 24116
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ~/usr/local/bin/magick | 4.4M | 主命令（静态链接） |
| ~/usr/local/bin/identify | 32B | wrapper script |
| ~/usr/local/bin/convert | 32B | wrapper script |
| ~/usr/local/bin/mogrify | 32B | wrapper script |
| ~/usr/local/lib/libMagickCore-7.Q16HDRI.a | - | 核心库 |
| ~/usr/local/lib/libMagickWand-7.Q16HDRI.a | - | Wand 库 |

## 注意事项

1. ImageMagick 7 使用 `magick` 作为主命令，其他命令（identify, convert等）通过 `magick <command>` 形式调用
2. 需要手动链接静态库，libtool 在交叉编译模式不正常工作
3. --disable-openmp 可能不生效，需要手动检查并删除 Makefile 中的 -fopenmp
