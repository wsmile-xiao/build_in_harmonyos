#!/usr/bin/env python3
"""Conan recipe — libzim 9.7.0.1 (meson)"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class LibzimConan(ConanFile):
    name = "libzim"
    version = "9.7.0.1"
    description = "Reference implementation of the ZIM file format"
    license = "GPL-2.0-only"
    homepage = "https://github.com/openzim/libzim"
    url = "https://github.com/openzim/libzim"

    generators = "PkgConfigDeps"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Fix upstream meson.build: 'required:false' is a string literal
        # but Meson treats it as a dependency name.  Change to keyword arg
        # required: false, and guard .version() with .found() in the
        # else (not-xapian) branch only.
        meson_build = os.path.join(self.source_folder, "meson.build")
        with open(meson_build) as f:
            content = f.read()

        # Fix 1: 'required:false' → required: false (keyword argument)
        content = content.replace("'required:false'", "required: false")

        # Fix 2: In the else branch (not-xapian), guard .version() with
        # .found() because icu_dep is optional (required: false).
        # The else branch is uniquely identified by the pattern:
        #   else
        #       icu_dep = dependency('icu-i18n', required: false, ...)
        #       if icu_dep.version().version_compare('>= 76')
        #           icu_dep = [icu_dep, dependency('icu-uc', required: false, ...)]
        #       endif
        #   endif
        old = ("else\n"
               "    icu_dep = dependency('icu-i18n', required: false, static:static_linkage)\n"
               "    if icu_dep.version().version_compare('>= 76')\n"
               "        icu_dep = [icu_dep, dependency('icu-uc', required: false, static:static_linkage)]\n"
               "    endif\n"
               "endif")
        new = ("else\n"
               "    icu_dep = dependency('icu-i18n', required: false, static: static_linkage)\n"
               "    if icu_dep.found()\n"
               "        if icu_dep.version().version_compare('>= 76')\n"
               "            icu_dep = [icu_dep, dependency('icu-uc', required: false, static: static_linkage)]\n"
               "        endif\n"
               "    endif\n"
               "endif")
        content = content.replace(old, new)

        with open(meson_build, "w") as f:
            f.write(content)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["with_xapian"] = "false"
        tc.project_options["werror"] = "false"
        tc.project_options["examples"] = "false"
        tc.project_options["tests"] = "false"
        tc.generate()

        gen_dir = os.path.join(self.build_folder, "conan")

        # Conan's xz package ships xz.pc, but libzim's meson.build calls
        # dependency('liblzma').  Create a liblzma.pc alias in the
        # generators folder so pkg-config can resolve it.
        if self.settings.os in ("Linux", "OHOS"):
            xz_pc = os.path.join(gen_dir, "xz.pc")
            liblzma_pc = os.path.join(gen_dir, "liblzma.pc")
            if os.path.isfile(xz_pc) and not os.path.isfile(liblzma_pc):
                shutil.copy2(xz_pc, liblzma_pc)

        # Meson cannot detect llvm-ar/llvm-ranlib on the OHOS worker.
        if self.settings.os == "OHOS":
            import glob as _glob
            native_file = os.path.join(gen_dir, "conan_meson_native.ini")
            if os.path.isfile(native_file):
                cc = None
                with open(native_file) as nf:
                    for line in nf:
                        if line.startswith("c = '") and not cc:
                            cc = line.strip().split("'")[1]
                ar = ranlib = None
                if cc:
                    cc_dir = os.path.dirname(cc)
                    ar_hits = _glob.glob(os.path.join(cc_dir, "llvm-ar*"))
                    ran_hits = _glob.glob(os.path.join(cc_dir, "llvm-ranlib*"))
                    ar = ar_hits[0] if ar_hits else shutil.which("llvm-ar")
                    ranlib = ran_hits[0] if ran_hits else shutil.which("llvm-ranlib")
                if ar and ranlib:
                    with open(native_file) as nf:
                        lines = nf.readlines()
                    with open(native_file, "w") as nf:
                        in_bin = False
                        for line in lines:
                            nf.write(line)
                            if line.strip() == "[binaries]":
                                in_bin = True
                            elif in_bin and line.startswith("cpp = '"):
                                nf.write("ar = '{}'\nranlib = '{}'\n".format(ar, ranlib))
                                in_bin = False

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

        # Sign the built library BEFORE packaging, so meson install copies
        # the signed version.  This is necessary because the OHOS dynamic
        # linker rejects unsigned shared libraries.
        # Use in-place signing (-inFile == -outFile) via self.run() to avoid
        # HMDFS shutil.move() corrupting the .codesign section (E050 variant).
        if self.settings.os == "OHOS":
            HNP_BIN = "/data/service/hnp/bin"
            so_file = os.path.join(self.build_folder, "src", "libzim.so.9.7.0")
            if os.path.isfile(so_file):
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                    oc=os.path.join(HNP_BIN, "llvm-objcopy"), f=so_file))
                self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=os.path.join(HNP_BIN, "binary-sign-tool"), f=so_file))
                self.output.info("libzim.so.9.7.0 signed in build dir (in-place)")

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # HMDFS workaround: replace symlinks with file copies (E050)
        # The HMDFS filesystem on the OHOS worker does not properly track
        # symlinks, so the dynamic linker cannot resolve libzim.so -> libzim.so.9.
        # The library was already signed in build() — meson install copies
        # the signed version.  We just need to make libzim.so.9 and libzim.so
        # into regular files on HMDFS.
        lib_dir = os.path.join(self.package_folder, "lib")
        real_file = os.path.join(lib_dir, "libzim.so.9.7.0")
        if os.path.isdir(lib_dir) and os.path.isfile(real_file):
            for link_name in ("libzim.so", "libzim.so.9"):
                link_path = os.path.join(lib_dir, link_name)
                try:
                    os.unlink(link_path)
                except OSError:
                    pass
                shutil.copyfile(real_file, link_path)

        # Sign all .so files (including versioned like libzim.so.9, libzim.so.9.7.0).
        # Use in-place signing (-inFile == -outFile) via self.run() to avoid
        # HMDFS shutil.move() corrupting the .codesign section (E050 variant).
        if self.settings.os == "OHOS" and os.path.isdir(lib_dir):
            HNP_BIN = "/data/service/hnp/bin"
            import glob as _glob
            sos = _glob.glob(os.path.join(lib_dir, "**", "*.so"), recursive=True)
            sos += _glob.glob(os.path.join(lib_dir, "**", "*.so.*"), recursive=True)
            for fpath in sos:
                if os.path.islink(fpath):
                    continue  # skip symlinks, only sign real ELF files
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                    oc=os.path.join(HNP_BIN, "llvm-objcopy"), f=fpath))
                self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=os.path.join(HNP_BIN, "binary-sign-tool"), f=fpath))

    def package_info(self):
        self.cpp_info.libs = ["zim"]
        self.cpp_info.set_property("pkg_config_name", "libzim")

    def requirements(self):
        self.requires("xz/5.6.2")
        self.requires("zstd/1.5.7")