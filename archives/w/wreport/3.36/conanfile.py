"""Conan recipe for wreport 3.36 on HarmonyOS PC."""

import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class WreportConan(ConanFile):
    name = "wreport"
    version = "3.36"
    description = "Weather report library for BUFR and CREX data"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ARPA-SIMC/wreport"
    url = "https://github.com/ARPA-SIMC/wreport"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.4.8.1", transitive_headers=True, transitive_libs=True)
        if self.settings.os == "OHOS":
            self.requires("python/3.12.9")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        toolchain = MesonToolchain(self)
        toolchain.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        if self.settings.os == "OHOS":
            python = self.dependencies["python"]
            package = python.package_folder
            executable = os.path.join(package, "bin", "python3")
            header = os.path.join(package, "include", "python3.12", "Python.h")
            library = os.path.join(package, "lib", "libpython3.12.so")
            pkgconfig = os.path.join(
                package, "lib", "pkgconfig", "python-3.12-embed.pc"
            )
            for path in (executable, header, library, pkgconfig):
                if not os.path.isfile(path):
                    raise ConanException(f"Conan Python development file missing: {path}")

            # Meson's interpreter and embed dependency must describe the same
            # relocatable Conan package. The upstream .pc has prefix=/.
            with open(pkgconfig, encoding="utf-8") as stream:
                metadata = stream.read()
            metadata, replacements = re.subn(
                r"(?m)^prefix=/$", f"prefix={package}", metadata, count=1
            )
            if replacements != 1:
                raise ConanException("unexpected Conan Python pkg-config prefix")
            with open(
                os.path.join(self.generators_folder, "python-3.12-embed.pc"),
                "w", encoding="utf-8"
            ) as stream:
                stream.write(metadata)

            libdirs = [os.path.join(package, "lib")]
            for dependency in sorted(self.dependencies.values(), key=lambda dep: str(dep.ref)):
                if not dependency.package_folder:
                    continue
                for entry in dependency.cpp_info.libdirs:
                    if not entry:
                        continue
                    path = entry if os.path.isabs(entry) else os.path.join(
                        dependency.package_folder, entry
                    )
                    if path not in libdirs and os.path.isdir(path):
                        libdirs.append(path)
            wrapper = os.path.join(self.generators_folder, "wreport-python3")
            with open(wrapper, "w", encoding="utf-8", newline="\n") as stream:
                stream.write("#!/bin/sh\n")
                stream.write(f"export PYTHONHOME={shlex.quote(package)}\n")
                stream.write(
                    "export LD_LIBRARY_PATH="
                    f"{shlex.quote(os.pathsep.join(libdirs))}"
                    "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\n"
                )
                stream.write(f"exec {shlex.quote(executable)} \"$@\"\n")
            os.chmod(wrapper, 0o755)
            toolchain.project_options["wreport_python"] = wrapper
        toolchain.generate()

        # Conan's OHOS profile pins clang but not ar. Meson otherwise probes
        # bare "llvm-ar", which is absent from the CI worker's process PATH.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("cpp") or executables.get("c")
        compiler_dir = os.path.dirname(compiler) if compiler else ""
        candidates = [executables.get("ar")]
        candidates.extend(
            os.path.join(compiler_dir, name)
            for name in ("llvm-ar", "ar") if compiler_dir
        )
        if self.settings.os == "OHOS":
            candidates.append("/storage/Users/currentUser/usr/local/bin/llvm-ar")
        candidates.extend((shutil.which("llvm-ar"), shutil.which("ar")))
        ar = next(
            (path for path in candidates if path and os.path.isabs(path)
             and os.path.isfile(path) and os.access(path, os.X_OK)), None
        )
        if ar is None:
            raise ConanException("cannot resolve an executable ar for Meson")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        with open(native_file, encoding="utf-8") as stream:
            content = stream.read()
        if "[binaries]\n" not in content:
            raise ConanException("Meson native file has no [binaries] section")
        if "\nar =" not in content:
            content = content.replace(
                "[binaries]\n", "[binaries]\nar = '%s'\n" % ar, 1
            )
            with open(native_file, "w", encoding="utf-8") as stream:
                stream.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        env = Environment()
        if self.settings.os == "OHOS":
            env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # runtest creates a private scratch directory. OHOS keeps /tmp read-only.
        env.define_path("TMPDIR", self.build_folder)
        with env.vars(self).apply():
            meson.configure()
            meson.build()
            meson.test()

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.libs = ["wreport"]
        self.cpp_info.set_property("pkg_config_name", "libwreport")
        table_dir = os.path.join(self.package_folder, "share", "wreport")
        self.runenv_info.define_path("WREPORT_TABLES", table_dir)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("wreport requires Linux or OHOS")
