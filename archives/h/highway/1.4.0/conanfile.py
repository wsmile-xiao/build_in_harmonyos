"""Highway with contrib and the maintained complete standalone upstream suite."""
import io
import json
import os
import re
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import copy, get
from ohos_sign import sign_elf


class HighwayConan(ConanFile):
    name = "highway"
    version = "1.4.0"
    description = "Portable SIMD library with runtime dispatch and vector algorithms"
    license = "Apache-2.0", "BSD-3-Clause"
    homepage = "https://github.com/google/highway"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports = "ohos_sign.py"

    def config_options(self):
        if self.settings.os == "Windows": del self.options.fPIC

    def layout(self):
        # The release contains a Bazel BUILD file. On a case-insensitive
        # source filesystem, CMake's default build/ directory collides with
        # it before generate() can create build/Release/generators.
        cmake_layout(self, build_folder="cmake-build")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local = os.environ.get("HIGHWAY_SOURCE_ARCHIVE")
        if local:
            archive = Path(local).resolve(strict=True)
            if not archive.is_file(): raise ConanException("source override must be a regular archive")
            source.update(url=archive.as_uri(), filename=archive.name)
        get(self, **source, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["HWY_ENABLE_TESTS"] = True
        tc.variables["BUILD_TESTING"] = True
        tc.variables["HWY_ENABLE_CONTRIB"] = True
        # This is upstream's maintained assertion/discovery implementation,
        # not a replacement consumer or a switch disabling the test suite.
        tc.variables["HWY_TEST_STANDALONE"] = True
        tc.variables["CMAKE_GTEST_DISCOVER_TESTS_DISCOVERY_MODE"] = "PRE_TEST"
        if str(self.settings.os) == "OHOS":
            for lang in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{lang}_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = True
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        runtime = Environment()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            runtime.prepend_path("LD_LIBRARY_PATH", self.build_folder)
        # hwy_list_targets runs as an upstream post-build command, so the
        # build-tree provider is required before the CTest discovery phase.
        with runtime.vars(self).apply():
            cmake.build()
        if str(self.settings.os) == "OHOS":
            for folder in (Path(self.build_folder), Path(self.build_folder, "tests"), Path(self.build_folder, "examples")):
                if folder.is_dir():
                    for p in sorted(folder.iterdir()):
                        if p.is_file() and not p.is_symlink() and p.read_bytes()[:4] == b"\x7fELF": sign_elf(p)
        if can_run(self):
            discovery = io.StringIO()
            with runtime.vars(self).apply():
                self.run('ctest --test-dir "{}" --show-only=json-v1'.format(self.build_folder), stdout=discovery, env="conanrun")
            tests = json.loads(discovery.getvalue())["tests"]
            names = [t["name"] for t in tests]
            if not names or len(set(names)) != len(names): raise ConanException("empty/duplicate upstream discovery")
            for t in tests:
                if any(p["name"] == "DISABLED" and p["value"] for p in t.get("properties", [])):
                    raise ConanException("a discovered upstream case is disabled")
            self.output.info("UPSTREAM_DISCOVERY_JSON=" + discovery.getvalue())
            output = io.StringIO()
            try:
                with runtime.vars(self).apply():
                    self.run('ctest --test-dir "{}" --output-on-failure --no-tests=error --timeout 180 -j2'.format(self.build_folder), stdout=output, env="conanrun")
            finally:
                self.output.info(output.getvalue())
            text = output.getvalue()
            if f"100% tests passed, 0 tests failed out of {len(names)}" not in text or re.search(r"Not Run|Skipped|\*\*\*Disabled", text, re.I):
                raise ConanException("upstream suite did not complete every discovered case")
            self.output.info(f"UPSTREAM_{len(names)}_OF_{len(names)}_PASS")

    def package(self):
        CMake(self).install()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            for p in Path(self.package_folder, "lib").glob("*.so*"):
                if p.is_file() and not p.is_symlink(): sign_elf(p)
        for name in ("LICENSE", "LICENSE-BSD3"):
            copy(self, name, self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "hwy")
        for key, lib, target, pkg in (("core", "hwy", "hwy::hwy", "libhwy"),
                                      ("contrib", "hwy_contrib", "hwy::hwy_contrib", "libhwy-contrib"),
                                      ("test", "hwy_test", "hwy::hwy_test", "libhwy-test")):
            component = self.cpp_info.components[key]
            component.libs = [lib]
            component.defines = ["HWY_SHARED_DEFINE" if self.options.shared else "HWY_STATIC_DEFINE"]
            component.set_property("cmake_target_name", target)
            component.set_property("pkg_config_name", pkg)
            if key != "core": component.requires = ["core"]
            if key == "test": component.defines.append("HWY_TEST_STANDALONE=1")
