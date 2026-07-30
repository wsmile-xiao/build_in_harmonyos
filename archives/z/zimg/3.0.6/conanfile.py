#!/usr/bin/env python3
"""Conan recipe for zimg 3.0.6.

The upstream release tag ships Autotools inputs but not generated configure
files, while the OHOS CI image does not provide autoreconf. Build the library
directly from src/zimg with the Conan-provided compiler instead.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import check_sha256, copy, export_conandata_patches, get, save, unzip
from conan.tools.layout import basic_layout


class ZimgConan(ConanFile):
    name = "zimg"
    version = "3.0.6"
    description = "Scaling, colorspace conversion, and dithering library"
    license = "WTFPL"
    homepage = "https://github.com/sekrit-twc/zimg"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"zimg 3.0.6 supports Linux/OHOS in this recipe, got {self.settings.os}"
            )

    def source(self):
        source = self.conan_data["sources"][0]
        staged = os.path.expanduser("~/Download/zimg-release-3.0.6.tar.gz")
        if os.path.isfile(staged):
            check_sha256(self, staged, source["sha256"])
            unzip(self, staged, strip_root=True)
        else:
            get(self, **source, strip_root=True)

    def build(self):
        src_root = os.path.join(self.source_folder, "src", "zimg")
        obj_root = os.path.join(self.build_folder, "obj")
        os.makedirs(obj_root, exist_ok=True)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = self._resolve_tool(compilers.get("cpp"), "clang++")
        ar = self._resolve_tool(compilers.get("ar"), "llvm-ar")

        build_flags, build_defines = self._build_type_flags()
        defines = list(build_defines)
        if self._is_arm():
            defines.append("-DZIMG_ARM")
        elif self._is_x86():
            defines.append("-DZIMG_X86")

        pic = []
        if self.options.get_safe("fPIC", True) or self.options.shared:
            pic.append("-fPIC")

        cxxflags = [
            "-std=c++14",
            *build_flags,
            "-fvisibility=hidden",
            "-Wall",
            "-Wextra",
            "-Wno-unused-parameter",
            "-Wno-missing-field-initializers",
            "-Isrc/zimg",
        ] + defines + pic

        objects = []
        for source in self._sources(src_root):
            rel = os.path.relpath(source, src_root)
            obj = os.path.join(obj_root, rel.replace(os.sep, "_") + ".o")
            objects.append(obj)
            cmd = [
                *self._exec_tool(cxx),
                *cxxflags,
                "-c",
                source,
                "-o",
                obj,
            ]
            self.run(" ".join(shlex.quote(part) for part in cmd), cwd=self.source_folder)

        if self.options.shared:
            lib = os.path.join(self.build_folder, "libzimg.so.2.0.0")
            cmd = [
                *self._exec_tool(cxx),
                "-shared",
                "-Wl,-soname,libzimg.so.2",
                "-o",
                lib,
                *objects,
                "-lm",
                "-pthread",
            ]
            self.run(" ".join(shlex.quote(part) for part in cmd))
        else:
            lib = os.path.join(self.build_folder, "libzimg.a")
            self.run(
                " ".join(shlex.quote(part) for part in [*self._exec_tool(ar), "rcs", lib, *objects])
            )

    def package(self):
        includedir = os.path.join(self.package_folder, "include")
        libdir = os.path.join(self.package_folder, "lib")
        pkgconfigdir = os.path.join(libdir, "pkgconfig")
        os.makedirs(includedir, exist_ok=True)
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(pkgconfigdir, exist_ok=True)

        api_dir = os.path.join(self.source_folder, "src", "zimg", "api")
        copy(self, "zimg.h", src=api_dir, dst=includedir, keep_path=False)
        copy(self, "zimg++.hpp", src=api_dir, dst=includedir, keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        if self.options.shared:
            built = os.path.join(self.build_folder, "libzimg.so.2.0.0")
            for name in ("libzimg.so.2.0.0", "libzimg.so.2", "libzimg.so"):
                shutil.copy2(built, os.path.join(libdir, name))
            self._sign_shared_libs()
        else:
            copy(self, "libzimg.a", src=self.build_folder, dst=libdir, keep_path=False)

        save(self, os.path.join(pkgconfigdir, "zimg.pc"), self._pkg_config())

    def package_info(self):
        self.cpp_info.libs = ["zimg"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "zimg")
        self.cpp_info.set_property("cmake_file_name", "zimg")
        self.cpp_info.set_property("cmake_target_name", "zimg::zimg")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    def _sources(self, src_root):
        sources = []
        for root, _, files in os.walk(src_root):
            norm = root.replace("\\", "/")
            if "/x86" in norm and not self._is_x86():
                continue
            if "/arm" in norm and not self._is_arm():
                continue
            for filename in files:
                if filename.endswith(".cpp"):
                    sources.append(os.path.join(root, filename))
        return sorted(sources)

    def _is_arm(self):
        return str(self.settings.arch) in ("armv7", "armv7hf", "armv8", "aarch64")

    def _is_x86(self):
        return str(self.settings.arch) in ("x86", "x86_64", "amd64")

    def _build_type_flags(self):
        build_type = str(self.settings.build_type)
        if build_type == "Debug":
            return ["-O0", "-g"], []
        if build_type == "RelWithDebInfo":
            return ["-O2", "-g"], ["-DNDEBUG"]
        if build_type == "MinSizeRel":
            return ["-Os"], ["-DNDEBUG"]
        return ["-O2"], ["-DNDEBUG"]

    @staticmethod
    def _tool_next_to(compiler, tool):
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        candidate = os.path.join(bindir, tool) if bindir else ""
        return candidate if candidate and os.path.isfile(candidate) else ""

    def _resolve_tool(self, configured, fallback):
        if configured and os.path.exists(configured):
            return configured
        found = shutil.which(fallback)
        if found:
            return found
        if configured:
            sibling = self._tool_next_to(configured, fallback)
            if sibling:
                return sibling
        home_candidate = os.path.join(os.path.expanduser("~"), "usr", "local", "bin", fallback)
        if os.path.exists(home_candidate):
            return home_candidate
        return fallback

    def _exec_tool(self, tool):
        if self._is_script(tool):
            return ["sh", tool]
        return [tool]

    @staticmethod
    def _is_script(path):
        if not path or not os.path.isfile(path):
            return False
        try:
            with open(path, "rb") as handle:
                return handle.read(2) == b"#!"
        except OSError:
            return False

    def _pkg_config(self):
        libs_private = "-lc++" if self.settings.os == "OHOS" else "-lstdc++"
        return f"""prefix=${{pcfiledir}}/../..
exec_prefix=${{prefix}}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: zimg
Description: Scaling, colorspace conversion, and dithering library
Version: {self.version}
Libs: -L${{libdir}} -lzimg
Libs.private: {libs_private}
Cflags: -I${{includedir}}
"""

    def _sign_shared_libs(self):
        if self.settings.os != "OHOS":
            return
        objcopy = self._resolve_tool(None, "llvm-objcopy")
        signer = self._resolve_tool(None, "binary-sign-tool")
        if not os.path.exists(objcopy) or not os.path.exists(signer):
            return
        libdir = os.path.join(self.package_folder, "lib")
        for name in ("libzimg.so.2.0.0", "libzimg.so.2", "libzimg.so"):
            path = os.path.join(libdir, name)
            if not os.path.exists(path):
                continue
            signed = path + ".signed"
            self.run(f"{objcopy} --remove-section .codesign {shlex.quote(path)}",
                     quiet=True)
            self.run(
                f"{signer} sign -inFile {shlex.quote(path)} "
                f"-outFile {shlex.quote(signed)} -selfSign 1",
                quiet=True,
            )
            os.replace(signed, path)
