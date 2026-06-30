# xclip 0.13 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 源码获取: git clone --depth 1 --branch 0.13 https://github.com/astrand/xclip
2. 引导 autotools: autoreconf -fi (需求 PERL5LIB 指向 automake-1.16)
3. Configure:
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX \
     --x-includes=$HOME/usr/local/include \
     --x-libraries=$HOME/usr/local/lib \
     CFLAGS="-I$HOME/tmp/stubs/xclip/include" \
     LDFLAGS="-L$HOME/tmp/stubs/xclip/lib"
   ```
4. Make: make (需在 Makefile 链接行加 -liconv)
5. Make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | X11/Xmu/Atoms.h 缺失 (libXmu) | xclip 依赖 libXmu，但系统无预编译包 | 创建 stub 头文件 X11/Xmu/Atoms.h 并提供 XA_CLIPBOARD/XA_UTF8_STRING 内联实现 |
| 2 | X11/Intrinsic.h 缺失 (libXt) | configure.ac 检查 Xt Intrinsic.h | 创建 stub 头文件 X11/Intrinsic.h |
| 3 | XmuClientWindow 链接失败 | configure.ac 检查 -lXmu，但 stub 库引用了 X11 函数 | 创建不依赖 X11 外部函数的 stub XmuClientWindow 实现 |
| 4 | XrmOptionDescRec 未定义 | 新版 libX11 将 Xrm 类型移入独立头文件 X11/Xresource.h | 在 xclip.c 添加 #include <X11/Xresource.h> |
| 5 | libiconv 链接失败 | libiconv_open/libiconv 符号需要 -liconv | 在 Makefile 链接行添加 -liconv，并创建 libiconv.so 软链接 |
| 6 | libxcb 运行时缺失 | libX11 6.4.0 基于 XCB 传输层 | 运行时需要在设备预装 libxcb |

## 源码修改

- xclip.c: 添加 `#include <X11/Xresource.h>`（兼容新版 libX11）
- Makefile: 链接行添加 `-liconv`

## 依赖版本

| 软件 | 版本 | 来源 |
|------|------|------|
| libx11 | 6.4.0 | cmd-pkgs 预编译 |
| libxext | 6.4.0 | cmd-pkgs 预编译 |
| libxau | 6.0.0 | cmd-pkgs 预编译 |
| libice | 6.3.0 | cmd-pkgs 预编译 |
| libsm | 6.0.1 | cmd-pkgs 预编译 |
| libiconv | 1.17 | cmd-pkgs 预编译 |
| xorgproto | 2024.1 | cmd-pkgs 预编译 |

## 验证结果

```bash
$ file xclip
xclip: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
$ readelf -d xclip | grep NEEDED
NEEDED libX11.so.6
NEEDED libiconv.so.2
NEEDED libc.so
```

## 注意事项

- xclip 为 X11 终端工具，运行时需要 libxcb、libXau 等 XCB 层库（编译时已通过预编译包安装 libX11 + libXau，但 libxcb 无 OpenHarmony 预编译包）
- 本编译为 aarch64 目标，二进制在无 X11 显示的 headless 环境无法直接运行测试
- libXmu 和 libXt 以 stub 方式满足配置检测，xclip 实际代码未直接调用 XmuClientWindow

