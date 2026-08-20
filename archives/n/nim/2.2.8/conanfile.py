from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
import os


class NimConan(ConanFile):
    name = "nim"
    version = "2.2.8"
    description = "Nim programming language compiler"
    license = "MIT"
    homepage = "https://nim-lang.org"
    url = ""

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        # R32: Platform check must include OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"nim is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # Download main Nim source
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download csources_v3 (bootstrap compiler in pure C)
        # git clone hangs on HarmonyOS; use HTTP download via conandata URL instead
        csources = self.conan_data.get("csources", {})
        get(self, **csources, strip_root=True, destination="csources_v3")

    def _get_cc(self):
        # R33: Get CC from Conan conf, no hardcoded paths
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return compilers.get("c", "clang")

    def _get_sdk_lib(self):
        """Derive OHOS SDK lib path from compiler path for LD_LIBRARY_PATH."""
        cc = self._get_cc()
        cc_real = os.path.realpath(cc)
        sdk_lib = os.path.normpath(os.path.join(os.path.dirname(cc_real), "..", "lib"))
        return sdk_lib if os.path.isdir(sdk_lib) else ""

    def build(self):
        apply_conandata_patches(self)
        cc = self._get_cc()
        sdk_lib = self._get_sdk_lib()
        ncpu = os.cpu_count() or 1
        ld_prefix = f'LD_LIBRARY_PATH="{sdk_lib}" ' if sdk_lib else ""

        # 1. Build bootstrap compiler from C sources (already downloaded in source())
        # uos=linux: HarmonyOS 'uname' returns 'HarmonyOS' which doesn't match
        # any Makefile case; override to 'linux' since OHOS is Linux-like.
        self.run(f'{ld_prefix}make -C csources_v3 -j{ncpu} CC="{cc}" uos=linux')

        # 2. Build koch (Nim build tool)
        self.run(f'{ld_prefix}bin/nim c --noNimblePath --skipUserCfg --skipParentCfg --hints:off --cc:clang koch')

        # 3. Build full Nim compiler (self-hosted bootstrap via koch boot)
        self.run(f'{ld_prefix}./koch boot -d:release --skipUserCfg --skipParentCfg --hints:off --cc:clang')

    def package(self):
        # Copy the compiler binary
        copy(self, "nim", src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        # Copy the standard library
        copy(self, "*", src=os.path.join(self.build_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
