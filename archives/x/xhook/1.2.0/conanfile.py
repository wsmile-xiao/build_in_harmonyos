#!/usr/bin/env python3
"""Conan recipe for xhook 1.2.0 (iQIYI PLT/GOT hook library).

xhook is an Android-native PLT (procedure linkage table) hook library for
ELF executables and shared libraries.  Upstream builds with ndk-build
(Android.mk); this recipe compiles the same source list with the OHOS
clang cross toolchain driven by Conan (CMake is NOT provided upstream, so
the recipe drives the compiler directly and stages artifacts itself).

HarmonyOS adaptation (patch 0001):
- android liblog -> HiLog: __android_log_print() is bridged to
  OH_LOG_Print() from <hilog/log.h> (libhilog_ndk.z.so).  HiLog's
  LogLevel enum matches android_LogPriority numerically (3..7), so the
  priority filtering logic is preserved verbatim.
- xh_jni.c (JNI bridge for the Android Java wrapper) is compiled out on
  OHOS; native consumers use the plain C API in xhook.h.
- bionic-only DT_ANDROID_REL{,A,SZ,ASZ} dynamic tags get local defines
  (musl elf.h lacks them); PAGE_MASK is derived from
  sysconf(_SC_PAGESIZE); <signal.h> is included explicitly for struct
  sigaction (bionic's pthread.h pulls it in indirectly).

No external conan dependencies: the library only needs libc, pthread and
the system HiLog NDK library (declared via system_libs so consumers get
-lhilog_ndk.z automatically).

Knowledge refs: E033 family (musl feature macros), platform-difference
handling per knowledge/operations/ohos-adaptation-patterns.md.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class XhookConan(ConanFile):
    name = "xhook"
    version = "1.2.0"
    description = "PLT hook library for Android ELF executables and shared libraries (iQIYI)"
    license = "MIT"
    homepage = "https://github.com/iqiyi/xhook"
    url = "https://github.com/iqiyi/xhook"
    topics = ("hook", "plt", "got", "elf", "instrumentation")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("xhook supports Linux and OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("xhook supports OHOS armv8 only")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise Exception("unsupported os: %s" % self.settings.os)

        # R33: compiler comes from Conan conf (profile), not shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        if os.path.isfile(cc):
            cc_bin = cc
        else:
            cc_bin = shutil.which(os.path.basename(cc)) or cc

        src = os.path.join(self.source_folder, "libxhook", "jni")
        build = self.build_folder
        objs = []
        sources = [
            "xhook.c", "xh_core.c", "xh_elf.c", "xh_jni.c",
            "xh_log.c", "xh_util.c", "xh_version.c",
        ]
        # -D_GNU_SOURCE: musl needs it for the full struct sigaction under
        # -std=c11 (bionic exposes it unconditionally).
        cflags = ["-Wall", "-Wextra", "-Werror", "-fvisibility=hidden",
                  "-std=c11", "-D_GNU_SOURCE", "-fPIC"]
        for s in sources:
            obj = os.path.join(build, s.replace(".c", ".o"))
            self.run('{} {} -I{} -c {} -o "{}"'.format(
                cc_bin, " ".join(cflags), src, os.path.join(src, s), obj))
            objs.append(obj)

        shared = self.options.shared
        lib = os.path.join(build, "libxhook.so" if shared else "libxhook.a")
        if shared:
            self.run('{} -shared -o "{}" {} -lpthread -lhilog_ndk.z'.format(
                cc_bin, lib, " ".join('"%s"' % o for o in objs)))
        else:
            ar = shutil.which("llvm-ar") or "ar"
            self.run('{} rcs "{}" {}'.format(ar, lib, " ".join('"%s"' % o for o in objs)))

    def package(self):
        src = os.path.join(self.source_folder, "libxhook", "jni")
        copy(self, "xhook.h", src, os.path.join(self.package_folder, "include"))
        copy(self, "*.so", self.build_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "*.a", self.build_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["xhook"]
        self.cpp_info.system_libs = ["pthread", "hilog_ndk.z"]
        self.cpp_info.set_property("cmake_file_name", "xhook")
        self.cpp_info.set_property("cmake_target_name", "xhook::xhook")
