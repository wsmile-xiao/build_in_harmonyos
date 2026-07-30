#!/usr/bin/env python3
"""Conan recipe for perl-netaddr-ip 4.079-r14 (Perl XS module).

Build system: Perl Makefile.PL (ExtUtils::MakeMaker)
CPAN module: NetAddr::IP
Contains XS code: Lite/Util/Util.xs → Util.so

Key adaptation for HarmonyOS:
  - The Lite/Util/configure.gcc script fails because config.status
    cannot create temp files (HarmonyOS /tmp is read-only).
  - Fix: manually create config.h from detection results, create
    localperl.h, and force XS mode with --xs flag.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlNetAddrIPConan(ConanFile):
    name = "perl-netaddr-ip"
    version = "4.079-r14"
    description = "Managing IPv4 and IPv6 addresses (NetAddr::IP Perl XS module)"
    license = "GPL-2.0-only or Artistic-1.0"
    homepage = "https://metacpan.org/dist/NetAddr-IP"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # HarmonyOS: set CPATH and LIBRARY_PATH for clang to find system headers
        # The conan build environment doesn't inherit the shell's CPATH, so we set it here.
        # sys/types.h and other POSIX headers are in musl/sysroot include paths.
        # Paths are discovered dynamically to avoid hardcoding username/SDK version (R33).
        home = os.path.expanduser("~")

        # Discover OHOS SDK sysroot path (version number changes between SDK updates)
        sysroot = self.conf.get("tools.build:sysroot", default=None)
        if not sysroot:
            sdk_dirs = glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot"
            )
            if sdk_dirs:
                sysroot = sdk_dirs[0]

        cpath_parts = [os.path.join(home, "usr", "local", "include")]
        if sysroot:
            cpath_parts.append(os.path.join(sysroot, "usr", "include"))
        os.environ["CPATH"] = ":".join(cpath_parts)

        os.environ["LIBRARY_PATH"] = os.path.join(home, "usr", "local", "lib")
        # Use build folder for TMPDIR (HarmonyOS /tmp is read-only, E002)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["PERL_CANARY_STABILITY_NOPROMPT"] = "1"

        build_dir = self.source_folder
        lite_util_dir = os.path.join(build_dir, "Lite", "Util")

        # Step 1: Manually create config.h for Lite/Util
        # The configure script fails on HarmonyOS because config.status
        # cannot create temp files in /tmp (read-only).
        config_h_content = """\
/* config.h - manually created for HarmonyOS */

#define HAVE_ARPA_INET_H 1
#define HAVE_GETHOSTBYNAME 1
#define HAVE_INET_ADDR 1
#define HAVE_INET_ATON 1
#define HAVE_INET_PTON 1
#define HAVE_INTTYPES_H 1
/* #undef HAVE_LIBNSL */
#define HAVE_MEMORY_H 1
#define HAVE_NETDB_H 1
#define HAVE_NETINET_IN_H 1
#define HAVE_STDINT_H 1
#define HAVE_STDLIB_H 1
#define HAVE_STRINGS_H 1
#define HAVE_STRING_H 1
#define HAVE_SYS_SOCKET_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_UNISTD_H 1
/* #undef LIBS */
#define PACKAGE_BUGREPORT ""
#define PACKAGE_NAME "NetAddr-IP-Util"
#define PACKAGE_STRING "NetAddr-IP-Util 1.53"
#define PACKAGE_TARNAME "netaddr-ip-util"
#define PACKAGE_VERSION "1.53"
#define SIZEOF_UINT16_T 2
#define SIZEOF_UINT32_T 4
#define SIZEOF_UINT8_T 1
#define SIZEOF_U_INT16_T 2
#define SIZEOF_U_INT32_T 4
#define SIZEOF_U_INT8_T 1
#define STDC_HEADERS 1
/* #undef WORDS_BIGENDIAN */
"""
        config_h_path = os.path.join(lite_util_dir, "config.h")
        with open(config_h_path, "w") as f:
            f.write(config_h_content)

        # Step 2: Create localperl.h (normally created by Makefile.PL when XS is enabled)
        localperl_h_path = os.path.join(lite_util_dir, "localperl.h")
        with open(localperl_h_path, "w") as f:
            f.write("/*\tWritten by Makefile.PL\n *\n *\tDo not modify this file, modify Makefile.PL instead\n *\n */\n")

        # Step 3: Run Lite/Util/Makefile.PL with --xs to force XS mode
        self.run("perl Makefile.PL --xs", cwd=lite_util_dir)

        # Step 4: Build Lite/Util XS module separately (ensures Util.so is generated)
        self.run("make", cwd=lite_util_dir)

        # Step 5: Run main Makefile.PL with INSTALL_BASE=/usr/local
        self.run("perl Makefile.PL INSTALL_BASE=/usr/local", cwd=build_dir)

        # Step 6: Build main module (recurses into Lite/Util)
        self.run("make -j1", cwd=build_dir)

    def package(self):
        build_dir = self.source_folder
        # Install to package folder using DESTDIR
        self.run(f'make install DESTDIR="{self.package_folder}"', cwd=build_dir)

        # Move Perl module files from usr/local/lib/perl5/ to lib/ for standard conan layout
        src_perl_lib = os.path.join(self.package_folder, "usr", "local", "lib", "perl5")
        dst_lib = os.path.join(self.package_folder, "lib")
        if os.path.isdir(src_perl_lib):
            # Copy all files from perl5 to lib/
            for item in os.listdir(src_perl_lib):
                src_item = os.path.join(src_perl_lib, item)
                dst_item = os.path.join(dst_lib, item)
                if os.path.isdir(src_item):
                    shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(dst_item), exist_ok=True)
                    shutil.copy2(src_item, dst_item)
            # Clean up the usr/ directory
            shutil.rmtree(os.path.join(self.package_folder, "usr"), ignore_errors=True)

        # Also copy .so to top-level lib/ for G4 product integrity check
        copy(self, "*.so", src=os.path.join(build_dir, "blib", "arch"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        # Perl XS module - the .so is the main artifact
        self.cpp_info.libs = ["Util"]
        # Set libdirs to the Perl module directory
        perl_arch_dir = os.path.join(self.package_folder, "lib", "aarch64-linux")
        if os.path.isdir(perl_arch_dir):
            self.cpp_info.libdirs = [perl_arch_dir]
        else:
            self.cpp_info.libdirs = ["lib"]
        # Set PERL5LIB for consumers
        if os.path.isdir(perl_arch_dir):
            self.runenv_info.append_path("PERL5LIB", perl_arch_dir)
            self.buildenv_info.append_path("PERL5LIB", perl_arch_dir)
