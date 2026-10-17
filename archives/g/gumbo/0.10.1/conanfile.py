#!/usr/bin/env python3
"""Conan recipe — gumbo 0.10.1 (direct-drive compile).

gumbo: Google's HTML5 parsing conformance library (the tokenizer/parser
behind html5lib), pure C89, zero external dependencies.  Upstream is
dormant since 0.10.1 (2016).

Platform task: 开源鸿蒙PC专项积分赛-依赖 · gumbo 0.10.1 (自导入, 5 火种).

Build system note: this is the GitHub tag archive — autotools inputs
only (no generated configure, no CMakeLists).  The C sources under
src/ are fully pre-generated (char_ref.c ragel output, tag_*.h gperf
outputs all ship in-tree) and reference no config.h/HAVE_* at all
(grep-verified), so build() drives the 11 translation units directly
through the conan toolchain and links the libtool-versioned SONAME
itself (-version-info 1:0:0 → libgumbo.so.1 / libgumbo.so.1.0.0, the
same contributed-wrapper precedent as subunit 1.4.5).  Verified
end-to-end on glibc (gcc: 11/11 TU, link, probe 7/7) before this
recipe was written.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

_TUS = [
    "attribute", "char_ref", "error", "parser", "string_buffer",
    "string_piece", "tag", "tokenizer", "utf8", "util", "vector",
]

_HEADERS = ["gumbo.h", "tag_enum.h"]


class GumboConan(ConanFile):
    name = "gumbo"
    version = "0.10.1"
    description = "Google's HTML5 parsing library (conformance tokenizer/parser, pure C89)"
    license = "Apache-2.0"
    homepage = "https://github.com/google/gumbo-parser"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        copy(self, "upstream_test.py", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        pass  # 纯 C89,零外部依赖

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        get(self, **self.conan_data["test_sources"]["gtest-1.7.0"],
            destination="gtest", strip_root=True)

    def _toolchain(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c", "clang")
        ar = ce.get("ar")
        if not ar:
            ccdir = os.path.dirname(cc) if os.path.sep in cc else ""
            ar = "ar"
            for name in ("llvm-ar", "ar"):
                cand = os.path.join(ccdir, name)
                if ccdir and os.path.isfile(cand):
                    ar = cand
                    break
        return cc, ar

    def build(self):
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "src")
        bld = os.path.join(self.build_folder or self.source_folder, "_build")
        os.makedirs(bld, exist_ok=True)
        cc, ar = self._toolchain()
        extra = ["-fPIC", "-O1", "-DNDEBUG"]
        objs = []
        for t in _TUS:
            obj = os.path.join(bld, t + ".o")
            cmd = [cc, "-c", os.path.join(src, t + ".c"), "-o", obj] + extra
            self.output.info(" ".join(cmd))
            subprocess.run(cmd, check=True)

            objs.append(obj)
        if self.options.shared:
            # 上游 -version-info 1:0:0 → soname .so.1 / file .so.1.0.0
            cmd = [cc, "-shared", "-Wl,-soname,libgumbo.so.1",
                   "-o", os.path.join(bld, "libgumbo.so.1.0.0")] + objs
            self.output.info(" ".join(cmd))
            subprocess.run(cmd, check=True)
        else:
            cmd = [ar, "rcs", os.path.join(bld, "libgumbo.a")] + objs
            self.output.info(" ".join(cmd))
            subprocess.run(cmd, check=True)

        if self.settings.os == "OHOS" and self.options.shared:
            signer = shutil.which("binary-sign-tool")
            if not signer:
                raise RuntimeError("Native binary-sign-tool required for OHOS shared library")
            library = os.path.join(bld, "libgumbo.so.1.0.0")
            signed = library + ".signed"
            subprocess.run([signer, "sign", "-selfSign", "1", "-inFile", library,
                            "-outFile", signed], check=True)
            os.replace(signed, library)

        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cxx = compilers.get("cpp") or shutil.which("clang++") or shutil.which("g++")
        if not cxx:
            raise RuntimeError("A C++ compiler is required for upstream gumbo tests")
        command = [sys.executable, os.path.join(self.source_folder, "upstream_test.py"),
                   self.source_folder, os.path.join(self.build_folder, "upstream-tests"),
                   "--compiler", cc, "--cxx", cxx]
        if self.settings.os == "OHOS":
            command.append("--native-ohos")
        subprocess.run(command, check=True)

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        inc = os.path.join(pkg, "include")
        os.makedirs(inc, exist_ok=True)
        for h in _HEADERS:
            copy(self, h, os.path.join(src, "src"), inc)
        libdir = os.path.join(pkg, "lib")
        os.makedirs(libdir, exist_ok=True)
        bld = os.path.join(self.build_folder or self.source_folder, "_build")
        if self.options.shared:
            realname = "libgumbo.so.1.0.0"
            shutil.copy2(os.path.join(bld, realname), os.path.join(libdir, realname))
            for name in ("libgumbo.so.1", "libgumbo.so"):
                dst = os.path.join(libdir, name)
                if not os.path.lexists(dst):
                    try:
                        os.symlink(realname, dst)
                    except OSError:
                        shutil.copy2(os.path.join(bld, realname), dst)
        else:
            shutil.copy2(os.path.join(bld, "libgumbo.a"),
                         os.path.join(libdir, "libgumbo.a"))
        # pkg-config 元数据(镜像上游 gumbo.pc.in)
        pc = f"""prefix={pkg}
exec_prefix=${{prefix}}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: gumbo
Description: HTML5 parsing library.
Version: {self.version}
Requires:
Libs: -L${{libdir}} -lgumbo
Cflags: -I${{includedir}}
"""
        os.makedirs(os.path.join(pkg, "lib", "pkgconfig"), exist_ok=True)
        with open(os.path.join(pkg, "lib", "pkgconfig", "gumbo.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(pc)
        copy(self, "COPYING", src, os.path.join(pkg, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gumbo")
        self.cpp_info.set_property("pkg_config_name", "gumbo")
        self.cpp_info.libs = ["gumbo"]
