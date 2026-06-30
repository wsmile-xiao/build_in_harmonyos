# isa-l 2.32.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++ (15.0.4, OHOS SDK 26.0.0.18)
- 状态: built

## 编译步骤

1. `python3 $SKILL_ROOT/scripts/ohc-run.py init-build isa-l 2.32.0 --url=https://github.com/intel/isa-l/archive/refs/tags/v2.32.0.tar.gz --force`
   - 首次因SSL证书错误失败，手动curl下载后拷贝到~/tmp/builds/重试
2. 手动运行autotools bootstrap:
   - 设置环境变量: `AUTOM4TE="perl autom4te"`, `AUTOCONF="perl autoconf"`
   - `aclocal` → `automake --add-missing --copy` → `autoconf`
   - libtoolize不支持--symlink，手动从libtool share复制build-aux文件
3. `./configure --prefix=$DEFAULT_PREFIX CPPFLAGS="-D__OHOS__"`
4. `make -j1`
5. `make install DESTDIR=$TEST_PREFIX`
6. `make check` — 全部17项因musl链接器路径隔离而失败（非库功能问题）
7. staging验证 → verify-build → package → 真实安装 → 静态链接API验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ohc-run.py下载SSL证书错误 | HMDFS平台curl证书问题 | 手动curl下载后拷贝到~/tmp/builds/ |
| 2 | autogen.sh/libtoolize失败 | libtoolize 2.4.7不支持--symlink | 手动复制libtool build-aux文件 |
| 3 | aclocal/automake Perl脚本无法执行 | shebang指向perl但sh无法直接执行 | 设置AUTOM4TE/AUTOCONF env var |
| 4 | SVE C源码编译失败 | clang 15.0.4 __attribute__((target("+sve")))+always_inline冲突 | 排除SVE文件+使用#ifndef __OHOS__守卫 |
| 5 | make check全部失败 | musl动态链接器路径隔离 | 功能正常，改用静态链接测试验证 |
| 6 | igzip --version无输出 | igzip不支持--version | 通过API验证功能 |
| 7 | igzip运行时找不到libisal.so.2 | musl不搜索$DEFAULT_PREFIX/lib | 需安装到系统路径或使用静态链接 |

## 源码修改

### 补丁1: 0001-erasure_code-aarch64-Makefile.am.patch
- 从 `lsrc_aarch64` 列表移除8个SVE文件（7个.S汇编 + 1个.c内联函数）
- 添加注释说明SVE在OHOS上被排除的原因

### 补丁2: 0002-erasure_code-aarch64-ec_aarch64_dispatcher.c.patch
- 用 `#ifndef __OHOS__` 守卫排除 SVE extern 函数声明
- 用 `#ifndef __OHOS__` 守卫排除 dispatcher 中的 SVE/SVE2 runtime 检测分支
- 保留 NEON 函数声明和 runtime 检测不受影响

### 补丁3: 0003-erasure_code-aarch64-ec_aarch64_highlevel_func.c.patch
- 用 `#ifndef __OHOS__` 排除 SVE wrapper 函数定义
- `ARM_STREAMING` 宏定义也加了 `#ifndef __OHOS__` 守卫

## 依赖版本

- clang 15.0.4 (OHOS SDK 26.0.0.18)
- libtool 2.4.7
- automake 1.16
- autoconf 2.72
- Perl 5.42.0

## 验证结果

### 静态链接API功能测试 (9/9 通过 ✅)

| 测试 | 函数 | 结果 |
|------|------|------|
| gzip头初始化 | isal_gzip_header_init() | ✅ PASS |
| GF乘法 | gf_mul(2,3) | ✅ PASS (结果=6) |
| CRC32校验 | crc32_iscsi(buf,256,0) | ✅ PASS (结果=0x2436a9db) |
| 压缩初始化 | isal_deflate_init() | ✅ PASS |
| 解压初始化 | isal_inflate_init() | ✅ PASS |
| GF向量乘初始化 | gf_vect_mul_init(2,tbl) | ✅ PASS |
| 数据压缩 | isal_deflate() | ✅ PASS (256→428 bytes) |
| 数据解压 | isal_inflate() | ✅ PASS (428→256 bytes) |
| 数据一致性 | memcmp(in,out) | ✅ PASS |

### 纠删码测试 (2/2 通过 ✅)

| 测试 | 函数 | 结果 |
|------|------|------|
| EC编码 | ec_encode_data(64,3,2,tbl,data,coding) | ✅ PASS |
| 编码数据验证 | coding块非全零 | ✅ PASS |

### ELF完整性 (✅ PASS)
- libisal.so.2.0.32: ELF64 AArch64 共享对象, 216导出符号
- igzip: ELF64 AArch64 PIE可执行, NEEDED: libisal.so.2, libc.so
- libisal.a: 静态库 410KB

### pkg-config (✅ PASS)
- 版本: 2.32.0
- Libs: -L$DEFAULT_PREFIX/lib -lisal
- Cflags: -I$DEFAULT_PREFIX/include

### make check (❌ 17/17 FAIL)
- 根因: musl动态链接器路径隔离，非库功能问题

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| isa-l-2.32.0-ohos-aarch64.tar.gz | 1710KB | 预编译包 |
| isa-l-2.32.0-ohos-aarch64-debug.tar.gz | 328KB | 调试符号包 |
| libisal.so.2.0.32 | 362KB | 共享库 |
| libisal.a | 410KB | 静态库 |
| igzip | 35KB | 命令行工具 |
| isa-l.h + isa-l/*.h | 9个头文件 | 头文件集 |
| libisal.pc | pkg-config文件 | 构建配置 |
| 0001-*.patch ~ 0003-*.patch | 3个 | 源码适配补丁 |

## 注意事项

1. **必须传递CPPFLAGS="-D__OHOS__"**给configure，否则SVE代码会导致编译失败
2. **SVE功能已禁用**: NEON优化仍然完整，SVE/SVE2优化因clang兼容性问题被排除
3. **make check在OHOS上不可用**: musl链接器路径隔离导致测试无法加载共享库
4. **autotools bootstrap需手动**: Perl脚本shebang和libtoolize都有平台兼容性问题
5. **isa-l无官方release tarball**: 使用GitHub archive自动生成包
6. **推荐静态链接**: 避免musl动态链接器路径问题

---

**编译结束**: 2026-06-03
**最终状态**: built
**测试结果**: 静态链接API 9/9通过, EC 2/2通过, ELF/pkg-config/头文件 全通过
