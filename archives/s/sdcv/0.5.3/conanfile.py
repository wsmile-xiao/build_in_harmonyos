from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
import os

required_conan_version = ">=2.0"

class SdcvConan(ConanFile):
    name = "sdcv"
    version = "0.5.3"
    description = "sdcv - console version of the StarDict program"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Dushistov/sdcv"
    url = "https://github.com/Dushistov/sdcv/archive/refs/tags/v0.5.3.tar.gz"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # glib 2.88.3 binary is available; 2.84 binaries are currently
        # unresolvable from the registry (remote resolution bug)
        self.requires("glib/2.88.3")
        self.requires("zlib/1.3.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def _abs(self, dep, path):
        path = str(path)
        if not os.path.isabs(path):
            path = os.path.join(str(dep.package_folder or ""), path)
        return path

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)

        glib = self.dependencies["glib"]
        # glib package cpp_info does not expose the glib-2.0 include layout;
        # construct it like the abiword-plugin-* recipes do
        glib_pf = str(glib.package_folder or "")
        glib_inc = [
            os.path.join(glib_pf, "include", "glib-2.0"),
            os.path.join(glib_pf, "lib", "glib-2.0", "include"),
        ]
        glib_lib = None
        for cand in ("libglib-2.0.so", "libglib-2.0.a"):
            p = os.path.join(glib_pf, "lib", cand)
            if os.path.isfile(p):
                glib_lib = p
                break
        # sdcv's bundled FindGLIB2.cmake short-circuits when both variables
        # are preset, so no pkg-config is needed on the build machine
        intl = self.dependencies["proxy-libintl"]
        intl_inc = self._abs(intl, intl.cpp_info.includedirs[0])
        intl_pf = str(intl.package_folder or "")
        intl_lib = None
        for cand in ("libintl.a", "libintl.so"):
            p = os.path.join(intl_pf, "lib", cand)
            if os.path.isfile(p):
                intl_lib = p
                break
        tc.variables["GLIB2_INCLUDE_DIRS"] = ";".join(glib_inc + [intl_inc])
        tc.variables["GLIB2_LIBRARIES"] = ";".join(
            [p for p in (glib_lib, intl_lib) if p])

        zlib = self.dependencies["zlib"]
        zlib_inc = self._abs(zlib, zlib.cpp_info.includedirs[0])
        zlib_libdir = self._abs(zlib, zlib.cpp_info.libdirs[0])
        zlib_lib = None
        for cand in ("libz.a", "libz.so"):
            p = os.path.join(zlib_libdir, cand)
            if os.path.isfile(p):
                zlib_lib = p
                break
        # preset the built-in FindZLIB module variables
        tc.variables["ZLIB_INCLUDE_DIR"] = zlib_inc
        tc.variables["ZLIB_LIBRARY"] = zlib_lib

        # readline is not adapted/published: disable instead of relying on
        # the upstream auto-detect fallback
        tc.variables["WITH_READLINE"] = False
        # NLS needs msgfmt/xgettext (GettextTools REQUIRED upstream); the CI
        # build environment does not provide a gettext toolchain
        tc.variables["ENABLE_NLS"] = False
        # run the upstream shell test suite via ctest
        tc.variables["BUILD_TESTS"] = True

        # restore upstream non-NLS semantics: OHOS glib's gi18n.h drops the
        # ENABLE_NLS gate, so _(String) would call an undeclared gettext().
        # A shim header (no shell-hostile parens in compile flags) defines
        # gettext() as the upstream pass-through macro.
        shim = os.path.join(self.generators_folder, "gettext_shim.h")
        with open(shim, "w") as f:
            f.write("#ifndef GLM_GETTEXT_SHIM_H\n"
                    "#define GLM_GETTEXT_SHIM_H\n"
                    "#define gettext(String) (String)\n"
                    "#endif\n")
        tc.variables["CMAKE_CXX_FLAGS"] = "-include {}".format(shim)

        # runtime resolution of host shared deps when ctest executes the
        # freshly built sdcv binary
        rpaths = []
        for _, dep in self.dependencies.items():
            for d in dep.cpp_info.libdirs:
                rpaths.append(self._abs(dep, d))
        if rpaths:
            tc.variables["CMAKE_BUILD_RPATH"] = ";".join(rpaths)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # OHOS lld drops DT_RUNPATH, so the ctest loader needs an explicit
        # LD_LIBRARY_PATH covering every host dependency libdir
        libdirs = []
        for _, dep in self.dependencies.items():
            for d in dep.cpp_info.libdirs:
                p = self._abs(dep, d)
                if os.path.isdir(p) and p not in libdirs:
                    libdirs.append(p)
        # t_json alone needs jq(1), which the OHOS platform does not provide;
        # excluded per-case (documented in notes.md), the other 10 run
        self.run('LD_LIBRARY_PATH="{0}:$LD_LIBRARY_PATH" ctest -E "^t_json$" --output-on-failure'.format(
            ":".join(libdirs)), cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
