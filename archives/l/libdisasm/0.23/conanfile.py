#!/usr/bin/env python3
"""Conan recipe for the libdisasm x86 disassembler library and x86dis CLI."""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibdisasmConan(ConanFile):
    name = "libdisasm"
    version = "0.23"
    description = "x86 disassembler library and x86dis command-line disassembler"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/bastard/"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libdisasm is supported only on Linux/OHOS")
        if self.settings.arch != "armv8" and self.settings.os == "OHOS":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_configure_args(self):
        # The bundled config.sub predates aarch64 and the 2003-era
        # configure misbehaves in cross mode; pass matching native-style
        # triples so the OHOS clang driver is used as a "native" build.
        if str(self.settings.os) == "OHOS":
            return ["--build=aarch64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-gnu"]
        return []

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._ohos_configure_args())
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Autotools.configure() execs ./configure directly, but HMDFS-backed
        # Conan homes deny direct exec of scripts (conan Error 126; neither
        # chmod nor creation mode can grant the exec bit there). Invoke the
        # script through the shell instead -- identical to upstream's
        # documented `sh ./configure` and harmless on CI workers.
        tc = AutotoolsToolchain(self)
        configure_args = tc.configure_args + self._ohos_configure_args()
        self.run('sh "{}" {}'.format(os.path.join(self.source_folder, "configure"),
                                     " ".join(configure_args)))
        autotools = Autotools(self)
        autotools.make(args=["-j1"])
        # The upstream `make check` suite (test/run-test.sh) round-trips every
        # instruction in ia32_test_insn.S through GNU `as --32` + `objdump` +
        # perl; those host-only x86 tools do not exist on the OHOS target, so
        # the check target is not run here. test_package exercises the library
        # API and the x86dis binary instead.

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Conan 2 copy() has no delete= argument; remove libtool *.la wrappers manually.
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["disasm"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
