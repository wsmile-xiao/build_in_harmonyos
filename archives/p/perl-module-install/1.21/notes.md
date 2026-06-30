# perl-module-install 1.21 适配笔记

## 编译环境
- 构建系统: perl (Makefile.PL + ExtUtils::MakeMaker)
- 编译日期: 2026-06-18（初始编译），2026-06-22（功能测试与文档完善）
- 编译器: N/A（纯 Perl 模块，无 C 编译）
- 状态: published

## 编译步骤

1. **下载源码**: `Module-Install-1.21.tar.gz` from CPAN
2. **解压**: `tar xzf Module-Install-1.21.tar.gz`
3. **配置**: `perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX`（~/usr/local）
4. **编译**: `make`（纯 .pm 文件复制到 blib/）
5. **测试**: `make test` — 36 个测试文件，547 个测试用例全部通过
6. **安装**: `make install` — 安装到 ~/usr/local/lib/perl5/
7. **打包**: `ohc-run.py package` — 生成预编译包 tar.gz (266KB, 51 个文件)
8. **验证**: `ohc-run.py verify-build` — 全部门禁通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make test 27/36 测试失败 | 缺少运行时依赖模块 File::Remove, YAML::Tiny, Module::ScanDeps | 使用 `cpan -T` 安装依赖后重测，全部通过 |
| 2 | INSTALL_BASE 路径未展开 | manifest 中使用了 `$DEFAULT_PREFIX` 变量占位符 | 实际编译时使用 `~/usr/local`，manifest 中记录为参数形式 |

## 源码修改

无。本软件为纯 Perl 模块，不需要任何源码修改即可在 OpenHarmony 平台编译运行。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| perl | 5.42.0 | 运行时 | 系统预装 (HNP /data/service/hnp/perl.org/perl_5.42.0/) |
| YAML::Tiny | 1.76 | 运行时 | 通过 cpan -T 安装 |
| File::Remove | 1.61 | 运行时 | 通过 cpan -T 安装 |
| Module::ScanDeps | 1.37 | 运行时 | 通过 cpan -T 安装 |

## 验证结果

### make test 结果
```
Files=36, Tests=547, All tests successful
Duration: 66 wallclock secs
```

### 功能测试结果 (2026-06-22)
```bash
# 模块加载测试
$ perl -e 'use lib "$ENV{HOME}/usr/local/lib/perl5"; use inc::Module::Install; print "Version: $Module::Install::VERSION\n"'
Module::Install loaded successfully
Version: 1.21

# 核心子模块加载 (21/21 通过)
$ perl -e '... require Module::Install::Metadata; require Module::Install::Makefile; ...'
Test 2 - Core submodules: 21 passed, 0 failed out of 21

# Makefile.PL 实际工作测试
$ perl Makefile.PL  # 生成 24615 字节 Makefile + inc/ 目录 (8 文件)
$ make              # 成功
$ make test         # 成功

# 复杂特性测试 (requires, recommends, features, auto_install)
$ perl Makefile.PL  # Module::AutoInstall 检测依赖，生成 META.yml
```

### 安装文件完整性
- Packlist: 37 个文件记录在 .packlist
- perllocal.pod: 已记录 Module::Install 安装
- 关键文件: 12/12 检查通过（Module/Install.pm, inc/Module/Install.pm, Module/AutoInstall.pm 等）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-module-install-1.21-ohos-aarch64.tar.gz | 266KB | 预编译包，包含 51 个文件 |

## 注意事项

1. **纯 Perl 模块**: 无 C 编译，无 ELF 二进制文件，不需要签名。这是最简单的模块类型。
2. **inc::Module::Install 用法**: Module::Install 必须通过 `use inc::Module::Install;` 加载，不能直接 `use Module::Install;`。这是设计如此，不是错误。
3. **依赖安装**: 三个运行时依赖 (YAML::Tiny, File::Remove, Module::ScanDeps) 需要在测试前安装。如未安装，make test 会有 27/36 失败。
4. **auto_install 交互式提示**: 使用 `auto_install` 指令的 Makefile.PL 会产生交互式提示（询问是否安装缺失依赖），在自动化场景中需要通过 `echo "y" | perl Makefile.PL` 或设置环境变量绕过。
5. **OpenHarmony 兼容性**: 完全兼容，无需任何平台适配或补丁。

---

**编译结束**: 2026-06-22
**最终状态**: published
