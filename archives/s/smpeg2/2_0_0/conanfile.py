#!/usr/bin/env python3
"""Conan recipe for smpeg2 2.0.0."""

import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Smpeg2Conan(ConanFile):
    name = "smpeg2"
    version = "2_0_0"
    description = "SDL2 MPEG audio/video decoding library"
    license = "LGPL-2.0-or-later"
    homepage = "https://icculus.org/smpeg/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        sdl2_config = os.path.join(
            self.dependencies["sdl2"].package_folder, "bin", "sdl2-config"
        ).replace("\\", "/")
        tc.configure_args.extend(["--disable-rpath", "--disable-mmx", f"SDL_CONFIG={sdl2_config}"])
        if str(self.settings.os) == "OHOS":
            triplet = self._ohos_triplet()
            tc.configure_args.extend([f"--build={triplet}", f"--host={triplet}"])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autogen_env = Environment()
        automake = self.dependencies.build["automake"].package_folder
        libtool = self.dependencies.build["libtool"].package_folder
        autogen_env.prepend_path("PATH", os.path.join(automake, "bin"))
        autogen_env.prepend_path("PATH", os.path.join(libtool, "bin"))
        autogen_env.prepend_path("ACLOCAL_PATH", os.path.join(automake, "share", "aclocal"))
        autogen_env.prepend_path(
            "ACLOCAL_PATH", os.path.join(automake, "share", "aclocal-1.18")
        )
        autogen_env.prepend_path("ACLOCAL_PATH", os.path.join(libtool, "share", "aclocal"))
        autogen_env.prepend_path("PERL5LIB", os.path.join(automake, "share", "automake-1.18"))
        autogen_env.define("ACLOCAL", os.path.join(automake, "bin", "aclocal"))
        autogen_env.define("AUTOMAKE", os.path.join(automake, "bin", "automake"))
        with autogen_env.vars(self).apply():
            self.run("sh autogen.sh", cwd=self.source_folder, env="conanbuild")
        self._refresh_gnu_config_scripts(automake)
        if str(self.settings.os) == "OHOS":
            self._patch_ohos_config_helpers()
            self._patch_config_status_temp_permissions()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _ohos_triplet(self):
        arch = str(self.settings.arch)
        arch_map = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "armv8_32": "arm",
            "armv7": "arm",
            "x86_64": "x86_64",
            "x86": "i686",
        }
        return f"{arch_map.get(arch, arch)}-unknown-linux-ohos"

    def _refresh_gnu_config_scripts(self, automake_folder):
        automake_config_dir = os.path.join(automake_folder, "share", "automake-1.18")
        for script in ("config.guess", "config.sub"):
            source = os.path.join(automake_config_dir, script)
            if not os.path.isfile(source):
                raise RuntimeError(f"Missing GNU config helper from automake: {source}")
            destination = os.path.join(self.source_folder, script)
            shutil.copy2(source, destination)
            self.output.info(f"Refreshed {script} from Conan automake package")

    def _patch_ohos_config_helpers(self):
        self._patch_ohos_config_guess()
        self._patch_ohos_config_sub()

    def _patch_config_status_temp_permissions(self):
        configure = os.path.join(self.source_folder, "configure")
        content = load(self, configure)
        old = "umask 077"
        new = "umask 022"
        if old in content:
            save(self, configure, content.replace(old, new))
        elif new not in content:
            raise RuntimeError("config.status umask anchor not found in configure")
        os.chmod(configure, 0o755)

    def _patch_ohos_config_guess(self):
        config_guess = os.path.join(self.source_folder, "config.guess")
        if not os.path.isfile(config_guess):
            return
        content = load(self, config_guess)
        marker = "# Conan OHOS early platform guard"
        if marker not in content:
            block = (
                f"{marker}\n"
                "case \"$(uname -s 2>/dev/null)\" in\n"
                "    HarmonyOS)\n"
                "        case \"$(uname -m 2>/dev/null)\" in\n"
                "            aarch64|arm64) echo aarch64-unknown-linux-ohos ;;\n"
                "            armv7*|armv8*) echo arm-unknown-linux-ohos ;;\n"
                "            x86_64|amd64) echo x86_64-unknown-linux-ohos ;;\n"
                "            i?86) echo i686-unknown-linux-ohos ;;\n"
                "            *) echo \"$(uname -m 2>/dev/null)\"-unknown-linux-ohos ;;\n"
                "        esac\n"
                "        exit 0 ;;\n"
                "esac\n\n"
            )
            first_newline = content.find("\n")
            if first_newline == -1:
                raise RuntimeError("config.guess is unexpectedly empty")
            content = content[: first_newline + 1] + block + content[first_newline + 1 :]
            save(self, config_guess, content)
            self.output.info("Patched config.guess for HarmonyOS")
        os.chmod(config_guess, 0o755)

    def _patch_ohos_config_sub(self):
        config_sub = os.path.join(self.source_folder, "config.sub")
        if not os.path.isfile(config_sub):
            return
        content = load(self, config_sub)
        if "linux-ohos" not in content:
            block = (
                "\ncase \"$1\" in\n"
                "    aarch64-unknown-linux-ohos|arm-unknown-linux-ohos|"
                "x86_64-unknown-linux-ohos|i686-unknown-linux-ohos)\n"
                "        echo \"$1\"\n"
                "        exit ;;\n"
                "esac\n"
            )
            first_newline = content.find("\n")
            if first_newline == -1:
                raise RuntimeError("config.sub is unexpectedly empty")
            content = content[: first_newline + 1] + block + content[first_newline + 1 :]
            save(self, config_sub, content)
            self.output.info("Patched config.sub for linux-ohos")
        os.chmod(config_sub, 0o755)

    def _archiver(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        ar = compiler_executables.get("ar")
        if ar:
            return ar.replace("\\", "/")
        compiler = compiler_executables.get("c") or compiler_executables.get("cpp")
        if compiler:
            for name in ("llvm-ar", "ar"):
                executable = f"{name}.exe" if os.name == "nt" else name
                candidate = os.path.join(os.path.dirname(compiler), executable)
                if os.path.exists(candidate):
                    return candidate.replace("\\", "/")
        return "ar"

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        if not self.options.shared:
            static_lib = os.path.join(self.package_folder, "lib", "libsmpeg2.a")
            if os.path.isfile(static_lib):
                self.output.info(
                    "Removing nested SDL2 static archive from libsmpeg2.a; "
                    "SDL2 remains a transitive Conan requirement"
                )
                self.run(f'"{self._archiver()}" d "{static_lib}" libSDL2.a')
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["smpeg2"]
        self.cpp_info.requires = ["sdl2::sdl2"]
        self.cpp_info.includedirs.append(
            os.path.join(self.dependencies["sdl2"].package_folder, "include", "SDL2")
        )
        self.cpp_info.set_property("cmake_file_name", "smpeg2")
        self.cpp_info.set_property("cmake_target_name", "smpeg2::smpeg2")
        self.cpp_info.set_property("pkg_config_name", "smpeg2")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
