#!/usr/bin/env python3
"""Conan recipe — libsmacker 1.1.1r35 (a C library for decoding .smk Smacker
Video files) for HarmonyOS PC / aarch64.

Upstream layout
---------------
SourceForge release tarball `libsmacker-1.1.1r35.tar.gz` (top dir
`libsmacker-1.1.1/`) ships a plain autotools build:

    configure.ac   AC_INIT([libsmacker], [1.1.1]) + AC_PROG_LIBTOOL
    Makefile.am    lib_LTLIBRARIES = libsmacker.la + noinst_PROGRAMS driver/smk2avi
    *.c/*.h        smacker.{c,h} smk_bitstream smk_hufftree smk_malloc
    tests/         **does not exist** — `driver.c` / `smk2avi.c` are demo
                   programs, `make check` is automake's empty default target

OHOS adaptations (all in the recipe / one small modified-file patch)
--------------------------------------------------------------------
* `patches/0001-install-header.patch` — upstream `Makefile.am` never installs
  the public header `smacker.h`, so an installed package would be unusable;
  also adds `-no-undefined` to `libsmacker_la_LDFLAGS` for shared builds.
  (Same fix as the Conan Center recipe for this package.)
* `build_requirements()` pulls `automake/1.18` + `libtool/2.5.4` — the
  release tarball ships no `configure`, so `build()` must bootstrap with
  `autoreconf -fi`, and `AC_PROG_LIBTOOL` needs `libtoolize`.  The device /
  CI image has only the autoconf family under /data/service/hnp/bin.
  (device-facts.md §一.4: harmonybrew's automake is *not* on the worker PATH.)
* `--build`/`--host` are passed explicitly: `config.guess` cannot identify
  `uname -s = HarmonyOS` and its compiler probe cannot create its temp dir
  on HMDFS, so the probe is bypassed; `config.sub` accepts
  `aarch64-unknown-linux-ohos`.
* After `autoreconf -fi` the generated `configure` is normalised from
  `umask 077 && mktemp -d` to `umask 022 && mkdir -p` (HMDFS turns a 0700
  directory into an unwritable `drwx--S---`, which aborts `config.status`
  with "could not setup config files machinery").  Standard fix for this
  family, applied in `build()` so the upstream tarball itself is untouched.
* `build()` runs the upstream demo program `driver` end-to-end against a
  synthesised .smk and asserts on the produced BMP — the demo is *not*
  a test target upstream, so this is adaptation-side evidence, not an
  upstream test case.

Dependency surface: **zero runtime requirements** (only libc).
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# config.guess cannot probe HarmonyOS, so both triplets are stated explicitly.
# config.sub accepts the *-linux-ohos form (verified on the device).
TRIPLET = "aarch64-unknown-linux-ohos"

# Upstream demo geometry of the synthesised clip (must match
# test_package/gen_smk.py: 8x8, 1 frame, solid colour 0x20).
DEMO_W, DEMO_H, DEMO_COLOR = 8, 8, 0x20
# driver.c dump_bmp() header: 14 (BITMAPFILEHEADER) + 40 (INFOHEADER) +
# 256 * 4 (palette) = 1078 bytes, plus one byte per pixel.
BMP_HEADER = 1078


def _prepare_autotools_env():
    """The installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed that do not exist in this environment.  Point the
    env vars at whatever is actually on PATH."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _fix_umask_077(path):
    """E114 family: HMDFS directories are created 2700 (setgid) and are not
    writable by their own owner, so `umask 077 && mktemp -d` produces a temp
    dir that config.status cannot write into.  Rewrite the two occurrences in
    the generated configure (and, through its embedded template, in
    config.status).  Prints hit/residual counts so a silent no-op is visible.
    """
    with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
        data = f.read()
    pairs = [
        ('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
         'tmp=`(umask 022 && mkdir -p "./confXXXXXX") 2>/dev/null`'),
        ('(umask 077 && mkdir "$tmp")',
         '(umask 022 && mkdir -p "$tmp")'),
    ]
    hits = 0
    for old, new in pairs:
        hits += data.count(old)
        data = data.replace(old, new)
    residual = data.count("umask 077")
    self_output = "[umask-fix] targets=%d residual_umask077=%d file=%s" % (
        hits, residual, path)
    print(self_output)
    if hits != 2 or residual != 0:
        raise ConanException(
            "umask 077 normalisation did not apply as expected "
            "(targets=%d residual=%d) - refusing to continue with a silent "
            "no-op fix" % (hits, residual))
    with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
        f.write(data)


