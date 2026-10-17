"""Headless MathGL 8.0.3 core for OpenHarmony PC."""

import hashlib
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy, get


class MathGLConan(ConanFile):
    name = "mathgl"
    version = "8.0.3-ds.2"
    description = "MathGL scientific plotting core with PNG and zlib support"
    license = "GPL-3.0-only"
    homepage = "https://mathgl.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def requirements(self):
        # libpng's published recipe also requires this exact zlib version.
        self.requires("zlib/1.3.2")
        self.requires("libpng/1.6.58.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("MATHGL_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration(
                    "MATHGL_SOURCE_ARCHIVE must be a regular file"
                )
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)
        # Debian's +ds orig tar omits src/s_hull, while its matching Debian
        # source tar carries the original GPL-3 implementation. Reproduce
        # Debian's pre-configure restoration with hash-bound exported files.
        overlay = self.conan_data["s_hull_overlay"][self.version]
        source_dir = Path(self.export_sources_folder, "patches", "s_hull")
        target_dir = Path(self.source_folder, "src", "s_hull")
        target_dir.mkdir(parents=True, exist_ok=True)
        for name, expected in overlay["files"].items():
            path = source_dir / name
            if not path.is_file():
                raise ConanInvalidConfiguration("missing Debian s_hull source: " + name)
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                raise ConanInvalidConfiguration("Debian s_hull checksum mismatch: " + name)
            copy(self, name, src=str(source_dir), dst=str(target_dir), keep_path=False)

    def generate(self):
        tc = CMakeToolchain(self)
        # Disable optional GUI/SWIG integrations. Keep MathGL's native
        # mgl_example test driver available; the Debian-restored s_hull
        # implementation makes the resulting archive GPL-3 regardless.
        # The source still defines both shared and static targets;
        # build and package only the static archive.
        tc.cache_variables.update(
            {
                "enable-lgpl": "OFF",
                "enable-zlib": "ON",
                "enable-png": "ON",
                "enable-openmp": "OFF",
                "enable-opengl": "OFF",
                "enable-pthread": "OFF",
                "enable-pthr-widget": "OFF",
                "enable-mpi": "OFF",
                "enable-freetype": "OFF",
                "enable-all": "OFF",
                "enable-all-widgets": "OFF",
                "enable-all-swig": "OFF",
                "enable-all-docs": "OFF",
                "enable-doc-html": "OFF",
                "enable-doc-info": "OFF",
                "enable-doc-pdf-en": "OFF",
                "enable-doc-pdf-ru": "OFF",
                "enable-doc-site": "OFF",
                "enable-mgltex": "OFF",
                "BUILD_SHARED_LIBS": "OFF",
            }
        )
        zlib = Path(self.dependencies["zlib"].package_folder)
        png = Path(self.dependencies["libpng"].package_folder)
        zlib_library = zlib / "lib" / "libz.a"
        png_candidates = [png / "lib" / "libpng16.so", png / "lib" / "libpng.so"]
        png_library = next((item for item in png_candidates if item.is_file()), None)
        if not zlib_library.is_file() or png_library is None:
            raise ConanInvalidConfiguration("zlib/libpng OHOS libraries not found")
        # Upstream uses include(FindZLIB/FindPNG), i.e. MODULE lookup. Bind
        # the exact Conan package files rather than relying on host paths.
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = str(zlib / "include")
        tc.cache_variables["ZLIB_LIBRARY"] = str(zlib_library)
        tc.cache_variables["PNG_PNG_INCLUDE_DIR"] = str(png / "include")
        tc.cache_variables["PNG_LIBRARY"] = str(png_library)
        tc.generate()
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="mgl-static", build_tool_args=["-j1"])
        cmake.build(target="mgl_example", build_tool_args=["-j1"])
        examples = Path(self.build_folder, "examples")
        executable = examples / "mgl_example"
        if not executable.is_file():
            raise ConanInvalidConfiguration("upstream mgl_example test driver missing")
        self.run('"%s" --mini --srnd' % executable, cwd=str(examples), env="conanrun")
        # samples.cpp declares 150 entries, of which full_test.cpp intentionally
        # skips the icon entry. Verify every rendered native sample, not just
        # the executable's zero exit code.
        pngs = list(examples.glob("*-sm.png"))
        if len(pngs) != 149:
            raise ConanInvalidConfiguration(
                "upstream sample render count is %d, expected 149" % len(pngs)
            )
        signature = bytes((137, 80, 78, 71, 13, 10, 26, 10))
        for path in pngs:
            with path.open("rb") as stream:
                if stream.read(8) != signature:
                    raise ConanInvalidConfiguration("invalid upstream PNG: " + path.name)
        self.run('"%s" --test --mini' % executable, cwd=str(examples), env="conanrun")
        test_png = examples / "test.png"
        if not test_png.is_file():
            raise ConanInvalidConfiguration("upstream --test PNG missing")
        with test_png.open("rb") as stream:
            if stream.read(8) != signature:
                raise ConanInvalidConfiguration("upstream --test PNG is invalid")
        self.output.info("MATHGL_UPSTREAM_PASS 150/150")

    def package(self):
        libraries = list(Path(self.build_folder).rglob("libmgl.a"))
        if len(libraries) != 1:
            raise ConanInvalidConfiguration(
                "expected exactly one libmgl.a, found %d" % len(libraries)
            )
        copy(
            self,
            "libmgl.a",
            src=str(libraries[0].parent),
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        generated = Path(self.build_folder, "include", "mgl2")
        for name in ("config.h", "dllexport.h"):
            if not (generated / name).is_file():
                raise ConanInvalidConfiguration("generated MathGL header missing: " + name)
            copy(
                self,
                name,
                src=str(generated),
                dst=os.path.join(self.package_folder, "include", "mgl2"),
                keep_path=False,
            )
        for name in ("COPYING", "COPYING_LGPL"):
            copy(
                self,
                name,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
                keep_path=False,
            )
        copy(
            self,
            "debian-copyright",
            src=os.path.join(self.export_sources_folder, "patches"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["mgl"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.defines = ["MGL_STATIC_DEFINE"]
        self.cpp_info.set_property("cmake_file_name", "mathgl")
        self.cpp_info.set_property("cmake_target_name", "mathgl::mathgl")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
