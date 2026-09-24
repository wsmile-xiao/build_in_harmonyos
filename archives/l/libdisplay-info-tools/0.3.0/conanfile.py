#!/usr/bin/env python3
"""Conan recipe - libdisplay-info-tools 0.3.0 (EDID decode CLI: di-edid-decode).

Upstream: https://gitlab.freedesktop.org/emersion/libdisplay-info (tag 0.3.0)

This package ships only the upstream command line tool `di-edid-decode`
(parse an EDID blob and print a human readable report).  The parsing
library itself belongs to the separate `libdisplay-info` package, so this
recipe links it statically and then trims the install tree down to bin/:
libdisplay-info.a, the public headers and the pkg-config file never appear
in two packages at once.

Upstream 0.3.0 has no meson_options.txt, so the CLI cannot be switched on
or off from the command line at all.  What it does get wrong for a
distribution is its command line contract: di-edid-decode only knows
-h/--help and returns -1 from both the -h and the unknown-option paths,
so neither `--version` nor `--help` can exit 0.  Patch 0001 adds a
--version flag fed from meson.project_version() and lets --help exit 0,
which is what the packaging smoke test (and every init script) expects.

Build-time dependency on hwdata (pnp.ids) is handled by shipping the data
file with this recipe (data/pnp.ids) and pointing upstream's meson fallback
at it (patch 0002).  hwdata is a pure data package: no conan recipe exists
for it, and the OHOS device has neither a hwdata pkg-config file nor the
hardcoded /usr/share/hwdata/pnp.ids that upstream falls back to, so meson
aborts at configure time unless the fallback is redirected.

Patch 0003 fixes a latent upstream bug that newer hwdata data files trigger:
tool/gen-search-table.py unpacks every pnp.ids line into (id, name) and dies
with ValueError on the bare "MV" line, which carries an ID but no name.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.meson import Meson, MesonToolchain


class LibdisplayInfoToolsConan(ConanFile):
    name = "libdisplay-info-tools"
    version = "0.3.0"
    description = ("Command line tools for libdisplay-info - decode EDID and "
                   "DisplayID blobs")
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/emersion/libdisplay-info"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # hwdata is a pure data package with no conan recipe, so the single
        # file upstream needs (pnp.ids, consumed by tool/gen-search-table.py)
        # travels with the recipe.  Downloading it during build() was the only
        # networked step of this recipe and it made `conan create` stall for the
        # whole job timeout whenever raw.githubusercontent.com was unreachable.
        copy(self, "data/pnp.ids", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libdisplay-info-tools supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        # meson refuses to configure when the source and build directories are
        # the same, so keep the upstream tree at the root and build in build/.
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        self._stage_pnp_ids()

    def _stage_pnp_ids(self):
        # tool/gen-search-table.py is driven by a meson custom_target and reads
        # pnp.ids from data/pnp.ids once patch 0002 has redirected upstream's
        # fallback (the hardcoded /usr/share/hwdata/pnp.ids does not exist on
        # the OHOS device).  hwdata has no conan recipe, so the file travels
        # with this recipe - see export_sources().
        #
        # Where the exported file ends up depends on the Conan version: 2.30
        # materialises export_sources inside the source tree
        # (export_sources_folder == source_folder, so copying from one to the
        # other raises "copy() 'src' and 'dst' arguments must have different
        # values"), older releases keep the two folders apart.
        dst_dir = os.path.join(self.source_folder, "data")
        if os.path.isfile(os.path.join(dst_dir, "pnp.ids")):
            return
        for candidate in (os.path.join(self.export_sources_folder, "data"),
                          os.path.join(self.recipe_folder, "data")):
            if not os.path.isfile(os.path.join(candidate, "pnp.ids")):
                continue
            if os.path.normpath(candidate) != os.path.normpath(dst_dir):
                copy(self, "pnp.ids", src=candidate, dst=dst_dir)
            return
        raise ConanException(
            "data/pnp.ids is missing - it ships with this recipe, see "
            "export_sources()"
        )

    def generate(self):
        tc = MesonToolchain(self)
        # Static library only: the resulting CLI then needs nothing but libc
        # and libm at runtime, and this package never ships a .so that would
        # collide with the libdisplay-info package.
        tc.project_options["default_library"] = "static"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_archiver()

    def _inject_meson_archiver(self):
        # Inject ar/ranlib full paths into conan_meson_native.ini
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar, _rl = _ce.get("ar"), _ce.get("ranlib")
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
            if _bindir:
                _cand = os.path.join(_bindir, "llvm-ar")
                if os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = os.path.join(_bindir, "llvm-ranlib")
                    if os.path.isfile(_rlc):
                        _rl = _rlc
        _nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not (_ar and os.path.isfile(_nf)):
            return
        with open(_nf, encoding="utf-8") as _f:
            _c = _f.read()
        if "\nar =" in _c or "[binaries]" not in _c:
            return
        _ins = "[binaries]\nar = '%s'\n" % _ar
        if _rl:
            _ins += "ranlib = '%s'\n" % _rl
        with open(_nf, "w", encoding="utf-8") as _f:
            _f.write(_c.replace("[binaries]\n", _ins, 1))

    def build(self):
        # pnp.ids is consumed by tool/gen-search-table.py to generate
        # pnp-id-table.c during the build.  It ships with the recipe and is
        # staged by source(); downloading it here turned this recipe into the
        # only one that needed the network at build time, and whenever
        # raw.githubusercontent.com was unreachable conan create stalled until
        # the whole job timed out (curl: (28) timed out after 60001 ms).
        pnp_ids_path = os.path.join(self.source_folder, "data", "pnp.ids")
        if not os.path.isfile(pnp_ids_path):
            raise ConanException(
                "pnp.ids is missing from the source folder - it ships with "
                "the recipe, see export_sources()/source()"
            )
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # Tools-only package: meson.install() also emits the static library,
        # the public headers and the pkg-config metadata.  Those belong to the
        # libdisplay-info package - drop them so the two can never collide.
        for name in ("include", "lib", "share"):
            path = os.path.join(self.package_folder, name)
            if os.path.isdir(path):
                rmdir(self, path)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS only loads ELF binaries that carry a valid .codesign
        # section; llvm-objcopy/binary-sign-tool ship in the OHOS SDK.
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            if not self._is_elf(path):
                continue
            self.run(
                '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                    oc=objcopy, f=path
                )
            )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=path
                )
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = []
        self.cpp_info.libs = []