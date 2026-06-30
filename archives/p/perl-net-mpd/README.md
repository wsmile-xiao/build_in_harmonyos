# perl-net-mpd (Net::MPD)

Communicate with an MPD (Music Player Daemon) server.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 0.07-r3 | published | 2026-06-29 |

## Description

Net::MPD provides an object-oriented interface to communicate with an MPD
(Music Player Daemon) server. It supports all commands defined in the MPD
protocol.

## Build System

- Module::Build::Tiny (Perl)
- Build: `perl Build.PL && ./Build && ./Build install`
- No C/C++ compilation required (pure Perl module)

## Dependencies

- Perl 5.10+
- version 0.77, Carp, IO::Socket::INET, Scalar::Util (all core Perl modules)

## OpenHarmony 适配说明

- 纯 Perl 模块，无 C/XS 编译，不存在 SELinux HMDFS 限制
- 使用 Module::Build::Tiny 构建 (`perl Build.PL && ./Build`)
- Conan 配方将产物重组到 `lib/` 根目录以通过 G4 产物完整性检查
- 用户通过 `conan install` 安装后设置 `PERL5LIB` 即可使用，无需管理员权限
- 功能测试全部通过（详见 `0.07-r3/reports/test-report.md`）
