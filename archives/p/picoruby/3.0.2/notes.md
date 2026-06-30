# picoruby 3.0.2 适配笔记

uid: notes-v2

## 编译环境
- 构建系统: custom (mruby Rake build system + Ruby)
- 编译日期: 2026-06-18
- 编译器: clang 15.0.4 (llvm-release)
- 平台: OpenHarmony ARM64 (HMDFS), musl libc
- TMPDIR: /storage/Users/currentUser/tmp
- DEFAULT_PREFIX: /storage/Users/currentUser/usr/local
- 状态: published

### 对话 #1: 初始化编译

**用户**: 编译 picoruby 3.0.2 for OpenHarmony

**助手**: 加载 openharmony-compile-agent 技能，运行 init-build。

**问题**: init-build 的 `_create_dual_track` 函数失败。tarball 内的 `test` 符号链接指向 `build/repos/host/mruby-pico-compiler/test`（构建时才生成），是 broken symlink。HMDFS 不支持 `os.link` 硬链接，fallback 到 `shutil.copytree` 时遇到 broken symlink 失败。

**解决方案**:
1. 手动用 `cp -r` 创建 `.work` 目录
2. 删除 `.orig` 中的 broken `test` symlink 并替换为空目录
3. 创建 marker `Makefile`（空文件）使 init-build 检测到 `.orig` 和 `.work` 为有效源码目录
4. 重新运行 init-build 成功

### 对话 #2: 首次编译尝试

**用户**: 执行 rake 构建

**助手**: picoruby 使用 mruby 的构建系统（Rakefile + Ruby），非标准 autotools/cmake。`rake` 命令会自动从 GitHub 克隆 5 个 gem 依赖（mruby-mrubyc, mruby-pico-compiler, mruby-bin-picorbc, mruby-bin-picoruby, mruby-bin-picoirb）。

```bash
cd $BUILD_SRC_DIR
export CC=clang CXX=clang++ CFLAGS="-fPIC -O2"
rake
```

**问题 1**: `ld.lld: error: unable to find library -lm`
- **根因**: musl libc 不提供独立的 libm.a/.so，数学函数已内置于 libc 中。构建系统 gcc toolchain 默认 `linker.libraries = %w(m)` 添加 `-lm`。
- **解决方案**: 创建空 stub `libm.a` 到 `~/usr/local/lib/`，使 `-lm` 解析到空库（符号由 libc 提供）。

```bash
echo "" > empty.c
clang -c empty.c -o empty.o
llvm-ar rcs ~/usr/local/lib/libm.a empty.o
```

**问题 2**: `ld.lld: error: undefined symbol: fseek/malloc/free/calloc`
- **根因**: 环境变量 `LD=ld.lld` 导致构建系统使用裸链接器而非编译器驱动，裸 ld.lld 不会自动链接 libc 和 CRT 启动文件。
- **解决方案**: 设置 `LD=clang`，让 clang 作为链接器驱动自动处理 libc 和 CRT 链接。

```bash
export LD=clang
```

### 对话 #3: picorbc 运行时崩溃修复

**用户**: 继续构建

**问题 3**: `[FATAL] Could't open tempfile`
- **根因**: `picorbc` 编译多个 .rb 文件时，C 标准库 `tmpfile()` 函数尝试在 `/tmp` 创建临时文件，但 OpenHarmony 的 `/tmp` 是只读文件系统（E002）。
- **定位**: `build/repos/host/mruby-bin-picorbc/tools/picorbc/picorbc.c` 第 131 行 `concatfile = tmpfile();`
- **解决方案**: 使用 `#ifdef __OHOS__` 守卫，用 `mkstemp()` + `$TMPDIR` 替代 `tmpfile()`：

```c
#ifdef __OHOS__
#include <unistd.h>
#include <fcntl.h>
static FILE *ohos_tmpfile(void) {
  const char *tmpdir = getenv("TMPDIR");
  if (!tmpdir || !tmpdir[0]) tmpdir = getenv("HOME");
  if (!tmpdir || !tmpdir[0]) tmpdir = ".";
  char template[512];
  snprintf(template, sizeof(template), "%s/.picorbc_XXXXXX", tmpdir);
  int fd = mkstemp(template);
  if (fd < 0) return NULL;
  unlink(template);
  return fdopen(fd, "w+b");
}
#define tmpfile ohos_tmpfile
#endif
```

**注意**: 此补丁作用于 gem 源码（mruby-bin-picorbc），非 picoruby 主仓库。已归档为 `patches/0001-picorbc-tmpfile-ohos.patch`。

修复后重新运行 `rake`，编译完全成功，生成 3 个二进制和 2 个静态库。

### 对话 #4: 安装与打包

**助手**: picoruby 不支持 `make install`，手动执行 DESTDIR 安装：

```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/{bin,lib,include}
cp bin/picoruby bin/picorbc bin/picoirb $TEST_PREFIX/$DEFAULT_PREFIX/bin/
cp build/host/lib/libmruby.a build/host/lib/libmruby_core.a $TEST_PREFIX/$DEFAULT_PREFIX/lib/
```

执行 `ohc-run.py package`，生成预编译包 `picoruby-3.0.2-ohos-aarch64.tar.gz` (1.9MB)。

本地安装到 `$DEFAULT_PREFIX/bin/` 后验证：
```
$ picoruby --version → PicoRuby 3.0.0
$ picoruby -e 'puts "hello"' → hello
$ picorbc --version → PicoRuby compiler 3.0.0
```

