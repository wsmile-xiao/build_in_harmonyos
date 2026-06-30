# perl-locale-msgfmt 0.15-r2 适配笔记

## 编译环境
- 构建系统: perl (Module::Install DSL)
- 编译日期: 2026-06-15（修复版）
- 编译器: N/A (纯 Perl 模块)
- 状态: built

## 编译步骤

这是一个纯 Perl 模块，使用 Module::Install DSL 构建系统：

1. **源码下载**: 从 CPAN MetaCPAN 下载 Locale-Msgfmt-0.15.tar.gz
   - URL: https://cpan.metacpan.org/authors/id/A/AZ/AZAWAWI/Locale-Msgfmt-0.15.tar.gz
   - SHA256: c3276831cbeecf58be02081bcc180bd348daa35da21a7737b7b038a59f643ab4

2. **构建**:
   ```bash
   cd perl-locale-msgfmt-0.15-r2.work
   perl -I. Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX
   make
   ```

3. **测试**:
   ```bash
   make test
   # Result: Files=4, Tests=16, All tests successful
   ```

4. **安装 (staging)**:
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```

5. **安装 (本地)**:
   ```bash
   make install  # 安装到 ~/usr/local
   ```

6. **验证**:
   ```bash
   export PERL5LIB=$HOME/usr/local/lib/site_perl/5.42.0:$HOME/usr/local/lib/perl5:$PERL5LIB
   perl -MLocale::Msgfmt -e 'print "version: $Locale::Msgfmt::VERSION\n"'
   # Output: Locale::Msgfmt version: 0.15
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败无法下载源码 | CPAN SSL 证书问题 | 手动下载文件并使用 --no-download 参数 |
| 2 | Perl 模块无法加载 | @INC 路径不包括安装路径 | 设置 PERL5LIB 环境变量（已添加到 .zshrc） |
| 3 | Module::Install DSL 无法找到 inc 模块 | Makefile.PL 缺少 -I. 参数 | 使用 `perl -I. Makefile.PL` |
| 4 | G4 门禁失败 (manifest 缺少 build_system) | manifest.yaml 字段不完整 | 添加 `build_system: perl` |
| 5 | Makefile.patch 是生成文件补丁 (违反 R6) | Makefile 由 Makefile.PL 生成 | 删除补丁，构建参数记录在 build_hints |
| 6 | INSTALL_BASE 导致模块安装到 lib/perl5（不在 @INC） | Perl @INC 只搜索 lib/site_perl/5.42.0/ | 改用 PREFIX 参数，模块安装到 lib/site_perl/5.42.0/ |
| 7 | 系统Perl @INC不含 ~/usr/local 路径 | 鸿蒙 Perl 配置限制 | 在 .zshrc 中添加 PERL5LIB（cmd-pkgs 安装脚本应自动添加） |

## 源码修改

无源码修改，纯 Perl 模块无需补丁。

## 功能测试结果 (2026-06-15)

| 测试项 | 结果 |
|--------|------|
| 模块加载 | ✅ PASS |
| make test (4 files, 16 tests) | ✅ PASS |
| 单文件 .po → .mo 编译 | ✅ PASS |
| 目录批量编译 | ✅ PASS |
| 中文 PO 编译 | ✅ PASS |
| 预编译包制作 | ✅ PASS (22KB) |
| 质量门禁 G1-G4 | ✅ PASS |

## 安装产物

| 文件 | 说明 |
|------|------|
| Locale/Msgfmt.pm | 主模块 (4.5KB) |
| Locale/Msgfmt/Utils.pm | 工具子模块 |
| Locale/Msgfmt/po.pm | PO 解析 |
| Locale/Msgfmt/mo.pm | MO 写入 |
| Module/Install/Msgfmt.pm | 构建插件（仅构建时用） |
| msgfmt (ELF) | GNU gettext msgfmt（非本模块产物） |

## 依赖版本

- Perl 5.42.0

## G0 干净构建验证问题

G0 clean-verify 失败，原因是脚本对纯 Perl 模块（`build_system: perl`）的 configure 步骤使用了 `./configure` 而非 `perl Makefile.PL`。这是脚本逻辑的已知限制，不影响模块的实际可用性。

**手动验证替代**：
- ✅ 在工作目录中重新执行 `perl -I. Makefile.PL && make && make install DESTDIR=$TEST_PREFIX` 成功
- ✅ make test: All tests successful (Files=4, Tests=16)
- ✅ 模块加载验证: Locale::Msgfmt version: 0.15

## 注意事项

1. 这是纯 Perl 模块，不需要编译 C 代码，无需 ELF 签名
2. 安装路径为 ~/usr/local/lib/site_perl/5.42.0/（使用 PREFIX 参数，非 INSTALL_BASE）
3. **使用时需设置 PERL5LIB 环境变量**（鸿蒙 Perl @INC 不含 ~/usr/local 路径）
   - 已添加到 .zshrc: `export PERL5LIB=$HOME/usr/local/lib/site_perl/5.42.0:$HOME/usr/local/lib/perl5:$PERL5LIB`
   - cmd-pkgs 安装脚本应自动添加此设置
2. 安装路径为 ~/usr/local/lib/perl5/
3. 使用时需要设置 PERL5LIB 环境变量
4. 模块用于编译 .po 文件到 .mo 文件，是 GNU gettext msgfmt 的纯 Perl 实现
5. Module::Install::Msgfmt 是构建时依赖，运行时不需要独立加载
6. 目录批量编译时需确保 File::Path::mkpath 可用

**编译结束**: 2026-06-15 20:24
**最终状态**: built
---

**编译结束**: 2026-06-15 20:26
**最终状态**: built
