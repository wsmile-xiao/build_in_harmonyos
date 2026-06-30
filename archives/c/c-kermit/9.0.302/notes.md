# c-kermit 9.0.302 适配笔记

## 编译环境
- 构建系统: makefile（手动 Makefile，非 autotools/configure）
- 编译日期: 2026-06-10
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 平台: OpenHarmony (HongMeng Kernel 1.12.0, aarch64)
- C库: musl libc
- 状态: built

## 编译步骤

c-kermit 使用手动 Makefile（8600+行），无标准 configure 脚本。采用模式 B（手动编译）：

```bash
# Step 1: 初始化
python3 $SKILL_ROOT/scripts/ohc-run.py init-build c-kermit 9.0.302 \
  --url=https://www.kermitproject.org/ftp/kermit/archives/cku302.tar.gz

# Step 2: 手动编译
cd $BUILD_SRC_DIR
make xermit \
  KTARGET=linux \
  "CC=clang" \
  "CC2=clang" \
  "CFLAGS=-O2 -fPIC -DLINUX -D__OHOS__ -DNOGETUSERSHELL -funsigned-char \
    -DFNFLOAT -DCK_POSIX_SIG -DCK_NEWTERM -DTCPSOCKET -DLINUXFSSTND \
    -DNOCOTFMC -DPOSIX -DUSE_STRERROR -DCK_NCURSES \
    -I/storage/Users/currentUser/usr/local/include" \
  "LNKFLAGS=-L/storage/Users/currentUser/usr/local/lib" \
  "LIBS=-lncurses -L/storage/Users/currentUser/usr/local/lib -lm"

# Step 2.5: DESTDIR 安装
make install DESTDIR=$TEST_PREFIX prefix=$DEFAULT_PREFIX \
  manroot=$DEFAULT_PREFIX BINARY=wermit \
  BINDIR=$DEFAULT_PREFIX/bin MANDIR=$DEFAULT_PREFIX/man/man1

# Step 5: 打包
python3 $SKILL_ROOT/scripts/ohc-run.py package c-kermit 9.0.302

# Step 6: 本地安装验证
make install prefix=$DEFAULT_PREFIX manroot=$DEFAULT_PREFIX \
  BINARY=wermit BINDIR=$DEFAULT_PREFIX/bin MANDIR=$DEFAULT_PREFIX/man/man1
kermit --version  # 输出 9.0.302 [9.0.302]

# Step 7: 收尾
python3 $SKILL_ROOT/scripts/ohc-run.py finish c-kermit 9.0.302 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `stdin->_cnt` 编译错误 | musl libc FILE 结构不透明，无法访问内部字段 `_cnt`、`_IO_read_end` 等 | ckucmd.c 添加 `#ifdef __OHOS__` 守卫，用 `conchk()` 替代 stdin 缓冲窥探 |
| 2 | `vhangup` 链接未定义 | OpenHarmony 无 `vhangup` syscall | ckupty.c 添加 `#ifdef __OHOS__` 守卫，undef `CK_VHANGUP` |
| 3 | `getusershell/endusershell` 链接未定义 | musl libc 无此函数 | CFLAGS 添加 `-DNOGETUSERSHELL`（代码内置条件编译支持） |
| 4 | `getutent/setutent/updwtmp` 链接未定义 | musl libc 无 utmp 系列函数 | ckupty.c 添加 `#ifdef __OHOS__` 守卫，undef `HAVE_GETUTENT/HAVE_SETUTENT/HAVE_UPDWTMP` |
| 5 | Makefile `linuxa` 目标强制 `CC=gcc` | 该目标硬编码 `CC=gcc`，覆盖我们的参数 | 直接调用 `make xermit` 目标并覆盖 CC=clang/CC2=clang |
| 6 | `make install` 生成绝对路径软链接 | DESTDIR 路径嵌入软链接目标 | 手动修复为相对路径：`rm -f && ln -s kermit kermit-sshsub`（R5） |
| 7 | 无标准测试套件 | c-kermit 是交互式通信软件 | 手动执行 13 项功能测试，详见 test-report.md |

## 源码修改

3 个补丁文件：

| 补丁 | 修改文件 | 类型 | 守卫 | 说明 |
|------|----------|------|------|------|
| 0001-ckcpro.c.patch | ckcpro.c | wart-regen | 无 | wart 预处理器重新生成的版本号更新 |
| 0002-ckucmd.c.patch | ckucmd.c | platform_compat | `#ifdef __OHOS__` | musl libc FILE internals 不可访问，用 conchk() 替代 |
| 0003-ckupty.c.patch | ckupty.c | platform_compat | `#ifdef __OHOS__` | OpenHarmony 缺 vhangup/utmp，守卫 undef 相关宏 |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| ncurses | 6.4-20221231 | 静态库（--without-shared，R4），路径 ~/usr/local |

## 验证结果

```bash
$ kermit --version
9.0.302 [9.0.302]

$ echo "show features" | kermit
Host info:
 Machine:    aarch64
 OS:         HarmonyOS

$ echo "show version" | kermit
Built for:  Linux
Running on: HarmonyOS #1 SMP HongMeng Kernel 1.12.0 aarch64

$ file ~/usr/local/bin/kermit
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| c-kermit-9.0.302-ohos-aarch64.tar.gz | 5.6MB | 预编译包（ELF 签名 + strip + RPATH） |
| c-kermit-9.0.302-ohos-aarch64-debug.tar.gz | 440KB | 调试符号包 |
| 0001-ckcpro.c.patch | 6KB | wart 重新生成 |
| 0002-ckucmd.c.patch | 11KB | __OHOS__ FILE internals 守卫 |
| 0003-ckupty.c.patch | 2.4KB | __OHOS__ vhangup/utmp 守卫 |

## 注意事项

1. c-kermit 使用手动 Makefile，不能使用标准 `ohc-run.py build`（模式 A），必须用模式 B 手动编译
2. `linuxa` 目标会覆盖 CC 参数，需直接调用 `xermit` 目标
3. musl libc 与 glibc 的 FILE 结构差异是核心适配点，所有涉及 stdin 缓冲窥探的代码都需要 `__OHOS__` 守卫
4. `-DNOGETUSERSHELL` 是代码内置的条件编译支持，无需源码修改
5. 软链接 `kermit-sshsub` 在 `make install` 后需手动修复为相对路径（R5）

---

**编译结束**: 2026-06-10 04:00
**最终状态**: built