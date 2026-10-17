import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class SordTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualRunEnv(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["buildtype"] = "release"
        tc.generate()
        self._patch_cross_file()

    def _patch_cross_file(self):
        compiler_exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = compiler_exes.get("ar") or "/data/service/hnp/bin/llvm-ar"
        ranlib = compiler_exes.get("ranlib") or "/data/service/hnp/bin/llvm-ranlib"
        pkg_config = self.conf.get("tools.gnu:pkg_config", default="", check_type=str) or ""
        if not pkg_config or not os.path.isfile(pkg_config):
            pkg_config = "/data/service/hnp/bin/pkg-config"

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insertion = "[binaries]\n"
            insertion += "ar = '{0}'\n".format(ar.replace("\\", "/"))
            insertion += "ranlib = '{0}'\n".format(ranlib.replace("\\", "/"))
            if pkg_config and os.path.isfile(pkg_config) and "\npkg-config =" not in content:
                insertion += "pkg-config = '{0}'\n".format(pkg_config.replace("\\", "/"))
            content = content.replace("[binaries]\n", insertion, 1)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        # Under cross-building the produced sordi/test binaries cannot run on the
        # build host, so skip all execution (this matches the main recipe, which
        # also guards meson.test() with cross_building()). On a native build
        # (CI runner is OHOS; or a pure-native local build) the binaries run for
        # real and we exercise them below.
        if cross_building(self):
            self.output.info("cross-building: skip test_package execution")
            return

        meson = Meson(self)
        meson.test()

        # Activate the Conan run environment (VirtualRunEnv) so libzix-0.so.0 /
        # libserd-0.so.0 resolve (explicit self.run under conanrun, not implicit
        # CTest). Run the sordi CLI end-to-end on the produced package.
        run_env = VirtualRunEnv(self).vars()
        package_folder = self.dependencies["sord"].package_folder
        sordi = os.path.join(package_folder, "bin", "sordi")
        sample = os.path.join(self.source_folder, "sample.ttl")
        output = os.path.join(self.build_folder, "sample.nt")
        self.run(f'"{sordi}" -i turtle -o ntriples "{sample}" > "{output}"', env="conanrun")
        with open(output, "r", encoding="utf-8") as handle:
            data = handle.read()
        if "http://example.org/s" not in data or "hello" not in data:
            raise RuntimeError("sordi did not convert sample Turtle input as expected")
