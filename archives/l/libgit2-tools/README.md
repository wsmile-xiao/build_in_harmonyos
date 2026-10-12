# libgit2-tools

git2 command-line tools built from the official libgit2 source tree.
The `git2` CLI provides subcommands (init, clone, commit, log, blame,
diff, cat-file, hash-object, ...) implemented on top of the libgit2
portable Git core library. Same packaging approach as the openSUSE
"libgit2-tools" split package.

## Version

| Version | Status | Date |
|---------|--------|------|
| 1.9.6 | built | 2026-09-18 |

## Dependencies

- openssl/3.5.6.1
- zlib/1.3.1.1

## Description

libgit2 is a portable, pure C implementation of the Git core methods.
This package ships the `git2` command-line utility produced by the
upstream CMake build (`BUILD_CLI=ON`), statically linked against the
libgit2 objects.
