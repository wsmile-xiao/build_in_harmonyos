#!/usr/bin/env python3
"""Conan recipe — libdisplay-info 0.3.0 (meson).

EDID and DisplayID library for parsing display metadata.
Build-time dependency on hwdata (pnp.ids) is handled by downloading the
data file during build since hwdata is not available as a conan package.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class LibdisplayInfoConan(ConanFile):
    name = "libdisplay-info"
    version = "0.3.0"
    description = "EDID and DisplayID library for parsing display metadata"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/emersion/libdisplay-info"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def requirements(self):
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
        self._inject_meson_archiver()
        self._setup_hwdata_env()

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

    def _setup_hwdata_env(self):
        # Create hwdata.pc in the generators folder (meson's pkg_config_path)
        # so meson's dependency('hwdata') finds pnp.ids at build time
        hwdata_dir = os.path.join(self.generators_folder, "hwdata")
        os.makedirs(hwdata_dir, exist_ok=True)

        # Create hwdata.pc in generators folder (where meson looks for pkg-config files)
        pc_path = os.path.join(self.generators_folder, "hwdata.pc")
        with open(pc_path, "w") as f:
            f.write(
                "prefix={}\n"
                "datadir=${{prefix}}\n"
                "pkgdatadir=${{prefix}}\n\n"
                "Name: hwdata\n"
                "Description: Hardware identification data\n"
                "Version: 0.366\n".format(hwdata_dir)
            )

    def build(self):
        # Download pnp.ids (hwdata is a pure data package, not in conan repo)
        pnp_ids_path = os.path.join(self.generators_folder, "hwdata", "pnp.ids")
        if not os.path.exists(pnp_ids_path):
            import urllib.request
            url = "https://raw.githubusercontent.com/vcrhonek/hwdata/master/pnp.ids"
            try:
                urllib.request.urlretrieve(url, pnp_ids_path)
            except Exception:
                # Fallback: curl with -k (skip SSL for public data file)
                self.run("curl -kfsSL " + url + " -o " + pnp_ids_path)
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
        # Sign ELF binaries (.so and executables) for HarmonyOS XPM
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
