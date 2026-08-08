#!/usr/bin/env python3
"""Conan recipe for chafa 1.18.2.

Chafa provides libchafa plus optional command-line tools.  The HarmonyOS
package keeps the library and disables the tools and external image loaders to
avoid pulling unrelated optional dependencies into this PR.
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class ChafaConan(ConanFile):
    name = "chafa"
    version = "1.18.2"
    description = "Image to ANSI/Unicode character art library"
    license = "LGPL-3.0-or-later"
    homepage = "https://hpjansson.org/chafa/"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
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

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"chafa is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_tmpdir()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def _configure_args(self):
        return [
            "--without-tools",
            "--without-avif",
            "--without-heif",
            "--without-jpeg",
            "--without-svg",
            "--without-tiff",
            "--without-webp",
            "--without-jxl",
            "--disable-gtk-doc",
            "--disable-man",
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
        ]

    def build(self):
        self._ensure_tmpdir()
        apply_conandata_patches(self)
        autotools = Autotools(self)
        configure_cmd = [
            "sh",
            os.path.join(self.source_folder, "configure"),
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
        ] + self._configure_args()
        self.run(" ".join(shlex.quote(arg) for arg in configure_cmd))
        autotools.make(args=["-j1"])
        if cross_building(self):
            self.output.info("cross-building: skip make check because target binaries are not runnable")
        else:
            self._extend_library_path_for_tests()
            autotools.make(target="check", args=["-j1"])

    def package(self):
        self._ensure_tmpdir()
        Autotools(self).install()
        if self.options.shared:
            self._sign_shared_libs()

    def package_info(self):
        self.cpp_info.libs = ["chafa"]
        self.cpp_info.includedirs = ["include/chafa", "lib/chafa/include", "include"]
        self.cpp_info.requires = ["glib::glib-2.0"]
        self.cpp_info.set_property("cmake_file_name", "chafa")
        self.cpp_info.set_property("cmake_target_name", "chafa::chafa")
        self.cpp_info.set_property("pkg_config_name", "chafa")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    def _ensure_tmpdir(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMPPREFIX"] = os.path.join(tmpdir, "zsh")
        self._ensure_tool_paths()

    def _ensure_tool_paths(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compiler_executables.get("c") or ""
        bindirs = []
        if cc and os.path.sep in cc:
            bindirs.append(os.path.dirname(cc))
        bindirs.extend([
            "/data/service/hnp/bin",
            "/data/service/hnp/make.org/make_4.4.1/bin",
            "/data/service/hnp/binutils.org/binutils_2.45/bin",
        ])
        path_parts = os.environ.get("PATH", "").split(os.pathsep)
        for bindir in reversed([p for p in bindirs if p and os.path.isdir(p)]):
            if bindir not in path_parts:
                path_parts.insert(0, bindir)
        os.environ["PATH"] = os.pathsep.join(path_parts)

        def first_tool(*names):
            for bindir in bindirs:
                for name in names:
                    candidate = os.path.join(bindir, name)
                    if os.path.isfile(candidate):
                        return candidate
            return ""

        make = first_tool("make", "gmake")
        ar = compiler_executables.get("ar") or first_tool("llvm-ar", "ar")
        ranlib = compiler_executables.get("ranlib") or first_tool("llvm-ranlib", "ranlib")
        if make:
            os.environ["MAKE"] = make
        if ar:
            os.environ["AR"] = ar
        if ranlib:
            os.environ["RANLIB"] = ranlib

    def _extend_library_path_for_tests(self):
        libdirs = [os.path.join(self.build_folder, "chafa", ".libs")]
        for dep in self.dependencies.host.values():
            package_folder = getattr(dep, "package_folder", None)
            if not package_folder:
                continue
            for subdir in ("lib", "lib64"):
                candidate = os.path.join(str(package_folder), subdir)
                if os.path.isdir(candidate):
                    libdirs.append(candidate)
        current = [p for p in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p]
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(libdirs + current)

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign")
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        for so in sos:
            if objcopy and os.path.isfile(objcopy):
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))
