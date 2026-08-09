# AppConfig 1.71 Adaptation Notes

## Source

- Upstream: CPAN `AppConfig`
- Version: 1.71
- URL: https://cpan.metacpan.org/modules/by-module/AppConfig/AppConfig-1.71.tar.gz
- SHA256: `1177027025ecb09ee64d9f9f255615c04db5e14f7536c344af632032eb887b0f`
- License: Perl license, equivalent to Artistic-1.0-Perl or GPL-1.0-or-later.

The CPAN module index for `modules/by-module/AppConfig/` lists only
`AppConfig-1.66.tar.gz` and `AppConfig-1.71.tar.gz`; 1.71 is the latest
stable release in that official index.

## Build Contract

AppConfig is a pure Perl distribution. It provides:

- `AppConfig.pm`
- `AppConfig/Args.pm`
- `AppConfig/CGI.pm`
- `AppConfig/File.pm`
- `AppConfig/Getopt.pm`
- `AppConfig/State.pm`
- `AppConfig/Sys.pm`

The upstream build system is `ExtUtils::MakeMaker` through `Makefile.PL`.
`Makefile.PL` declares Perl 5.8.8 or newer, `Test::More` for tests, and
`Test::Pod` only for optional author POD checks.

## Dependencies

- Runtime/build interpreter: `perl/5.42.2`
- No XS code, no C/C++ library dependency, and no source patches.

W0 evidence for `perl/5.42.2`:

- Fresh Conan home: `E:/HarmonyPC/conan-homes/appconfig-1.71-w0-20260810-053000`
- Download log: `E:/HarmonyPC/source-audit/appconfig-1.71/w0-perl-5.42.2/download-perl_5.42.2.stdout.log`
- Install JSON: `E:/HarmonyPC/source-audit/appconfig-1.71/w0-perl-5.42.2/install-perl_5.42.2.json`
- Result: `perl/5.42.2#13c4f5bde5668df0b7268c4d0c01073c`, package id
  `6b129b068851896169fae42d399fa922d239ce8a`, package revision
  `ec97109d67c453b723126b261da3fd9e`, binary `Download`.

## Upstream Tests

Official source inventory contains 16 `t/*.t` files. In a normal installation
path, two author POD tests are skipped by upstream logic because
`AUTOMATED_TESTING` is unset or `Test::Pod` is unavailable:

- `t/97-pod.t`
- `t/99_author.t`

The 14 functional upstream tests were run with `PERL5LIB=lib`:

- `t/appconfig.t`
- `t/args.t`
- `t/block.t`
- `t/cgi.t`
- `t/compact.t`
- `t/const.t`
- `t/default.t`
- `t/file.t`
- `t/flag.t`
- `t/getopt.t`
- `t/multi.t`
- `t/novars.t`
- `t/state.t`
- `t/sys.t`

Result: 14/14 functional upstream tests passed. Raw log:
`E:/HarmonyPC/source-audit/appconfig-1.71/upstream-functional-tests-git-perl.log`.

## Packaging

The recipe runs:

```bash
perl Makefile.PL PREFIX=/usr/local INSTALLDIRS=site
make -j1
make install DESTDIR=<package_folder>
```

It also copies the pure Perl modules into package `lib/` so consumers have a
stable Conan-side module root. `package_info()` prepends that directory to
`PERL5LIB`.
