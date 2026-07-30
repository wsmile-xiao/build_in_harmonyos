#!/usr/bin/env python3
"""Conan recipe for MultiMarkdown 6.6.0."""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class MultimarkdownConan(ConanFile):
    name = "multimarkdown"
    version = "6.6.0"
    description = "Lightweight markup processor to produce HTML, LaTeX, and more"
    license = "MIT"
    homepage = "https://github.com/fletcher/MultiMarkdown-6"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def configure(self):
        cc = os.environ.get("CC", "clang")
        cxx = os.environ.get("CXX", "clang++")
        self.conf_info.define("tools.build:compiler_executables", {"c": cc, "cpp": cxx})

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generator = "Unix Makefiles"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["SHAREDBUILD"] = "ON"
        # Enable TEST so CuTest run_tests target is built (1 CuTest + 11 ADD_MMD_TEST = 12 ctest).
        # Patch 0001 fixes upstream add_definitions(-DTEST) leak to target_compile_definitions
        # so -DTEST is scoped to run_tests only and does not break multimarkdown CLI link.
        tc.cache_variables["TEST"] = "ON"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            # E092: CMake does not recognize OHOS, force aarch64 explicitly
            # to match the repository's existing OHOS recipes convention
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

        tc_file = Path(self.generators_folder) / "conan_toolchain.cmake"
        if tc_file.exists():
            content = tc_file.read_text(encoding="utf-8")
            content = content.replace("/data/service/hnp/bin/clang++", "clang++")
            content = content.replace("/data/service/hnp/bin/clang", "clang")
            tc_file.write_text(content, encoding="utf-8")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        from conan.tools.build import can_run
        if can_run(self):
            # Fix shebang in source tree: MarkdownTest.pl has #!/usr/bin/perl
            # but build env has perl at /data/service/hnp/bin/perl
            mmd_test = os.path.join(self.source_folder, "tests", "MarkdownTest.pl")
            if os.path.isfile(mmd_test):
                with open(mmd_test, "r") as f:
                    content = f.read()
                if "#!/usr/bin/perl" in content:
                    content = content.replace("#!/usr/bin/perl", "#!/usr/bin/env perl", 1)
                    with open(mmd_test, "w") as f:
                        f.write(content)
            self.run("ctest --output-on-failure --parallel 1", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["MultiMarkdown"]
        self.cpp_info.includedirs = ["include/libMultiMarkdown"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
