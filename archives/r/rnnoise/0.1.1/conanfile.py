#!/usr/bin/env python3
"""Conan recipe — rnnoise 0.1.1 (RNN-based noise suppression library, C).

rnnoise is an Autotools (configure/make) project. It builds the static/shared
librnnoise plus an example demo program (example only, not installed as library
headers/objects of the package contract uses include/rnnoise.h).

R-notes: No runtime dependencies beyond libm. The recipe uses
AutotoolsToolchain, which maps os=OHOS to the HarmonyOS target via the
OHOS-adapted conan; pass the explicit --host for aarch64-linux-ohos so
config.guess/lt_cv produce a valid aarch64 host triple.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RnnoiseConan(ConanFile):
    name = "rnnoise"
    version = "0.1.1"
    description = "RNNoise - noise suppression library based on a recurrent neural network"
    license = "BSD-3-Clause"
    homepage = "https://gitlab.xiph.org/xiph/rnnoise"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("rnnoise is supported only on Linux/OHOS")
        if self.settings.arch != "armv8" and self.settings.os == "OHOS":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # The v0.1.1 tarball ships no generated configure/aclocal.m4, so the
        # build must bootstrap with autoreconf. The sandbox only has the
        # autoconf family under /data/service/hnp/bin (no automake/libtool),
        # so pull them via tool_requires (same precedent as
        # abiword-plugin-docbook: automake/1.18 + libtool/2.5.4 published in
        # the ohpcd artifact registry).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--host=aarch64-unknown-linux-gnu",
                "--build=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The v0.1.1 tarball ships configure.ac/Makefile.am only; bootstrap the
        # generated configure/Makefile.in with autoreconf before configuring.
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")

        if self.settings.os == "OHOS":
            # E114 (same as libgsf/abiword-plugin-docbook): the OHOS security
            # framework blocks script subprocesses from creating temp dirs and
            # writing files there (config.status: ./confXXXXXX/subs1.awk:
            # Permission denied). Pre-create a writable dir, point TMPDIR at it,
            # and repoint configure's internal ac_tmp there; also stop the trap
            # from deleting the pre-created dir at exit.
            import tempfile
            fixed_tmp = os.path.join(self.build_folder, "configure-ac-tmp")
            os.makedirs(fixed_tmp, exist_ok=True)
            os.environ["TMPDIR"] = fixed_tmp
            _cfg_path = os.path.join(self.source_folder, "configure")
            if os.path.exists(_cfg_path):
                with open(_cfg_path, "r", encoding="utf-8") as _f:
                    _cfg = _f.read()
                if "ac_tmp=$tmp" not in _cfg:
                    raise ConanException(
                        "E114: ac_tmp=$tmp pattern not found in configure; "
                        "autoconf may have changed the template")
                _cfg = _cfg.replace("ac_tmp=$tmp", "ac_tmp={}".format(fixed_tmp))
                _old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
                _new_trap = 'exit $exit_status'
                if _old_trap in _cfg:
                    _cfg = _cfg.replace(_old_trap, _new_trap)
                with open(_cfg_path, "w", encoding="utf-8") as _f:
                    _f.write(_cfg)
                os.chmod(_cfg_path, 0o755)
                self.output.info("  [ok] Patched configure: ac_tmp -> {} + TMPDIR (HMDFS)".format(fixed_tmp))

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)
        # The example binary is a build artifact, not part of the library package.
        copy(self, "rnnoise.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["rnnoise"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("pkg_config_name", "rnnoise")