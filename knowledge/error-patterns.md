# 🐛 错误模式知识库 — 主索引

> **版本**: v3.2 | **总条目**: 75 (E001-E075)
> 📂 **子文件**: [doc/E001.md~E020.md](./doc/) (E001-E020) · [doc/E021.md~E049.md](./doc/) (E021-E049) · [doc/E050.md~E080.md](./doc/) (E050-E080) · 结构化数据见 [graph/*.kv](./graph/)

## 🔍 快速检索

```bash
grep -n "关键词" knowledge/error-patterns*.md   # 跨文件搜索所有子文件
```

常用搜索：`relocation\|-fPIC` / `undefined reference` / `Permission denied\|SELinux` / `musl\|_GNU_SOURCE`

---

## 📋 完整索引表

| # | 类型 | 严重度 | 搜索关键词 | 所在文件 |
|---|------|--------|-----------|---------|
| ~~E001~~ | ~~工具链~~ | ~~🔴~~ | ~~configure, cc not found, C compiler, clang, PATH~~ | **→ [graph/E001.kv](./graph/E001.kv) + [doc/E001.md](./doc/E001.md)** |
| ~~E002~~ | ~~环境~~ | ~~🔴~~ | ~~/tmp, temporary directory, read-only, erofs, TMPDIR~~ | **→ [graph/E002.kv](./graph/E002.kv) + [doc/E002.md](./doc/E002.md)** |
| ~~E003~~ | ~~链接~~ | ~~🟡~~ | ~~pthread, undefined reference, -lpthread, -pthread~~ | **→ [graph/E003.kv](./graph/E003.kv) + [doc/E003.md](./doc/E003.md)** |
| ~~E004~~ | ~~链接~~ | ~~🔴~~ | ~~symbol not found, musl, BIND_NOW, ImportError, dlopen~~ | **→ [graph/E004.kv](./graph/E004.kv) + [doc/E004.md](./doc/E004.md)** |
| ~~E005~~ | ~~编译~~ | ~~🟡~~ | ~~relocation, -fPIC, R_AARCH64, static library, PIC~~ | **→ [graph/E005.kv](./graph/E005.kv) + [doc/E005.md](./doc/E005.md)** |
| ~~E006~~ | ~~SSL~~ | ~~🔴~~ | ~~OpenSSL, BAD_SIGNATURE, RSA_verify, no-asm, SSL~~ | **→ [graph/E006.kv](./graph/E006.kv) + [doc/E006.md](./doc/E006.md)** |
| ~~E007~~ | ~~配置~~ | ~~🟡~~ | ~~config.guess, build type, HarmonyOS, autoconf~~ | **→ [graph/E007.kv](./graph/E007.kv) + [doc/E007.md](./doc/E007.md)** |
| ~~E008~~ | ~~系统调用~~ | ~~🟡~~ | ~~fstat, Permission denied, pipe, lseek, EACCES~~ | **→ [graph/E008.kv](./graph/E008.kv) + [doc/E008.md](./doc/E008.md)** |
| ~~E009~~ | ~~SELinux~~ | ~~🔴~~ | ~~SELinux, domain transition, subprocess, adhoc_bin~~ | **→ [graph/E009.kv](./graph/E009.kv) + [doc/E009.md](./doc/E009.md)** |
| ~~E010~~ | ~~工具~~ | ~~🟡~~ | ~~toybox, sed, expr, GNU coreutils, 正则表达式~~ | **→ [graph/E010.kv](./graph/E010.kv) + [doc/E010.md](./doc/E010.md)** |
| ~~E011~~ | ~~编译~~ | ~~🟡~~ | ~~__OHOS__, undefined, macro, -D~~ | **→ 已废弃(工具链默认包含)** |
| ~~E012~~ | ~~工具链~~ | ~~🔴~~ | ~~llvm-ar, ar command not found, LLVM toolchain, RANLIB~~ | **→ [graph/E012.kv](./graph/E012.kv) + [doc/E012.md](./doc/E012.md)** |
| ~~E013~~ | ~~链接~~ | ~~🟡~~ | ~~dlopen, dlsym, undefined reference, -ldl, libdl~~ | **→ [graph/E013.kv](./graph/E013.kv) + [doc/E013.md](./doc/E013.md)** |
| ~~E014~~ | ~~系统调用~~ | ~~🟡~~ | ~~syslog, getrandom, syscall, NO_SYSLOG~~ | **→ [graph/E014.kv](./graph/E014.kv) + [doc/E014.md](./doc/E014.md)** |
| ~~E015~~ | ~~编译~~ | ~~🟡~~ | ~~sys/socket.h, No such file, header, CPPFLAGS, sysroot~~ | **→ 已废弃(编译器自动搜索sysroot)** |
| ~~E016~~ | ~~汇编~~ | ~~🟡~~ | ~~assembler error, unknown instruction, ARM, --disable-asm~~ | **→ [graph/E016.kv](./graph/E016.kv) + [doc/E016.md](./doc/E016.md)** |
| ~~E017~~ | ~~网络~~ | ~~🟡~~ | ~~GitHub, wget timeout, curl timed out, network, mirror~~ | **→ [graph/E017.kv](./graph/E017.kv) + [doc/E017.md](./doc/E017.md)** |
| ~~E018~~ | ~~SELinux~~ | ~~🟡~~ | ~~symbolic link, ln, Permission denied, wrapper script~~ | **→ [graph/E018.kv](./graph/E018.kv) + [doc/E018.md](./doc/E018.md)** |
| ~~E019~~ | ~~运行时~~ | ~~🔴~~ | ~~shared libraries, LD_LIBRARY_PATH, rpath, cannot open~~ | **→ [graph/E019.kv](./graph/E019.kv) + [doc/E019.md](./doc/E019.md)** |
| ~~E020~~ | ~~兼容性~~ | ~~🟡~~ | ~~FILE structure, _IO_read_ptr, musl, incomplete type, glibc~~ | **→ [graph/E020.kv](./graph/E020.kv) + [doc/E020.md](./doc/E020.md)** |
| ~~E021~~ | ~~配置~~ | ~~🟡~~ | ~~BUILDEXEEXT, .exe, case insensitive, configure~~ | **→ [graph/E021.kv](./graph/E021.kv) + [doc/E021.md](./doc/E021.md)** |
| ~~E022~~ | ~~系统调用~~ | ~~🟢~~ | ~~sem_unlink, POSIX semaphore, /dev/shm, FileNotFoundError~~ | **→ [graph/E022.kv](./graph/E022.kv) + [doc/E022.md](./doc/E022.md)** |
| ~~E023~~ | ~~系统~~ | ~~🟢~~ | ~~locale, FAIL, UTF-8, LC_ALL, test_strcoll, test_locale~~ | **→ [graph/E023.kv](./graph/E023.kv) + [doc/E023.md](./doc/E023.md)** |
| ~~E024~~ | ~~系统~~ | ~~🟡~~ | ~~Unix socket, bind, AF_UNIX, multiprocessing, PermissionError~~ | **→ [graph/E024.kv](./graph/E024.kv) + [doc/E024.md](./doc/E024.md)** |
| ~~E025~~ | ~~编译~~ | ~~🟡~~ | ~~CAN_RAW_FD_FRAMES, CAN socket, undeclared, pyconfig.h~~ | **→ [graph/E025.kv](./graph/E025.kv) + [doc/E025.md](./doc/E025.md)** |
| ~~E026~~ | ~~兼容性~~ | ~~🟡~~ | ~~TLS, thread-local storage, __thread, _Thread_local, musl~~ | **→ [graph/E026.kv](./graph/E026.kv) + [doc/E026.md](./doc/E026.md)** |
| ~~E027~~ | ~~链接~~ | ~~🟡~~ | ~~libintl_gettext, gettext, -lnls, --disable-nls, NLS~~ | **→ [graph/E027.kv](./graph/E027.kv) + [doc/E027.md](./doc/E027.md)** |
| ~~E028~~ | ~~运行时~~ | ~~🔴~~ | ~~共享库冲突, ncurses, system library, --without-shared~~ | **→ [graph/E028.kv](./graph/E028.kv) + [doc/E028.md](./doc/E028.md)** |
| ~~E029~~ | ~~运行时~~ | ~~🟡~~ | ~~bash-malloc, musl incompatible, --without-bash-malloc~~ | **→ [graph/E029.kv](./graph/E029.kv) + [doc/E029.md](./doc/E029.md)** |
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
| E066 | 脚本 | 🟡 | tar xzf, .tar.xz, ohc-run.py refresh-patch, tar xJf | [runtime](./error-patterns-runtime.md#e066-refresh-patchsh-不支持-tarxz-格式) |
| E067 | 脚本 | 🟡 | grep, 正则元字符, grep -F, fixed string, BRE | [runtime](./error-patterns-runtime.md#e067-grep-匹配含正则元字符的固定字符串失败) |
| E072 | 配置 | 🔴 | config.sub, invalid triplet, ohos, unknown operating system | **→ [graph/E072.kv](./graph/E072.kv) + [doc/E072.md](./doc/E072.md)** |
| E073 | 运行时/FS | 🔴 | shared library, .so, symlink, cannot load, dlopen, HMDFS | **→ [graph/E073.kv](./graph/E073.kv) + [doc/E073.md](./doc/E073.md)** |
| E074 | 构建/SELinux | 🟡 | make -j, FIFO, jobserver, hang, parallel build | **→ [graph/E074.kv](./graph/E074.kv) + [doc/E074.md](./doc/E074.md)** |
| E075 | 配置/环境 | 🟡 | C_INCLUDE_PATH, pkg-config, cflags empty, header not found | **→ [graph/E075.kv](./graph/E075.kv) + [doc/E075.md](./doc/E075.md)** |
| **E076** | **文件系统/系统调用** | **🟡** | **fstat, lseek, pipe, EACCES, coreutils (cat/head/tail/dd)** | **→ [graph/E076.kv](./graph/E076.kv) + [doc/E076.md](./doc/E076.md)** |
| **E077** | **ELF签名/打包后处理** | **🔴** | **patchelf/strip 后签名失效, operation not permitted, 四步重签流程** | **→ [graph/E077.kv](./graph/E077.kv) + [doc/E077.md](./doc/E077.md)** |
| **E078** | **musl动态链接/BIND_NOW** | **🔴** | **Error relocating .so: symbol not found, ImportError, LDSHARED vs BLDSHARED** | **→ [graph/E078.kv](./graph/E078.kv) + [doc/E078.md](./doc/E078.md)** |
| **E079** | **HMDFS硬链接不支持** | **🟡** | **cannot create hard link: Operation not permitted, make install/git/ccache/cargo/pnpm** | **→ [graph/E079.kv](./graph/E079.kv) + [doc/E079.md](./doc/E079.md)** |
| **E080** | **Python venv lib64 symlink 被拒** | **🟡** | **Permission denied: lib->lib64, venv, HMDFS os.symlink** | **→ [graph/E080.kv](./graph/E080.kv) + [doc/E080.md](./doc/E080.md)** |

## 📊 统计

| 类别 | 范围 | 数量 | 子文件 |
|------|------|------|--------|
| 平台/环境 | E001-E020 | **20** | core.md |
| 编译/构建 | E021-E049 | **29** | compile.md |
| 运行时/测试 | E050-E073 | **24** | runtime.md + troubleshooting.md |
| **合计** | **E001-E080** | **80** | — |

严重度: 🔴阻塞=27 · 🟡中等=39 · 🟢轻微=6 · ✅已解决=1 · 🟡待确认=2

---
*v3.0 模块化版 | 2026-04-08 | 从 v2.6 单文件拆分为 4 文件*
