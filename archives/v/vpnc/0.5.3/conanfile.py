#!/usr/bin/env python3
"""Conan recipe for vpnc 0.5.3 — Cisco-compatible IPSec VPN client.

vpnc uses a plain Makefile (no configure script) and depends on libgcrypt.
Build produces two executables: vpnc (VPN client) and cisco-decrypt (password decoder).
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get,
    copy,
    apply_conandata_patches,
    export_conandata_patches,
    replace_in_file,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class VpncConan(ConanFile):
    name = "vpnc"
    version = "0.5.3"
    description = "Client for Cisco VPN concentrator"
    license = "GPL-2.0-or-later"
    homepage = "https://www.unix-ag.uni-kl.de/~massar/vpnc/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libgcrypt/1.12.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Add dependency include/lib paths to CFLAGS/LDFLAGS
        # so they are available even if the Makefile doesn't use CPPFLAGS
        for _, dep in self.dependencies.items():
            for incdir in dep.cpp_info.includedirs:
                tc.extra_cflags.append(
                    "-I{}".format(os.path.join(dep.package_folder, incdir))
                )
            for libdir in dep.cpp_info.libdirs:
                tc.extra_ldflags.append(
                    "-L{}".format(os.path.join(dep.package_folder, libdir))
                )
        # Add library names to LDFLAGS — the Makefile normally gets these
        # from `libgcrypt-config --libs`, but that binary is not shipped in
        # the Conan package, so we add them explicitly here.
        for _, dep in self.dependencies.items():
            for lib in dep.cpp_info.libs:
                tc.extra_ldflags.append("-l{}".format(lib))
        tc.generate()

    def build(self):
        # R32: Platform compatibility check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

        apply_conandata_patches(self)

        # --- Source patches for non-glibc Linux (OHOS) ---
        sysdep_h = os.path.join(self.source_folder, "sysdep.h")
        sysdep_c = os.path.join(self.source_folder, "sysdep.c")

        # 1. <error.h> is a glibc-only header; OHOS defines __linux__ but
        #    does not ship error.h.  Split the #if block so that glibc
        #    keeps HAVE_ERROR + the include, while non-glibc Linux defines
        #    the other HAVE_* macros (functions are available in the OHOS
        #    libc) but NOT HAVE_ERROR — vpnc has its own error() fallback
        #    in sysdep.c guarded by #ifndef HAVE_ERROR.
        replace_in_file(
            self,
            sysdep_h,
            "#if defined(__linux__) || defined(__GLIBC__)\n#include <error.h>\n\n#define HAVE_VASPRINTF 1\n#define HAVE_ASPRINTF  1\n#define HAVE_ERROR     1\n#define HAVE_GETLINE   1\n#define HAVE_UNSETENV  1\n#define HAVE_SETENV    1\n#endif",
            "#if defined(__GLIBC__)\n/* On glibc Linux, error.h exists and provides error(). */\n#include <error.h>\n#define HAVE_VASPRINTF 1\n#define HAVE_ASPRINTF  1\n#define HAVE_ERROR     1\n#define HAVE_GETLINE   1\n#define HAVE_UNSETENV  1\n#define HAVE_SETENV    1\n#endif\n\n/* On non-glibc Linux (e.g., OHOS), error.h is not available,\n   but asprintf, vasprintf, getline, setenv, unsetenv are\n   provided by the C library.  vpnc has its own error()\n   fallback in sysdep.c guarded by #ifndef HAVE_ERROR. */\n#if defined(__linux__) && !defined(__GLIBC__)\n#define HAVE_VASPRINTF 1\n#define HAVE_ASPRINTF  1\n#define HAVE_GETLINE   1\n#define HAVE_UNSETENV  1\n#define HAVE_SETENV    1\n#endif",
        )

        # 1b. OHOS does not provide getpass().  Add a forward declaration
        #     in sysdep.h so config.c and vpnc.c can call it.  The
        #     implementation is added to sysdep.c (see below).
        replace_in_file(
            self,
            sysdep_h,
            "#ifndef HAVE_UNSETENV\nextern int unsetenv(const char *name);\n#endif",
            "#ifndef HAVE_UNSETENV\nextern int unsetenv(const char *name);\n#endif\n\n/* OHOS does not provide getpass(); our own implementation is in sysdep.c */\n#if defined(__linux__) && !defined(__GLIBC__)\nchar *getpass(const char *prompt);\n#endif",
        )

        # 2. On non-glibc Linux (OHOS), both linux/if_ether.h (pulled in
        #    via linux/if_tun.h in sysdep.c) and netinet/if_ether.h
        #    (included by sysdep.h) define struct ethhdr with incompatible
        #    include guards, causing a redefinition error.
        #    Fix: define __UAPI_DEF_ETHHDR 0 in sysdep.c before including
        #    linux/if_tun.h so that linux/if_ether.h skips its struct
        #    ethhdr definition.  netinet/if_ether.h (in sysdep.h) then
        #    provides the sole definition.
        replace_in_file(
            self,
            sysdep_c,
            "#elif defined(__linux__)\n#include <linux/if_tun.h>",
            "#elif defined(__linux__)\n/* Prevent linux/if_ether.h from defining struct ethhdr;\n   netinet/if_ether.h (via sysdep.h) provides it instead. */\n#define __UAPI_DEF_ETHHDR 0\n#include <linux/if_tun.h>",
        )

        # 3. On non-glibc Linux (OHOS), <netinet/if_ether.h> may not define
        #    struct ether_addr (or the struct is incomplete), causing
        #    sizeof(struct ether_addr) to fail in the ETH_ALEN macro.
        #    Fix: define ETH_ALEN as the constant 6 on non-glibc Linux.
        replace_in_file(
            self,
            sysdep_h,
            "#define ETH_ALEN (sizeof(struct ether_addr))",
            "#if defined(__linux__) && !defined(__GLIBC__)\n"
            "#define ETH_ALEN 6\n"
            "#else\n"
            "#define ETH_ALEN (sizeof(struct ether_addr))\n"
            "#endif",
        )

        # 3b. On non-glibc Linux (OHOS), getpass() is not declared by
        #     unistd.h.  Add a forward declaration to sysdep.h so that
        #     config.c (and other files) can call it without implicit
        #     declaration errors.  The implementation is in sysdep.c (#4).
        replace_in_file(
            self,
            sysdep_h,
            "#if defined(__linux__) && !defined(__GLIBC__)\n"
            "#define ETH_ALEN 6\n"
            "#else\n"
            "#define ETH_ALEN (sizeof(struct ether_addr))\n"
            "#endif",
            "#if defined(__linux__) && !defined(__GLIBC__)\n"
            "#define ETH_ALEN 6\n"
            "#else\n"
            "#define ETH_ALEN (sizeof(struct ether_addr))\n"
            "#endif\n"
            "\n"
            "/* On non-glibc Linux (OHOS), getpass() is not provided by the\n"
            "   C library.  Declaration here so callers see the prototype;\n"
            "   implementation is in sysdep.c. */\n"
            "#if defined(__linux__) && !defined(__GLIBC__)\n"
            "char *getpass(const char *prompt);\n"
            "#endif",
        )

        # 4. OHOS does not provide getpass().  Add a simple implementation
        #    to sysdep.c that uses termios to disable echo while reading
        #    the password from /dev/tty.
        replace_in_file(
            self,
            sysdep_c,
            "	ret = putenv(newenv);\n	if (ret == -1)\n		free(newenv);\n\n	return ret;\n}\n#endif",
            "	ret = putenv(newenv);\n	if (ret == -1)\n		free(newenv);\n\n	return ret;\n}\n#endif\n\n/* Provide getpass() for platforms that lack it (e.g., OHOS). */\n#if defined(__linux__) && !defined(__GLIBC__)\n#include <termios.h>\nchar *getpass(const char *prompt)\n{\n\tstruct termios oldt, newt;\n\tstatic char buf[256];\n\tFILE *tty;\n\n\ttty = fopen(\"/dev/tty\", \"r+\");\n\tif (!tty)\n\t\ttty = stdin;\n\n\tfprintf(stderr, \"%s\", prompt);\n\n\tif (tcgetattr(fileno(tty), &oldt) == 0) {\n\t\tnewt = oldt;\n\t\tnewt.c_lflag &= ~ECHO;\n\t\ttcsetattr(fileno(tty), TCSANOW, &newt);\n\t}\n\n\tif (!fgets(buf, sizeof(buf), tty))\n\t\tbuf[0] = '\\0';\n\tbuf[strcspn(buf, \"\\n\")] = '\\0';\n\n\ttcsetattr(fileno(tty), TCSANOW, &oldt);\n\tif (tty != stdin)\n\t\tfclose(tty);\n\tfprintf(stderr, \"\\n\");\n\n\treturn buf;\n}\n#endif",
        )

        # R33: Get compiler from Conan conf
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"

        # Build vpnc and cisco-decrypt.
        # CC is passed on the command line (overrides Makefile's CC=gcc).
        # CFLAGS/LDFLAGS come from conanbuild env (via AutotoolsToolchain).
        # The Makefile uses ?= for CFLAGS/LDFLAGS so environment values
        # are honoured, and += appends Makefile-specific flags.
        # CPPFLAGS uses += so -DVERSION is appended to the env value.
        # Explicit targets "vpnc cisco-decrypt" skip the default "all"
        # target which also builds vpnc.8 (man page, needs makeman.pl)
        # and vpnc-script (not needed in the Conan package).
        self.run(
            'make -j1 CC={} BINS="vpnc cisco-decrypt" vpnc cisco-decrypt'.format(
                shlex.quote(cc)
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        # Manual install — the Makefile's install target uses the `install`
        # command which may not be available on OHOS.
        copy(self, "vpnc", src=self.source_folder,
             dst=os.path.join(self.package_folder, "sbin"))
        copy(self, "cisco-decrypt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "vpnc-disconnect", src=self.source_folder,
             dst=os.path.join(self.package_folder, "sbin"))
        copy(self, "pcf2vpnc", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "vpnc.conf", src=self.source_folder,
             dst=os.path.join(self.package_folder, "etc/vpnc"))

    def package_info(self):
        # vpnc is a standalone binary, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
