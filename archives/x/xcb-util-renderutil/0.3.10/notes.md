# xcb-util-renderutil 0.3.10 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-05
- 编译器: clang-15 (OpenHarmony SDK)
- 状态: built

## 编译步骤

1. `python3 ohc-run.py init-build xcb-util-renderutil 0.3.10 --url="..." --tar=tar.gz`
2. `source .build-context-xcb-util-renderutil-0.3.10`
3. `cd BUILD_SRC_DIR && autoreconf -fvi`
4. VPATH构建：在独立目录运行configure
   ```bash
   cd xcb-util-renderutil-0.3.10-build
   sh ../xcb-util-renderutil-0.3.10.work/configure \
     --prefix=$DEFAULT_PREFIX \
     --host=aarch64-linux-ohos \
     CC=clang \
     "CFLAGS=-fPIC -O2 -fuse-ld=bfd" \
     "LDFLAGS=-fuse-ld=bfd -Wl,-rpath,$HOME/usr/local/lib" \
     CPPFLAGS="-I$HOME/usr/local/include"
   ```
5. 修补config.status（移除umask 077，解决hmdfs SGID冲突）
6. `sh ./config.status` — 重新生成配置文件
7. `make -j2` — 编译（libtool不创建共享库，需手动创建）
8. 手动创建共享库：
   ```bash
   clang -shared -fPIC -O2 -fuse-ld=bfd \
     -Wl,-soname,libxcb-render-util.so.0 \
     -Wl,-rpath,/storage/Users/currentUser/usr/local/lib \
     -o .libs/libxcb-render-util.so.0.0.0 \
     cache.o util.o glyph.o \
     -L/storage/Users/currentUser/usr/local/lib -lxcb -lxcb-render
   ```
9. `make install DESTDIR=$TEST_PREFIX`
10. `python3 ohc-run.py verify-build xcb-util-renderutil 0.3.10`
11. `python3 ohc-run.py package xcb-util-renderutil 0.3.10`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ld.lld无法工作 | ld.lld依赖libxml2.so.16但系统只有libxml2.so.2 | 使用 `-fuse-ld=bfd` 强制GNU ld |
| 2 | configure conftest无法执行 | 所有文件系统（/storage, /tmp, /dev/shm）均为noexec | 使用 `--host=aarch64-linux-ohos` 交叉编译模式 |
| 3 | config.status创建临时目录失败 | hmdfs强制SGID + umask 077 = drwx--S---，导致Permission denied | 修补config.status，将 `(umask 077 && mktemp -d)` 改为 `(mktemp -d)` |
| 4 | libtool不创建共享库 | configure无法执行测试程序，libtool设置build_libtool_libs=no和archive_cmds="" | 手动用clang -shared创建libxcb-render-util.so.0.0.0 |
| 5 | pkg-config找不到xcb-render | 需要自定义xcb-render.pc和xcb.pc | 创建xcb-render.pc，修改xcb.pc添加xcbproto_version |

## 源码修改

无源码修改（所有修补均为生成的配置文件或pkg-config文件，非源码）

## 依赖版本

- libxcb 1.17.0（预安装在~/usr/local，共享库+头文件+pkg-config）
- xcb-proto 1.17.0（用于生成render.h等头文件）
- clang-15（OpenHarmony SDK编译器）
- GNU ld (ld.bfd) 2.45（来自binutils_2.45）

## 验证结果

```bash
# 共享库验证
readelf -h libxcb-render-util.so.0.0.0
# Type: DYN (Shared object file), Machine: AArch64

readelf -d libxcb-render-util.so.0.0.0
# NEEDED: libxcb.so, libxcb-render.so.0, libc.so
# SONAME: libxcb-render-util.so.0

# pkg-config验证（待make install后）
pkg-config --modversion xcb-renderutil
# 期望: 0.3.10
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libxcb-render-util.so.0.0.0 | 25208 | 共享库（AArch64 ELF64） |
| libxcb-render-util.so.0 | symlink | soname链接 |
| libxcb-render-util.so | symlink | 开发链接 |
| libxcb-render-util.a | 11516 | 静态库 |
| xcb_renderutil.h | header | 头文件 |
| xcb-renderutil.pc | pkg-config | 包配置文件 |

## 注意事项

1. hmdfs文件系统强制SGID位，`umask 077`创建的临时目录会变成`drwx--S---`导致Permission denied，必须修补config.status
2. libtool在此环境下无法自动创建共享库，需要手动用`clang -shared`创建
3. 路径中包含`/storage/Users/currentUser`，RUNPATH需要与此路径一致
---

**编译结束**: 2026-08-09 03:22
**最终状态**: built
