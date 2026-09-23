#!/usr/bin/env python3
"""Conan recipe for mars 1.3.0 (Tencent cross-platform infrastructure library).

Upstream (https://github.com/Tencent/mars) builds via per-platform CMake
trees that only know MSVC/ANDROID/APPLE plus scons/ndk-build variants — none
of which apply to a headless OHOS cross build.  This recipe drives the OHOS
clang toolchain directly (like a hand-rolled ndk-build) over the exact
source lists the upstream comm/log/boost CMakeLists glob for a non-MSVC,
non-Android platform, and stages headers + three static libraries:

  * libmars-comm.a   — comm (utils, network, socket, messagequeue, xlogger)
  * libmars-xlog.a   — log (appender, formater, log_buffer, log_crypt, uECC)
  * libmars-boost.a  — bundled boost 1.60 subset mars compiles itself

STN/SDT (the network stack) need a live platform bridge (callback
registration + netinfo source); on OHOS they are consumer-level and out of
scope for this package — comm + xlog is the core deliverable, matching the
platform guidance (core Comm+Xlog first).

HarmonyOS adaptation (patch 0001):
- thread.h: OHOS branch for Thread::unsafe_exit() — musl has no
  pthread_cancel(); fall back to the Android-style SIGUSR2 delivery.
- debugger_utils.c: BSD sysctl probe guarded off on OHOS (musl has no
  sys/sysctl.h); message_queue.cc only consults it in DEBUG+__APPLE__
  builds, so the stub mirrors "not traced".
- comm/ohos/platform_comm_ohos.cc (new): native OHOS implementation of the
  platform abstraction upstream provides via JNI on Android
  (comm/jni/platform_comm.cc) — getNetInfo falls back to a UDP-probe
  local_ipstack_detect() (same technique comm uses for AI_ADDRCONFIG),
  wifi/SIM/APN queries report unavailable (no cellular/Java bridge on a
  PC), ConsoleLog routes into the xlogger pipeline instead of
  __android_log_write.
- comm/ohos/xlogger_threadinfo_ohos.cc (new): pid/tid source for the log
  formatter (musl gettid() needs _GNU_SOURCE, enabled build-wide).

External dependency: zlib (log_buffer deflate compression).  No libcurl —
the optional curl-backed DNS/crypt extras are not part of the default
upstream static-lib build.

Knowledge refs: E033 family (musl feature macros), ohos-adaptation-patterns.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MarsConan(ConanFile):
    name = "mars"
    version = "1.3.0"
    description = "Tencent Mars - cross-platform infrastructure library (comm utils, xlog logging, bundled boost)"
    license = "MIT"
    homepage = "https://github.com/Tencent/mars"
    url = "https://github.com/Tencent/mars"
    topics = ("tencent", "mars", "xlog", "network", "logging", "infrastructure")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # log_buffer.cc / appender.cc: deflate-compressed log payloads.
        self.requires("zlib/1.3.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mars supports Linux and OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("mars supports OHOS armv8 only")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler comes from Conan conf (profile), not shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        cc_bin = cc if os.path.isfile(cc) else (shutil.which(os.path.basename(cc)) or cc)
        cxx_bin = cxx if os.path.isfile(cxx) else (shutil.which(os.path.basename(cxx)) or cxx)
        ar = shutil.which("llvm-ar") or "ar"

        src = os.path.join(self.source_folder, "mars")
        build = self.build_folder
        cxxstd = "gnu++14"  # upstream CMakeUtils for ANDROID/UNIX

        base_flags = ["-fno-exceptions", "-fPIC", "-D_GNU_SOURCE"]

        # include model mirrors upstream comm/CMakeLists.txt:
        #   -I<mars> -I<mars>/comm -I<mars>/log -I<repo root (tarball root)>
        inc = [
            "-I" + src,
            "-I" + os.path.join(src, "comm"),
            "-I" + os.path.join(src, "log"),
            "-I" + os.path.join(src, "log", "crypt"),
            "-I" + os.path.join(src, "log", "crypt", "micro-ecc-master"),
            "-I" + os.path.join(src, "boost"),
            "-I" + self.source_folder,  # repo root: <root>/mars/boost/... includes
        ]
        zlib_info = self.dependencies["zlib"].cpp_info.aggregated_components()
        for d in zlib_info.includedirs:
            inc.append("-I" + d)

        def compile_pair(c_files, cxx_files, tag, extra_defines):
            outdir = os.path.join(build, tag)
            os.makedirs(outdir, exist_ok=True)
            objs = []
            defs = " ".join(base_flags + extra_defines)
            # Upstream CMakeUtils does add_definitions(-DXLOGGER_TAG="mars::tag")
            # which lands on the compiler command line as a *string literal*
            # (quoted). Keep the quotes through self.run's shell by using
            # shell-safe escaping: -DXLOGGER_TAG="mars::tag"
            tagdef = '-DXLOGGER_TAG=\\"mars::%s\\"' % tag
            for s in c_files:
                obj = os.path.join(outdir, s.replace("/", "_") + ".o")
                self.run('%s %s %s %s -c "%s" -o "%s"' % (
                    cc_bin, defs, " ".join(inc), tagdef,
                    os.path.join(src, s), obj))
                objs.append(obj)
            for s in cxx_files:
                obj = os.path.join(outdir, s.replace("/", "_") + ".o")
                self.run('%s -std=%s %s %s %s -c "%s" -o "%s"' % (
                    cxx_bin, cxxstd, defs, " ".join(inc), tagdef,
                    os.path.join(src, s), obj))
                objs.append(obj)
            lib = os.path.join(build, "libmars-%s.a" % tag)
            self.run('%s rcs "%s" %s' % (ar, lib, " ".join('"%s"' % o for o in objs)))
            return lib

        # ---------------- libmars-comm.a ----------------
        # Source list mirrors upstream comm/CMakeLists.txt globs for a
        # non-MSVC, non-Android platform: top-level *.cc/*.c + assert +
        # crypt + network + socket + xlogger + corepattern + dns +
        # messagequeue + unix/socket, plus the OHOS platform layer.
        comm_c = [
            "comm/adler32.c", "comm/md5.c", "comm/time_utils.c",
            "comm/assert/__assert.c", "comm/debugger/debugger_utils.c",
            "comm/xlogger/xloggerbase.c", "comm/xlogger/loginfo_extract.c",
            "comm/crypt/pkcs7_padding.c",
            "comm/network/getgateway.c",
        ]
        comm_cxx = [
            "comm/alarm.cc", "comm/anr.cc", "comm/autobuffer.cc",
            "comm/basepacker.cc", "comm/boost_exception.cc",
            "comm/comm_frequency_limit.cc", "comm/http.cc", "comm/memdbg.cc",
            "comm/mmap_util.cc", "comm/ptrbuffer.cc", "comm/singleton.cc",
            "comm/strutil.cc", "comm/tickcount.cc", "comm/tinyxml2.cc",
            "comm/crypt/ibase64.cc",
            "comm/network/getaddrinfo_with_timeout.cc",
            "comm/network/getdnssvraddrs.cc",
            "comm/network/getifaddrs.cc",
            "comm/network/local_routetable.cc",
            "comm/network/netinfo_util.cc",
            "comm/socket/block_socket.cc", "comm/socket/complexconnect.cc",
            "comm/socket/getsocktcpinfo.cc", "comm/socket/local_ipstack.cc",
            "comm/socket/nat64_prefix_util.cc",
            "comm/socket/socket_address.cc", "comm/socket/tcpclient.cc",
            "comm/socket/tcpclient_fsm.cc", "comm/socket/tcpserver.cc",
            "comm/socket/tcpserver_fsm.cc", "comm/socket/udpclient.cc",
            "comm/socket/udpserver.cc", "comm/socket/unix_socket.cc",
            "comm/messagequeue/message_queue.cc",
            "comm/dns/dns.cc",
            "comm/unix/socket/socketbreaker.cc",
            "comm/unix/socket/socketpoll.cc",
            "comm/unix/socket/socketselect.cc",
            "comm/ohos/platform_comm_ohos.cc",
            "comm/ohos/xlogger_threadinfo_ohos.cc",
        ]
        compile_pair(comm_c, comm_cxx, "comm", [])

        # ---------------- libmars-xlog.a ----------------
        # Upstream log/CMakeLists.txt non-MSVC path: src/*.cc + crypt/*.cc +
        # crypt/micro-ecc-master/*.c (JNI glue and ../mk_template are
        # Android-only).
        xlog_c = ["log/crypt/micro-ecc-master/uECC.c"]
        xlog_cxx = [
            "log/src/appender.cc", "log/src/formater.cc",
            "log/src/log_buffer.cc", "log/crypt/log_crypt.cc",
        ]
        compile_pair(xlog_c, xlog_cxx, "xlog", [])

        # ---------------- libmars-boost.a ----------------
        # Exact list from upstream boost/CMakeLists.txt (the non-MSVC,
        # non-ANDROID branch keeps its fixed source set; coroutine/context
        # ASM pieces are ANDROID-only).
        boost_src = [
            "libs/atomic/src/lockpool.cpp",
            "libs/date_time/src/gregorian/date_generators.cpp",
            "libs/date_time/src/gregorian/gregorian_types.cpp",
            "libs/date_time/src/gregorian/greg_month.cpp",
            "libs/date_time/src/gregorian/greg_weekday.cpp",
            "libs/date_time/src/posix_time/posix_time_types.cpp",
            "libs/exception/src/clone_current_exception_non_intrusive.cpp",
            "libs/filesystem/src/codecvt_error_category.cpp",
            "libs/filesystem/src/operations.cpp",
            "libs/filesystem/src/path.cpp",
            "libs/filesystem/src/path_traits.cpp",
            "libs/filesystem/src/portability.cpp",
            "libs/filesystem/src/unique_path.cpp",
            "libs/filesystem/src/utf8_codecvt_facet.cpp",
            "libs/filesystem/src/windows_file_codecvt.cpp",
            "libs/iostreams/src/file_descriptor.cpp",
            "libs/iostreams/src/mapped_file.cpp",
            "libs/smart_ptr/src/sp_collector.cpp",
            "libs/smart_ptr/src/sp_debug_hooks.cpp",
            "libs/system/src/error_code.cpp",
            "libs/thread/src/future.cpp",
        ]
        compile_pair([], ["boost/" + s for s in boost_src], "boost", ["-DBOOST_NO_EXCEPTIONS"])

    def package(self):
        src = os.path.join(self.source_folder, "mars")

        # headers: install root = <prefix>/include/mars/... so consumers do
        # #include "mars/comm/autobuffer.h" / "appender.h"
        for header_root, dest in (
            ("comm", "mars/comm"),
            ("log", "mars/log"),
            ("boost", "mars/boost"),
        ):
            base = os.path.join(src, header_root)
            for root, _, files in os.walk(base):
                rel = os.path.relpath(root, base)
                for f in files:
                    if f.endswith((".h", ".hpp", ".inl", ".inc")):
                        d = os.path.join(self.package_folder, "include", dest, rel) if rel != "." \
                            else os.path.join(self.package_folder, "include", dest)
                        copy(self, f, root, d)

        copy(self, "libmars-comm.a", self.build_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "libmars-xlog.a", self.build_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "libmars-boost.a", self.build_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["mars-comm", "mars-xlog", "mars-boost"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.defines = ["_GNU_SOURCE"]
        # consumers include like "mars/comm/..." and "appender.h" (xlog)
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "mars")
        self.cpp_info.set_property("cmake_target_name", "mars::mars")
