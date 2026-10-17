#!/usr/bin/env python3
"""Conan recipe for libuuid 2.40.4 (Autotools) — libuuid from util-linux."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibuuidConan(ConanFile):
    name = "libuuid"
    version = "2.40.4"
    description = "Universally unique identifier library from util-linux"
    license = "BSD-3-Clause"
    homepage = "https://www.kernel.org/pub/linux/utils/util-linux/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if self.options.shared:
            raise ConanInvalidConfiguration("libuuid is packaged as a static library")
        self._gnu_triplet()

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _prepare_autotools_env(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "")
        bindir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        toolchain_awk = ""
        if bindir:
            for name in ("gawk", "awk"):
                candidate = os.path.join(bindir, name)
                if os.path.exists(candidate):
                    toolchain_awk = candidate
                    break
        awk = toolchain_awk or shutil.which("gawk") or shutil.which("awk")
        if not awk:
            raise ConanInvalidConfiguration("An awk implementation is required")
        os.environ["AWK"] = awk
        os.environ["ac_cv_prog_AWK"] = awk
        return awk

    def _gnu_triplet(self, arch=None):
        arch = str(arch or self.settings.arch)
        arch_triplets = {
            "armv8": "aarch64-unknown-linux-gnu",
            "armv8.3": "aarch64-unknown-linux-gnu",
            "aarch64": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-unknown-linux-gnu",
        }
        triplet = arch_triplets.get(arch)
        if not triplet:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return triplet

    def generate(self):
        awk = self._prepare_autotools_env()
        host_triplet = self._gnu_triplet()
        build_arch = self.settings_build.get_safe("arch") if self.settings_build else None
        build_triplet = self._gnu_triplet(build_arch or self.settings.arch)
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"AWK={awk}",
            f"ac_cv_prog_AWK={awk}",
            f"--build={build_triplet}",
            f"--host={host_triplet}",
            "--disable-all-programs",
            "--enable-libuuid",
            "--without-python",
            "--disable-makeinstall-chown",
            "--disable-makeinstall-setuid",
            "--enable-static",
            "--disable-shared",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._prepare_autotools_env()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="test_uuid_parser", args=["-j1"])
        if can_run(self):
            self.run(os.path.join(self.build_folder, "test_uuid_parser"))
        else:
            self.output.info("Skipping test_uuid_parser run: cannot run target binaries in this context")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=f"{self.package_folder}/licenses", keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["uuid"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "uuid")
        self.cpp_info.set_property("cmake_file_name", "uuid")
        self.cpp_info.set_property("cmake_target_name", "uuid::uuid")