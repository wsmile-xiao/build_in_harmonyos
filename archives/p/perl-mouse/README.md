# perl-mouse

Mouse is a lightweight Perl object-oriented framework that is compatible with Moose but with significantly lower overhead. It provides most of Moose's features including:

- Class definition with `has` attributes
- Type constraints
- Roles and method modifiers (before/after/around)
- Inheritance and method resolution
- Metaclass API for introspection
- Mouse::Tiny for minimal single-file usage

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 2.6.0-r0 | built | 2026-06-24 | XS 模块编译成功, HNP 包已创建 |

## OpenHarmony 平台说明

### 编译

Mouse 使用 Module::Build 构建系统（非 Makefile.PL），编译命令：

```bash
# 设置 CFLAGS 包含 OHOS SDK sysroot 头文件
export CFLAGS="-fPIC -O2 -I$SYSROOT/usr/include -I$SYSROOT/usr/include/aarch64-linux-ohos"

# 构建
perl Build.PL --prefix=$DEFAULT_PREFIX
./Build
./Build install DESTDIR=$TEST_PREFIX
```

### 运行时

- **PurePerl 模式**: 直接安装后可用, 所有功能完整, 性能略低
- **XS 模式**: 需安装 HNP 包到 `/data/service/hnp/perl.org/` 启用高性能模式
- HNP 安装: `sudo bash packaging/install-hnp.sh`

### SELinux 说明

XS `.so` 文件在 `~/usr/local/` (HMDFS) 上无法被 `hishell_hap` domain 加载（SELinux `hmdfs:s0` vs `hnp_file:s0` 限制）。安装 HNP 包到系统目录可解决。

### 依赖

- Perl 5.42.0 (已预装)
- Module::Build 0.4234+
- Module::Build::XSUtil 0.19+
- Devel::PPPort 3.73+
