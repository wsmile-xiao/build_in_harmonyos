#!/usr/bin/env python3
"""Conan recipe for GNU GRUB 2.12 targeting x86_64-elf/EFI."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    mkdir,
    replace_in_file,
    rm,
    save,
)
from conan.tools.layout import basic_layout


class X8664ElfGrubConan(ConanFile):
    name = "x86_64-elf-grub"
    version = "2.12"
    description = "GNU GRUB host tools targeting x86_64-elf and x86_64 EFI"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/grub/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("x86_64-elf-binutils/2.46.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _compiler_executables(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        cxx = compilers.get("cpp")
        if not cc or not cxx:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must define both 'c' and 'cpp'"
            )
        return cc, cxx

    def _target_tools(self):
        dependency = self.dependencies.build["x86_64-elf-binutils"]
        tool_bin = os.path.join(dependency.package_folder, "bin")
        names = ("ld", "objcopy", "strip", "nm", "ranlib")
        tools = {
            name: os.path.join(tool_bin, f"x86_64-elf-{name}") for name in names
        }
        missing = [path for path in tools.values() if not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                "x86_64-elf-binutils is missing required tools: "
                + ", ".join(missing)
            )
        return tools

    def _configure_shell(self):
        if str(self.settings.os) == "OHOS":
            candidates = ["/system/bin/sh"]
        else:
            candidates = [os.environ.get("CONFIG_SHELL"), shutil.which("sh")]

        for candidate in candidates:
            if not candidate:
                continue
            resolved = (
                candidate
                if os.path.isabs(candidate)
                else shutil.which(candidate)
            )
            if not resolved:
                continue
            resolved = os.path.realpath(resolved)
            if not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
                continue
            return resolved

        raise ConanInvalidConfiguration(
            "a native POSIX shell is required to configure GRUB"
        )

    def _configure_environment(self):
        cc, cxx = self._compiler_executables()
        target_tools = self._target_tools()
        configure_shell = self._configure_shell()
        temp_dir = os.path.join(self.build_folder, ".tmp")
        mkdir(self, temp_dir)
        true_program = shutil.which("true") or "true"
        prefix_maps = " ".join(
            (
                f"-ffile-prefix-map={self.source_folder}=grub-{self.version}",
                f"-ffile-prefix-map={self.build_folder}=grub-{self.version}/build",
                f"-fdebug-prefix-map={self.source_folder}=grub-{self.version}",
                f"-fdebug-prefix-map={self.build_folder}=grub-{self.version}/build",
            )
        )

        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("BUILD_CC", cc)
        env.define("CFLAGS", f"-O2 -g {prefix_maps}")
        env.define("CXXFLAGS", f"-O2 -g {prefix_maps}")
        # HNP Clang's x86_64-elf driver delegates linking to an absent gcc.
        # Keep the frontend bare-metal while selecting the published GNU ld.
        env.define(
            "TARGET_CC",
            f"{cc} --target=x86_64-unknown-linux-gnu "
            f"--ld-path={target_tools['ld']} "
            "-Xclang -triple -Xclang x86_64-unknown-unknown-elf "
            "-fno-pic -fno-pie -no-pie -Wno-unused-command-line-argument",
        )
        env.define("TARGET_CFLAGS", f"-Os {prefix_maps}")
        env.define("TARGET_CCASFLAGS", prefix_maps)
        env.define("TARGET_OBJCOPY", target_tools["objcopy"])
        env.define("TARGET_STRIP", target_tools["strip"])
        env.define("TARGET_NM", target_tools["nm"])
        env.define("TARGET_RANLIB", target_tools["ranlib"])
        env.define("CONFIG_SHELL", configure_shell)
        env.define("SHELL", configure_shell)
        env.define("TMPDIR", temp_dir)
        env.define("MAKEINFO", true_program)
        env.define("HELP2MAN", true_program)
        return env.vars(self)

    def build(self):
        apply_conandata_patches(self)

        # GRUB's generated dependency fragments include this optional file.
        # An empty file is sufficient when no out-of-tree modules are supplied.
        save(self, os.path.join(self.source_folder, "grub-core", "extra_deps.lst"), "")
        mkdir(self, self.build_folder)

        configure_args = [
            "--prefix=/",
            "--target=x86_64-elf",
            "--with-platform=efi",
            "--program-prefix=x86_64-elf-",
            "--disable-werror",
            "--disable-nls",
            "--disable-efiemu",
            "--disable-grub-mkfont",
            "--disable-grub-themes",
            "--disable-grub-mount",
            "--disable-device-mapper",
            "--disable-liblzma",
            "--disable-libzfs",
            "--disable-grub-emu-sdl",
            "--disable-grub-emu-sdl2",
            "--disable-grub-emu-pci",
        ]
        configure = os.path.join(self.source_folder, "configure")
        configure_shell = self._configure_shell()
        configure_command = " ".join(
            [
                f"CONFIG_SHELL={shlex.quote(configure_shell)}",
                f"SHELL={shlex.quote(configure_shell)}",
                shlex.quote(configure_shell),
                shlex.quote(configure),
            ]
            + [shlex.quote(arg) for arg in configure_args]
        )

        with self._configure_environment().apply():
            self.run(configure_command, cwd=self.build_folder, env="conanbuild")

            jobs = min(build_jobs(self), 8)
            self.run(
                f"make -j{jobs} {shlex.quote(f'SHELL={configure_shell}')} "
                f"{shlex.quote('TARGET_LDFLAGS=-Wl,-no-pie')}",
                cwd=self.build_folder,
                env="conanbuild",
            )

            # GRUB's complete suite needs QEMU, filesystem tools and target
            # runtimes. These four upstream C unit tests are self-contained.
            check_args = [
                "check",
                f"SHELL={configure_shell}",
                "check_PROGRAMS=example_unit_test printf_test date_test cmp_test",
                "check_SCRIPTS=",
                "TESTS=example_unit_test printf_test date_test cmp_test",
                "TARGET_LDFLAGS=-Wl,-no-pie",
            ]
            check_command = "make " + " ".join(
                shlex.quote(arg) for arg in check_args
            )
            self.run(check_command, cwd=self.build_folder, env="conanbuild")

    def package(self):
        configure_shell = self._configure_shell()
        package_command = " ".join(
            [
                "make",
                "install",
                shlex.quote(f"SHELL={configure_shell}"),
                shlex.quote("TARGET_LDFLAGS=-Wl,-no-pie"),
                shlex.quote(f"DESTDIR={self.package_folder}"),
                shlex.quote("man_MANS="),
            ]
        )
        with self._configure_environment().apply():
            self.run(package_command, cwd=self.build_folder, env="conanbuild")

        platform_dir = os.path.join(
            self.package_folder, "lib", "grub", "x86_64-efi"
        )
        # Installed .module files only carry GDB symbols; GRUB loads .mod files.
        rm(self, "x86_64-elf-*.module", folder=platform_dir)

        modinfo = os.path.join(platform_dir, "modinfo.sh")
        target_tools = self._target_tools()
        replacements = (
            (self.build_folder, f"grub-{self.version}/build"),
            (self.source_folder, f"grub-{self.version}"),
            # modinfo.sh.in does not export TARGET_OBJCOPY.
            *(
                (target_tools[name], f"x86_64-elf-{name}")
                for name in ("ld", "strip", "nm", "ranlib")
            ),
        )
        for original, portable in replacements:
            replace_in_file(
                self,
                modinfo,
                original,
                portable,
            )

        modinfo_contents = load(self, modinfo)
        leaked_roots = (
            self.build_folder,
            self.source_folder,
            self.dependencies.build["x86_64-elf-binutils"].package_folder,
        )
        leaked = [path for path in leaked_roots if path in modinfo_contents]
        if leaked:
            raise ConanInvalidConfiguration(
                "modinfo.sh contains non-portable build paths: "
                + ", ".join(leaked)
            )

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
