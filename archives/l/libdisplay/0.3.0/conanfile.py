#!/usr/bin/env python3
"""Conan recipe — libdisplay 0.3.0 (meson).

EDID and DisplayID library for parsing display metadata.
OHOS adaptation:
- hwdata (pnp.ids) is not packaged in OHOS; a bundled pnp.ids is added by
  the 0002 patch and meson.build falls back to files('pnp.ids') (0001).
- MesonToolchain: c_std c11, wrap_mode nodownload (no subproject fetch),
  ar/ranlib full paths injected into the native file (llvm-ar not on PATH).
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class LibdisplayInfoConan(ConanFile):
    name = "libdisplay"
    version = "0.3.0"
    description = "EDID and DisplayID library for parsing display metadata"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/emersion/libdisplay-info"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def requirements(self):
        # No external library deps; hwdata is a pure data file bundled via patch.
        pass

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["c_std"] = "c11"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_compiler_paths()

    def _inject_compiler_paths(self):
        # Rewrite bare compiler names (c/cpp/ar/ranlib/strip) in the meson
        # native file to absolute paths. The OHOS sandbox cannot exec bare
        # 'clang'/'llvm-ar' via PATH (hmmac posix_spawn restriction), so meson
        # must get absolute paths or configure fails with "Unknown compiler".
        import shutil
        _nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(_nf):
            return
        with open(_nf, encoding="utf-8") as _f:
            _c = _f.read()
        # Map meson key -> (bare name, preferred absolute binary)
        _map = {
            "c": ("clang", shutil.which("clang")),
            "cpp": ("clang++", shutil.which("clang++")),
            "ar": ("llvm-ar", shutil.which("llvm-ar") or shutil.which("ar")),
            "ranlib": ("llvm-ranlib", shutil.which("llvm-ranlib") or shutil.which("ranlib")),
            "strip": ("llvm-strip", shutil.which("llvm-strip") or shutil.which("strip")),
        }
        _changed = False
        for _k, (_bare, _abs) in _map.items():
            if not _abs:
                continue
            _old = "%s = '%s'" % (_k, _bare)
            _new = "%s = '%s'" % (_k, _abs)
            if _old in _c:
                _c = _c.replace(_old, _new)
                _changed = True
        # MesonToolchain only writes c/cpp into [binaries]; ar/ranlib/strip
        # must be appended with absolute paths or meson probes bare names
        # ("Unknown linker(s): llvm-ar") and configure fails in the OHOS
        # sandbox (cannot exec bare names via PATH).
        if "[binaries]" in _c:
            _missing = []
            for _k in ("ar", "ranlib", "strip"):
                if not _map[_k][1]:
                    continue
                if ("%s = " % _k) not in _c:
                    _missing.append("%s = '%s'" % (_k, _map[_k][1]))
            if _missing:
                _c = _c.replace(
                    "[binaries]",
                    "[binaries]\n" + "\n".join(_missing),
                    1,
                )
                _changed = True
        if not _changed and "[binaries]" not in _c:
            # No [binaries] section at all: prepend one with absolute paths
            _ins = "[binaries]\n" + "".join(
                "%s = '%s'\n" % (_k, _map[_k][1])
                for _k in ("c", "cpp", "ar", "ranlib", "strip")
                if _map[_k][1]
            )
            _c = _ins + _c
            _changed = True
        if _changed:
            with open(_nf, "w", encoding="utf-8") as _f:
                _f.write(_c)

    def build(self):
        # 0001 (meson.build pnp.ids fallback) + 0002 (bundled pnp.ids) applied
        # here, before meson.configure(), so the data file is in the source tree.
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # Sign ELF binaries (.so and executables) for HarmonyOS
        targets = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True
        )
        targets += glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True
        )
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run(
                '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                    oc=objcopy, f=f
                )
            )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=f
                )
            )

    def package_info(self):
        self.cpp_info.libs = ["display-info"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "libdisplay-info")
