# IO-HTML 1.004 编译笔记

## 编译环境

- **软件**: IO-HTML (perl-io-html)
- **版本**: 1.004
- **编译日期**: 2026-06-11
- **构建系统**: Perl (ExtUtils::MakeMaker)
- **编译器**: 不需要（纯 Perl 模块）

### 系统环境

- **Perl 版本**: 5.42.0
- **操作系统**: OpenHarmony
- **架构**: aarch64

### 环境变量

```bash
DEFAULT_PREFIX=/storage/Users/currentUser/usr/local
TEST_PREFIX=/storage/Users/currentUser/tmp/test-install-perl-io-html-1.004
BUILD_SRC_DIR=/storage/Users/currentUser/tmp/builds/perl-io-html-.work
```

## 编译步骤

### Step 1: 初始化

```bash
SKILL_ROOT="/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent"
python3 "$SKILL_ROOT/scripts/ohc-run.py" init-build perl-io-html \
  --url=http://www.cpan.org/authors/id/C/CJ/CJM/IO-HTML-1.004.tar.gz
```

**URL 说明**:
- 原始 HTTPS URL 因 SSL 证书问题失败
- 使用 HTTP URL 成功下载
- CPAN 路径: `/authors/id/C/CJ/CJM/IO-HTML-1.004.tar.gz`

### Step 2: 生成 Makefile

```bash
cd $BUILD_SRC_DIR
perl Makefile.PL PREFIX=$DEFAULT_PREFIX
```

**输出**:
```
Checking if your kit is complete...
Looks good
Generating a Unix-style Makefile
Writing Makefile for IO::HTML
```

### Step 3: 编译

```bash
make
```

**输出**:
```
cp lib/IO/HTML.pm blib/lib/IO/HTML.pm
```

**说明**: IO-HTML 是纯 Perl 模块，无需 XS 编译，仅需复制 .pm 文件。

### Step 4: 安装到测试目录

```bash
make install DESTDIR=$TEST_PREFIX
```

**安装产物**:
- `/storage/Users/currentUser/tmp/test-install-perl-io-html-1.004/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/IO/HTML.pm`
- `perllocal.pod` 安装信息

### Step 5: 执行测试

```bash
make test
```

**测试结果**:
```
All tests successful.
Files=5, Tests=165,  1 wallclock secs
Result: PASS
```

**测试详情**:
- `t/00-all_prereqs.t`: ok
- `t/00-load.t`: ok
- `t/10-find.t`: ok
- `t/20-open.t`: ok
- `t/30-outfile.t`: ok

### Step 6: 打包

```bash
python3 "$SKILL_ROOT/scripts/ohc-run.py" package perl-io-html 1.004
```

**打包产物**: `perl-io-html-1.004-ohos-aarch64.tar.gz` (28KB)

### Step 7: 验证

```bash
# 使用 PERL5LIB 验证模块加载
PERL5LIB="/storage/Users/currentUser/tmp/test-install-perl-io-html-1.004/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0" \
  perl -MIO::HTML -e 'print $IO::HTML::VERSION . "\n"'
```

**验证结果**: `1.004`

## 问题与方案

### 问题 1: HTTPS SSL 证书验证失败

**错误信息**:
```
<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
unable to get local issuer certificate (_ssl.c:1000)>
```

**解决方案**:
- 使用 HTTP 协议代替 HTTPS: `http://www.cpan.org/authors/id/...`
- 或等待 init-build 自动安装 CA 证书（已自动执行）

### 问题 2: 版本号解析问题

**现象**:
- init-build 生成的上下文文件中版本号为空
- BUILD_VERSION=""

**原因**:
- URL 解析逻辑可能未正确提取版本号
- tarball 解压后的目录名缺少版本号

**解决方案**:
- 手动更新 `.build-context` 文件中的版本号
- 从 META.yml 中提取版本号: `version: '1.004'`

### 问题 3: 质量门禁 G4 失败

**错误**: `manifest 缺少 build_system`

**原因**:
- 验证脚本检查的是软件级 manifest.yaml
- 需要在软件级 manifest.yaml 中添加 `build_system: perl` 字段

**解决方案**:
- 在 `archives/p/perl-io-html/manifest.yaml` 中添加 `build_system: perl`

### 问题 4: Perl 模块安装路径

**现象**:
- 安装到 `$DEFAULT_PREFIX` 后无法通过 `perl -MIO::HTML` 加载
- Perl 的 @INC 不包含用户自定义路径

**原因**:
- Perl 5.42.0 的 @INC 固定为 `/data/service/hnp/perl.org/perl_5.42.0/lib/...`
- PREFIX 安装路径与 Perl @INC 不匹配

**解决方案**:
- 验证时使用 PERL5LIB 环境变量
- 打包后的安装脚本应正确设置 PERL5LIB 或安装到系统 Perl 目录

### 问题 5: 系统目录权限不足

**错误**:
```
ERROR: Can't create '/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/IO'
Permission denied
```

**原因**:
- `/data/service/hnp/perl.org/perl_5.42.0` 是系统管理目录
- 普通用户无写入权限

**解决方案**:
- 使用 DESTDIR 模式打包
- 由 cmd-pkgs 安装脚本处理权限和路径问题

## 依赖

### 运行时依赖

- Perl >= 5.008
- Carp (核心模块)
- Encode >= 2.10
- Exporter >= 5.57 (核心模块)

### 构建依赖

- ExtUtils::MakeMaker (核心模块)
- Test::More >= 0.88 (测试)

## 源码修改

**无源码修改** - 纯 Perl 模块，无需适配

## 交付物

- **预编译包**: `perl-io-html-1.004-ohos-aarch64.tar.gz` (28KB)
- **manifest.yaml**: 完整的编译元数据
- **notes.md**: 本文档

## 注意事项

1. **纯 Perl 模块**: 无 XS 代码，无需特殊链接参数
2. **安装路径**: Perl 模块需要安装到 Perl @INC 路径或设置 PERL5LIB
3. **测试**: 所有 165 个测试全部通过
4. **无需补丁**: 原始源码无需修改即可编译
**编译耗时**: 约 15 分钟
**知识沉淀**: 纯 Perl 模块编译流程、PERL5LIB 验证方法
---

**编译结束**: 2026-06-12 10:42
**最终状态**: published
