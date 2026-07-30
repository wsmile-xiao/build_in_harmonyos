#!/usr/bin/env python3
"""Conan recipe for osmctools 0.9 — OpenStreetMap data conversion/filter tools (C, direct compile).

osmctools ships three single-file CLI binaries:
  osmconvert  (links zlib: gzopen/gzread/gzseek/gzclose + libm)
  osmfilter   (only libc)
  osmupdate   (only libc)

The upstream 0.9 GitLab tag archive contains only configure.ac + Makefile.am + the
three .c sources — NO pre-generated configure/Makefile.in. Bootstrapping autotools
needs `aclocal` (from automake), which is NOT installed on the OHOS build machine
(only autoconf 2.72 is present). Rather than fight the toolchain, compile the three
single-file programs directly, exactly as the upstream header comment recommends:

    gcc osmconvert.c -lz -O3 -o osmconvert

The two extra `int main()` in osmconvert.c live inside `#if 0` blocks (standalone
test programs cosrk.c/cosr.c, explicitly disabled by the preprocessor), so a single
`clang -c osmconvert.c` produces one main — no symbol clash.

R26: not a system same-name library; static/shared irrelevant for application packages.
R32: settings.os checked in ("Linux", "OHOS").
R33: compiler/flags come from Conan conf, never bare ${CC}/${CFLAGS}.
R34/R28: test_package/ exists and runs the actual osmconvert/osmfilter binaries.
R38: CLI binaries -> commands.json declared at software level.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class OsmctoolsConan(ConanFile):
    name = "osmctools"
    version = "0.9"
    description = "Fast OpenStreetMap data conversion/filter/update command-line tools (osmconvert, osmfilter, osmupdate)"
    license = "AGPL-3.0-only"
    homepage = "https://gitlab.com/osm-c-tools/osmctools"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib provides <zlib.h> + libz.a; osmconvert links it (gzopen/gzread/gzseek/gzclose).
        self.requires("zlib/1.3.1")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "osmctools is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No autotools bootstrap needed — direct compile recipe.
        # Expose zlib's include/lib dirs to the build() compile commands via env vars
        # (zlib is a Conan dependency; its package folder is resolved at build time).
        pass

    def _zlib_paths(self):
        """Resolve zlib header dir and static library absolute path from the Conan dep.

        Linking by absolute path (libz.a) avoids depending on -L/-l runtime search,
        which is fragile under the OHOS cross toolchain (libz.a is Conan-built, not
        in the system lib search path).
        """
        dep = self.dependencies["zlib"]
        pkg = dep.package_folder
        inc = os.path.join(pkg, "include")
        libz = os.path.join(pkg, "lib", "libz.a")
        if not os.path.isfile(libz):
            # fall back to package root if layout differs
            libz = os.path.join(pkg, "libz.a")
        return inc, libz

    def build(self):
        src = self.source_folder
        bin_out = os.path.join(self.build_folder, "bin")
        os.makedirs(bin_out, exist_ok=True)

        # R33: get compiler from Conan conf, not bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # Resolve zlib include dir + libz.a absolute path (osmconvert needs <zlib.h> + libz)
        z_inc, libz = self._zlib_paths()

        # Build type -> optimization flags
        opt = "-O3" if self.settings.build_type == "Release" else "-O0"

        # E063: upstream comment compiles with -O3; do NOT add -Werror (configure.ac had
        # AM_INIT_AUTOMAKE([foreign -Wall -Werror]) but we bypass autotools entirely).
        # Relax warnings that would be errors under some toolchains:
        cflags = [opt, "-Wno-error", "-D__OHOS__=1"]

        # --- osmconvert: needs zlib (libz.a) and libm (uses sin/cos) ---
        # Link libz.a by absolute path — robust against toolchain lib search gaps.
        self.run(
            " ".join([
                cc, *cflags,
                "-I" + z_inc,
                os.path.join(src, "src", "osmconvert.c"),
                libz, "-lm",
                "-o", os.path.join(bin_out, "osmconvert"),
            ]),
            env="conanbuild",
        )

        # --- osmfilter: only libc ---
        self.run(
            " ".join([
                cc, *cflags,
                os.path.join(src, "src", "osmfilter.c"),
                "-o", os.path.join(bin_out, "osmfilter"),
            ]),
            env="conanbuild",
        )

        # --- osmupdate: only libc ---
        self.run(
            " ".join([
                cc, *cflags,
                os.path.join(src, "src", "osmupdate.c"),
                "-o", os.path.join(bin_out, "osmupdate"),
            ]),
            env="conanbuild",
        )

    def package(self):
        # Install the three binaries into <package_folder>/bin
        # build() wrote them to <build_folder>/bin/
        src_bin = os.path.join(self.build_folder, "bin")
        dst_bin = os.path.join(self.package_folder, "bin")
        copy(self, "osmconvert", src_bin, dst_bin)
        copy(self, "osmfilter", src_bin, dst_bin)
        copy(self, "osmupdate", src_bin, dst_bin)

    def package_info(self):
        # osmctools is a binary-only application package (three CLI tools, no library)
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # zlib is consumed at link time for osmconvert (-lz)
        self.cpp_info.system_libs = ["z", "m"]
        # Ensure the three binaries are on PATH for VirtualRunEnv (test_package)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
