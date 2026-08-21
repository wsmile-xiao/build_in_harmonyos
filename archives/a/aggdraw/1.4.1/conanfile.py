"""Conan recipe for aggdraw 1.4.1, a CPython C++ drawing extension."""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AggdrawConan(ConanFile):
    name = "aggdraw"
    version = "1.4.1"
    package_type = "application"
    description = "High-quality drawing interface for PIL"
    license = "Python (MIT style)"
    homepage = "https://github.com/pytroll/aggdraw"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("python", "graphics", "drawing", "cxx-extension")

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"aggdraw is adapted for Linux/OHOS, got {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"aggdraw/1.4.1 is validated for OHOS armv8, got {self.settings.arch}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Build the extension directly. The CI Python image does not guarantee
        # setuptools, while pyproject.toml would require setuptools.build_meta.
        # Direct compilation keeps the package independent of worker site-packages.
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compiler_executables.get("cpp") or "clang++"
        import sysconfig

        py_include = sysconfig.get_path("include")
        py_platinclude = sysconfig.get_path("platinclude")
        # OHOS Python can report a stale build-time LIBDIR; libpython is next to
        # the running interpreter under sys.prefix on both device and CI.
        py_lib_dir = os.path.join(sys.prefix, "lib")
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        ext_suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
        source_files = [
            "aggdraw.cxx",
            "agg2/src/agg_arc.cpp",
            "agg2/src/agg_bezier_arc.cpp",
            "agg2/src/agg_curves.cpp",
            "agg2/src/agg_rounded_rect.cpp",
            "agg2/src/agg_path_storage.cpp",
            "agg2/src/agg_rasterizer_scanline_aa.cpp",
            "agg2/src/agg_trans_affine.cpp",
            "agg2/src/agg_vcgen_contour.cpp",
            "agg2/src/agg_vcgen_stroke.cpp",
        ]
        objects_dir = os.path.join(self.build_folder, "objects")
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(objects_dir, exist_ok=True)
        os.makedirs(staging, exist_ok=True)
        include_flags = f'-I"{self.source_folder}/agg2/include" -I"{py_include}"'
        if py_platinclude and py_platinclude != py_include:
            include_flags += f' -I"{py_platinclude}"'
        object_files = []
        for source in source_files:
            source_path = os.path.join(self.source_folder, source)
            object_path = os.path.join(objects_dir, os.path.basename(source) + ".o")
            self.run(
                f'"{cxx}" -fPIC -O2 -DVERSION=1.4.1 {include_flags} '
                f'-c "{source_path}" -o "{object_path}"'
            )
            object_files.append(object_path)
        linker = "-fuse-ld=/data/service/hnp/bin/ld " if self.settings.os == "OHOS" else ""
        extension = os.path.join(staging, "aggdraw" + ext_suffix)
        objects = " ".join(f'"{obj}"' for obj in object_files)
        self.run(
            f'"{cxx}" -shared {linker}{objects} '
            f'-L"{py_lib_dir}" -lpython{py_version} -o "{extension}"'
        )
        if self.settings.os == "OHOS":
            # Sign the final ELF while it is still in the build staging area.
            # Signing after Conan copies it into the package cache produces a
            # tool-successful signature that OHOS Python rejects from dlopen.
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            if not os.path.isfile(sign_tool) or not os.path.isfile(objcopy):
                raise ConanInvalidConfiguration(
                    "OHOS signing tools are required for the aggdraw extension"
                )
            self.run(
                f'"{objcopy}" --remove-section .codesign "{extension}" '
                f'2>/dev/null || true'
            )
            self.run(
                f'"{sign_tool}" sign -inFile "{extension}" '
                f'-outFile "{extension}" -selfSign 1'
            )
            if not os.path.isfile(extension):
                raise ConanInvalidConfiguration(
                    f"binary-sign-tool did not produce {extension}"
                )
            os.chmod(extension, 0o755)

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        copy(self, "*", src=staging, dst=self.package_folder, keep_path=True)
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # Keep the signed build artifact intact when copying it into the
        # package. The signature is deliberately created in build().
        if self.settings.os == "OHOS":
            import glob as _glob
            extension_modules = _glob.glob(
                os.path.join(self.package_folder, "aggdraw*.so")
            )
            if not extension_modules:
                raise ConanInvalidConfiguration(
                    "aggdraw extension module was not packaged"
                )
            for so_file in extension_modules:
                os.chmod(so_file, 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.append_path("PYTHONPATH", self.package_folder)
