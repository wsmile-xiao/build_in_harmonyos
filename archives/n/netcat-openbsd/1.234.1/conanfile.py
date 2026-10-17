#!/usr/bin/env python3
"""Conan recipe for netcat-openbsd 1.234.1.

netcat-openbsd is the OpenBSD rewrite of nc (netcat), providing arbitrary
TCP/UDP connections and listens. This recipe builds the `nc` executable
using a Makefile-based build system with Debian portability patches and
OHOS-specific compatibility functions (strtonum, readpassphrase,
explicit_bzero, b64_ntop) provided inline in ohos-compat.c.

The recipe is self-contained — no external libbsd dependency required.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, save
from conan.tools.layout import basic_layout


OHOS_COMPAT_H = """\
/*
 * ohos-compat.h - BSD compatibility functions for OHOS
 *
 * Provides strtonum, readpassphrase, explicit_bzero, b64_ntop
 * which are not available in OHOS libc.
 */
#ifndef OHOS_COMPAT_H
#define OHOS_COMPAT_H

#include <stddef.h>
#include <sys/types.h>

/* strtonum (from BSD) */
long long strtonum(const char *numstr, long long minval, long long maxval, const char **errstr);

/* readpassphrase (from BSD) */
#define RPP_ECHO_OFF    0x00
#define RPP_ECHO_ON     0x01
#define RPP_STDIN       0x02
#define RPP_REQUIRE_TTY 0x04
char *readpassphrase(const char *prompt, char *buf, size_t bufsiz, int flags);

/* explicit_bzero (from BSD) */
void explicit_bzero(void *b, size_t len);

/* b64_ntop (from resolver library) */
int b64_ntop(const unsigned char *src, size_t srclength, char *target, size_t targsize);

#endif /* OHOS_COMPAT_H */
"""

OHOS_COMPAT_C = """\
/*
 * ohos-compat.c - BSD compatibility function implementations for OHOS
 *
 * Implements strtonum, readpassphrase, explicit_bzero, b64_ntop
 * which are not available in OHOS libc.
 */
#include "ohos-compat.h"

#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <ctype.h>

/* ---- strtonum (from OpenBSD) ---- */
long long
strtonum(const char *numstr, long long minval, long long maxval,
    const char **errstr)
{
    long long val;
    char *ep;

    if (errstr != NULL)
        *errstr = NULL;

    if (numstr == NULL || *numstr == '\\0') {
        if (errstr != NULL)
            *errstr = "invalid";
        return 0;
    }

    errno = 0;
    val = strtoll(numstr, &ep, 10);
    if (errno == EINVAL || numstr == ep || *ep != '\\0') {
        if (errstr != NULL)
            *errstr = "invalid";
        return 0;
    }
    if (errno == ERANGE || val < minval || val > maxval) {
        if (errstr != NULL)
            *errstr = "out of range";
        return 0;
    }

    return val;
}

/* ---- explicit_bzero (from OpenBSD) ---- */
void
explicit_bzero(void *b, size_t len)
{
    volatile unsigned char *p = (volatile unsigned char *)b;
    while (len--)
        *p++ = 0;
}

/* ---- readpassphrase (from OpenBSD) ---- */
char *
readpassphrase(const char *prompt, char *buf, size_t bufsiz, int flags)
{
    int save_errno, save_flags, status;
    int fd;
    struct termios term, oterm;
    char *p, *end;

    if (bufsiz == 0) {
        errno = EINVAL;
        return NULL;
    }

    if (flags & RPP_STDIN)
        fd = 0;
    else {
        fd = open("/dev/tty", O_RDWR);
        if (fd < 0) {
            fd = 0;
            if (dprintf(fd, "%s", prompt) < 0)
                return NULL;
        } else {
            if (write(fd, prompt, strlen(prompt)) < 0) {
                close(fd);
                return NULL;
            }
        }
    }

    save_errno = errno;

    if (!(flags & RPP_ECHO_ON)) {
        if (tcgetattr(fd, &oterm) == 0) {
            memcpy(&term, &oterm, sizeof(term));
            term.c_lflag &= ~(ECHO | ECHONL);
            tcsetattr(fd, TCSANOW, &term);
            save_flags = fcntl(fd, F_GETFL, 0);
            if (save_flags != -1)
                fcntl(fd, F_SETFL, save_flags | O_NONBLOCK);
        }
    }

    p = buf;
    end = buf + bufsiz - 1;
    while (p < end) {
        status = read(fd, p, 1);
        if (status == -1) {
            if (errno == EINTR)
                continue;
            break;
        } else if (status == 0) {
            break;
        }
        if (*p == '\\n' || *p == '\\r')
            break;
        p++;
    }
    *p = '\\0';

    if (!(flags & RPP_ECHO_ON)) {
        if (tcgetattr(fd, &term) == 0) {
            tcsetattr(fd, TCSANOW, &oterm);
            if (save_flags != -1)
                fcntl(fd, F_SETFL, save_flags);
        }
    }

    if (!(flags & RPP_STDIN))
        close(fd);

    errno = save_errno;
    return buf;
}

/* ---- b64_ntop (from resolver library) ---- */
static const char b64_table[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

int
b64_ntop(const unsigned char *src, size_t srclength, char *target, size_t targsize)
{
    size_t i, j;
    size_t output_len;

    output_len = ((srclength + 2) / 3) * 4;
    if (targsize < output_len + 1)
        return -1;

    for (i = 0, j = 0; i + 2 < srclength; i += 3, j += 4) {
        target[j] = b64_table[src[i] >> 2];
        target[j+1] = b64_table[((src[i] & 0x03) << 4) | (src[i+1] >> 4)];
        target[j+2] = b64_table[((src[i+1] & 0x0f) << 2) | (src[i+2] >> 6)];
        target[j+3] = b64_table[src[i+2] & 0x3f];
    }

    if (i < srclength) {
        target[j++] = b64_table[src[i] >> 2];
        if (i + 1 < srclength) {
            target[j++] = b64_table[((src[i] & 0x03) << 4) | (src[i+1] >> 4)];
            target[j++] = b64_table[(src[i+1] & 0x0f) << 2];
        } else {
            target[j++] = b64_table[(src[i] & 0x03) << 4];
            target[j++] = '=';
        }
        target[j++] = '=';
    }

    target[j] = '\\0';
    return (int)j;
}
"""


class NetcatOpenbsdConan(ConanFile):
    name = "netcat-openbsd"
    version = "1.234.1"
    description = "OpenBSD rewrite of nc (netcat) - arbitrary TCP/UDP connections and listens"
    license = "BSD-3-Clause"
    homepage = "https://salsa.debian.org/debian/netcat-openbsd"
    url = "https://snapshot.debian.org/archive/debian/20251023T202923Z/pool/main/n/netcat-openbsd/netcat-openbsd_1.234.orig.tar.gz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # Write OHOS compatibility files (provides strtonum, readpassphrase,
        # explicit_bzero, b64_ntop - functions not in OHOS libc)
        save(self, os.path.join(self.source_folder, "ohos-compat.h"), OHOS_COMPAT_H)
        save(self, os.path.join(self.source_folder, "ohos-compat.c"), OHOS_COMPAT_C)
        self.run("make -j1 CC=clang", cwd=self.source_folder)

    def package(self):
        copy(self, "nc", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "nc.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
