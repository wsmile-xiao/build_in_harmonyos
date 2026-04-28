# 错误模式索引（人类浏览入口）

> 本文件从 `graph/index.tsv` 生成，供人类快速浏览所有已知错误模式。
> AI 引擎请直接使用 `graph/index.tsv`（机器可读）。

## 目录

| ID | 严重度 | 分类 | 触发工具 | 关键词 | 自动修复 | 方案 | 原则 | 文档 |
|----|--------|------|---------|--------|---------|------|------|------|
| E001 | 3 | toolchain | configure | cc not found, C compiler, clang, PATH | ✅ | set-env-var | P-TOOLCHAIN-001 | [doc](doc/E001.md) |
| E002 | 3 | environment | configure\|make\|install | /tmp, temporary, read-only, erofs, TMPDIR | ✅ | set-env-var | | [doc](doc/E002.md) |
| E003 | 2 | linking | make\|ld\|clang | pthread, undefined reference, -lpthread | ✅ | add-cflags | P-CFLAGS-001 | [doc](doc/E003.md) |
| E004 | 3 | runtime-linking | python\|ld\|runtime | symbol not found, ImportError, undefined symbol | ❌ | modify-ldshared | P-RUNTIME-002 | [doc](doc/E004.md) |
| E005 | 2 | linking | make\|ld | -fPIC, relocation, R_AARCH64, PIC | ✅ | add-cflags | P-CFLAGS-001 | [doc](doc/E005.md) |
| E006 | 3 | ssl\|asm | openssl\|python\|curl\|wget | OpenSSL, BAD_SIGNATURE, RSA_verify, PSS | ❌ | reconfigure-no-asm | | [doc](doc/E006.md) |
| E007 | 2 | autotools-config | configure | config.guess, build type, HarmonyOS, autoconf | ✅ | patch-autotools-script | P-AUTOTOOLS-001, P-AUTOTOOLS-002 | [doc](doc/E007.md) |
| E008 | 2 | syscall\|compat | configure\|make\|cc\|runtime | fstat, EACCES, Permission denied, pipe | ❌ | source-patch | P-PATCH-001 | [doc](doc/E008.md) |
| E009 | 2 | selinux\|security | python\|make\|shell\|runtime | SELinux, domain transition, adhoc_bin | ✅ | pipe-bypass | | [doc](doc/E009.md) |
| E010 | 2 | tool-compat | configure\|make\|sed\|expr | toybox, sed, expr, GNU coreutils | ✅ | install-gnu-tools | | [doc](doc/E010.md) |
| E011 | 3 | platform\|hmdfs\|permissions | configure\|config.status | umask 077, Permission denied, config.status | ✅ | edit-umask-in-configure | P-PATCH-001 | [doc](doc/E011.md) |
| E012 | 3 | toolchain | configure\|make\|ar | ar command not found, llvm-ar, RANLIB | ✅ | set-env-var | P-TOOLCHAIN-001 | [doc](doc/E012.md) |
| E013 | 2 | linking | ld\|clang\|make | dlopen, dlsym, dlclose, -ldl | ✅ | add-ldflags | | [doc](doc/E013.md) |
| E014 | 2 | syscall\|compat | ld\|clang\|configure | syslog, getrandom, unimplemented, syscall | ✅ | add-cflags-disable | | [doc](doc/E014.md) |
| E015 | 2 | linking\|nls | make\|ld | libintl_dgettext, dgettext, undefined symbol | ❌ | configure-libs-option | | [doc](doc/E015.md) |
| E016 | 2 | asm\|compat | as\|clang\|configure\|make | assembler, unknown instruction, ARM mode | ✅ | reconfigure-no-asm | | [doc](doc/E016.md) |
| E017 | 2 | network | wget\|curl\|git\|configure | GitHub, timeout, timed out, wget, curl | ✅ | use-ghfast | | [doc](doc/E017.md) |
| E018 | 2 | selinux\|filesystem | ln\|make\|install\|configure | ln, symlink, Permission denied, wrapper script | ✅ | wrapper-script | | [doc](doc/E018.md) |
| E019 | 3 | runtime\|linking | ld\|runtime\|shell | shared library, cannot open, lib*.so, LD_LIBRARY_PATH | ✅ | set-ld-library-path | P-RUNTIME-002 | [doc](doc/E019.md) |
| E020 | 2 | libc\|compat | cc\|clang\|configure | _IO_FILE, _IO_read_ptr, musl, glibc, opaque type | ❌ | source-patch | P-PATCH-001 | [doc](doc/E020.md) |
| E042 | 2 | packaging\|rpath\|linking\|runtime | patchelf\|packaging\|runtime | RPATH, patchelf, lib-dynload, extension module | ✅ | set-rpath-patchelf | P-RUNTIME-002 | [doc](doc/E042.md) |
| E050 | 3 | filesystem\|hmdfs\|linking\|runtime | ld\|clang\|pip\|make | HMDFS, symlink, symbolic link, os.path.exists | ✅ | copy-replace-symlink | | [doc](doc/E050.md) |
| E051 | 3 | kernel\|syscall\|compat\|security | runtime\|cc\|python | SIGSYS, signal 31, exit 159, setreuid | ❌ | source-patch | P-PATCH-001 | [doc](doc/E051.md) |
| E063 | 2 | compiler\|warnings\|compat | cc\|clang\|make | -Werror, warning to error, int-conversion | ✅ | add-cflags-disable-werror | P-CFLAGS-001 | [doc](doc/E063.md) |
| E064 | 3 | autotools\|configuration\|security | configure\|autotools | conftest, cross compile, configure, ac_cv_ | ❌ | trigger-security-dialog | P-AUTOTOOLS-001 | [doc](doc/E064.md) |
| E074 | 2 | selinux\|build-system\|filesystem | make | make -j, parallel, FIFO, jobserver, hang | ✅ | env-var-override | P-BUILD-001 | [doc](doc/E074.md) |
| E075 | 2 | configuration\|environment\|pkg-config | configure\|cmake\|cc | C_INCLUDE_PATH, pkg-config, cflags empty | ✅ | env-var-remove | P-ENV-001 | [doc](doc/E075.md) |
| E076 | 2 | filesystem\|syscall\|runtime-behavior | cc\|clang\|coreutils | fstat, lseek, pipe, tty, socket, EACCES | ❌ | source-patch-ifdef | P-SYSCALL-001 | [doc](doc/E076.md) |
| E083 | 3 | jvm\|security\|signing | java\|System.load\|System.loadLibrary | System.load, Permission denied, dlopen, JNI | ❌ | sign-jdk-and-library | P-SIGN-001 | [doc](doc/E083.md) |
| E096 | 2 | cmake\|compiler\|configuration | cmake | CMAKE_CXX_STANDARD, C++17, C++20 | ✅ | cmake-cxx-standard-explicit | | [doc](doc/E096.md) |
| E103 | 3 | build-system\|cmake\|compat | cmake | cmake_minimum_required, Compatibility, CMake 4 | ✅ | bump-cmake-minimum-version | | [doc](doc/E103.md) |

> 完整列表见 `graph/index.tsv`（100+ 条目）。上表仅列出高优先级/高频条目。
> 
> **使用方式**：
> - AI 引擎：直接匹配 `graph/index.tsv` + `graph/E*.kv`
> - 人类浏览：按关键词 Ctrl+F 搜索，找到 E 编号后读 `doc/E{NNN}.md`

---
*error-patterns.md · 从 graph/index.tsv 生成 · 2026-04-28*
