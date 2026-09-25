import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm, rmdir


class CsfmlConan(ConanFile):
    name = "csfml"
    version = "3.0.0"
    description = "Official C bindings for SFML, delivering the System and Network modules on OpenHarmony PC"
    license = "Zlib"
    homepage = "https://www.sfml-dev.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    _disabled_modules = ("Window", "Graphics", "Audio")
    _bundled = ("sfml", "catch2")

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    @property
    def _sfml_src(self):
        return os.path.join(self.source_folder, "bundled", "sfml-src")

    @property
    def _catch2_src(self):
        return os.path.join(self.source_folder, "bundled", "catch2-src")

    @property
    def _sfml_prefix(self):
        return os.path.join(self.build_folder, "bundled-sfml")

    def _extract(self, spec, destination):
        get(self, filename=spec["archive"], destination=destination, url=spec["url"],
            sha256=spec["sha256"], strip_root=True)

    def _fetch_sources(self):
        # conan create can skip source() when the recipe source folder is already
        # cached, which would leave an empty tree behind (build() then fails with
        # "no CMakeLists.txt"), so every archive is verified before building.
        if not os.path.isfile(os.path.join(self.source_folder, "CMakeLists.txt")):
            self._extract(self.conan_data["sources"], self.source_folder)
        for name in self._bundled:
            destination = os.path.join(self.source_folder, "bundled", "%s-src" % name)
            if not os.path.isfile(os.path.join(destination, "CMakeLists.txt")):
                self._extract(self.conan_data["bundled_sources"][name], destination)

    def source(self):
        self._fetch_sources()

    def _build_bundled_sfml(self):
        build_dir = os.path.join(self.build_folder, "bundled-sfml-build")
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        defs = [
            "-DCMAKE_TOOLCHAIN_FILE=%s" % shlex.quote(toolchain),
            # Keeps SFML_DIR (computed in generate(), before this install exists) deterministic.
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
            "-DSFML_BUILD_WINDOW=OFF",
            "-DSFML_BUILD_GRAPHICS=OFF",
            "-DSFML_BUILD_AUDIO=OFF",
            "-DSFML_BUILD_NETWORK=ON",
            "-DSFML_BUILD_EXAMPLES=OFF",
            "-DSFML_BUILD_DOC=OFF",
            "-DSFML_BUILD_TEST_SUITE=OFF",
        ]
        self.run("cmake -B %s -S %s %s" % (shlex.quote(build_dir), shlex.quote(self._sfml_src),
                                           " ".join(defs)), env="conanbuild")
        self.run("cmake --build %s --parallel 4" % shlex.quote(build_dir), env="conanbuild")
        self.run("cmake --install %s --prefix %s" % (shlex.quote(build_dir),
                                                     shlex.quote(self._sfml_prefix)), env="conanbuild")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CSFML_BUILD_WINDOW"] = False
        tc.cache_variables["CSFML_BUILD_GRAPHICS"] = False
        tc.cache_variables["CSFML_BUILD_AUDIO"] = False
        tc.cache_variables["CSFML_BUILD_NETWORK"] = True
        tc.cache_variables["CSFML_BUILD_DOC"] = False
        tc.cache_variables["CSFML_BUILD_EXAMPLES"] = False
        tc.cache_variables["CSFML_INSTALL_PKGCONFIG_FILES"] = False
        tc.cache_variables["CSFML_LINK_SFML_STATICALLY"] = True
        tc.cache_variables["CSFML_BUILD_TEST_SUITE"] = True
        tc.cache_variables["FETCHCONTENT_SOURCE_DIR_CATCH2"] = self._catch2_src
        tc.cache_variables["SFML_DIR"] = os.path.join(self._sfml_prefix, "lib", "cmake", "SFML")
        if str(self.settings.os) in ("Linux", "OHOS", "HarmonyOS"):
            # RUNPATH instead of RPATH so conanrun's LD_LIBRARY_PATH wins at test time.
            tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,--enable-new-dtags"
            # CMake ships no Platform/HarmonyOS module, so the SONAME flag stays
            # undefined and the shared libraries would be linked without -Wl,-soname.
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def _run_upstream_tests(self):
        # catch_discover_tests runs the test binaries through a CMake discovery
        # script before ctest lists anything, so libcsfml-*.so must be reachable
        # straight from the build tree (the OHOS loader ignores build-tree RPATH).
        libdir = os.path.join(self.build_folder, "lib")
        self.run("env LD_LIBRARY_PATH={} ctest --test-dir {} --output-on-failure".format(
            shlex.quote(libdir), shlex.quote(self.build_folder)), env="conanbuild")

    def build(self):
        self._fetch_sources()
        apply_conandata_patches(self)
        self._build_bundled_sfml()
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "4"])
        self._run_upstream_tests()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "license.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        for module in self._disabled_modules:
            rmdir(self, os.path.join(self.package_folder, "include", "CSFML", module))
            rm(self, "%s.h" % module, os.path.join(self.package_folder, "include", "CSFML"))
        for header in ("GPUPreference.h", "OpenGL.h"):
            rm(self, header, os.path.join(self.package_folder, "include", "CSFML"))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") or not self.options.shared:
            return
        import glob

        hnp_bin = "/data/service/hnp/bin"
        objcopy = os.environ.get("OHOS_OBJCOPY", os.path.join(hnp_bin, "llvm-objcopy"))
        signer = os.environ.get("OHOS_SIGN_TOOL", os.path.join(hnp_bin, "binary-sign-tool"))
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.warning("binary-sign-tool/llvm-objcopy unavailable; skipping ELF re-signing")
            return
        objects = []
        for pattern in ("lib/*.so", "lib/*.so.*", "bin/*"):
            objects.extend(glob.glob(os.path.join(self.package_folder, pattern)))
        for path in sorted(set(objects)):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            with open(path, "rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    continue
            self.run('%s --remove-section .codesign %s 2>/dev/null || true' %
                     (shlex.quote(objcopy), shlex.quote(path)))
            self.run('%s sign -inFile %s -outFile %s -selfSign 1' %
                     (shlex.quote(signer), shlex.quote(path), shlex.quote(path + ".signed")))
            if os.path.isfile(path + ".signed"):
                os.replace(path + ".signed", path)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CSFML")

        system = self.cpp_info.components["system"]
        system.libs = ["csfml-system"]
        system.set_property("cmake_target_name", "csfml-system")
        if str(self.settings.os) in ("Linux", "OHOS", "HarmonyOS"):
            system.system_libs = ["pthread"]

        network = self.cpp_info.components["network"]
        network.libs = ["csfml-network"]
        network.requires = ["system"]
        network.set_property("cmake_target_name", "csfml-network")
