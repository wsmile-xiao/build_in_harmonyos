#!/usr/bin/env python3
"""Conan recipe for zim-tools 3.7.0 (Meson-based)."""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class ZimtoolsConan(ConanFile):
    name = "zim-tools"
    version = "3.7.0"
    description = "Various tools to interact with ZIM files"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/openzim/zim-tools"
    url = "https://github.com/openzim/zim-tools"

    package_type = "application"

    generators = "PkgConfigDeps"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libzim/9.7.0")
        self.requires("docopt.cpp/0.6.3")
        self.requires("gumbo-parser/0.10.1")
        self.requires("kainjow-mustache/4.1")
        self.requires("zlib/1.3.1")
        self.requires("file/5.48")
        self.requires("icu4c/77")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Patch src/zimcheck/meson.build: the upstream uses
        # compiler.has_header('mustache.hpp') which cannot find the header
        # from the kainjow-mustache Conan package.  Replace with
        # dependency('kainjow-mustache') which uses pkg-config.
        zimcheck_meson = os.path.join(self.source_folder, "src", "zimcheck", "meson.build")
        if os.path.isfile(zimcheck_meson):
            with open(zimcheck_meson) as f:
                content = f.read()
            old = """if compiler.has_header('mustache.hpp')
  extra_include = []
elif compiler.has_header('mustache.hpp', args: '-I/usr/include/kainjow')
  extra_include = ['/usr/include/kainjow']
else
  error('Cannot find header mustache.hpp')
endif

inc = include_directories(extra_include)

zimcheck_deps = [libzim_dep, icu_dep, docopt_dep]"""
            new = """mustache_dep = dependency('kainjow-mustache', required: false)
if mustache_dep.found()
  extra_include = []
  zimcheck_deps = [libzim_dep, icu_dep, docopt_dep, mustache_dep]
elif compiler.has_header('mustache.hpp', args: '-I/usr/include/kainjow')
  extra_include = ['/usr/include/kainjow']
  zimcheck_deps = [libzim_dep, icu_dep, docopt_dep]
else
  error('Cannot find header mustache.hpp')
  zimcheck_deps = [libzim_dep, icu_dep, docopt_dep]
endif

inc = include_directories(extra_include)"""
            content = content.replace(old, new)
            with open(zimcheck_meson, "w") as f:
                f.write(content)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["static-linkage"] = "false"
        tc.generate()

        # ICU comes from the Conan icu4c package.  PkgConfigDeps generates
        # icu-uc.pc (its pkg_config_name), but zim-tools's meson.build calls
        # dependency('icu-i18n').  Create an icu-i18n.pc alias so pkg-config
        # can resolve it.
        gen_dir = os.path.join(self.build_folder, "conan")
        icu_uc_pc = os.path.join(gen_dir, "icu-uc.pc")
        icu_i18n_pc = os.path.join(gen_dir, "icu-i18n.pc")
        if os.path.isfile(icu_uc_pc) and not os.path.isfile(icu_i18n_pc):
            shutil.copy2(icu_uc_pc, icu_i18n_pc)

        # Conan's file package ships file.pc, but zim-tools's meson.build
        # calls dependency('libmagic').  Create a libmagic.pc alias.
        file_pc = os.path.join(gen_dir, "file.pc")
        libmagic_pc = os.path.join(gen_dir, "libmagic.pc")
        if os.path.isfile(file_pc) and not os.path.isfile(libmagic_pc):
            shutil.copy2(file_pc, libmagic_pc)

        # Conan's xz package ships xz.pc, but libzim's meson.build calls
        # dependency('liblzma').  Create a liblzma.pc alias.
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
                    with open(native_file) as rf:
                        lines = rf.readlines()
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

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # HMDFS workaround: replace symlinks with file copies (E050)
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for fname in os.listdir(lib_dir):
                fpath = os.path.join(lib_dir, fname)
                if os.path.islink(fpath):
                    real_file = os.path.join(lib_dir, os.readlink(fpath))
                    if os.path.isfile(real_file):
                        os.unlink(fpath)
                        shutil.copy2(real_file, fpath)

        # Sign ELF binaries for HarmonyOS runtime
        HNP_BIN = "/data/service/hnp/bin"
        if self.settings.os == "OHOS":
            for bindir in (os.path.join(self.package_folder, "bin"),
                           os.path.join(self.package_folder, "lib")):
                if not os.path.isdir(bindir):
                    continue
                for fname in os.listdir(bindir):
                    fpath = os.path.join(bindir, fname)
                    if not os.path.isfile(fpath):
                        continue
                    # Remove old codesign section
                    r = subprocess.run(
                        [os.path.join(HNP_BIN, "llvm-objcopy"),
                         "--remove-section", ".codesign", fpath],
                        capture_output=True, timeout=30)
                    if r.returncode != 0:
                        raise Exception(
                            f"llvm-objcopy failed for {fpath}: "
                            f"returncode={r.returncode} stderr={r.stderr}")
                    # Self-sign
                    tmp = fpath + ".signed.tmp"
                    r = subprocess.run(
                        [os.path.join(HNP_BIN, "binary-sign-tool"),
                         "sign", "-inFile", fpath,
                         "-outFile", tmp, "-selfSign", "1"],
                        capture_output=True, timeout=30)
                    if r.returncode == 0 and os.path.exists(tmp):
                        shutil.move(tmp, fpath)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []