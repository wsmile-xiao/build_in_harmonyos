# 🐛 错误模式知识库 — 主索引

> **版本**: v3.0 (模块化) | **总条目**: 68 (E001-E068)
> 📂 **子文件**: [core.md](./error-patterns-core.md) (E001-E020) · [compile.md](./error-patterns-compile.md) (E021-E049) · [runtime.md](./error-patterns-runtime.md) (E050-E068)

## 🔍 快速检索

```bash
grep -n "关键词" knowledge/error-patterns*.md   # 跨文件搜索所有子文件
```

常用搜索：`relocation\|-fPIC` / `undefined reference` / `Permission denied\|SELinux` / `musl\|_GNU_SOURCE`

---

## 📋 完整索引表

| # | 类型 | 严重度 | 搜索关键词 | 所在文件 |
|---|------|--------|-----------|---------|
| E001 | 工具链 | 🔴 | configure, cc not found, C compiler, clang, PATH | [core](./error-patterns-core.md#e001-找不到编译器) |
| E002 | 环境 | 🔴 | /tmp, temporary directory, read-only, erofs, TMPDIR | [core](./error-patterns-core.md#e002-临时目录不可写) |
| E003 | 链接 | 🟡 | pthread, undefined reference, -lpthread, -pthread | [core](./error-patterns-core.md#e003-找不到-pthread) |
| E004 | 链接 | 🔴 | symbol not found, musl, BIND_NOW, ImportError, dlopen | [core](./error-patterns-core.md#e004-符号找不到-musl-bind_now) |
| E005 | 编译 | 🟡 | relocation, -fPIC, R_AARCH64, static library, PIC | [core](./error-patterns-core.md#e005-静态库链接共享库失败) |
| E006 | SSL | 🔴 | OpenSSL, BAD_SIGNATURE, RSA_verify, no-asm, SSL | [core](./error-patterns-core.md#e006-openssl-bad_signature) |
| E007 | 配置 | 🟡 | config.guess, build type, HarmonyOS, autoconf | [core](./error-patterns-core.md#e007-configguess-无法识别系统) |
| E008 | 系统调用 | 🟡 | fstat, Permission denied, pipe, lseek, EACCES | [core](./error-patterns-core.md#e008-fstat-返回-eacces) |
| E009 | SELinux | 🔴 | SELinux, domain transition, subprocess, adhoc_bin | [core](./error-patterns-core.md#e009-selinux-域转换限制) |
| E010 | 工具 | 🟡 | toybox, sed, expr, GNU coreutils, 正则表达式 | [core](./error-patterns-core.md#e010-toybox-兼容性问题) |
| E011 | 编译 | 🟡 | __OHOS__, undefined, macro, compiler flag, -D | [core](./error-patterns-core.md#e011-__ohos__-未定义) |
| E012 | 工具链 | 🔴 | llvm-ar, ar command not found, LLVM toolchain, RANLIB | [core](./error-patterns-core.md#e012-找不到-llvm-ar) |
| E013 | 链接 | 🟡 | dlopen, dlsym, undefined reference, -ldl, libdl | [core](./error-patterns-core.md#e013-动态链接错误) |
| E014 | 系统调用 | 🟡 | syslog, getrandom, syscall, unimplemented, NO_SYSLOG | [core](./error-patterns-core.md#e014-系统调用不可用) |
| E015 | 编译 | 🟡 | sys/socket.h, No such file, header, CPPFLAGS, sysroot | [core](./error-patterns-core.md#e015-找不到头文件) |
| E016 | 编译 | 🟡 | assembler error, unknown instruction, ARM, --disable-asm | [core](./error-patterns-core.md#e016-汇编代码错误) |
| E017 | 网络 | 🟡 | GitHub, wget timeout, curl timed out, network, mirror | [core](./error-patterns-core.md#e017-github-下载慢) |
| E18 | SELinux | 🟡 | symbolic link, ln, Permission denied, wrapper script | [core](./error-patterns-core.md#e018-软链接创建失败) |
| E019 | 运行时 | 🔴 | shared libraries, LD_LIBRARY_PATH, rpath, cannot open | [core](./error-patterns-core.md#e019-库加载失败) |
| E020 | 兼容性 | 🟡 | FILE structure, _IO_read_ptr, musl, incomplete type, glibc | [core](./error-patterns-core.md#e020-musl-file-结构差异) |
| E021 | 配置 | 🟡 | BUILDEXEEXT, .exe, case insensitive, configure | [compile](./error-patterns-compile.md#e021-buildexeext-异常) |
| E022 | 系统调用 | 🟢 | sem_unlink, POSIX semaphore, /dev/shm, FileNotFoundError | [compile](./error-patterns-compile.md#e022-posix-信号量差异) |
| E023 | 系统 | 🟢 | locale, FAIL, UTF-8, LC_ALL, test_strcoll, test_locale | [compile](./error-patterns-compile.md#e023-locale-支持不完整) |
| E024 | 系统 | 🟡 | Unix socket, bind, AF_UNIX, multiprocessing, PermissionError | [compile](./error-patterns-compile.md#e024-unix-domain-socket-受限) |
| E025 | 编译 | 🟡 | CAN_RAW_FD_FRAMES, CAN socket, undeclared, pyconfig.h | [compile](./error-patterns-compile.md#e025-can-socket-宏未定义) |
| E026 | 兼容性 | 🟡 | TLS, thread-local storage, __thread, _Thread_local, musl | [compile](./error-patterns-compile.md#e026-线程局部存储tls-差异) |
| E027 | 链接 | 🟡 | libintl_gettext, gettext, -lnls, --disable-nls, NLS | [compile](./error-patterns-compile.md#e027-libintl_gettext-链接失败) |
| E028 | 运行时 | 🔴 | 共享库冲突, ncurses, system library, --without-shared | [compile](./error-patterns-compile.md#e028-用户编译的共享库与系统库冲突) |
| E029 | 运行时 | 🟡 | bash-malloc, musl incompatible, --without-bash-malloc | [compile](./error-patterns-compile.md#e029-bash-内置-malloc-与-musl-不兼容) |
| E030 | 配置 | 🟡 | m32, 32-bit, strace, personality, --disable-mpers | [compile](./error-patterns-compile.md#e030-鸿蒙无-32-位兼容层导致-strace-编译失败) |
| E031 | 运行时 | 🔴 | /proc/stat, htop, Permission denied, procfs, SELinux | [compile](./error-patterns-compile.md#e031-proc-文件系统-selinux-访问限制) |
| E032 | 编译 | 🟡 | _GNU_SOURCE, DIR, dirent, opendir, _BSD_SOURCE | [compile](./error-patterns-compile.md#e032-_gnu_source-未定义导致-dirent-api-不完整) |
| E033 | 编译 | 🟡 | cchar_t, ncurses, _XOPEN_SOURCE_EXTENDED, setcchar | [compile](./error-patterns-compile.md#e033-ncurses-宽字符函数需要-_xopen_source_extended) |
| E034 | 运行时 | 🟡 | CA certificates, SSL, wget, ca-certificates | [compile](./error-patterns-compile.md#e034-系统缺少-ca-证书包) |
| E035 | 工具链 | 🟢 | libtoolize, func_add_hook, autotools, shell function | [compile](./error-patterns-compile.md#e035-libtoolize-shell-函数加载失败) |
| E036 | 配置 | 🟡 | platform string, space, get_platform, sysconfig, uname | [compile](./error-patterns-compile.md#e036-平台字符串含空格导致构建路径错误) |
| E037 | 环境 | 🟡 | /usr/bin/env, shebang, bad interpreter, #!/bin/sh | [compile](./error-patterns-compile.md#e037-usrbinenv-不存在导致-shebang-失败) |
| E038 | 运行时 | 🟡 | groff, macro file, man-db, tmac, mandoc, g.tmac | [compile](./error-patterns-compile.md#e038-groff-宏文件缺失) |
| E039 | 兼容性 | 🟡 | iconv, //IGNORE, Invalid argument, musl, glibc extension | [compile](./error-patterns-compile.md#e039-musl-iconv-不支持-ignore-后缀) |
| E040 | 运行时 | 🔴 | SIGSEGV, mandb, MAN_OWNER, NULL pointer, getpwnam | [compile](./error-patterns-compile.md#e040-man_owner-空指针解引用段错误) |
| E041 | 构建 | 🟡 | automake, version mismatch, ACLOCAL, /bin/true, VPATH | [compile](./error-patterns-compile.md#e041-automake-版本不匹配触发重生成) |
| E042 | 打包 | 🔴 | RPATH, ImportError, patchelf, 扩展模块, $ORIGIN | [compile](./error-patterns-compile.md#e042-扩展模块-rpath-遗漏导致运行时库找不到) |
| E043 | 脚本 | 🟡 | BASH_SOURCE, HiShell, toybox ash, activate.sh, $0 | [compile](./error-patterns-compile.md#e043-activatesh-中-bash_source-在-hishell-不可用) |
| E044 | 运行时 | 🔴 | PYTHONHOME, ModuleNotFoundError, encodings, 可移植包 | [compile](./error-patterns-compile.md#e044-可移植包缺少-pythonhome-导致标准库找不到) |
| E045 | 系统调用 | ✅ | mmap, W^X, RWX, CFUNCTYPE, MemoryError, mprotect | [compile](./error-patterns-compile.md#e045-mmap-rwx-被拒w^x-策略) |
| E046 | SELinux/FS | 🟡 | chmod, Permission denied, st_mode unchanged, 不生效 | [compile](./error-patterns-compile.md#e046-chmod-完全不生效) |
| E047 | FS | 🟢 | st_mode, other-read, 0o004, umask, HMDFS, 0o640 | [compile](./error-patterns-compile.md#e047-文件权限-other-read-被额外屏蔽) |
| E048 | 内核 | 🟢 | UDPLITE, IPPROTO_UDPLITE, Permission denied, socket | [compile](./error-patterns-compile.md#e048-udplite-协议不支持) |
| E049 | 构建/脚本 | 🟡 | shebang, 硬编码路径, /bin/env, 可移植性, env 参数 | [compile](./error-patterns-compile.md#e049-脚本-shebang-硬编码绝对路径导致不可移植) |
| E050 | 系统调用 | 🟡 | find_library, ldconfig, SubprocessError, ctypes, cffi | [runtime](./error-patterns-runtime.md#e050-find_library-崩溃ldconfig-不存在) |
| E051 | 内核/信号 | 🔴 | SIGSYS, setreuid, setregid, chroot, exit 159, core dump | [runtime](./error-patterns-runtime.md#e051-未实现-syscall-触发-sigsys-导致进程崩溃) |
| E052 | 构建/RPATH | 🔴 | rpath, libpython, LD_LIBRARY_PATH, 子进程, exit 127 | [runtime](./error-patterns-runtime.md#e052-rpath-缺失导致子进程找不到-libpython) |
| E053 | 工具链 | 🔴 | cc1plus, clang++, CXX compiler, C++ 编译器 | [runtime](./error-patterns-runtime.md#e053-cc1plus-不可用必须使用-clang) |
| E054 | 安全机制 | 🟡 | 首次执行, 安全确认弹窗, Permission denied, make check | [runtime](./error-patterns-runtime.md#e054-外来二进制首次执行被安全确认弹窗阻止) |
| E055 | 子进程 | 🟡 | posix_spawn, fork/exec, vfork, subprocess, errpipe | [runtime](./error-patterns-runtime.md#e055-posix_spawn-与-forkexec-行为差异) |
| E056 | 测试 | 🔴 | unittest, SkipIf, reason, IndentationError, 多行装饰器 | [runtime](./error-patterns-runtime.md#e056-unittestskipif-reason-换行反转导致-indentationerror) |
| E057 | 测试 | 🟡 | regrtest, worker, 并发测试, cpu_count, TESTOPTS -j | [runtime](./error-patterns-runtime.md#e057-regrtest-默认多worker导致并发竞态) |
| E058 | 补丁质量 | 🔴 | sed, configure, Makefile, 不可复现, .patch, distclean | [runtime](./error-patterns-runtime.md#e058-sed-操作生成文件导致补丁不可复现) |
| E059 | 补丁质量 | 🔴 | 源码修改, .patch 文件, diff, 补丁丢失, PROGRESS.md | [runtime](./error-patterns-runtime.md#e059-源码修改未保存为-patch-文件) |
| E060 | 补丁质量 | 🟡 | __OHOS__, 守卫, 上游化, 硬编码, #ifdef, 平台隔离 | [runtime](./error-patterns-runtime.md#e060-补丁缺少-__ohos__-守卫无法上游化) |
| E061 | gnulib | 🔴 | gnulib, stdbool.h, stdbool-c99, conftest, gl_STDBOOL_H | [runtime](./error-patterns-runtime.md#e061-gnulib-stdbool-h-模块缺失) |
| E062 | gnulib | 🟡 | FLEXIBLE_ARRAY_MEMBER, undeclared, flexmember.h, C99 | [runtime](./error-patterns-runtime.md#e062-flexible_array_member-未定义) |
| E063 | 编译 | 🔴 | -Werror, warning, int-conversion, Wno-error, 警告升级 | [runtime](./error-patterns-runtime.md#e063--werror-导致警告变错误) |
| E064 | configure | 🔴 | conftest, inaccessible, cross compile, cache, ac_cv_ | [runtime](./error-patterns-runtime.md#e064-conftest-无法执行导致配置检测失败) |
| E065 | 编译 | 🟡 | xzalloc, size_t, undeclared, gnulib, xalloc.h, CPPFLAGS | [runtime](./error-patterns-runtime.md#e065-gnulib-头文件包含顺序导致符号未声明) |
| E066 | 脚本 | 🟡 | tar xzf, .tar.xz, refresh-patch.sh, tar xJf | [runtime](./error-patterns-runtime.md#e066-refresh-patchsh-不支持-tarxz-格式) |
| E067 | 脚本 | 🟡 | grep, 正则元字符, grep -F, fixed string, BRE | [runtime](./error-patterns-runtime.md#e067-grep-匹配含正则元字符的固定字符串失败) |

## 📊 统计

| 类别 | 范围 | 数量 | 子文件 |
|------|------|------|--------|
| 平台/环境 | E001-E020 | **20** | core.md |
| 编译/构建 | E021-E049 | **29** | compile.md |
| 运行时/测试 | E050-E068 | **19** | runtime.md |
| **合计** | **E001-E068** | **68** | — |

严重度: 🔴阻塞=23 · 🟡中等=33 · 🟢轻微=6 · ✅已解决=1 · 🟡待确认=2

---
*v3.0 模块化版 | 2026-04-08 | 从 v2.6 单文件拆分为 4 文件*
