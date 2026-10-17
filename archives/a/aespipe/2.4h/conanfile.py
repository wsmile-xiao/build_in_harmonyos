import os
import shutil
import ctypes

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AespipeConan(ConanFile):
    name = "aespipe"
    version = "2.4h"
    description = "AES encrypting and decrypting command-line pipe"
    license = "GPL-2.0-only"
    homepage = "https://loop-aes.sourceforge.net/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def build_requirements(self):
        if str(self.settings_build.os) == "Windows":
            self.tool_requires("make/4.4.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-asm",
            "--disable-padlock",
            "--disable-intelaes",
        ])
        if str(self.settings.os) == "OHOS":
            target, sysroot = self._ohos_target()
            tc.configure_args.append(f"--host={target}")
            tc.configure_args.append("GPG_PROG=no")
            target_flags = [f"--target={target}"]
            if sysroot:
                target_flags.append(f"--sysroot={sysroot}")
            tc.cflags.extend(target_flags + ["-D__MUSL__"])
            tc.cxxflags.extend(target_flags + ["-D__MUSL__"])
            tc.ldflags.extend(target_flags)
        tc.generate()

    def _ohos_target(self):
        target = (
            "x86_64-linux-ohos"
            if str(self.settings.arch) == "x86_64"
            else "aarch64-linux-ohos"
        )
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compilers.get("c") or compilers.get("cpp")
        if not compiler:
            raise ConanInvalidConfiguration("OHOS compiler executable is not configured")

        candidates = []
        configured = self.conf.get(
            "tools.build:sysroot", default="", check_type=str
        )
        if configured:
            candidates.append(configured)

        directory = os.path.dirname(os.path.abspath(compiler))
        for _ in range(5):
            candidates.append(os.path.join(directory, "sysroot"))
            parent = os.path.dirname(directory)
            if parent == directory:
                break
            directory = parent

        for candidate in candidates:
            if os.path.isdir(candidate):
                return target, self._short_path(candidate)

        # The official OHOS worker exposes a compiler wrapper without a sibling
        # sysroot. Its profile supplies the compiler resource paths, so only the
        # target flag is needed when no explicit sysroot directory is available.
        return target, None

    @staticmethod
    def _short_path(path):
        if os.name == "nt" and " " in path:
            buffer = ctypes.create_unicode_buffer(32768)
            length = ctypes.windll.kernel32.GetShortPathNameW(path, buffer, len(buffer))
            if length:
                path = buffer.value
        return path.replace("\\", "/")

    def _configure_shell(self):
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            shutil.which("sh"),
            "C:/Program Files/Git/bin/sh.exe",
            "C:/Program Files/Git/usr/bin/sh.exe",
            "E:/Git/bin/sh.exe",
            "E:/Git/usr/bin/sh.exe",
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate.replace("\\", "/")
        raise ConanInvalidConfiguration("A POSIX sh executable is required")

    def _llvm_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compilers.get("c") or compilers.get("cpp")
        if not compiler:
            return name
        executable = f"{name}.exe" if os.name == "nt" else name
        candidate = os.path.join(os.path.dirname(compiler), executable)
        return self._short_path(candidate) if os.path.exists(candidate) else name

    def _c_compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compilers.get("c")
        if not compiler:
            raise ConanInvalidConfiguration("C compiler executable is not configured")
        return self._short_path(compiler)

    def _make_program(self):
        for dependency in self.dependencies.build.values():
            if getattr(getattr(dependency, "ref", None), "name", None) == "make":
                for executable in ("gnumake.exe", "make.exe", "make"):
                    candidate = os.path.join(dependency.package_folder, "bin", executable)
                    if os.path.isfile(candidate):
                        return candidate.replace("\\", "/")
        return (shutil.which("make") or "make").replace("\\", "/")

    def _make(self, arguments):
        command = f'"{self._make_program()}"'
        if os.name == "nt":
            command += f' SHELL="{self._configure_shell()}"'
        return f"{command} {arguments}"

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if os.name == "nt":
            configure = os.path.join(self.source_folder, "configure").replace("\\", "/")
            args = autotools._configure_args
            if not isinstance(args, str):
                args = " ".join(args)
            env = Environment()
            env.define("CONFIG_SITE", "")
            if str(self.settings.os) == "OHOS":
                target, sysroot = self._ohos_target()
                optimize = "-O3" if str(self.settings.build_type) == "Release" else "-O0 -g"
                target_flags = [f"--target={target}"]
                if sysroot:
                    target_flags.append(f"--sysroot={sysroot}")
                env.define("CC", self._c_compiler())
                env.define(
                    "CFLAGS",
                    " ".join(target_flags + ["-D__MUSL__", optimize]),
                )
                cppflags = (
                    "-DNDEBUG"
                    if str(self.settings.build_type) == "Release"
                    else ""
                )
                env.define("CPPFLAGS", cppflags)
                env.define("LDFLAGS", " ".join(target_flags))
            env.define("AR", self._llvm_tool("llvm-ar"))
            env.define("RANLIB", self._llvm_tool("llvm-ranlib"))
            env.define("NM", self._llvm_tool("llvm-nm"))
            env.define("STRIP", self._llvm_tool("llvm-strip"))
            with env.vars(self).apply():
                self.run(
                    f'"{self._configure_shell()}" "{configure}" {args}'
                )
                self.run(
                    self._make(f"-j{build_jobs(self)}"), cwd=self.build_folder
                )
            return
        else:
            autotools.configure()
        self.run(self._make(f"-j{build_jobs(self)}"), cwd=self.build_folder, env="conanbuild")

    def package(self):
        copy(
            self,
            "aespipe",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "aespipe.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
