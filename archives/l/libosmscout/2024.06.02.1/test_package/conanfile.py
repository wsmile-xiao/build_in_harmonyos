#!/usr/bin/env python3
"""test_package for libosmscout — end-to-end consumer verification.

The single consumer binary ``test_libosmscout`` walks the complete public
pipeline of the packaged libraries:

1. core geometry / number codec assertions (component ``OSMScout::OSMScout``)
2. GPX XML parsing through libxml2 (component ``OSMScout::GPX``)
3. OSM XML import into a real map database (component ``OSMScout::Import``)
4. database open plus client-side directory validation
   (components ``OSMScout::OSMScout`` + ``OSMScout::Client``)
5. MapService tile lookup and MapPainterSVG rendering of the imported data
   (components ``OSMScout::Map`` + ``OSMScout::MapSVG``)

OHOS note
---------
Conan installs shared dependency libraries as ``libxml2.so`` ->
``libxml2.so.16`` -> ``libxml2.so.16.1.3`` symlink chains.  The OHOS storage
loader refuses to follow such symlinks (it reports ``Error loading shared
library libxml2.so.16`` with an empty errno, while the very same file copied
as a regular file loads fine), so the consumer binary cannot start straight
out of the Conan package folder.  :meth:`generate` therefore materialises the
dependency shared objects as real files into ``<build>/realdep_libs`` and
prepends that directory to ``LD_LIBRARY_PATH`` for the run scope.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class TestLibosmscoutConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        dep = self.dependencies[self.tested_reference_str]
        styles = os.path.join(dep.package_folder, "share", "osmscout", "stylesheets")
        tc.variables["OSMSCOUT_TEST_STYLESHEETS"] = styles
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

        # Materialise dependency shared objects: symlinked libraries cannot be
        # loaded by the OHOS storage loader, see the module docstring.
        real_dir = os.path.join(self.build_folder, "realdep_libs")
        os.makedirs(real_dir, exist_ok=True)
        copied = 0
        for requirement in self.dependencies.host.values():
            if not requirement.package_folder:
                continue
            for libdir in requirement.cpp_info.libdirs:
                folder = os.path.join(requirement.package_folder, libdir)
                if not os.path.isdir(folder):
                    continue
                for entry in sorted(os.listdir(folder)):
                    if ".so" not in entry:
                        continue
                    destination = os.path.join(real_dir, entry)
                    if os.path.exists(destination):
                        continue
                    # copy2 follows symlinks, so the real ELF content lands here
                    shutil.copy2(os.path.join(folder, entry), destination)
                    copied += 1
        self.output.info("materialised %d dependency shared objects into %s"
                         % (copied, real_dir))

        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", real_dir)
        env.vars(self, scope="run").save_script("conanrealdep_run")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        # ctest entry point (add_test in CMakeLists.txt)
        cmake.test(env="conanrun")
        # direct execution of the consumer binary so that its assertions end up
        # verbatim in the CI log (L0d requires a literal self.run call)
        self.run(os.path.join(self.build_folder, "test_libosmscout"),
                 env="conanrun")
