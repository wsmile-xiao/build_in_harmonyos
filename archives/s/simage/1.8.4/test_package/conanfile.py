#!/usr/bin/env python3
"""test_package for simage 1.8.4 — consumers built via direct cmake + ohos.toolchain."""
import glob
import json
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        from conan.tools.cmake import cmake_layout
        cmake_layout(self)

    def _ohos_toolchain(self):
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut)
        if ndk:
            candidates.append(os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake"))
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME，或在 profile [conf] 配 "
            "tools.cmake.cmaketoolchain:user_toolchain=[<sdk>/ohos/native/build/cmake/ohos.toolchain.cmake]"
        )

    def build(self):
        toolchain = self._ohos_toolchain()
        defs = " ".join([
            '-DCMAKE_TOOLCHAIN_FILE="%s"' % toolchain,
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
            '-DCMAKE_PREFIX_PATH="%s"' % self.generators_folder,
            '-Dsimage_DIR="%s"' % self.generators_folder,
            "-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=BOTH",
            "-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=BOTH",
            "-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH",
            '-DCMAKE_FIND_ROOT_PATH="%s"' % self.generators_folder,
        ])
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake -B "%s" -S "%s" %s' % (bdir, self.source_folder, defs))
        self.run('cmake --build "%s"' % bdir)

    def test(self):
        bin_path = os.path.join(self.build_folder, "build-ohos", "test_simage")
        # Run consumer binary but always emit HMBS evidence afterwards,
        # even when binary returns non-zero (Conan would otherwise throw before emit).
        bin_ok = True
        try:
            self.run('"%s"' % bin_path)
        except ConanException:
            bin_ok = False

        # Re-emit upstream ctest result carried in the package (per-round guarantee for HMBS rule4)
        pkg_folder = self.dependencies["simage"].package_folder
        summary_path = os.path.join(pkg_folder, "res", "upstream_test_summary.json")
        if not os.path.isfile(summary_path):
            raise ConanException("missing upstream test summary in package: " + summary_path)
        with open(summary_path, "r", encoding="utf-8") as h:
            upstream = json.load(h)
        # Dual-channel emit so HMBS scanner finds it regardless of log capture path
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)

        if upstream.get("status") != "passed":
            raise ConanException("upstream test summary status is not passed: " + json.dumps(upstream, ensure_ascii=False))
        if not bin_ok:
            raise ConanException("test_simage binary failed (see HMBS_TEST_PACKAGE_RESULT above)")
