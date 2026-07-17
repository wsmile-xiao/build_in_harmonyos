#!/usr/bin/env python3
"""Conan recipe for id3v2 0.1.12 — command-line ID3v1/v2 tag editor.

id3v2 reads, writes and converts ID3 tags in MP3 files. It is a thin C++
command-line tool built on top of id3lib. id3lib is not published to the
artifact registry and is a 2003-era autotools library, so this recipe vendors
id3lib 3.8.3 (second source in conandata.yml, extracted to _id3lib/) and
builds it as a static library as part of the id3v2 build (superbuild).

Build system: id3v2 flat C++ sources + vendored id3lib autotools.
License: LGPL-2.1
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


def _silent_remove(path):
    """Remove a file if it exists, ignoring errors."""
    try:
        os.remove(path)
    except OSError:
        pass


def _stage_id3lib(stage_dir, id3lib_dir):
    """Copy id3lib public headers + the static library into a staging prefix
    so the id3v2 compile can use -I<stage>/include and -L<stage>/lib."""
    inc_dir = os.path.join(stage_dir, "include", "id3")
    lib_dir = os.path.join(stage_dir, "lib")
    os.makedirs(inc_dir, exist_ok=True)
    os.makedirs(lib_dir, exist_ok=True)
    src_inc = os.path.join(id3lib_dir, "include", "id3")
    for name in os.listdir(src_inc):
        src = os.path.join(src_inc, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(inc_dir, name))
    shutil.copy2(os.path.join(id3lib_dir, "src", ".libs", "libid3.a"),
                 os.path.join(lib_dir, "libid3.a"))


def _sign_elf(conan, bin_path):
    """Sign an ELF binary so it is executable on HarmonyOS (no-op where the
    signing tool is absent, e.g. the Linux build container)."""
    sign_tool = "/data/service/hnp/bin/binary-sign-tool"
    objcopy = "/data/service/hnp/bin/llvm-objcopy"
    if not os.path.exists(sign_tool):
        conan.output.info("binary-sign-tool not found, skipping ELF signing")
        return
    subprocess.run([objcopy, "--remove-section", ".codesign", bin_path],
                   capture_output=True, timeout=10)
    tmp = bin_path + ".signed.tmp"
    for _ in range(3):
        r = subprocess.run(
            [sign_tool, "sign", "-inFile", bin_path, "-outFile", tmp, "-selfSign", "1"],
            capture_output=True, timeout=30)
        if r.returncode == 0 and os.path.exists(tmp):
            shutil.move(tmp, bin_path)
            os.chmod(bin_path, 0o755)
            return
    if os.path.exists(tmp):
        os.remove(tmp)
    raise ConanException(
        f"ELF signing failed after 3 attempts for {bin_path}; "
        f"the binary will not be executable on HarmonyOS.")


class Id3v2Conan(ConanFile):
    name = "id3v2"
    version = "0.1.12"
    description = "Command-line ID3v1/v2 tag editor for MP3 files (built on id3lib)"
    license = "LGPL-2.1"
    homepage = "https://id3v2.sourceforge.net/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # id3lib uses zlib for compressed ID3 frames; linked statically into id3v2.
        self.requires("zlib/1.3.1")

    def layout(self):
        # id3v2 ships a flat Makefile; build and generate in the source tree.
        self.folders.build = "."
        self.folders.source = "."
        self.folders.generators = "."

    def validate(self):
        # R32: platform check uses in ("Linux", "OHOS"), never == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"id3v2 requires Linux or OHOS, got {self.settings.os}")

    def source(self):
        srcs = self.conan_data["sources"]
        # id3v2 sources → source root
        get(self, url=srcs[0]["url"], sha256=srcs[0]["sha256"], strip_root=True)
        # vendored id3lib 3.8.3 → _id3lib/
        get(self, url=srcs[1]["url"], sha256=srcs[1]["sha256"],
            destination="_id3lib", strip_root=True)
        # The upstream tarball ships stale pre-built objects and a binary;
        # remove them so the build only ever uses freshly compiled objects.
        for stale in ("convert.o", "list.o", "id3v2.o", "genre.o", "id3v2",
                      "create_map", "create_map.o"):
            _silent_remove(os.path.join(self.source_folder, stale))

    def _build_env(self):
        """Build environment with compiler paths and flags sourced from Conan
        (R33: never from bare shell variables)."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        # compiler.libcxx=libc++ from the profile; the hnp clang has no default
        # C++ header search path, so -stdlib=libc++ is required for both the
        # compile and link stages.
        libcxx = "-stdlib=libc++"
        # id3lib needs zlib headers (configure probe) and the static lib (link).
        zlib_pkg = self.dependencies["zlib"].package_folder
        zlib_inc = os.path.join(zlib_pkg, "include")
        zlib_libdir = os.path.join(zlib_pkg, "lib")
        env = os.environ.copy()
        env.update({
            "CC": cc,
            "CXX": cxx,
            "CXXFLAGS": libcxx,
            "CPPFLAGS": f"-I{zlib_inc}",
            "LDFLAGS": f"{libcxx} -L{zlib_libdir}",
            "CXXCPP": f"{cxx} {libcxx} -I{zlib_inc} -E",
            # id3lib's old libtool is more reliable under /bin/sh.
            "CONFIG_SHELL": "/bin/sh",
            "SHELL": "/bin/sh",
        })
        return cc, cxx, libcxx, zlib_inc, zlib_libdir, env

    def build(self):
        apply_conandata_patches(self)  # patches the vendored id3lib under _id3lib/

        cc, cxx, libcxx, zlib_inc, zlib_libdir, env = self._build_env()
        # Publish the build environment into os.environ so the self.run() calls
        # below (and their configure/make children) inherit it. self.run()'s env
        # arg takes a list of generated env-script names, not a dict; all values
        # here still originate from self.conf / self.dependencies (R33).
        os.environ.update(env)
        id3lib = os.path.join(self.source_folder, "_id3lib")

        # ── Stage 1: build the vendored id3lib as a static library ──
        # The 2003 config.sub only accepts a triplet with a vendor field, and
        # only knows aarch64 via the patched HarmonyOS branch, so pass the
        # triplet explicitly (bypasses config.guess, which fails on aarch64).
        arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
        gnu_arch = arch_map.get(str(self.settings.arch), str(self.settings.arch))
        triplet = f"{gnu_arch}-unknown-linux-ohos"
        stage = os.path.join(self.build_folder, "_stage")
        self.run(
            f"./configure --build={triplet} --host={triplet} "
            f"--disable-shared --enable-static --prefix={stage} "
            f"--disable-cxx-warnings",
            cwd=id3lib)
        # Build only the library (src/); skip examples/id3com whose sources
        # need unrelated C++ modernization and are not used by id3v2.
        self.run("make -j1 -C src", cwd=id3lib)
        _stage_id3lib(stage, id3lib)

        # ── Stage 2: compile id3v2 and link against vendored id3lib ──
        # Manual compile instead of the upstream Makefile: that Makefile links
        # `-lz -lid3` (wrong order for static archives) and defines VERSION via
        # fragile shell quoting. subprocess with an arg list avoids both.
        stage_inc = os.path.join(stage, "include")
        stage_lib = os.path.join(stage, "lib")
        subprocess.run(
            [cxx, libcxx, f"-I{stage_inc}", f'-DVERSION="{self.version}"',
             "-c", "convert.cpp", "list.cpp", "id3v2.cpp", "genre.cpp"],
            check=True, cwd=self.build_folder, env=env)
        # Link order matters for static archives: id3v2 → id3lib → zlib.
        subprocess.run(
            [cxx, libcxx, f"-L{stage_lib}", f"-L{zlib_libdir}", "-o", "id3v2",
             "convert.o", "list.o", "id3v2.o", "genre.o", "-lid3", "-lz"],
            check=True, cwd=self.build_folder, env=env)

    def package(self):
        copy(self, "id3v2", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "id3v2.1", src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        _sign_elf(self, os.path.join(self.package_folder, "bin", "id3v2"))

    def package_info(self):
        # CLI tool — no public library interface; zlib is statically embedded.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
