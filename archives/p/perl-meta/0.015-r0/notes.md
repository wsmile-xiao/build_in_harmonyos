# 编译笔记 — perl-meta 0.015-r0

## 软件信息

- **名称**: perl-meta (CPAN distribution `meta`)
- **版本**: 0.015-r0 (CPAN version 0.015)
- **作者**: Paul Evans (leonerd@leonerd.org.uk)
- **描述**: meta-programming API for Perl
- **类型**: Perl XS module (contains C code, meta.xs)
- **CPAN URL**: https://cpan.metacpan.org/authors/id/P/PE/PEVANS/meta-0.015.tar.gz
- **构建系统**: Module::Build (Build.PL)
- **Perl 要求**: >= 5.14

## 编译过程

### Step 1: init-build
- 下载来源: CPAN (www.cpan.org mirror, due to SSL certificate issues with cpan.metacpan.org)
- init-build 自动检测构建系统为 "autotools"（误检测，实际为 Module::Build）
- 环境检查通过: clang 18.1.8 (编译用), cc (clang 15.0.4, 链接用)

### Step 2: 编译

**问题 1: 编译器配置错误**
- Perl `$Config{cc}` = `clang` (clang 18.1.8, 无 OpenHarmony sysroot)
- `$Config{lddlflags}` = `-shared -O2 -fstack-protector-strong` (ld.lld 不识别 `-fstack-protector-strong`)
- `$Config{ld}` = `clang` (同上)

**解决方案**: 设置 `CC=cc LD=cc` 环境变量
- ExtUtils::CBuilder 检查 `$ENV{CC}` 和 `$ENV{LD}` (Base.pm line 40, 45)
- `cc` (clang 15.0.4) 有正确的 OpenHarmony SDK sysroot，能找到 libc、CRT 文件
- Build.PL 中添加 `config` 覆盖（`#ifdef __OHOS__` 守卫）

**问题 2: 构建系统检测**
- init-build 误检测为 "autotools"
- 实际使用 `perl Build.PL` (Module::Build)
- 手动修复 manifest.yaml 的 build_system 字段

### 编译命令
```bash
cd $BUILD_SRC_DIR
export CC=cc LD=cc
perl Build.PL --prefix=$DEFAULT_PREFIX
./Build
./Build test          # 全部通过 (14 files, 158 tests)
./Build install --destdir=$TEST_PREFIX  # DESTDIR 模式
./Build install       # 安装到 $DEFAULT_PREFIX
```

### 测试结果
```
All tests successful.
Files=14, Tests=158, 4 wallclock secs
Result: PASS
```
- 13 个测试文件全部通过
- 1 个测试跳过 (t/99pod.t, 需要 Test::Pod, 非关键)

### 运行时行为
- XS 模块 meta.so 编译成功，NEEDED 只有 libc.so
- `LD` 环境变量在运行时干扰 .so 加载（已知平台限制）
- 使用 `env -u LD perl -Mmeta` 可正常加载

### 补丁
- Build.PL: 添加 OHOS 平台检测和 config 覆盖（cc/ld/lddlflags）

---

**编译开始**: 2026-06-17
**编译结束**: 2026-06-17
**最终状态**: published ✅
---

**编译结束**: 2026-06-17 18:07
**最终状态**: published
