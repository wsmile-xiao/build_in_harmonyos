import os
import glob
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches


class Allegro5Conan(ConanFile):
    name = "allegro5"
    version = "5.2.11.3"
    description = "Allegro 5 — A cross-platform game programming library"
    license = "BSD-3-Clause"
    url = "https://github.com/liballeg/allegro5"
    homepage = "https://liballeg.org/"
    topics = ("game", "multimedia", "graphics", "audio")
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    package_type = "library"
    exports_sources = "patches/**"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            strip_root=True,
        )
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)

        # Match Conan shared option to allegro5 SHARED option
        tc.variables["SHARED"] = self.options.shared

        # ---- platform drivers (all disabled for headless) ----
        tc.variables["WANT_X11"] = False
        tc.variables["WANT_X11_XF86VIDMODE"] = False
        tc.variables["WANT_X11_XINERAMA"] = False
        tc.variables["WANT_X11_XRANDR"] = False
        tc.variables["WANT_X11_XSCREENSAVER"] = False
        tc.variables["WANT_D3D"] = False
        tc.variables["WANT_D3D9EX"] = False
        tc.variables["WANT_OPENGL"] = False
        tc.variables["WANT_SHADERS_GL"] = False
        tc.variables["WANT_SHADERS_D3D"] = False

        # ---- audio backends (all disabled) ----
        tc.variables["WANT_AUDIO"] = False
        tc.variables["WANT_ALSA"] = False
        tc.variables["WANT_OSS"] = False
        tc.variables["WANT_PULSEAUDIO"] = False
        tc.variables["WANT_JACK"] = False
        tc.variables["WANT_OPENAL"] = False
        tc.variables["WANT_OPENSL"] = False
        tc.variables["WANT_DSOUND"] = False

        # ---- platform-specific features (disabled) ----
        tc.variables["WANT_NATIVE_DIALOG"] = False
        tc.variables["WANT_VIDEO"] = False
        tc.variables["WANT_PHYSFS"] = False

        # ---- docs / examples / tests (disabled) ----
        tc.variables["WANT_DOCS"] = False
        tc.variables["WANT_DOCS_HTML"] = False
        tc.variables["WANT_DOCS_MAN"] = False
        tc.variables["WANT_EXAMPLES"] = False
        tc.variables["WANT_DEMO"] = False
        tc.variables["WANT_TESTS"] = False

        # ---- addons ----
        tc.variables["WANT_FONT"] = True
        tc.variables["WANT_IMAGE"] = True
        tc.variables["WANT_IMAGE_JPG"] = False
        tc.variables["WANT_IMAGE_PNG"] = True
        tc.variables["WANT_IMAGE_WEBP"] = False
        tc.variables["WANT_IMAGE_FREEIMAGE"] = False
        tc.variables["WANT_TTF"] = True
        tc.variables["WANT_COLOR"] = True
        tc.variables["WANT_MEMFILE"] = True
        tc.variables["WANT_PRIMITIVES"] = True

        # ---- build type ----
        tc.variables["WANT_MONOLITH"] = False
        tc.variables["WANT_STATIC_RUNTIME"] = False
        tc.variables["WANT_RELEASE_LOGGING"] = False

        # ---- OHOS: musl libc specific fixes ----
        if self.settings.os == "OHOS":
            tc.variables["UNIX"] = "TRUE"
            # Fix RPATH so addon libs can find liballegro.so at runtime.
            # musl ld resolves NEEDED entries containing "/" as relative
            # paths and does NOT fall back to LD_LIBRARY_PATH.
            tc.variables["CMAKE_SKIP_BUILD_RPATH"] = False
            tc.variables["CMAKE_SKIP_RPATH"] = False
            tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = False
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
            tc.variables["CMAKE_INSTALL_RPATH"] = "\$ORIGIN"

        tc.generate()

    def build(self):
        if self.settings.os == "OHOS":
            # Some CI workers lack LD_LIBRARY_PATH for lld's libxml2 dependency.
            # lld has RUNPATH=$ORIGIN/../lib but musl's ld may not resolve it.
            # Search for the llvm lib dir relative to the compiler.
            cc = os.environ.get("CC", "/data/service/hnp/bin/clang")
            cc_dir = os.path.dirname(os.path.realpath(cc) if os.path.islink(cc) else cc)
            llvm_candidates = [
                os.path.join(cc_dir, "..", "ohos-sdk.org", "*", "ohos", "native", "llvm", "lib"),
                os.path.join(cc_dir, "..", "lib"),
            ]
            for pattern in llvm_candidates:
                matches = glob.glob(pattern)
                if matches:
                    llvm_lib = os.path.realpath(matches[0])
                    ld_path = os.environ.get("LD_LIBRARY_PATH", "")
                    os.environ["LD_LIBRARY_PATH"] = (
                        f"{llvm_lib}:{ld_path}" if ld_path else llvm_lib
                    )
                    self.output.info(f"allegro5: LD_LIBRARY_PATH += {llvm_lib}")
                    break
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self, "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # allegro5 appends "-static" suffix for static builds
        suffix = "-static" if not self.options.shared else ""

        self.cpp_info.set_property("cmake_file_name", "allegro5")
        # cmake_target_name set per-component below; root-level would duplicate

        self.cpp_info.components["_allegro5_core"].libs = [f"allegro{suffix}"]
        self.cpp_info.components["_allegro5_core"].set_property("cmake_target_name", "allegro5::allegro")
        self.cpp_info.components["_allegro5_core"].set_property("pkg_config_name", "allegro-5")

        self.cpp_info.components["allegro_color"].libs = [f"allegro_color{suffix}"]
        self.cpp_info.components["allegro_color"].requires = ["_allegro5_core"]

        self.cpp_info.components["allegro_memfile"].libs = [f"allegro_memfile{suffix}"]
        self.cpp_info.components["allegro_memfile"].requires = ["_allegro5_core"]

        self.cpp_info.components["allegro_primitives"].libs = [f"allegro_primitives{suffix}"]
        self.cpp_info.components["allegro_primitives"].requires = ["_allegro5_core"]

        self.cpp_info.components["allegro_font"].libs = [f"allegro_font{suffix}"]
        self.cpp_info.components["allegro_font"].requires = ["_allegro5_core"]

        self.cpp_info.components["allegro_image"].libs = [f"allegro_image{suffix}"]
        self.cpp_info.components["allegro_image"].requires = ["_allegro5_core"]

        if self.settings.os == "OHOS":
            self.cpp_info.components["_allegro5_core"].system_libs = ["m"]
        else:
            self.cpp_info.components["_allegro5_core"].system_libs = ["m", "pthread", "dl"]
