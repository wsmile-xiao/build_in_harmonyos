#!/usr/bin/env python3
"""Conan recipe for jnoise 0.6.0 (Fons Adriaensen) -- OHOS aarch64.

jnoise is a small command line JACK client that generates white and pink
noise (two output ports).  The upstream tarball is a raw Makefile project:
`source/Makefile`, no configure script, single output binary `jnoise`.

OHOS portability notes (see notes.md):
  - The link rule hardcodes the compiler name `g++`; OpenHarmony ships only
    clang/clang++ (no g++ anywhere on PATH) and R33 requires the compiler to
    come from the Conan profile, so the patch replaces it with `$(CXX)`.
  - The install target calls bare `install` (coreutils); that command is not
    on PATH on OpenHarmony (the toybox build is at /bin/install, proven by
    executing it -- `ls -l /bin/install` reports Permission denied, i.e. stat
    is a false negative there).  The patch parameterises it as
    `INSTALL ?= /bin/install`, the same fix as sibling recipe aeolus/0.10.4.
  - `PREFIX = /usr/local` is a plain assignment, so it is overridden from the
    make command line (PREFIX=/ plus DESTDIR) instead of being patched.  The
    Makefile also bakes `-DSHARED="$(PREFIX)/share"` into CPPFLAGS, but
    `SHARED` is referenced nowhere in the 0.6.0 sources (grep over *.cc/*.h:
    0 hits), so no runtime path is embedded.
  - CPPFLAGS/LDFLAGS go through the *environment*, never as make command-line
    variables, because the Makefile uses `CPPFLAGS +=` (which carries
    -DPROGRAM/-DVERSION) and a command-line override would drop it.
  - `-lrt` in `jnoise: LDLIBS += -ljack -lrt` is kept as-is: the OHOS
    toolchain resolves it (see notes.md evidence).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class JnoiseConan(ConanFile):
    name = "jnoise"
    version = "0.6.0"
    package_type = "application"
    description = "jnoise -- command line JACK client generating white and pink noise"
    license = "GPL-2.0-or-later"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/"
    url = "https://kokkinizita.linuxaudio.org/linuxaudio/"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("jnoise supports Linux and OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("jnoise supports OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("jack/1.9.22")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain(self):
        """Return (cxx, source_dir, cflags, ldflags, env_prefix) for build/package."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp") or "clang++"
        source_dir = os.path.join(self.source_folder, "source")
        dep = self.dependencies["jack"]
        include_flags = "-I" + os.path.join(dep.package_folder, "include")
        lib_flags = "-L" + os.path.join(dep.package_folder, "lib")
        # E132: the OHOS SDK lld driver needs libxml2.so.16 from its own
        # llvm/lib; musl ldso does not expand $ORIGIN RUNPATH (E019), so some
        # CI workers cannot load it unless that directory is on LD_LIBRARY_PATH.
        # Keep lld -- binaries linked with GNU ld get Permission denied in the
        # OHOS sandbox.
        env_prefix = ""
        try:
            real = os.path.realpath(cxx)
            llvm_lib = os.path.join(os.path.dirname(os.path.dirname(real)), "lib")
            if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
                env_prefix = 'export LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}"; '.format(llvm_lib)
        except OSError:
            pass
        return cxx, source_dir, include_flags, lib_flags, env_prefix

    def build(self):
        apply_conandata_patches(self)
        cxx, source_dir, include_flags, lib_flags, env_prefix = self._toolchain()
        self.run(
            env_prefix +
            'CPPFLAGS="{}" LDFLAGS="{}" make -C "{}" -j1 PREFIX=/ CXX="{}" jnoise'.format(
                include_flags, lib_flags, source_dir, cxx
            )
        )
        # Upstream ships no check/test target (the Makefile has only
        # all/install/clean), so verification is entirely consumer-side in
        # test_package/.

    def package(self):
        cxx, source_dir, include_flags, lib_flags, env_prefix = self._toolchain()
        self.run(
            env_prefix +
            'make -C "{}" -j1 PREFIX=/ DESTDIR="{}" CXX="{}" install'.format(
                source_dir, self.package_folder, cxx
            )
        )
        self._sign_elf(os.path.join(self.package_folder, "bin", "jnoise"))

    def _sign_elf(self, path):
        """Self-sign the produced ELF; OHOS refuses to execute unsigned binaries."""
        if str(self.settings.os) != "OHOS" or not os.path.isfile(path):
            return
        hnp = "/data/service/hnp/bin"
        signer = shutil.which("binary-sign-tool") or os.path.join(hnp, "binary-sign-tool")
        objcopy = shutil.which("llvm-objcopy") or os.path.join(hnp, "llvm-objcopy")
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; packaged ELF stays unsigned")
            return
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       capture_output=True, timeout=60)
        tmp = path + ".signed"
        proc = subprocess.run([signer, "sign", "-inFile", path, "-outFile", tmp,
                               "-selfSign", "1"], capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and os.path.isfile(tmp):
            shutil.move(tmp, path)
        else:
            if os.path.isfile(tmp):
                os.remove(tmp)
            self.output.warning("self-sign failed: " +
                                (proc.stderr or proc.stdout or "").strip())
        os.chmod(path, 0o755)

    def package_info(self):
        # Application package: consumers run bin/jnoise.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "jnoise")
        self.cpp_info.set_property("cmake_target_name", "jnoise::jnoise")