class LibsmackerConan(ConanFile):
    name = "libsmacker"
    version = "1.1.1r35"
    description = "A C library for decoding .smk Smacker Video files"
    license = "LGPL-2.1-or-later"
    homepage = "http://libsmacker.sourceforge.net"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)
        # test_package/gen_smk.py doubles as the input generator for the
        # upstream `driver` demo check in build(); export it as source so it
        # is present in the source folder during `conan create`.
        copy(self, "*", src=os.path.join(self.recipe_folder, "test_package"),
             dst=os.path.join(self.export_sources_folder, "test_package"))

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libsmacker is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        # zero runtime dependencies: only libc is used by the upstream
        # sources (see the #include inventory in notes.md).
        pass

    def build_requirements(self):
        # The release tarball ships no `configure`, so build() runs
        # `autoreconf -fi`; AC_PROG_LIBTOOL additionally needs libtoolize.
        # The device / CI image only ships the autoconf family.
        # tool_requires are resolved with the *build* profile, so both
        # -pr:h and -pr:b must be passed to conan create.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess fails on HarmonyOS (uname = HarmonyOS, and its temp
        # dir probe cannot write on HMDFS) => state the triplets explicitly
        # so configure never runs the probe.
        tc.configure_args.append("--build=%s" % TRIPLET)
        tc.configure_args.append("--host=%s" % TRIPLET)
        # R26 / template default: deliver a static library unless the
        # consumer flips the `shared` option.
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # No `configure` in the tarball: bootstrap it.
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        _fix_umask_077(os.path.join(self.source_folder, "configure"))

        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits the HMDFS jobserver fifo
        autotools.make(args=["-j1"])

        self._check_upstream_demo()

    def _check_upstream_demo(self):
        """Run the upstream `driver` demo (driver.c) end to end against a
        synthesised .smk and assert on the produced BMP.  This is
        *adaptation-side* evidence that the delivered library really decodes
        frames on OHOS; upstream itself has no test target.
        """
        gen = os.path.join(self.source_folder, "test_package", "gen_smk.py")
        if not os.path.isfile(gen):
            raise ConanException("gen_smk.py missing from source folder: %s"
                                 % gen)
        sys.path.insert(0, os.path.dirname(gen))
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("gen_smk", gen)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            smk_bytes = mod.build_smk()
        finally:
            sys.path.pop(0)
        smk_path = os.path.join(self.build_folder, "demo.smk")
        with open(smk_path, "wb") as fh:
            fh.write(smk_bytes)
        print("[demo-check] wrote %s (%d bytes)" % (smk_path, len(smk_bytes)))

        # driver.c writes bmp/out_%04u.bmp relative to cwd and returns 0.
        self.run("mkdir -p bmp && ./driver demo.smk", cwd=self.build_folder,
                 env="conanbuild")

        bmp_path = os.path.join(self.build_folder, "bmp", "out_0000.bmp")
        if not os.path.isfile(bmp_path):
            raise ConanException("driver produced no BMP at %s" % bmp_path)
        with open(bmp_path, "rb") as fh:
            bmp = fh.read()
        expect_size = BMP_HEADER + DEMO_W * DEMO_H
        if bmp[:2] != b"BM":
            raise ConanException("BMP magic mismatch: %r" % bmp[:2])
        if len(bmp) != expect_size:
            raise ConanException("BMP size %d != expected %d"
                                 % (len(bmp), expect_size))
        # 8bpp palette BMP: pixel rows are appended after the 1078-byte
        # header, bottom-up; every pixel must be the solid colour we encoded.
        pixels = bmp[BMP_HEADER:]
        wrong = sum(1 for b in pixels if b != DEMO_COLOR)
        if wrong:
            raise ConanException("%d/%d pixels are not 0x%02x"
                                 % (wrong, len(pixels), DEMO_COLOR))
        print("[demo-check] OK magic=BM size=%d pixels=%d colour=0x%02x"
              % (len(bmp), len(pixels), DEMO_COLOR))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Conan 2 copy() has no delete= argument; drop libtool *.la wrappers.
        for name in os.listdir(os.path.join(self.package_folder, "lib")):
            if name.endswith(".la"):
                os.remove(os.path.join(self.package_folder, "lib", name))

    def package_info(self):
        self.cpp_info.libs = ["smacker"]
