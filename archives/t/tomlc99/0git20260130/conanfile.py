#!/usr/bin/env python3
"""Conan recipe — tomlc99 0git20260130 (direct-drive compile).

tomlc99: TOML v1.0 parser in clean ANSI C89/C99, zero external
dependencies (single toml.c/toml.h).  Upstream is a rolling master
with no tags/releases; the package version is a dated master snapshot
(0git20260130, commit 29076dfd09, 2026-01-30) following the
agnostic-lizard-0git20201010 precedent.

Platform task: 开源鸿蒙PC专项积分赛-依赖 · tomlc99 0git20260130 (自导入, 5 火种).

Build system note: upstream ships a plain Makefile with static/shared
libraries, sample tools and an install target. This library-only build()
drives the single translation unit directly and links the library
itself.  Upstream has no SONAME convention either; this package
establishes libtoml.so.0 / .so.0.0.0 (documented in notes.md).  The
CLI tools (toml_cat/toml_json/toml_sample) are not part of the
library package.  Verified end-to-end on glibc (gcc: 1/1 TU, both
artifacts, probe 8/8) before this recipe was written.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class Tomlc99Conan(ConanFile):
    name = "tomlc99"
    version = "0git20260130"
    description = "TOML v1.0 parser in ANSI C99 (single translation unit, zero deps)"
    license = "MIT"
    homepage = "https://github.com/cktan/tomlc99"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        copy(self, "upstream_test.py", self.recipe_folder, self.export_sources_folder)
        copy(self, "patches/*", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        pass  # 纯 C,零外部依赖

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        for name, data in self.conan_data["test_sources"].items():
            get(self, **data, destination="test-fixtures/" + name, strip_root=True)

    def _toolchain(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or shutil.which("clang") or shutil.which("gcc")
        if not cc or not os.path.isabs(cc) or not os.path.isfile(cc):
            raise RuntimeError("An absolute configured C compiler is required")
        ar = ce.get("ar")
        if not ar:
            ccdir = os.path.dirname(cc) if os.path.sep in cc else ""
            ar = None
            suffix = os.path.basename(cc).removeprefix("clang") if os.path.basename(cc).startswith("clang") else ""
            for name in ("llvm-ar" + suffix, "llvm-ar", "ar"):
                cand = os.path.join(ccdir, name)
                if ccdir and os.path.isfile(cand):
                    ar = cand
                    break
            ar = ar or shutil.which("llvm-ar") or shutil.which("ar")
        if not self.options.shared and (not ar or not os.path.isabs(ar) or not os.path.isfile(ar)):
            raise RuntimeError("An absolute compatible archiver is required")
        return cc, ar

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        bld = os.path.join(self.build_folder or self.source_folder, "_build")
        os.makedirs(bld, exist_ok=True)
        cc, ar = self._toolchain()
        obj = os.path.join(bld, "toml.o")
        cmd = [cc, "-c", os.path.join(src, "toml.c"), "-o", obj,
               "-fPIC", "-O1", "-DNDEBUG"]
        self.output.info(" ".join(cmd))
        subprocess.run(cmd, check=True)
        if self.options.shared:
            cmd = [cc, "-shared", "-Wl,-soname,libtoml.so.0",
                   "-o", os.path.join(bld, "libtoml.so.0.0.0"), obj]
            self.output.info(" ".join(cmd))
            subprocess.run(cmd, check=True)
        else:
            cmd = [ar, "rcs", os.path.join(bld, "libtoml.a"), obj]
            self.output.info(" ".join(cmd))
            subprocess.run(cmd, check=True)

        signer = None
        if self.settings.os == "OHOS":
            signer = shutil.which("binary-sign-tool")
            if not signer:
                raise RuntimeError("Native signer required for complete OHOS tests")
            if self.options.shared:
                library = os.path.join(bld, "libtoml.so.0.0.0")
                subprocess.run([signer, "sign", "-selfSign", "1", "-inFile", library,
                                "-outFile", library + ".signed"], check=True, timeout=30)
                os.replace(library + ".signed", library)
        command = [sys.executable, os.path.join(src, "upstream_test.py"), src,
                   os.path.join(src, "test-fixtures"),
                   os.path.join(self.build_folder, "upstream-tests"), "--compiler", cc]
        if signer:
            command += ["--signer", signer]
        subprocess.run(command, check=True)

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        inc = os.path.join(pkg, "include")
        os.makedirs(inc, exist_ok=True)
        copy(self, "toml.h", src, inc)
        libdir = os.path.join(pkg, "lib")
        os.makedirs(libdir, exist_ok=True)
        bld = os.path.join(self.build_folder or self.source_folder, "_build")
        if self.options.shared:
            realname = "libtoml.so.0.0.0"
            shutil.copy2(os.path.join(bld, realname), os.path.join(libdir, realname))
            for name in ("libtoml.so.0", "libtoml.so"):
                dst = os.path.join(libdir, name)
                if not os.path.lexists(dst):
                    try:
                        os.symlink(realname, dst)
                    except OSError:
                        shutil.copy2(os.path.join(bld, realname), dst)
        else:
            shutil.copy2(os.path.join(bld, "libtoml.a"),
                         os.path.join(libdir, "libtoml.a"))
        # pkg-config 元数据(镜像上游 libtoml.pc.sample)
        pc = f"""prefix={pkg}
exec_prefix=${{prefix}}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: libtoml
Description: TOML v1.0 parser in ANSI C99.
Version: {self.version}
Requires:
Libs: -L${{libdir}} -ltoml
Cflags: -I${{includedir}}
"""
        os.makedirs(os.path.join(pkg, "lib", "pkgconfig"), exist_ok=True)
        with open(os.path.join(pkg, "lib", "pkgconfig", "libtoml.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(pc)
        copy(self, "LICENSE", src, os.path.join(pkg, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libtoml")
        self.cpp_info.set_property("cmake_target_name", "libtoml::libtoml")
        self.cpp_info.set_property("pkg_config_name", "libtoml")
        self.cpp_info.libs = ["toml"]
