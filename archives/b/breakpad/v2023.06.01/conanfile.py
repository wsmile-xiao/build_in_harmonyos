#!/usr/bin/env python3
"""Conan recipe — Breakpad v2023.06.01 (Autotools).

Breakpad is Google's crash reporting library. This recipe builds
the static libraries (libbreakpad.a, libbreakpad_client.a) and
tools (dump_syms, minidump_stackwalk, etc.) for HarmonyOS.

Adaptations for HarmonyOS:
  1. config.guess: HarmonyOS platform detection + exit
  2. config.sub: linux-ohos kernel-OS combination
  3. linux_syscall_support.h: stub (lss not in release tarball)
  4. stab.h: stub (not in HarmonyOS sysroot)
  5. umask 077 fix: HMDFS filesystem permission issue
  6. -Wno-error=sign-compare: system header CMSG_NXTHDR warning
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# LSS stub content - minimal linux_syscall_support.h
LSS_STUB = r'''/* Minimal linux_syscall_support.h stub for HarmonyOS compilation. */
#ifndef LINUX_SYSCALL_SUPPORT_H
#define LINUX_SYSCALL_SUPPORT_H
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <sys/uio.h>
#include <sys/wait.h>
#include <sys/prctl.h>
#include <sys/ptrace.h>
#include <sys/syscall.h>
#include <sys/mman.h>
#include <sys/utsname.h>
#include <unistd.h>
#include <fcntl.h>
#include <dirent.h>
#include <errno.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <string.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef uint64_t kernel_sigset_t;
struct kernel_sigaction {
    void (*sa_handler_)(int);
    unsigned long sa_flags;
    void (*sa_restorer)(void);
    kernel_sigset_t sa_mask;
};
struct kernel_iovec { void *iov_base; size_t iov_len; };
struct kernel_msghdr {
    void *msg_name; int msg_namelen;
    struct kernel_iovec *msg_iov; size_t msg_iovlen;
    void *msg_control; size_t msg_controllen; unsigned int msg_flags;
};
struct kernel_dirent {
    unsigned long long d_ino; long long d_off;
    unsigned short d_reclen; unsigned char d_type; char d_name[];
};
#define kernel_stat stat
static inline int sys_close(int fd) { return close(fd); }
static inline int sys_open(const char *p, int f, ...) {
    mode_t m=0; if(f&O_CREAT){va_list a;va_start(a,f);m=(mode_t)va_arg(a,int);va_end(a);} return open(p,f,m);
}
static inline ssize_t sys_read(int fd, void *b, size_t c) { return read(fd,b,c); }
static inline ssize_t sys_write(int fd, const void *b, size_t c) { return write(fd,b,c); }
static inline off_t sys_lseek(int fd, off_t o, int w) { return lseek(fd,o,w); }
static inline int sys_pipe(int f[2]) { return pipe(f); }
static inline ssize_t sys_sendmsg(int s, const struct kernel_msghdr *m, int f) { return sendmsg(s,(const struct msghdr*)m,f); }
static inline void *sys_mmap(void *a, size_t l, int p, int f, int fd, off_t o) { return mmap(a,l,p,f,fd,o); }
static inline int sys_munmap(void *a, size_t l) { return munmap(a,l); }
static inline pid_t sys_waitpid(pid_t p, int *s, int o) { return waitpid(p,s,o); }
static inline pid_t sys_getpid(void) { return getpid(); }
static inline pid_t sys_gettid(void) { return (pid_t)syscall(__NR_gettid); }
static inline int sys_tgkill(pid_t g, pid_t t, int s) { return (int)syscall(__NR_tgkill,g,t,s); }
static inline int sys_prctl(int o, ...) {
    va_list a; va_start(a,o); unsigned long a2=va_arg(a,unsigned long),a3=va_arg(a,unsigned long),a4=va_arg(a,unsigned long),a5=va_arg(a,unsigned long); va_end(a); return prctl(o,a2,a3,a4,a5);
}
static inline long sys_ptrace(int r, ...) {
    va_list a; va_start(a,r); pid_t p=va_arg(a,pid_t); void *ad=va_arg(a,void*); void *d=va_arg(a,void*); va_end(a); return ptrace(r,p,ad,d);
}
static inline ssize_t sys_readlink(const char *p, char *b, size_t s) { return readlink(p,b,s); }
static inline int sys_sigaltstack(const stack_t *s, stack_t *o) { return sigaltstack(s,o); }
static inline int sys_sigemptyset(sigset_t *s) { return sigemptyset(s); }
static inline int sys_sigfillset(sigset_t *s) { return sigfillset(s); }
static inline int sys_rt_sigaction(int sig, const struct kernel_sigaction *act, struct kernel_sigaction *old, size_t ss) {
    struct sigaction sa,osa; int r;
    if(act){memset(&sa,0,sizeof(sa));sa.sa_handler=act->sa_handler_;sa.sa_flags=(int)act->sa_flags;sa.sa_restorer=act->sa_restorer;memcpy(&sa.sa_mask,&act->sa_mask,ss<sizeof(sigset_t)?ss:sizeof(sigset_t));}
    r=sigaction(sig,act?&sa:NULL,old?&osa:NULL);
    if(old&&r==0){memset(old,0,sizeof(*old));old->sa_handler_=osa.sa_handler;old->sa_flags=osa.sa_flags;old->sa_restorer=osa.sa_restorer;memcpy(&old->sa_mask,&osa.sa_mask,ss);}
    return r;
}
static inline int sys_getdents(int fd, struct kernel_dirent *d, unsigned int c) { return (int)syscall(__NR_getdents64,fd,d,c); }
static inline int sys_stat(const char *p, struct stat *b) { return stat(p,b); }
static inline int sys_fstat(int fd, struct stat *b) { return fstat(fd,b); }
extern int clone(int (*fn)(void*), void *st, int fl, void *ar, ...);
static inline int sys_clone(int (*fn)(void*), void *st, int fl, void *ar, ...) {
    va_list a; va_start(a,ar); pid_t *p=va_arg(a,pid_t*); void *t=va_arg(a,void*); pid_t *c=va_arg(a,pid_t*); va_end(a); return clone(fn,st,fl,ar,p,t,c);
}
#ifdef __cplusplus
}
#endif
#endif
'''

# stab.h stub content
STAB_H = r'''/* stab.h - stab debugging format constants (minimal) */
#ifndef __GNU_STAB__
#define __GNU_STAB__
#define N_GSYM 0x20
#define N_FUN 0x24
#define N_STSYM 0x26
#define N_LCSYM 0x28
#define N_OPT 0x3c
#define N_RSYM 0x40
#define N_SLINE 0x44
#define N_SO 0x64
#define N_LSYM 0x80
#define N_BINCL 0x82
#define N_SOL 0x84
#define N_PSYM 0xa0
#define N_EINCL 0xa2
#define N_LBRAC 0xc0
#define N_RBRAC 0xe0
#define N_UNDF 0x00
#define N_TYPE 0x0e
#define N_SECT 0x04
#define N_STAB 0x1d
#endif
'''


class BreakpadConan(ConanFile):
    name = "breakpad"
    version = "v2023.06.01"
    description = "Google Breakpad - a set of client and server components for crash reporting"
    license = "BSD-3-Clause"
    homepage = "https://github.com/google/breakpad"
    url = "https://github.com/google/breakpad"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: BUILD_SHARED_LIBS=OFF — breakpad always builds static .a libs
        # (no -static linker flag: system lacks libz.a for dump_syms tool)
        # Fix system header sign-compare warning (CMSG_NXTHDR)
        tc.extra_cxxflags.append("-Wno-error=sign-compare")
        tc.generate()

    def build(self):
        src = self.source_folder

        # 1. Create lss stub (linux_syscall_support.h not in release tarball)
        lss_dir = os.path.join(src, "src", "third_party", "lss")
        os.makedirs(lss_dir, exist_ok=True)
        save(self, os.path.join(lss_dir, "linux_syscall_support.h"), LSS_STUB)

        # 2. Create stab.h stub (not in HarmonyOS sysroot)
        save(self, os.path.join(src, "src", "stab.h"), STAB_H)

        # 3. Fix config.guess: add HarmonyOS detection + exit
        cg_path = os.path.join(src, "autotools", "config.guess")
        if os.path.exists(cg_path):
            cg = open(cg_path).read()
            if "HarmonyOS" not in cg:
                # Add HarmonyOS case before NetBSD case
                harmony_case = '''    *:HarmonyOS:*:*)
	case "$UNAME_MACHINE" in
	    aarch64|arm64) MACHINE=aarch64 ;;
	    armv7*|armv8*) MACHINE=arm ;;
	    x86_64|amd64)  MACHINE=x86_64 ;;
	    i?86)         MACHINE=i686 ;;
	    *)            MACHINE="$UNAME_MACHINE" ;;
	esac
	echo "${MACHINE}-unknown-linux-ohos"; exit
	;;
'''
                cg = cg.replace(
                    '    *:NetBSD:*:*)',
                    harmony_case + '    *:NetBSD:*:*)'
                )
                open(cg_path, 'w').write(cg)

        # 4. Fix config.sub: add linux-ohos to allowed kernel-OS combos
        cs_path = os.path.join(src, "autotools", "config.sub")
        if os.path.exists(cs_path):
            cs = open(cs_path).read()
            if "linux-ohos" not in cs:
                # Add ohos-linux mapping
                cs = cs.replace(
                    'linux-*)',
                    'ohos-linux)\n\t\t\tbasic_os=linux-ohos\n\t\t\t;;\n\tlinux-*)'
                )
                # Add linux-ohos to allowed kernel-OS combinations
                cs = cs.replace(
                    'linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib*',
                    'linux-gnu* | linux-dietlibc* | linux-android* | linux-ohos* | linux-newlib*'
                )
                # Add ohos* to OS list
                cs = cs.replace(
                    'gnu* | android* |',
                    'gnu* | android* | ohos* |'
                )
                open(cs_path, 'w').write(cs)

        # 5. Fix umask 077 issue: HMDFS filesystem permission problem
        # The umask 077 creates directories with drwx--S--- which
        # prevents file creation on HarmonyOS HMDFS.
        configure_path = os.path.join(src, "configure")
        if os.path.exists(configure_path):
            conf = open(configure_path).read()
            conf = conf.replace('(umask 077 && mktemp', '(mktemp')
            conf = conf.replace('(umask 077 && mkdir', '(mkdir')
            open(configure_path, 'w').write(conf)

        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["breakpad", "breakpad_client"]
        # Headers are installed under include/breakpad/ and use internal
        # relative includes like "google_breakpad/common/..." so both
        # include/ and include/breakpad/ must be in the search path
        self.cpp_info.includedirs = ["include", "include/breakpad"]
