# unac 1.8.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-16
- 编译器: clang 15.0.4 / clang++
- 操作系统: OpenHarmony (aarch64)
- 状态: published

## 编译步骤（真实执行记录）

### Step 1: init-build
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build unac 1.8.0 --url=https://deb.debian.org/debian/pool/main/u/unac/unac_1.8.0.orig.tar.gz
```
输出：tarball 已存在(275KB)，历史状态 published（无 configure_options），环境检查通过，依赖已就绪。

### Step 2: configure
```bash
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX
```
configure 正常完成，检测到 iconv、vsnprintf、getopt_long 等功能均可用。

### Step 3: make（首次失败 → 重编成功）

**首次编译失败**：
```
clang-15: error: no such file or directory: './.libs/libunac.so'
make[1]: *** [Makefile:808: unaccent] Error 1
```

**根因分析**: HMDFS 文件系统软链接创建延迟，libunac.so.1.0.8 已生成但 libunac.so 符号链接尚未创建。

**解决方案**: `make clean && make -j1`，重新编译成功。

### Step 4: make install DESTDIR（staging 安装）
```bash
make install DESTDIR=$TEST_PREFIX HELP2MAN=/bin/true
```
安装到 `$TEST_PREFIX/$DEFAULT_PREFIX/`，产物包括：
- bin/unaccent
- lib/libunac.so.1.0.8, libunac.so.1, libunac.so, libunac.a, libunac.la
- include/unac.h
- lib/pkgconfig/unac.pc
- share/man/man1/unaccent.1, share/man/man3/unac.3

### Step 5: make check（测试）
```bash
LD_LIBRARY_PATH="$BUILD_SRC_DIR/.libs:$DEFAULT_PREFIX/lib:$LD_LIBRARY_PATH" make check
```
输出：
```
PASS: t_unac
# TOTAL: 1, PASS: 1, SKIP: 0, FAIL: 0
```
全部测试通过。

### Step 6: 功能验证

**去重音测试**:
```bash
$DEFAULT_PREFIX/bin/unaccent UTF-8 "café"
```
输出：`cafe` ✅

**版本验证**:
```bash
$DEFAULT_PREFIX/bin/unaccent
```
输出包含 `Version 1.8.0` ✅

**pkg-config 验证**:
```bash
pkg-config --modversion unac   → 1.8.0
pkg-config --libs unac          → -L.../usr/local/lib -lunac
pkg-config --cflags unac        → -I.../usr/local/include
```

### Step 7: 预编译包制作
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package unac 1.8.0
```
产物：
- unac-1.8.0-ohos-aarch64.tar.gz (449KB)
- unac-1.8.0-ohos-aarch64-debug.tar.gz (194KB)

### Step 8: 本地安装
```bash
make install HELP2MAN=/bin/true
```
安装到 `$DEFAULT_PREFIX`，本地验证通过。

### Step 9: finish
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish unac 1.8.0 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首次 make 失败：`no such file: './.libs/libunac.so'` | HMDFS 软链接创建延迟，libunac.so 符号链接未在链接阶段及时创建 | `make clean && make -j1` 重新构建解决 |
| 2 | G0 干净构建验证失败 | `patch: Unknown option 'input'`，鸿蒙平台 patch 命令不支持 `--input` 参数 | config.log 非源码文件不应生成补丁，已从编辑追踪器中移除 |
| 3 | manifest 缺少 build_system | 初始模板中 build_system 仅在 build.system 子字段 | 添加顶层 build_system: autotools 字段 |

## 源码修改

无源码修改，无需补丁。unac 1.8.0 在 OpenHarmony 上可直接用标准 autotools 编译。

## 依赖版本

- iconv（系统自带，musl libc 内置）

## ELF 依赖信息

```
unaccent:
  RUNPATH: /storage/Users/currentUser/usr/local/lib
  NEEDED: libunac.so.1, libc.so
```

## 注意事项

- unaccent 不支持 `--version` 选项，版本信息需通过不带参数运行查看
- 需设置 `LD_LIBRARY_PATH` 包含 `$DEFAULT_PREFIX/lib` 或依赖 RPATH 自动加载
- 首次编译若遇到 HMDFS 软链接问题，clean 后重编即可

---

**编译结束**: 2026-06-16
**最终状态**: published
