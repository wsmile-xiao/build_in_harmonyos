#!/usr/bin/env python3
"""Conan recipe for mcrypt 2.6.8."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class McryptConan(ConanFile):
    name = "mcrypt"
    version = "2.6.8"
    description = "Command-line file encryption utility using libmcrypt"
    license = "GPL-3.0-or-later"
    homepage = "https://mcrypt.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libmcrypt/2.5.8")
        self.requires("mhash/0.9.9.9")
        self.requires("zlib/1.3.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mcrypt requires a POSIX target with libmcrypt/mhash")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._remove_stale_configure_outputs()

    def generate(self):
        tc = AutotoolsToolchain(self)
        prefix = os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))

        tc.configure_args.extend([
            "--prefix=/",
            "--disable-nls",
            "--disable-rpath",
            "--enable-static-link",
        ])
        for include_dir in self._dependency_dirs("include"):
            tc.extra_cflags.append(f"-I{include_dir}")
        for lib_dir in self._dependency_dirs("lib"):
            tc.extra_ldflags.append(f"-L{lib_dir}")
        tc.extra_cflags.append(f"-I{os.path.join(prefix, 'include')}")
        tc.extra_ldflags.append(f"-L{os.path.join(prefix, 'lib')}")
        if str(self.settings.os) == "OHOS":
            tc.extra_ldflags.append("-static")
        tc.generate()

        env = Environment()
        env.prepend_path("PATH", os.path.join(prefix, "bin"))
        for variable, tool in {
            "AR": "llvm-ar",
            "RANLIB": "llvm-ranlib",
            "NM": "llvm-nm",
            "LD": "ld.lld",
            "STRIP": "llvm-strip",
        }.items():
            tool_path = os.path.join(prefix, "bin", tool)
            if os.path.exists(tool_path):
                env.define_path(variable, tool_path)
        for bin_dir in self._dependency_dirs("bin"):
            env.prepend_path("PATH", bin_dir)
        libmcrypt_config = os.path.join(self.dependencies["libmcrypt"].package_folder, "bin", "libmcrypt-config")
        if os.path.exists(libmcrypt_config):
            if str(self.settings.os) == "OHOS":
                libmcrypt_prefix = self.dependencies["libmcrypt"].package_folder
                env.define(
                    "LIBMCRYPT_CONFIG",
                    "/bin/sh {0} --prefix={1}".format(
                        shlex.quote(libmcrypt_config),
                        shlex.quote(libmcrypt_prefix),
                    ),
                )
            else:
                env.define_path("LIBMCRYPT_CONFIG", libmcrypt_config)
        for pkgconfig in self._dependency_dirs(os.path.join("lib", "pkgconfig")):
            env.prepend_path("PKG_CONFIG_PATH", pkgconfig)
        if str(self.settings.os) == "OHOS":
            sysroot = os.path.join(prefix, "sysroot")
            cc = self._compiler_command("c", os.path.join(prefix, "bin", "clang-15"))
            cxx = self._compiler_command("cpp", f"{os.path.join(prefix, 'bin', 'clang-15')} --driver-mode=g++")
            env.define("CPP", self._preprocessor_command(cc, sysroot))
            env.define("CXXCPP", self._preprocessor_command(cxx, sysroot))
            tmpdir = os.path.expanduser("~/tmp")
            os.makedirs(tmpdir, exist_ok=True)
            env.define_path("TMPDIR", tmpdir)
        env.vars(self).save_script("mcrypt_deps")

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            for folder in {self.source_folder, self.build_folder}:
                configure = os.path.join(folder, "configure")
                if os.path.exists(configure):
                    os.chmod(configure, 0o755)
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            self._configure_with_shell(autotools)
        else:
            autotools.configure()
        self._mirror_prebuilt_gaa_sources()
        autotools.make(args=["-j1"])

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if str(self.settings.os) == "OHOS":
            self._prepare_install_hook_binary()
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    def _remove_stale_configure_outputs(self):
        for filename in ("config.status", "config.cache", "config.log", "libtool"):
            path = os.path.join(self.source_folder, filename)
            if os.path.exists(path):
                os.remove(path)

    def _dependency_dirs(self, relative):
        directories = []
        for dependency in self.dependencies.values():
            directory = os.path.join(dependency.package_folder, relative)
            if os.path.isdir(directory):
                directories.append(directory)
        return directories

    def _configure_with_shell(self, autotools):
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure):
            configure = os.path.join(self.build_folder, "configure")
        configure_args = getattr(autotools, "_configure_args", "") or ""
        command = 'config_shell="${{CONFIG_SHELL:-${{SHELL:-sh}}}}"; CONFIG_SHELL="$config_shell" "$config_shell" {0} {1}'.format(
            shlex.quote(configure),
            configure_args,
        )
        self.run(command, cwd=self.build_folder, env=["conanbuild", "mcrypt_deps"])

    def _mirror_prebuilt_gaa_sources(self):
        build_src = os.path.join(self.build_folder, "src")
        source_src = os.path.join(self.source_folder, "src")
        if not os.path.isdir(build_src) or not os.path.isdir(source_src):
            return
        if os.path.abspath(build_src) == os.path.abspath(source_src):
            return
        filenames = ["gaaout.c", "mcrypt.gaa"]
        filenames.extend(name for name in os.listdir(source_src) if name.endswith(".h"))
        for filename in filenames:
            source = os.path.join(source_src, filename)
            if os.path.isfile(source):
                shutil.copy2(source, os.path.join(build_src, filename))

    def _prepare_install_hook_binary(self):
        source = os.path.join(self.build_folder, "src", "mcrypt")
        destination = os.path.join(self.build_folder, "mcrypt")
        if os.path.isfile(source) and not os.path.exists(destination):
            shutil.copy2(source, destination)

    def _compiler_command(self, language, fallback):
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        command = compilers.get(language) or fallback
        if isinstance(command, (list, tuple)):
            return " ".join(shlex.quote(str(part)) for part in command)
        return str(command)

    def _preprocessor_command(self, compiler, sysroot):
        parts = [compiler, "-E"]
        if os.path.isdir(sysroot):
            parts.append(f"--sysroot={shlex.quote(sysroot)}")
        parts.append("-D__MUSL__")
        return " ".join(parts)
