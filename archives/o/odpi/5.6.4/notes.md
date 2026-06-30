# odpi 5.6.4 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，非 autotools）
- 编译日期: 2026-06-17
- 编译器: clang 15.0.4 / clang++
- 平台: OpenHarmony aarch64 (HongMeng Kernel)
- 状态: built

## 软件简介

ODPI-C（Oracle Database Programming Interface for C）是 Oracle 官方提供的 C 语言
数据库编程接口库，为驱动程序和应用程序开发者简化 Oracle 数据库访问。它在 OCI
（Oracle Call Interface）之上提供通用封装层。

## 编译步骤

### 步骤 1: init-build

```bash
# GitHub 直连超时，使用 codeload 镜像下载
curl -fsSL -o $HOME/tmp/odpi-5.6.4.tar.gz \
  "https://codeload.github.com/oracle/odpi/tar.gz/refs/tags/v5.6.4"

python3 $SKILL_ROOT/scripts/ohc-run.py init-build odpi 5.6.4 \
  --url=file://$HOME/tmp/odpi-5.6.4.tar.gz
```

### 步骤 2: 编译

ODPI 使用纯 Makefile，无 configure 脚本。构建命令：

```bash
cd $BUILD_SRC_DIR
make LDFLAGS="-shared" PREFIX=$DEFAULT_PREFIX -j1
```

### 步骤 3: 安装（DESTDIR staging）

ODPI 的 Makefile 不支持 DESTDIR 变量，`make install DESTDIR=...` 中 DESTDIR 会被忽略。
手动创建 staging 目录：

```bash
STAGING="$TEST_PREFIX$DEFAULT_PREFIX"
mkdir -p "$STAGING/lib" "$STAGING/include" "$STAGING/share/odpi"
cp $DEFAULT_PREFIX/lib/libodpic.so.5.6.4 "$STAGING/lib/"
cd "$STAGING/lib" && ln -s libodpic.so.5.6.4 libodpic.so.5 && ln -s libodpic.so.5 libodpic.so
cp $DEFAULT_PREFIX/include/dpi.h "$STAGING/include/"
cp -r $DEFAULT_PREFIX/share/odpi/* "$STAGING/share/odpi/"
```

### 步骤 4: 打包

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package odpi 5.6.4
```

### 步骤 5: 本地安装

```bash
make install PREFIX=$DEFAULT_PREFIX LDFLAGS="-shared"
```

### 步骤 6: 测试程序编译与运行

```bash
cd test
make CC=clang LD=clang CFLAGS="-I../include -fPIC -O2 -Wall" LDFLAGS=""
# 36 个测试程序全部编译成功
# 运行报 DPI-1047（缺少 Oracle Client 库），属预期行为
```

### 步骤 7: 收尾

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish odpi 5.6.4 built
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build odpi 5.6.4
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | github.com 网络不通 | 改用 codeload.github.com 镜像下载 |
| 2 | 链接报 `undefined symbol: main` | 环境变量 LDFLAGS 覆盖了 Makefile 中 `LDFLAGS ?= -shared`，导致缺少 `-shared` 标志 | make 命令行显式传 `LDFLAGS="-shared"` |
| 3 | Makefile 不支持 DESTDIR | Makefile 中 install 目标直接使用 `$(PREFIX)/lib` 等路径，无 `$(DESTDIR)` 前缀 | 手动创建 staging 目录并复制文件 |
| 4 | 测试程序初次编译为共享库 | 测试 Makefile 的链接规则使用 `$(LDFLAGS)`，传入 `-shared` 导致生成 .so 而非可执行文件 | 编译测试时传 `LDFLAGS=""` |
| 5 | make check 不存在 | ODPI 使用纯 Makefile，无 check 目标 | 编译并运行 test/ 目录中的测试程序，记录真实输出 |
| 6 | 测试运行报 DPI-1047 | 平台未安装 Oracle Instant Client | 预期行为，非编译问题 |

## 源码修改

无源码修改，无补丁。

## 依赖版本

无外部依赖。仅使用系统库：
- libc（C 标准库）
- libdl（动态加载，-ldl）
- libpthread（线程，-lpthread）

运行时需要 Oracle Instant Client（libclntsh.so），但这是运行时依赖，非编译依赖。

## 验证结果

```bash
# 库格式检查
$ file lib/libodpic.so.5.6.4
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

# 动态依赖
$ readelf -d lib/libodpic.so.5.6.4 | grep NEEDED
  (NEEDED) Shared library: [libc.so]

# 导出符号
$ nm -D lib/libodpic.so.5.6.4 | grep " T " | wc -l
659

# 版本号
$ grep DPI_MAJOR_VERSION include/dpi.h
  #define DPI_MAJOR_VERSION 5
  #define DPI_MINOR_VERSION 6
  #define DPI_PATCH_LEVEL 4

# 测试程序编译
$ cd test && make CC=clang LD=clang CFLAGS="-I../include -fPIC -O2 -Wall" LDFLAGS=""
  # 36 个测试程序编译成功

# 测试程序运行
$ ./build/TestSuiteRunner
  DPI-1047: Cannot locate a 64-bit Oracle Client libraries (预期，无 Oracle 环境)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| odpi-5.6.4-ohos-aarch64.tar.gz | 2809KB | 预编译包（库 + 头文件 + samples + test） |
| odpi-5.6.4-ohos-aarch64-debug.tar.gz | 274KB | 调试符号包 |

## 注意事项

1. **LDFLAGS 覆盖问题**: 平台环境变量 LDFLAGS 会覆盖 Makefile 的 `?= -shared` 赋值，
   必须在 make 命令行显式传 `LDFLAGS="-shared"`。
2. **无 DESTDIR 支持**: Makefile 的 install 目标不支持 DESTDIR 变量，
   需手动创建 staging 目录。
3. **无 make check**: 使用 test/Makefile 编译并运行测试程序替代。
4. **Oracle Client 依赖**: 运行时需要 Oracle Instant Client，
   这是 ODPI 设计上的要求（ODPI 是 OCI 的封装层）。