## 编译步骤（真实执行）

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build picoruby 3.0.2 \
  --url=https://github.com/picoruby/picoruby/archive/refs/tags/3.0.2.tar.gz
```

### 2. 构建（真实执行）
```bash
cd $BUILD_SRC_DIR
export CC=clang CXX=clang++ CFLAGS="-fPIC -O2" LD=clang
rake
```
输出摘要：
```
Build summary:
================================================
      Config Name: host
 Output Directory: build/host
         Binaries: picorbc, picoruby, picoirb
    Included Gems:
             mruby-bin-picoirb - picoirb executable
             mruby-bin-picorbc - picoruby compiler executable
             mruby-bin-picoruby - picoruby executable
             mruby-mrubyc - mruby/c library
             mruby-pico-compiler - small footprint mruby compiler library
================================================
```

### 3. DESTDIR 安装（R20）
```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/{bin,lib,include}
cp bin/picoruby bin/picorbc bin/picoirb $TEST_PREFIX/$DEFAULT_PREFIX/bin/
cp build/host/lib/libmruby.a build/host/lib/libmruby_core.a $TEST_PREFIX/$DEFAULT_PREFIX/lib/
```

### 4. 打包
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package picoruby 3.0.2
# ✅ picoruby-3.0.2-ohos-aarch64.tar.gz: 2017KB
```

### 5. 本地安装验证
```bash
cp bin/* $DEFAULT_PREFIX/bin/
$DEFAULT_PREFIX/bin/picoruby -e 'puts "Hello from PicoRuby!"'
# → Hello from PicoRuby!
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ld.lld: error: unable to find library -lm` | musl libc 不提供独立 libm | 创建空 stub libm.a 到 ~/usr/local/lib/ |
| 2 | `ld.lld: undefined symbol: fseek/malloc/free` | LD=ld.lld 裸链接器不链接 libc | 设置 LD=clang 使用编译器驱动 |
| 3 | `[FATAL] Could't open tempfile` | picorbc 用 tmpfile() 写只读 /tmp | 源码补丁 #ifdef __OHOS__ 用 mkstemp+TMPDIR |
| 4 | init-build copytree 失败 | broken symlink + HMDFS 不支持硬链接 | 手动 cp -r + marker Makefile |

## 源码修改

### patches/0001-picorbc-tmpfile-ohos.patch
- **文件**: `build/repos/host/mruby-bin-picorbc/tools/picorbc/picorbc.c`（gem mruby-bin-picorbc）
- **修改**: 添加 `#ifdef __OHOS__` 守卫的 `ohos_tmpfile()` 函数，用 `mkstemp()` + `$TMPDIR` 替代 `tmpfile()`
- **原因**: OpenHarmony /tmp 只读（E002），C 库 `tmpfile()` 无法创建临时文件

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| Ruby (CRuby) | 4.0.2 | 运行 rake 构建脚本 |
| git | 2.45.2 | 克隆 picoruby 的 gem 依赖 |
| clang | 15.0.4 | C/C++ 编译器 |
| stub libm.a | - | 兼容 musl/glibc 差异 |

## 验证结果（真实执行）

```
$ picoruby --version
PicoRuby 3.0.0

$ picoruby -e 'puts "Hello from PicoRuby on OpenHarmony!"'
Hello from PicoRuby on OpenHarmony!

$ picoruby -e 'puts 1 + 2'
3

$ picoruby -e '3.times { |i| puts "iteration #{i}" }'
iteration 0
iteration 1
iteration 2

$ picoruby -e 'a = [1, 2, 3]; puts a.map { |x| x * 2 }.join(", ")'
2, 4, 6

$ picoruby -e 'begin; raise "test error"; rescue => e; puts "Caught: #{e.message}"; end'
Caught: test error

$ picorbc compile_test.rb
$ ls -la compile_test.mrb  →  138 bytes (mrb bytecode)

$ picorbc --version
PicoRuby compiler 3.0.0

$ file bin/picoruby
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/picoruby | 317,888 B | PicoRuby 解释器 |
| bin/picorbc | 203,200 B | PicoRuby 编译器 (.rb → .mrb) |
| bin/picoirb | 326,080 B | PicoRuby REPL |
| lib/libmruby.a | 605,326 B | mruby 完整静态库 (323 符号) |
| lib/libmruby_core.a | 412,972 B | mruby 核心静态库 (185 符号) |

## 知识积累 ✅

- ✅ picoruby 使用 mruby 的 Rake 构建系统，非 autotools/cmake
- ✅ musl libc 无独立 libm，需创建空 stub libm.a
- ✅ LD=clang 必需：避免裸 ld.lld 不链接 libc
- ✅ tmpfile() 在 OHOS 失败：/tmp 只读，用 mkstemp+TMPDIR 替代（R10 适配模式）
- ✅ picoruby 不支持 make install，需手动 DESTDIR 安装

## 注意事项

1. picoruby 使用非标准构建系统（Rake），不支持 `make install`，需手动安装
2. 构建过程需要 Ruby 解释器（系统已有 Ruby 4.0.2）
3. 构建过程需要从 GitHub 克隆 gem 依赖，需要网络访问
4. 版本号显示为 3.0.0 而非 3.0.2（上游 gem 版本号不一致，非编译问题）
5. LD=clang 是必需的环境变量（避免使用裸 ld.lld 链接器）
6. picoruby 不支持 -b 选项执行 .mrb 字节码文件
7. String#reverse 等部分 Ruby 方法未实现（微控制器定位，方法子集有限）
---

**编译结束**: 2026-06-18 15:03
**最终状态**: published
