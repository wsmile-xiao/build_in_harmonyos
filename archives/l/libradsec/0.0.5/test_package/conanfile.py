#!/usr/bin/env python3
"""Conan test_package — libradsec 0.0.5 consumer test.

R34: test.c calls the libradsec public API (context/connection/peer/packet/AVP)
to verify the package links and behaves correctly as a consumer.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibradsecTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libradsec.so has DT_NEEDED libevent_core.so. The test binary links
        # against libradsec, so at runtime the loader must resolve libevent.
        # Require libevent DIRECTLY here so its package_folder is populated in
        # self.dependencies (a transitive/sibling-only access leaves
        # package_folder as None → os.path.join(..., None) TypeError), and its
        # lib dir lands on LD_LIBRARY_PATH (set explicitly in test() below).
        self.requires("libevent/2.1.12")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Ship test.conf (realm configuration) next to the test binary. The
        # test loads it via rs_context_read_config(); without a realm the
        # connection setup path NULL-derefs conn->realm (see test.c). Copied
        # into the build folder so it is reachable as the cwd-relative path
        # when test() runs ./test_libradsec test.conf.
        import shutil
        src = os.path.join(self.source_folder, "test.conf")
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(self.build_folder, "test.conf"))

    def test(self):
        # R34: run the test binary that calls libradsec API (prints HMBS marker)
        # On OHOS, VirtualRunEnv doesn't reliably set LD_LIBRARY_PATH (shared lib),
        # so set it explicitly to the libradsec package's lib dir (libevent pattern).
        # libradsec.so also has DT_NEEDED libevent_core.so, so libevent's lib dir
        # must be on LD_LIBRARY_PATH too for the runtime to resolve it.
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libradsec")
        lib_dirs = [
            os.path.join(self.dependencies["libradsec"].package_folder, "lib"),
        ]
        # libradsec.so has DT_NEEDED libevent_core.so; add libevent's lib dir so
        # the runtime resolves it (libevent is required directly by this test
        # package, so its package_folder is populated). Use cpp_info.libdirs as
        # the authoritative path so the fix does not depend on package_folder
        # being non-None for the sibling relationship.
        if "libevent" in self.dependencies:
            ev = self.dependencies["libevent"]
            dirs = [d for d in (ev.cpp_info.libdirs or []) if d]
            if dirs:
                lib_dirs.extend(dirs)
            elif ev.package_folder:
                lib_dirs.append(os.path.join(ev.package_folder, "lib"))
        self.run("LD_LIBRARY_PATH={}:$LD_LIBRARY_PATH {} test.conf".format(":".join(lib_dirs), test_bin),
                 env="conanrun")
