"""Conan recipe for libtwin's native HarmonyOS PC build."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibtwinConan(ConanFile):
    name = "libtwin"
    version = "13.05.03.15.06-g287d16c"
    description = "Small software-rendered window system and pixmap library"
    license = "LGPL-2.0-or-later"
    homepage = "https://git.kernel.org/pub/scm/linux/kernel/git/geoff/libtwin.git"
    url = homepage
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        public = {"transitive_headers": True, "transitive_libs": True}
        self.requires("libpng/1.6.58.2", **public)
        self.requires("libjpeg-turbo/3.2.0", **public)
        self.requires("zlib/1.3.2", **public)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append(
            "--disable-static" if self.options.shared else "--disable-shared"
        )
        if self.settings.os == "OHOS":
            toolchain.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
                "--disable-x11",
                "--disable-fbdev",
                "--disable-linux-mouse",
                "--disable-linux-joystick",
                "--disable-linux-touchscreen",
                "--disable-twin-ttf",
                "--disable-altivec",
            ])
        toolchain.generate()

    def _native_env(self):
        env = Environment()
        env.define_path("TMPDIR", self.build_folder)
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        compiler_conf = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        tool_dir = os.path.dirname(compiler_conf.get("c", ""))
        if tool_dir:
            env.prepend_path("PATH", tool_dir)
            for variable, executable in {
                "AR": "llvm-ar",
                "RANLIB": "llvm-ranlib",
                "NM": "llvm-nm",
                "STRIP": "llvm-strip",
            }.items():
                path = os.path.join(tool_dir, executable)
                if os.path.isfile(path):
                    env.define_path(variable, path)
        for dependency in self.dependencies.host.values():
            for include_dir in dependency.cpp_info.includedirs:
                env.append("CPPFLAGS", f"-I{include_dir}")
            for library_dir in dependency.cpp_info.libdirs:
                env.append("LDFLAGS", f"-L{library_dir}")
        return env

    def build(self):
        apply_conandata_patches(self)
        os.makedirs(self.build_folder, exist_ok=True)
        with self._native_env().vars(self).apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()
            # The upstream release has no check_PROGRAMS/TESTS; keep make check
            # visible while the consumer test supplies real API validation.
            autotools.make(target="check")

    def package(self):
        with self._native_env().vars(self).apply():
            Autotools(self).install()
        libtool_archive = os.path.join(self.package_folder, "lib", "libtwin.la")
        if os.path.isfile(libtool_archive):
            os.unlink(libtool_archive)

    def package_info(self):
        self.cpp_info.libs = ["twin"]

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libtwin requires Linux or OHOS")
