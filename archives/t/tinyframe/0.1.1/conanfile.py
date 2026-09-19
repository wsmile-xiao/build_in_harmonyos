import os
import shutil
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, collect_libs, copy,
                               export_conandata_patches, get, save)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TinyframeConan(ConanFile):
    name = "tinyframe"
    version = "0.1.1"
    description = "Minimal Frame Streams encoder and decoder library"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/DNS-OARC/tinyframe"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tinyframe supports Linux and OHOS only")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _build_environment(self):
        # The Git tag archive contains configure.ac but not configure.  Its
        # PKG_INSTALLDIR macro is supplied by pkg-config rather than automake,
        # so expose the macro directory without assuming a fixed SDK version.
        pkg_config = shutil.which("pkg-config")
        candidates = []
        if pkg_config:
            candidates.append(Path(pkg_config).resolve().parent.parent /
                              "share" / "aclocal")
        candidates.append(Path("/usr/share/aclocal"))
        macro_dirs = [str(path) for path in candidates
                      if (path / "pkg.m4").is_file()]
        env = Environment()
        if macro_dirs:
            env.define("ACLOCAL_PATH", os.pathsep.join(macro_dirs))
        if self.settings.os == "OHOS":
            # HNP bash runs in a separate HarmonyOS application security
            # domain and cannot resolve a cwd below the Conan cache over a
            # reverse-SSH session.  Autoconf is POSIX-sh compatible.
            env.define_path("SHELL", "/system/bin/sh")
            env.define_path("CONFIG_SHELL", "/system/bin/sh")
            wrapper_dir = Path(self.build_folder) / ".ohos-tools"
            if wrapper_dir.is_dir():
                env.prepend_path("PATH", str(wrapper_dir))
        return env.vars(self)

    def build(self):
        if self.settings.os == "OHOS":
            # Aggregated profile scripts are sourced after recipe-generated
            # scripts.  Append these two values so they remain the final shell
            # selection when Conan starts each Autotools command.
            conanbuild = os.path.join(self.generators_folder, "conanbuild.sh")
            save(self, conanbuild,
                 '\nexport SHELL="/system/bin/sh"\n'
                 'export CONFIG_SHELL="/system/bin/sh"\n', append=True)
            wrapper_dir = Path(self.build_folder) / ".ohos-tools"
            wrapper_dir.mkdir(exist_ok=True)
            mktemp = wrapper_dir / "mktemp"
            save(self, str(mktemp), "#!/system/bin/sh\nexit 1\n")
            mktemp.chmod(mktemp.stat().st_mode | stat.S_IEXEC)
        autotools = Autotools(self)
        # Apply after the profile environment so the OHOS shell override wins.
        with self._build_environment().apply():
            apply_conandata_patches(self)
            if not os.path.isfile(os.path.join(self.source_folder, "configure")):
                autotools.autoreconf()
            autotools.configure()
            autotools.make(args=["-j1"])
            autotools.make(target="check", args=["-j1"])

    def package(self):
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        with self._build_environment().apply():
            Autotools(self).install(args=["-j1"])

    def package_info(self):
        self.cpp_info.libs = collect_libs(self) or ["tinyframe"]
        self.cpp_info.set_property("cmake_file_name", "tinyframe")
        self.cpp_info.set_property("cmake_target_name", "tinyframe::tinyframe")
        self.cpp_info.set_property("pkg_config_name", "libtinyframe")
