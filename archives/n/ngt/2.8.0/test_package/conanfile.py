import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class NgtTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: same CMAKE_SYSTEM_NAME workaround as the main recipe so that the
        # consumer CMake behaves like a Linux build on the OHOS device.
        if str(self.settings.os) in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        # R34: each test binary really links the packaged NGT library and
        # exercises its C++ API (build an index, search, assert exact self
        # match / deletions / property round-trips / error paths). The suite
        # covers the distance/object/graph type matrices plus persistence,
        # CRUD, batch query, property and error scenarios (see MANIFEST.yml
        # for the per-binary assertion counts). env="conanrun" injects the
        # ngt/openblas/libomp lib dirs into LD_LIBRARY_PATH.
        binaries = [
            "test_ngt",        # baseline ANNG/L2/float (11 checks)
            "test_distance",   # L1/L2/Angle/Cosine (32)
            "test_objecttype", # Float/Uint8 + L2/Hamming (24)
            "test_graph",      # ANNG/ONNG/IANNG (24)
            "test_persist",    # save/reopen rw+ro (21)
            "test_crud",       # append/remove (15)
            "test_batch",      # multi-query sessions (24)
            "test_property",   # get/set property round-trip (11)
            "test_errors",     # exception paths (5)
        ]
        for name in binaries:
            test_bin = os.path.join(self.cpp.build.bindirs[0], name)
            self.run(test_bin, env="conanrun")
