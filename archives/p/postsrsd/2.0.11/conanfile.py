#!/usr/bin/env python3
"""Conan recipe — postsrsd 2.0.11 (CMake application).

PostSRSd is the Sender Rewriting Scheme (SRS) daemon for Postfix.

Dependency handling (W0 2026-09-26 verified):
  * libConfuse 3.3 is a hard, unconditional build dependency and is NOT
    published to the artifact repository (conan install --requires=confuse/3.3
    -> "Unable to find confuse/3.3 in remotes"). postsrsd's CMakeLists uses
    FetchContent + ExternalProject (add_autotools_dependency) to build it
    statically, so this recipe fetches confuse-3.3.tar.gz as a second source,
    points FETCHCONTENT_SOURCE_DIR_CONFUSE at it, and applies the two OHOS
    fixes (config.sub ohos triplet + configure tmpdir umask) in build().
  * Check 0.15.2 (test framework) is triggered by BUILD_TESTING and also
    fetched via FetchContent; same localize via FETCHCONTENT_SOURCE_DIR_CHECK.
  * WITH_MILTER / WITH_SQLITE / WITH_REDIS are optional and stay OFF.

OHOS adaptation points (patches/0001..0004):
  1) patches/0001 cmake/utils.cmake add_autotools_dependency(): define
     AUTOTOOLS_BUILD_HOST_ARGS (CMAKE_SYSTEM_NAME=OHOS or host HarmonyOS) and
     pass --build/--host so the vendored autotools dependency's configure does
     not run config.guess (which cannot identify uname -s == HarmonyOS);
     disable the PATCH_COMMAND autoreconf step (confuse 3.3 tarball ships
     generated configure, rerunning autoreconf would regenerate it and drop
     our configure tmpdir fix and lose reproducibility).
  2) patches/0002 src/endpoint.c: unix endpoint supports "unix:abstract:name"
     (abstract AF_UNIX socket, knowledge E461) since OHOS rejects
     filesystem-path bind with EPERM; abstract bind uses
     offsetof(sun_path)+1+namelen address length.
  3) patches/0003 tests/blackbox/socketmap.py: blackbox test uses
     unix:abstract:name and probes connection instead of watching a socket
     file (abstract socket has no filesystem entry).
  4) patches/0004 tests/unit/test_netstring.c: tmpfile() is hardcoded to /tmp
     on musl, which is read-only on HarmonyOS, so tmpfile() returns NULL and
     the netstring_io_test segfaults. Create the temp file under $TMPDIR
     instead.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get, replace_in_file)


class PostsrsdConan(ConanFile):
    name = "postsrsd"
    version = "2.0.11"
    description = "Postfix Sender Rewriting Scheme (SRS) daemon"
    license = "GPL-3.0-only"
    homepage = "https://github.com/roehling/postsrsd"
    url = "https://github.com/roehling/postsrsd"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "with_upstream_tests": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # no external Conan dependencies; confuse/check are vendored below

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(self, **self.conan_data["confuse"],
            destination=os.path.join(self.source_folder, "third_party", "confuse"),
            strip_root=True)
        get(self, **self.conan_data["check"],
            destination=os.path.join(self.source_folder, "third_party", "check"),
            strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # systemd unit / sysusers.d are OHOS-irrelevant and would be installed
        # to /etc/systemd without privileges; keep those optional installs OFF.
        tc.variables["INSTALL_SYSTEMD_SERVICE"] = "OFF"
        # secrets generation writes into sysconfdir at install time with
        # absolute paths and is not usable in a packaged OHOS app either.
        tc.variables["GENERATE_SRS_SECRET"] = "OFF"
        # Use the locally fetched tarballs instead of CMake FetchContent hitting
        # GitHub at configure time (CI/offline reproducibility).
        tc.variables["FETCHCONTENT_SOURCE_DIR_CONFUSE"] = os.path.join(
            self.source_folder, "third_party", "confuse")
        tc.variables["FETCHCONTENT_SOURCE_DIR_CHECK"] = os.path.join(
            self.source_folder, "third_party", "check")
        tc.generate()

    def _build_env(self):
        # The OHOS SDK linker depends on its bundled libxml2. The Conan build
        # environment can otherwise prepend package runtime directories and
        # make lld load an ABI-incompatible libxml2 before CMake's try-link.
        # The SDK path is derived from the environment variable first (set on
        # the CI runner) and falls back to probing the HNP SDK tree for the
        # latest installed ohos-sdk version's llvm/lib directory.
        import glob
        import re
        build_env = Environment()
        build_env.unset("LD_LIBRARY_PATH")
        sdk_llvm_lib = os.environ.get("OHOS_SDK_LLVM_LIB")
        if not sdk_llvm_lib:
            # Probe newest installed SDK version (avoids version-locked path).
            def _sdk_version(path):
                m = re.search(r"/ohos-sdk_([0-9._]+)/ohos/native/llvm/lib$", path)
                return tuple(int(x) for x in m.group(1).split(".")) if m else (0,)
            candidates = sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"),
                key=_sdk_version,
            )
            sdk_llvm_lib = candidates[-1] if candidates else ""
        if sdk_llvm_lib and os.path.isdir(sdk_llvm_lib):
            build_env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return build_env

    def build(self):
        apply_conandata_patches(self)
        confuse_src = os.path.join(self.source_folder, "third_party", "confuse")
        # NOTE (R6 justification): confuse is a FetchContent-vendored dependency
        # whose source tree is NOT part of the postsrsd main source. The Conan
        # patch mechanism (apply_conandata_patches) only applies to the main
        # source root, so OHOS portability fixes for the vendored dependency
        # are applied here with replace_in_file (same pattern as bmon 4.0,
        # which edits the vendored configure in build()). All edit points are
        # enumerated below and verified by the local build.
        #
        # confuse 3.3 config.sub (2018-02-22) does not recognize the OHOS
        # triplet; teach it aarch64-unknown-linux-ohos (mirrors bmon's
        # 0002-config-sub-ohos.patch, verified by local build).
        cfgsub = os.path.join(confuse_src, "support", "config.sub")
        if os.path.isfile(cfgsub):
            replace_in_file(
                self,
                cfgsub,
                "linux-dietlibc | linux-newlib* | \\\n  linux-musl*",
                "linux-dietlibc | linux-newlib* | linux-ohos* | \\\n  linux-musl*")
            replace_in_file(
                self,
                cfgsub,
                "| -linux-newlib* | -linux-musl* | -linux-uclibc* \\",
                "| -linux-newlib* | -linux-musl* | -linux-uclibc* | -linux-ohos* \\")
        # HMDFS: files created under `umask 077` become unwritable by the
        # config.status awk machinery -> "Permission denied: subs1.awk".
        # Relax umask 077 used for the tmpdir (verified: mkdir 077 on HMDFS
        # yields drwx--S--- which is not writable by the owner).
        configure = os.path.join(confuse_src, "configure")
        if os.path.isfile(configure):
            replace_in_file(self, configure,
                            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null` &&')
            replace_in_file(self, configure,
                            'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
                            'tmp=./conf$$-$RANDOM\n  mkdir "$tmp"')

        cmake = CMake(self)
        build_env = self._build_env()
        with build_env.vars(self).apply():
            cmake.configure()
            cmake.build()
        if self.options.get_safe("with_upstream_tests", False) and can_run(self):
            test_env = VirtualRunEnv(self).environment()
            with test_env.vars(self).apply():
                cmake.test()

    def package(self):
        cmake = CMake(self)
        build_env = self._build_env()
        with build_env.vars(self).apply():
            cmake.install()

    def package_info(self):
        # conan_toolchain.cmake maps CMAKE_INSTALL_SBINDIR -> bin,
        # so the binary lands in bin/ (verified via cmake_install.cmake).
        self.cpp_info.bindirs = ["bin"]