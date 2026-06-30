# perl-module-install (Module::Install)

Module::Install is a Perl module that provides a framework for building,
packaging, and distributing Perl modules. It is an alternative to
ExtUtils::MakeMaker with additional features like auto-installation of
dependencies, bundled distributions, and more.

## Version: 1.21

## Build Details
- **Build System**: perl Makefile.PL (ExtUtils::MakeMaker)
- **Platform**: OpenHarmony aarch64
- **Perl Version**: 5.42.0
- **Module Type**: Pure Perl (no C compilation, no ELF binaries)
- **Dependencies**: YAML::Tiny 1.76, File::Remove 1.61, Module::ScanDeps 1.37
- **Patches**: None required (fully compatible with OpenHarmony)
- **Status**: published

## Installation

```bash
# 通过预编译包安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-module-install 1.21

# 验证安装
perl -e 'use lib "$ENV{HOME}/usr/local/lib/perl5"; use inc::Module::Install; print "Version: $Module::Install::VERSION\n"'
```

## Usage

Module::Install 必须通过 `inc::Module::Install` 加载，不能直接 `use Module::Install`。

```perl
# Makefile.PL 示例
use inc::Module::Install;

name 'My-Module';
version '0.01';
license 'perl';
requires 'perl' => '5.008';
all_from 'lib/MyModule.pm';
WriteAll;
```

## Notes

- 纯 Perl 模块，不受 SELinux HMDFS 限制，安装后可立即使用
- `auto_install` 指令会产生交互式提示，自动化场景请用 `echo "y" | perl Makefile.PL`
- 运行时依赖需在 `make test` 前安装，否则 27/36 测试文件会失败

## Test Results
- `make test`: 36 files, 547 tests, all passed
- Functional tests: 10/10 passed (module loading, Makefile generation, complex features)
- Quality gates: G1-G4 all PASS
