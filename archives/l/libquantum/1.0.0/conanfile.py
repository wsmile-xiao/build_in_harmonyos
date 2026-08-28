#!/usr/bin/env python3
"""Conan recipe for libquantum 1.0.0.

libquantum is a C library for the simulation of a quantum computer. Based on
the principles of quantum mechanics, it provides an implementation of a
quantum register with basic gate operations (Hadamard, CNOT, Pauli-X/Y/Z,
phase, QFT), quantum measurement, decoherence, density-matrix operations and
building blocks for Grover's and Shor's algorithms.

Build approach: libquantum ships a 2008-era autoconf (configure.in /
config.status) that cannot reliably create its temp subdirs on the OHOS
restricted build filesystem (no mkfifo, flaky mktemp). Rather than patch the
upstream sources, the recipe generates the three autotools output headers
(config.h, types.h, quantum.h) from their .in templates with the values
configure.in would detect for aarch64/musl, then compiles the library C
sources directly with the OHOS clang and archives them into libquantum.a with
ar. This is a build-system adaptation in the recipe only — no upstream source
file is modified (zero patch).

No AutotoolsToolchain/Autotools generators are used: build() compiles directly
with the resolved CC, so no cbuildenv-*.sh is written into the source tree.
"""
import json
import os
import re
import shutil
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, rm
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibquantumConan(ConanFile):
    name = "libquantum"
    version = "1.0.0"
    description = (
        "C library for the simulation of quantum mechanics and quantum "
        "computers: quantum register, Hadamard/CNOT/Pauli gates, QFT, "
        "Grover/Shor algorithm building blocks, measurement and decoherence."
    )
    license = "GPL-3.0-or-later"
    homepage = "http://www.libquantum.de/"
    url = ""
    topics = ("quantum", "quantum-computing", "simulation",
              "physics", "qubit", "quantum-register")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libquantum is supported only on Linux/OHOS"
            )

    def layout(self):
        basic_layout(self)

    def generate(self):
        # No-op: we compile directly with subprocess + the resolved CC, so
        # no AutotoolsToolchain/env generators are needed. This also prevents
        # Conan 2 from auto-injecting VirtualBuildEnv which would write shell
        # env scripts into the source tree (tripping the CI junk-file gate).
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_cc(self):
        """Resolve the real OHOS clang, defending against a dead profile path."""
        ce = self.conf.get("tools.build:compiler_executables", default=None)
        cc = None
        if ce:
            try:
                d = json.loads(ce) if isinstance(ce, str) else ce
                cc = d.get("c")
            except Exception:
                pass
        if cc and os.path.isfile(cc) and os.access(cc, os.X_OK):
            return cc
        return os.environ.get("CC") or "clang"

    # Library C sources (exclude demos/tools that have main(): grover.c,
    # shor.c, quobprint.c, quobdump.c). These constitute libquantum.a per
    # Makefile.in's libquantum_a_OBJECTS.
    _LIB_SOURCES = [
        "qureg.c", "gates.c", "measure.c", "matrix.c", "complex.c",
        "decoherence.c", "density.c", "qec.c", "qft.c", "qtime.c",
        "classic.c", "oaddn.c", "omuln.c", "expn.c", "objcode.c",
        "error.c", "version.c",
    ]

    @staticmethod
    def _replace_undef(text, name, replacement):
        """Replace a whole-line '#undef NAME' with '#define NAME replacement'.

        Uses line-anchored regex so PACKAGE doesn't match inside
        PACKAGE_BUGREPORT, COMPLEX_FLOAT inside COMPLEX_FLOAT_EXTENDED, etc.
        """
        pattern = re.compile(r"^#undef\s+" + re.escape(name) + r"\s*$", re.M)
        return pattern.sub(f"#define {name} {replacement}", text)

    def _generate_headers(self):
        """Generate config.h, types.h, quantum.h from their .in templates.

        Replicates the autoconf type-detection logic (configure.in lines
        55-124) deterministically for aarch64/musl, instead of running the
        flaky 2008 config.status which cannot create its temp subdirs on
        this restricted filesystem.
        """
        src = self.source_folder
        cf_type = "float _Complex"
        mu_type = "unsigned long long"
        imaginary = "__builtin_complex(0.0f, 1.0f)"

        # --- config.h ---
        with open(os.path.join(src, "config.h.in")) as f:
            tmpl = f.read()

        for define in [
            "HAVE_FCNTL_H", "HAVE_STDLIB_H", "HAVE_STRING_H",
            "HAVE_UNISTD_H", "HAVE_MEMORY_H", "HAVE_STRINGS_H",
            "HAVE_SYS_STAT_H", "HAVE_SYS_TYPES_H", "HAVE_INTTYPES_H",
            "HAVE_STDINT_H", "STDC_HEADERS", "HAVE_LONG_LONG",
        ]:
            tmpl = self._replace_undef(tmpl, define, "1")

        tmpl = self._replace_undef(tmpl, "COMPLEX_FLOAT", cf_type)
        tmpl = self._replace_undef(tmpl, "MAX_UNSIGNED", mu_type)
        tmpl = self._replace_undef(tmpl, "IMAGINARY", imaginary)

        for name, value in [
            ("PACKAGE", '"libquantum"'),
            ("PACKAGE_VERSION", '"1.0.0"'),
            ("PACKAGE_STRING", '"libquantum 1.0.0"'),
            ("PACKAGE_NAME", '"libquantum"'),
            ("PACKAGE_TARNAME", '"libquantum"'),
            ("PACKAGE_BUGREPORT", '"bug-libquantum@gnu.org"'),
        ]:
            tmpl = self._replace_undef(tmpl, name, value)

        with open(os.path.join(src, "config.h"), "w") as f:
            f.write(tmpl)

        # --- types.h ---
        with open(os.path.join(src, "types.h.in")) as f:
            tmpl = f.read()
        tmpl = tmpl.replace("@CF_TYPE@", cf_type)
        tmpl = tmpl.replace("@MU_TYPE@", mu_type)
        tmpl = tmpl.replace("@I@", imaginary)
        with open(os.path.join(src, "types.h"), "w") as f:
            f.write(tmpl)

        # --- quantum.h ---
        with open(os.path.join(src, "quantum.h.in")) as f:
            tmpl = f.read()
        tmpl = tmpl.replace("@CF_TYPE@", cf_type)
        tmpl = tmpl.replace("@MU_TYPE@", mu_type)
        with open(os.path.join(src, "quantum.h"), "w") as f:
            f.write(tmpl)

    def build(self):
        cc = self._resolve_cc()
        src = self.source_folder

        self._generate_headers()

        env = dict(os.environ)
        env["MAKEFLAGS"] = ""
        env["TMPDIR"] = src

        pic = "-fPIC" if self.options.get_safe("fPIC", True) else ""
        opt = "-O2" if self.settings.build_type == "Release" else "-g"
        cflags = shlex.split(
            f"{pic} {opt} -DHAVE_CONFIG_H -I. -include types.h -Wall"
        )

        objects = []
        for cfile in self._LIB_SOURCES:
            ofile = cfile.replace(".c", ".o")
            cmd = [cc] + cflags + ["-c", cfile, "-o", ofile]
            self.output.info("CC " + cfile)
            subprocess.check_call(cmd, cwd=src, env=env)
            objects.append(ofile)

        ar = shutil.which("ar") or "ar"
        ranlib = shutil.which("ranlib") or "ranlib"
        lib_path = os.path.join(src, "libquantum.a")
        if os.path.exists(lib_path):
            os.remove(lib_path)
        subprocess.check_call([ar, "rcs", lib_path] + objects, cwd=src, env=env)
        if ranlib:
            subprocess.check_call([ranlib, lib_path], cwd=src, env=env)

    def package(self):
        src = self.source_folder
        inc_dir = os.path.join(self.package_folder, "include")
        os.makedirs(inc_dir, exist_ok=True)
        # Install quantum.h (public API) plus config.h and types.h which
        # quantum.h #includes — consumers need all three to compile.
        copy(self, "quantum.h", src=src, dst=inc_dir)
        copy(self, "config.h", src=src, dst=inc_dir)
        copy(self, "types.h", src=src, dst=inc_dir)
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        copy(self, "libquantum.a", src=src, dst=lib_dir)
        lic_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(lic_dir, exist_ok=True)
        copy(self, "COPYING", src=src, dst=lic_dir)
        copy(self, "README", src=src, dst=lic_dir)

    def package_info(self):
        self.cpp_info.libs = ["quantum"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "libquantum")
        self.cpp_info.set_property("cmake_target_name", "libquantum::libquantum")
