#!/usr/bin/env python3
"""Conan recipe for libUEMF 0.2.8 — portable C99 EMF/EMF+/WMF metafile library.

libUEMF reads, writes and prints Enhanced Metafile (EMF), EMF+ (PMF) and
Windows Metafile (WMF) files.  The OHOS package ships:

  * libuemf.so.0.0.3 — the shared C library behind the 10 public headers
  * bin/             — 8 upstream command line tools (reademf, readwmf,
                       cutemf, pmfdual2single and the 4 testbed programs),
                       declared in archives/l/libuemf/commands.json (R38)

build() also runs the upstream reference suite (testit.sh equivalent): the
testbed programs regenerate the metafiles whose reference copies ship in the
source tree and reademf/readwmf dumps are compared against the shipped
*_ref* files — 16 comparisons in total.  testit.sh itself cannot run on
OHOS because it needs the drm_tools programs extract/execinput.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibuemfConan(ConanFile):
    name = "libuemf"
    version = "0.2.8"
    description = "Portable C99 library to read, write and print EMF, EMF+ and WMF metafiles"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/mathog/libUEMF"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # libuemf is not a system library name on OHOS; ship the shared library
    # and let Conan manage the runtime dependency (R26).
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._materialize_source_symlinks()

    def _materialize_source_symlinks(self):
        """The upstream tarball ships the top-level headers as relative
        symlinks into include/ (e.g. uemf.h -> include/uemf.h).  They resolve
        inside the source tree so the build succeeds, but cmake.install()
        preserves them and leaves the packaged include/ with dangling links
        (the test_package consumer then cannot find uemf.h).  Replace every
        file symlink in the source tree with a real copy of its in-tree
        target; the content stays byte-identical."""
        for root, _, files in os.walk(self.source_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path):
                    real = os.path.realpath(path)
                    if os.path.isfile(real):
                        os.unlink(path)
                        shutil.copy2(real, path)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._upstream_reference_suite()

    def _compare_bytes(self, outdir, produced, reference):
        """Byte-exact comparison of a regenerated file against its reference."""
        produced_path = os.path.join(outdir, produced)
        reference_path = os.path.join(self.source_folder, reference)
        self.run(f'cmp -s "{produced_path}" "{reference_path}"')

    def _compare_dump(self, outdir, produced, reference):
        """Compare a reademf/readwmf text dump against its reference.

        Byte-exact cmp first.  If that differs, retry both sides normalized
        for printf sign-extension: plain char is unsigned on aarch64 (OHOS),
        so a byte 0x80 prints as `80`, while the x86-generated reference has
        `FFFFFF80`.  Collapsing `FFFFFFxx` -> `xx` in the dump's hex tokens
        is semantics-preserving and still fails on any real content change.
        """
        produced_path = os.path.join(outdir, produced)
        reference_path = os.path.join(self.source_folder, reference)
        norm = 'sed "s/FFFFFF\\([0-9A-F][0-9A-F]\\)/\\1/g"'
        self.run(
            f'cmp -s "{produced_path}" "{reference_path}" '
            f'|| {{ {norm} "{reference_path}" > "{reference_path}.norm" && '
            f'{norm} "{produced_path}" | cmp -s - "{reference_path}.norm"; }}'
        )

    def _upstream_reference_suite(self):
        """Regenerate the reference metafiles and compare (testit.sh, 16 checks).

        testit.sh needs drm_tools (extract/execinput) which OHOS does not
        ship, so the generation steps are driven directly.  Every command
        cds into the build folder and carries LD_LIBRARY_PATH explicitly:
        the conanbuild environment points it at the OHOS SDK llvm/lib
        instead of the build tree (testit.sh did the same with one export),
        and conan invokes build() with the caller's working directory.  Text
        dumps fall back to a sign-extension-normalized comparison (see
        _compare_dump).
        """
        bindir = os.path.abspath(self.cpp.build.bindirs[0])
        outdir = bindir
        # Run every generation/dump step with an explicit in-shell `cd`: conan
        # invokes build() with the caller's working directory (the project
        # root for the G2 clean rebuild), so a Python-level chdir is not
        # enough to keep the generated metafiles inside the build folder.
        pre = f'cd "{bindir}" && LD_LIBRARY_PATH="{bindir}"'
        self.run(f'{pre} "{bindir}/testbed_emf" 4 >/dev/null')
        self.run(f'cd "{bindir}" && mv test_libuemf.emf test_libuemf30.emf')
        self.run(f'{pre} "{bindir}/testbed_emf" 0 >/dev/null')
        self.run(f'cd "{bindir}" && {pre} "{bindir}/reademf" test_libuemf.emf >test_libuemf_emf.txt')
        self.run(f'cd "{bindir}" && {pre} "{bindir}/reademf" test_libuemf30.emf >test_libuemf30_emf.txt')
        self.run(f'{pre} "{bindir}/testbed_wmf" 0 >/dev/null')
        self.run(f'cd "{bindir}" && {pre} "{bindir}/readwmf" test_libuemf.wmf >test_libuemf_wmf.txt')
        self.run(f'{pre} "{bindir}/test_mapmodes_emf" -vX 2000 -vY 1000 >/dev/null')
        self.run(f'{pre} "{bindir}/testbed_pmf" 0 >/dev/null')
        self.run(f'cd "{bindir}" && {pre} "{bindir}/reademf" test_libuemf_p.emf >test_libuemf_p_emf.txt')
        self._compare_bytes(outdir, "test_libuemf.emf", "test_libuemf_ref.emf")
        self._compare_bytes(outdir, "test_libuemf30.emf", "test_libuemf_ref30.emf")
        self._compare_dump(outdir, "test_libuemf_emf.txt", "test_libuemf_ref_emf.txt")
        self._compare_dump(outdir, "test_libuemf30_emf.txt", "test_libuemf_ref30_emf.txt")
        self._compare_bytes(outdir, "test_libuemf.wmf", "test_libuemf_ref.wmf")
        self._compare_dump(outdir, "test_libuemf_wmf.txt", "test_libuemf_ref_wmf.txt")
        self._compare_bytes(outdir, "test_libuemf_p.emf", "test_libuemf_p_ref.emf")
        self._compare_dump(outdir, "test_libuemf_p_emf.txt", "test_libuemf_p_ref_emf.txt")
        for mapmode in ("anisotropic", "hienglish", "himetric", "isotropic",
                        "loenglish", "lometric", "text", "twips"):
            self._compare_bytes(outdir, f"test_mm_{mapmode}.emf", f"test_mm_{mapmode}_ref.emf")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["uemf"]
