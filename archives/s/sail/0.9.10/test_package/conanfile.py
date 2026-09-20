#!/usr/bin/env python3
"""test_package for sail 0.9.10 — consumes the built SAIL library.

build(): compiles the consumer executable linked against the packaged sail,
         driving cmake directly (system/HMBS cmake + OHOS NDK toolchain) to
         avoid the conancenter cmake tool_requires that has no OHOS source
         entry (KeyError: 'OHOS').
test():  runs the consumer (which emits HMBS_TEST_PACKAGE_RESULT after real
         API assertions) and then re-emits the upstream ctest summary as
         HMBS_UPSTREAM_TEST_RESULT (the hmbs evidence gate only scans the
         test_package stage stdout, and the cached package may skip build()).
"""
import glob
import json
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout


class SailTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ohos_toolchain(self):
        ut = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list
        )
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut)
        if ndk:
            candidates.append(os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake"))
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake")
        )
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME，或在 profile [conf] 配 "
            "tools.cmake.cmaketoolchain:user_toolchain=[<sdk>/ohos/native/build/cmake/ohos.toolchain.cmake]"
        )

    def build(self):
        # Direct cmake invocation (mirrors the sail main recipe and in-tree
        # libtiff): avoids the conancenter cmake tool_requires KeyError:'OHOS'.
        toolchain = self._ohos_toolchain()
        defs = " ".join([
            '-DCMAKE_TOOLCHAIN_FILE="%s"' % toolchain,
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
            # find_package(Sail CONFIG) must find the CMakeDeps-generated
            # config files in the generators folder.
            '-DCMAKE_PREFIX_PATH="%s"' % self.generators_folder,
            # OHOS NDK ohos.toolchain.cmake sets CMAKE_FIND_ROOT_PATH to the
            # sysroot and its find root modes DEFAULT to ONLY. Even though we
            # override MODE_*_PACKAGE=BOTH below, the NDK toolchain may still
            # filter the CMAKE_PREFIX_PATH search, so `find_package(Sail CONFIG)`
            # failed ("Could not find a package configuration file provided by
            # 'Sail'") because the generators-folder SailConfig.cmake (outside
            # the sysroot root path) was never reached. Point <Name>_DIR
            # directly at the generators folder: CONFIG-mode find_package
            # checks <PackageName>_DIR first and uses it literally, completely
            # bypassing CMAKE_FIND_ROOT_PATH / MODE_* root filtering. CMakeDeps
            # writes SailConfig.cmake at the root of the generators folder
            # (root cmake_file_name="Sail"), so Sail_DIR resolves it directly.
            '-DSail_DIR="%s"' % self.generators_folder,
            # OHOS NDK toolchain defaults find root modes to ONLY; force BOTH
            # so the CMakeDeps config files in the generators folder are found.
            "-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=BOTH",
            "-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=BOTH",
            "-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH",
            # Belt-and-suspenders: SailConfig.cmake (and every codec dep config
            # it find_dependency()s) lives in the generators folder, which is
            # OUTSIDE the OHOS toolchain's CMAKE_FIND_ROOT_PATH (the sysroot).
            # If the toolchain forces MODE_PACKAGE=ONLY after our BOTH override,
            # the generators folder is filtered out and find_package still
            # fails. Appending the generators folder to CMAKE_FIND_ROOT_PATH
            # makes it reachable under BOTH root modes, so the top-level
            # find_package(Sail) AND the internal find_dependency() calls for
            # GIF/PNG/JPEG/TIFF/transitives all resolve.
            '-DCMAKE_FIND_ROOT_PATH="%s"' % self.generators_folder,
        ])
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake -B "%s" -S "%s" %s' % (bdir, self.source_folder, defs))
        self.run('cmake --build "%s"' % bdir)

    def test(self):
        # Run the consumer: it decodes a hardcoded BMP via sail_load_from_memory
        # and emits HMBS_TEST_PACKAGE_RESULT on stdout after real assertions.
        # The static libsail-codecs pulls the shared codec deps (libtiff.so,
        # libpng.so, ...) as DT_NEEDED, so prepend every dep lib dir to
        # LD_LIBRARY_PATH, else the loader fails their relocations
        # (Error relocating .../libtiff.so: WebPPictureImportRGBA: symbol not
        # found), the exact runtime failure seen in the main build's ctest.
        libdirs = []
        for dep in self.dependencies.values():
            pkg = dep.package_folder
            if not pkg:
                continue
            for d in (dep.cpp_info.libdirs or []):
                if not d:
                    continue
                absp = d if os.path.isabs(d) else os.path.join(pkg, d)
                if os.path.isdir(absp) and absp not in libdirs:
                    libdirs.append(absp)
            if not dep.cpp_info.libdirs:
                cand = os.path.join(pkg, "lib")
                if os.path.isdir(cand) and cand not in libdirs:
                    libdirs.append(cand)
        old = os.environ.get("LD_LIBRARY_PATH", "")
        combined = ":".join(libdirs + ([old] if old else []))
        test_bin = os.path.join(self.build_folder, "build-ohos", "test_sail")
        self.run('export LD_LIBRARY_PATH="%s"; "%s"' % (combined, test_bin))

        # Re-emit the upstream ctest result carried in the package.
        package_folder = self.dependencies["sail"].package_folder
        summary_path = os.path.join(package_folder, "res", "upstream_test_summary.json")
        if not os.path.isfile(summary_path):
            raise ConanException(
                "missing upstream test summary in package: " + summary_path
            )
        with open(summary_path, "r", encoding="utf-8") as handle:
            upstream = json.load(handle)
        if upstream.get("status") != "passed":
            raise ConanException(
                "upstream test summary status is not passed: "
                + json.dumps(upstream, ensure_ascii=False)
            )
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
