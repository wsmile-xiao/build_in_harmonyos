#!/usr/bin/env python3
"""Conan recipe — fftw 3.3.10.4 (autotools)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout
import os
import glob


class FftwConan(ConanFile):
    name = "fftw"
    version = "3.3.10.4"
    description = "Fastest Fourier Transform in the West"
    license = "GPL-2.0-or-later"
    homepage = "https://www.fftw.org/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def export_sources(self):
        return ["patches/*"]

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # build == host → native path, skips config.guess
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        # Follow options.shared (same rationale as 3.3.10.2 CMake BUILD_SHARED_LIBS)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        # Threads: produce separate libfftw3_threads (matches 3.3.10.2 WITH_COMBINED_THREADS=OFF)
        # pyfftw probes -lfftw3_threads for multi-threading support
        tc.configure_args.append("--enable-threads")
        # No --with-combined-threads: default is separate library (matches CMake OFF)
        # No --enable-openmp: disabled by default (matches 3.3.10.2 ENABLE_OPENMP=OFF)
        # No Fortran compiler on OHOS
        tc.configure_args.append("--disable-fortran")
        # Skip documentation build (not a library feature)
        tc.configure_args.append("--disable-doc")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix umask in configure scripts (OHOS platform issue)
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # Code signing is OHOS-specific. The tools (objcopy, binary-sign-tool)
        # only exist on OHOS devices at /data/service/hnp/bin/.
        # On other profiles (os=Linux) they don't exist → guard with os check.
        # Without signing, dlopen of .so fails with Permission denied on OHOS.
        if self.settings.os != "OHOS":
            return
        # Sign: ① lib/ .so files ② bin/ ELF executables
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):   # Only sign real ELF, skip symlinks
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # Include fftw3_threads (produced by --enable-threads without --with-combined-threads)
        self.cpp_info.libs = ['fftw3', 'fftw3_threads']
        self.cpp_info.set_property("cmake_file_name", "fftw")
        self.cpp_info.set_property("cmake_target_name", "fftw::fftw")
        self.cpp_info.set_property("pkg_config_name", "fftw3")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ['m']

    # ── Include directory detection (ported from 3.3.10.2) ──────────────
    # Avoids issues where public headers are installed in versioned subdirs.
    _STD_HEADER_NAMES = {
        "time.h", "math.h", "string.h", "stdio.h", "stdlib.h", "assert.h",
        "errno.h", "signal.h", "limits.h", "float.h", "locale.h", "setjmp.h",
        "ctype.h", "wchar.h", "wctype.h", "complex.h", "fenv.h", "inttypes.h",
        "stdint.h", "stddef.h", "stdarg.h", "stdbool.h", "iso646.h", "uchar.h",
        "memory", "list", "array", "vector", "string", "map", "set", "queue",
        "stack", "algorithm", "functional", "utility", "thread", "mutex",
        "atomic", "chrono", "ranges", "format", "locale",
    }

    def _detect_include_dirs(self):
        """Scan include/ for subdirectories containing headers, avoiding
        directories with standard header names that could shadow system headers."""
        base = os.path.join(self.package_folder, "include")
        dirs = ["include"]
        if not os.path.isdir(base):
            return dirs
        for name in sorted(os.listdir(base)):
            sub = os.path.join(base, name)
            if not os.path.isdir(sub):
                continue
            try:
                direct = os.listdir(sub)
            except OSError:
                continue
            if any(f in self._STD_HEADER_NAMES for f in direct):
                continue
            for _root, _d, files in os.walk(sub):
                if any(f.endswith((".h", ".hpp", ".hh", ".hxx")) for f in files):
                    dirs.append("include/" + name)
                    break
        return dirs
