# iodine 0.8.0 适配笔记

## 编译环境
- 构建系统: makefile（简单 Makefile，非 cmake/autotools，任务标注的 cmake 与实际源码不符）
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4 / clang++
- 平台: OpenHarmony (aarch64, musl libc)
- 状态: built

## 编译步骤

1. 初始化: `ohc-run.py init-build iodine 0.8.0 --url=https://github.com/yarrick/iodine/archive/refs/tags/v0.8.0.tar.gz`
2. 进入源码 `src/` 目录手动编译:
```bash
cd $BUILD_SRC_DIR/src
make clean
make -j1 CC=clang \
  CFLAGS="-fPIC -O2 -std=c99 -c -g -Wall -DLINUX -D_GNU_SOURCE -pedantic -Wstrict-prototypes -Wtype-limits -Wmissing-declarations -Wmissing-prototypes -I$DEFAULT_PREFIX/include" \
  LDFLAGS="-lz -L$DEFAULT_PREFIX/lib" \
  TARGETOS=Linux
```
3. Staging 安装: `make install DESTDIR=$TEST_PREFIX prefix=$DEFAULT_PREFIX`
4. 预编译包制作: `ohc-run.py package iodine 0.8.0`
5. 本地安装: `make install prefix=$DEFAULT_PREFIX`
6. 用户验证: `iodine -v` → version 0.8.0 ✅

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `static int daemon()` 与系统 `unistd.h` 冲突 | iodine 在非 GLIBC 平台定义 static daemon()，但 OpenHarmony musl libc 已提供 daemon(3) | 添加 `!defined(HAVE_DAEMON)` 到 `#if` 守卫条件，通过 CFLAGS 传递 `-DHAVE_DAEMON`（R8: 功能探测宏替代平台宏） |
| 2 | `do_detach()` 函数缺少 void 参数 | 定义为 `do_detach()` 而非 `do_detach(void)`，触发 -Wstrict-prototypes | 改为 `do_detach(void)` |
| 3 | CFLAGS 命令行覆盖丢失 `-c` 标志导致链接错误 | Make 的命令行变量覆盖机制：命令行 CFLAGS 会替换 Makefile 中所有赋值（包括 `+=`），导致源 Makefile 中的 `-c` 标志丢失 | 通过 os.environ 设置 CFLAGS 而非命令行参数，使 Makefile 的 += 能正确追加 |
| 4 | TARGETOS=HarmonyOS 不被 osflags 脚本识别 | `uname` 输出 "HarmonyOS"，osflags 脚本只处理 Linux/Darwin/Windows 等已知平台，不输出任何平台标志 | 设置 `TARGETOS=Linux` |

## 源码修改（track-edit 已记录）

修改文件: `src/common.c`
- 行 60: 添加 `&& !defined(HAVE_DAEMON)` 到 `#if` 守卫条件，跳过 static daemon() 定义
- 行 279: 改 `do_detach()` 为 `do_detach(void)`，修复函数原型

补丁文件: `0001-src-common.c.patch`（功能探测宏 HAVE_DAEMON）

## 依赖版本

- zlib 1.3.1（Conan 依赖，通过 `self.requires("zlib/1.3.1")` 声明）

## 真实执行验证结果

### 版本验证
```bash
$ iodine -v
iodine IP over DNS tunneling client
version 0.8.0 from 2023-04-17

$ iodined -v
iodine IP over DNS tunneling server
version 0.8.0 from 2023-04-17
```

### 二进制检查
```bash
$ file sbin/iodine
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ file sbin/iodined
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ readelf -d iodine | grep NEEDED
  (NEEDED) Shared library: [libc.so]

$ readelf -d iodined | grep NEEDED
  (NEEDED) Shared library: [libc.so]
```

### 安装完整性
```bash
Staging 目录文件:
  sbin/iodine      (256512 bytes)
  sbin/iodined     (264704 bytes)
  share/man/man8/iodine.8
  share/doc/iodine/README.md

预编译包内容:
  sbin/iodine
  sbin/iodined
  share/man/man8/iodine.8
  share/doc/iodine/README.md
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| iodine-0.8.0-ohos-aarch64.tar.gz | 325KB | 预编译包（含 iodine/iodined 二进制 + man 页 + README） |
| iodine-0.8.0-ohos-aarch64-debug.tar.gz | 298KB | debug 符号包 |

## 注意事项

- iodine 使用简单 Makefile（非 cmake/autotools），任务标注的 cmake 构建系统与实际源码不符
- 二进制安装到 `sbin/` 目录而非 `bin/`（iodine 是网络管理工具，sbin 为标准安装路径）
- osflags 脚本不识别 HarmonyOS，需设置 TARGETOS=Linux
- 命令行覆盖 Makefile 变量时需包含所有必要标志（特别是 `-c`）
- iodine 需要 TUN 设备权限才能执行端到端隧道测试，当前环境不具备此条件
---

**编译结束**: 2026-06-12 14:34
**最终状态**: built
