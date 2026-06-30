# catgirl 2.2a 适配笔记

## 编译环境
- 构建系统: custom (自定义 configure + Makefile)
- 编译日期: 2026-05-22
- 编译器: clang/clang++ (15.0.4)
- 状态: published

## 编译步骤

1. **初始化编译环境**
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build catgirl 2.2a --url="file:///path/to/catgirl-2.2a.tar.gz" --no-download
   ```

2. **创建 ncursesw.pc**
   由于 ncurses 手动编译安装，缺少 pkg-config 文件，手动创建：
   ```bash
   echo "prefix=/storage/Users/currentUser/usr/local
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include/ncursesw

Name: ncursesw
Description: Ncurses library with wide character support
Version: 6.4
Libs: -L${libdir} -lncursesw
Cflags: -I${includedir} -D_GNU_SOURCE" > ~/usr/local/lib/pkgconfig/ncursesw.pc
   ```

3. **运行 configure**
   ```bash
   cd ~/builds/catgirl-2.2a.work
   export PREFIX=/storage/Users/currentUser/usr/local
   export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
   ./configure --prefix=$PREFIX
   ```

4. **修改 config.mk（手动）**
   configure 生成的 config.mk 需要修改：
   - 添加 OBJS += compat_readpassphrase.o（HarmonyOS 不在 Linux 分支）
   - 添加 explicit_bzero 宏定义（musl libc 缺少此函数）
   - 使用静态库路径替代 pkg-config 的动态链接

   最终 config.mk 内容：
   ```
   PREFIX = /storage/Users/currentUser/usr/local
   CFLAGS += -D_GNU_SOURCE -I/storage/Users/currentUser/usr/local/include -I/storage/Users/currentUser/usr/local/include/ncursesw
   LDADD.libtls = /storage/Users/currentUser/usr/local/lib/libtls.a /storage/Users/currentUser/usr/local/lib/libssl.a /storage/Users/currentUser/usr/local/lib/libcrypto.a
   LDADD.ncursesw = /storage/Users/currentUser/usr/local/lib/libncursesw.a
   CFLAGS += -D'OPENSSL_BIN="/storage/Users/currentUser/usr/local/bin/openssl"'
   CFLAGS += -D'explicit_bzero(b,l)=__builtin_memset((b),0,(l))'
   OBJS += compat_readpassphrase.o
   ```

5. **编译**
   ```bash
   make clean && make all
   ```

6. **安装验证**
   ```bash
   # Staging 安装
   mkdir -p $TEST_PREFIX/$PREFIX/bin $TEST_PREFIX/$PREFIX/man/man1
   install -m 755 catgirl $TEST_PREFIX/$PREFIX/bin/catgirl
   install -m 644 catgirl.1 $TEST_PREFIX/$PREFIX/man/man1/catgirl.1

   # 本地安装
   install -m 755 catgirl $PREFIX/bin/catgirl
   install -m 644 catgirl.1 $PREFIX/man/man1/catgirl.1
   ```

7. **运行测试**
   ```bash
   make check  # edit.t 测试通过
   $PREFIX/bin/catgirl  # 输出 "host required"，验证可用
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ncursesw pkg-config not found | ncurses 手动编译，无 .pc 文件 | 手动创建 ncursesw.pc |
| 2 | undefined symbol: readpassphrase | HarmonyOS uname != "Linux"，未添加 compat_readpassphrase.o | 手动修改 config.mk: OBJS += compat_readpassphrase.o |
| 3 | undefined symbol: explicit_bzero | musl libc 缺少 BSD 函数 explicit_bzero | 添加宏定义: -D'explicit_bzero(b,l)=__builtin_memset((b),0,(l))' |
| 4 | undefined symbol: OPENSSL_init_ssl 等 | libtls.a 需要依赖 libssl.a 和 libcrypto.a | 使用完整静态库路径替代 pkg-config 链接 |
| 5 | 动态链接 libtls.so | configure 使用 -ltls（动态链接） | 改用静态库完整路径 |
| 6 | install -d not supported | toybox install 不支持 -d 选项 | 手动创建目录并使用 install 复制文件 |

## 源码修改

**config.mk（configure 生成的文件，需手动修改）**

主要修改：
1. 使用静态库完整路径替代 pkg-config 链接
2. 添加 compat_readpassphrase.o 到 OBJS
3. 添加 explicit_bzero 宏定义

**ncursesw.pc（手动创建）**

创建位置：~/usr/local/lib/pkgconfig/ncursesw.pc

## 依赖版本

| 依赖 | 版本 | 编译状态 | pkg-config |
|------|------|---------|-----------|
| ncurses | 6.4 | 手动编译 | ❌ 无（手动创建） |
| libtls | 来自 libressl | 已安装 | ✅ 有 |
| libssl | 来自 libressl | 已安装 | ❌ 无 |
| libcrypto | 来自 libressl | 已安装 | ❌ 无 |

## 验证结果

```bash
# 二进制大小
ls -lh ~/usr/local/bin/catgirl
# -rwxrwx--- 2.2M catgirl (静态链接)

# 动态依赖
readelf -d catgirl | grep NEEDED
# 只依赖 libc.so（系统 C 库）

# 功能验证
~/usr/local/bin/catgirl
# 输出: catgirl: host required（正常，IRC 客户端需要服务器地址）

# 测试套件
make check
# edit.t 测试通过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| catgirl-2.2a-ohos-aarch64.tar.gz | ~2.2M | 预编译包（待生成） |

## 注意事项

1. **静态链接必要性**：catgirl 需要静态链接 libtls、libssl、libcrypto、libncursesw，避免运行时找不到库
2. **explicit_bzero 替代**：musl libc 没有 explicit_bzero，使用 __builtin_memset 替代（clang 支持）
3. **compat_readpassphrase**：HarmonyOS uname 不是 "Linux"，需要手动添加 compat_readpassphrase.o
4. **configure 生成文件修改**：config.mk 是 configure 生成的，不能通过补丁修改，需要在编译流程中手动修改

---

**编译结束**: 2026-05-22 11:31
**最终状态**: built

**质量门禁结果**: FAIL
- G0 干净构建验证：FAIL（configure 在干净环境失败，需手动修改 config.mk）
- G1 二进制完整性：PASS
- G2 功能可用性：PASS（有警告）
- G3 可移植性：PASS
- G4 档案完整性：FAIL（缺少预编译包）

**编译成功关键修改**：
1. 手动创建 ncursesw.pc（ncurses 无 pkg-config）
2. 手动修改 config.mk：
   - 添加 OBJS += compat_readpassphrase.o
   - 添加 explicit_bzero 宏定义
   - 使用静态库完整路径替代 pkg-config 链接
3. 手动安装（toybox install 不支持 -d）

**编译状态**: built（编译成功，可运行）
**预编译包**: 待手动创建（需解决 package 命令的循环依赖问题）
---

**编译结束**: 2026-05-22 11:31
**最终状态**: built
