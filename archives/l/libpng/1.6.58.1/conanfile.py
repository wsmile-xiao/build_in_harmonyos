#!/usr/bin/env python3
"""Conan recipe for libpng 1.6.58.1 (upstream 1.6.58)."""

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class LibpngConan(ConanFile):
    name = "libpng"
    version = "1.6.58.1"
    description = "PNG reference library"
    license = "libpng-2.0"
    homepage = "https://libpng.sourceforge.io/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    _test_programs = (
        "pngtest",
        "pnggetset",
        "pngunknown",
        "pngstest",
        "pngvalid",
        "pngimage",
        "pngcp",
        "timepng",
    )
    _nested_pngstest_drivers = (
        "pngstest-1.8",
        "pngstest-1.8-alpha",
        "pngstest-linear",
        "pngstest-linear-alpha",
        "pngstest-none",
        "pngstest-none-alpha",
        "pngstest-sRGB",
        "pngstest-sRGB-alpha",
    )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("zlib/1.3.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._autotools_toolchain().generate()

    def build(self):
        apply_conandata_patches(self)
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._configure_with_posix_shell()
                self._run_with_posix_shell("make -j1")
                self._prepare_ohos_test_programs()
                self._route_nested_pngstest_drivers()
                shell = shlex.quote(self._posix_shell())
                test_environment = Environment()
                if self.options.shared:
                    test_environment.prepend_path(
                        "LD_LIBRARY_PATH", os.path.join(self.build_folder, ".libs")
                    )
                with test_environment.vars(self).apply():
                    self._run_with_posix_shell(
                        f"make -j1 check LOG_COMPILER={shell}"
                    )
            else:
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(args=["-j1"])
                autotools.make(target="check", args=["-j1"])

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_with_posix_shell(
                    f"make -j1 install DESTDIR={destination}"
                )
            else:
                Autotools(self).install(args=["-j1"])
        self._relocate_metadata()
        if str(self.settings.os) == "OHOS":
            for name in ("pngfix", "png-fix-itxt"):
                self._sign_elf(Path(self.package_folder, "bin", name))
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["png16"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libpng")
        self.cpp_info.set_property("cmake_target_name", "libpng::libpng")
        self.cpp_info.set_property("pkg_config_name", "libpng")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    def _autotools_toolchain(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        return tc

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        mkdir = shutil.which("mkdir")
        if mkdir:
            environment.define("MKDIR_P", f"{mkdir} -p")
        return environment

    def _configure_with_posix_shell(self):
        shell = self._posix_shell()
        compiler = self._c_compiler()
        triplet = subprocess.check_output(
            [compiler, "-dumpmachine"], text=True
        ).strip()
        if not triplet:
            raise ConanInvalidConfiguration("C compiler returned an empty target triplet")
        configure = Path(self.source_folder, "configure")
        temporary_configure = Path(self.build_folder, ".conan-configure")
        try:
            shutil.copy2(configure, temporary_configure)
            self._relax_private_umask(temporary_configure)
            arguments = self._autotools_toolchain().configure_args + [
                f"--build={triplet}",
                f"--srcdir={self.source_folder}",
            ]
            quoted_arguments = " ".join(
                shlex.quote(argument) for argument in arguments
            )
            self._run_with_posix_shell(
                f"{shlex.quote(shell)} {shlex.quote(str(temporary_configure))} "
                f"{quoted_arguments}"
            )
        finally:
            if temporary_configure.exists():
                temporary_configure.unlink()

    def _run_with_posix_shell(self, command):
        shell = shlex.quote(self._posix_shell())
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _posix_shell(self):
        shell = "/system/bin/sh" if os.path.isfile("/system/bin/sh") else shutil.which("sh")
        if not shell:
            raise ConanInvalidConfiguration("No POSIX shell is available")
        return shell

    def _c_compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c") or shutil.which("cc")
        if not compiler:
            raise ConanInvalidConfiguration("No C compiler is configured")
        return compiler

    def _prepare_ohos_test_programs(self):
        build = Path(self.build_folder)
        if self.options.shared:
            self._sign_elf(build / ".libs" / "libpng16.so.16.58.0")
        for name in self._test_programs:
            executable = build / ".libs" / name if self.options.shared else build / name
            self._sign_elf(executable)
            if self.options.shared:
                shutil.copy2(executable, build / name)

    def _route_nested_pngstest_drivers(self):
        shell = shlex.quote(self._posix_shell())
        original = 'exec "${srcdir}/tests/pngstest"'
        replacement = f'exec {shell} "${{srcdir}}/tests/pngstest"'
        for name in self._nested_pngstest_drivers:
            driver = Path(self.source_folder, "tests", name)
            if not driver.is_file():
                raise ConanInvalidConfiguration(
                    f"required upstream test driver is missing: {driver}"
                )
            content = driver.read_text(encoding="utf-8")
            if content.count(original) != 1:
                raise ConanInvalidConfiguration(
                    f"upstream test driver invocation changed: {driver}"
                )
            driver.write_text(
                content.replace(original, replacement, 1), encoding="utf-8"
            )

    def _sign_elf(self, executable):
        executable = Path(executable)
        if not executable.is_file():
            raise ConanInvalidConfiguration(
                f"required OHOS test ELF is missing: {executable}"
            )
        objcopy = self._resolve_tool("objcopy")
        readelf = self._resolve_tool("readelf")
        signer = self._resolve_tool("binary-sign-tool", llvm=False)
        temporary = executable.with_name(
            f"{executable.name}.signing-{os.getpid()}"
        )
        try:
            shutil.copy2(executable, temporary)
            sections = subprocess.run(
                [readelf, "-S", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if ".codesign" in sections:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", str(temporary)],
                    check=True,
                )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    str(temporary),
                    "-outFile",
                    str(temporary),
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            signed_sections = subprocess.run(
                [readelf, "-S", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if ".codesign" not in signed_sections:
                raise ConanException(f"signer did not add .codesign: {executable}")
            os.replace(temporary, executable)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _resolve_tool(self, tool, llvm=True):
        compiler = self._c_compiler()
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path)
        compiler_name = os.path.basename(compiler_path)
        suffix = (
            compiler_name[len("clang") :]
            if compiler_name.startswith("clang")
            else ""
        )
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        candidates = [executables.get(tool)]
        if compiler_dir:
            if llvm:
                candidates.extend(
                    [
                        os.path.join(compiler_dir, f"llvm-{tool}{suffix}"),
                        os.path.join(compiler_dir, f"llvm-{tool}"),
                    ]
                )
            candidates.append(os.path.join(compiler_dir, tool))
        if llvm and suffix:
            candidates.append(f"llvm-{tool}{suffix}")
        if llvm:
            candidates.append(f"llvm-{tool}")
        candidates.append(tool)
        for candidate in candidates:
            if candidate:
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved
        raise ConanInvalidConfiguration(f"required OHOS tool was not found: {tool}")

    @staticmethod
    def _relax_private_umask(configure):
        path = Path(configure)
        content = path.read_text(encoding="utf-8", errors="surrogateescape")
        if content.count("umask 077") != 2:
            raise ConanInvalidConfiguration(
                "unexpected number of private umask commands in configure"
            )
        content = content.replace("umask 077", "umask 022")
        path.write_text(content, encoding="utf-8", errors="surrogateescape")

    def _relocate_metadata(self):
        for name in ("libpng16.pc", "libpng.pc"):
            pc_path = Path(self.package_folder, "lib", "pkgconfig", name)
            if not pc_path.is_file():
                raise ConanException(f"installed pkg-config file is missing: {name}")
            content = pc_path.read_text(encoding="utf-8")
            content, count = re.subn(
                r"^prefix=.*$",
                "prefix=${pcfiledir}/../..",
                content,
                count=1,
                flags=re.MULTILINE,
            )
            if count != 1:
                raise ConanException(f"{name} has no unique prefix field")
            pc_path.write_text(content, encoding="utf-8")
        for name in ("libpng16.la", "libpng.la"):
            la_path = Path(self.package_folder, "lib", name)
            if la_path.is_file():
                la_path.unlink()
        for name in ("libpng16-config", "libpng-config"):
            config_path = Path(self.package_folder, "bin", name)
            if config_path.is_file():
                config_path.unlink()
