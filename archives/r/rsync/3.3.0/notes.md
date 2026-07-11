# Notes — rsync 3.3.0

## Build Date: 2026-07-08

## Build Environment
- Compiler: clang 15.0.4
- Platform: aarch64-unknown-linux-ohos
- Build System: autotools (configure + make)

## Steps Performed

### 1. init-build
- Downloaded rsync-3.3.0.tar.gz from https://rsync.samba.org/ftp/rsync/src/rsync-3.3.0.tar.gz
- Extracted to ~/tmp/builds/rsync-3.3.0.work
- Build context generated successfully

### 2. Tool Check (R18)
- All build tools verified present (sed, gawk, grep, find, make, automake, autoconf, libtool, pkg-config)

### 3. Dependency Installation (R18)
- Checked Conan 制品仓 (ohpcd remote): xxhash, zstd, lz4, openssl 均未找到 @ohpcd/stable 版本
- Installed pre-compiled packages from cmd-pkgs to $HOME/usr/local:
  - xxhash 0.8.2
  - zstd 1.5.6
  - lz4 1.10.0 (installed in separate dir, created symlinks to standard location)
- openssl already available on system

### 4. Configure
- **Issue 1**: config.guess could not recognize OHOS platform
  - Fix: Replaced config.guess and config.sub with automake-1.17 versions (patches 0001, 0002)
  - Knowledge graph: E114 category (platform-hmdfs)

- **Issue 2**: config.status mktemp creates temp directory in current dir with wrong permissions on HMDFS
  - Error: `can't create ./confXXXXXX/subs1.awk: Permission denied`
  - Fix: Programmatic fix in build() via _fix_config_status_mktemp(), applied between configure --no-create and config.status execution
  - NOT a source patch (config.status is a generated file)
  - Knowledge graph: E114 (exact match)

### 5. Make
- Success (exit code 0)
- Warnings: deprecation warnings in bundled zlib/popt (non-critical)
- Linked with: -llz4 -lzstd -lxxhash -lcrypto

### 6. Make Install (DESTDIR)
- Success: installed to staging directory
- Products: bin/rsync, bin/rsync-ssl, man pages

### 7. Make Check
- **Failed** (exit code 2)
- Reason: `whoami: bad uid 20020099` — OHOS platform does not have whoami/id commands
- Impact: Test infrastructure failure, not a compilation issue
- Binary verified working: `rsync --version` outputs correct version and feature list

### 8. Binary Verification
- rsync --version: OK (version 3.3.0, protocol version 31)
- Checksum: xxh128 xxh3 xxh64 (xxhash) md5 md4 sha1 none
- Compress: zstd lz4 zlibx zlib none
- Optimizations: openssl-crypto
- Dynamic deps: libzstd.so.1, libcrypto.so.3, libc.so
- xxhash and lz4 linked statically (.a files)

## Conan Recipe
- conanfile.py: Generated and fixed by AI
  - requirements: None (xxhash/zstd/lz4/openssl not available as Conan packages on ohpcd remote;
    installed via cmd-pkgs to $HOME/usr/local, paths passed via AutotoolsToolchain)
  - generate(): AutotoolsToolchain with -static (R26), --prefix from Conan, --no-create (E114),
    system dependency paths via expanduser("~") (R33: no hardcoded absolute paths)
  - build(): Uses Autotools.configure() and Autotools.make() (R33: flags from toolchain, not shell env vars)
  - E114 fix: _fix_config_status_mktemp() applied between configure --no-create and config.status
  - E165 fix: _fix_all_shebangs() fixes #!/bin/sh → #!/system/bin/sh
  - HAVE_GETPASS: _undef_getpass() after config.status generates config.h
  - package_info(): rsync is a tool, not a library
- conandata.yml: URL and sha256 filled in; patches 0001-config.guess.patch and 0002-config.sub.patch
- test_package/: Updated to run rsync --version instead of linking to library

## Patches
- 0001-config.guess.patch: Replace config.guess with automake version for HarmonyOS recognition
- 0002-config.sub.patch: Replace config.sub with automake version for HarmonyOS platform support
- E114 (config.status mktemp): Programmatic fix in build(), NOT a source patch (config.status is generated)

**质量返工**: 2026-07-08 — 修复 R33 违规（硬编码路径、绕过 toolchain）和归档问题（补丁声明、构建产物清理）
**发布返工**: 2026-07-08 — 修复 E114（config.status 在 build_folder 而非 source_folder）、R34（test.c 调用 rsync --version）、R38（commands.json）、prefix 双重嵌套（移除 --prefix 覆盖）、conan-verify 全门禁通过
---

**编译结束**: 2026-07-08 14:39
**最终状态**: published
