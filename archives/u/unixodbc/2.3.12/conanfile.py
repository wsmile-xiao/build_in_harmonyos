#!/usr/bin/env python3
"""Conan recipe for unixODBC 2.3.12."""

import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UnixodbcConan(ConanFile):
    name = "unixodbc"
    version = "2.3.12"
    description = "ODBC driver manager for Unix-like systems"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.unixodbc.org/"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "unixODBC recipe is currently adapted for Linux/OHOS only"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        if self.settings.os == "OHOS":
            env = tc.environment()
            shell = self._select_shell()
            tmpdir = os.path.join(self.build_folder, "tmp")
            env.define("CONFIG_SHELL", shell)
            env.define("SHELL", shell)
            env.define("TMPDIR", tmpdir)
            env.define("TMPPREFIX", os.path.join(tmpdir, "zsh"))
            self._define_compiler_tools(env)
            tc.generate(env=env)
        else:
            tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._prepare_tmpdir()
        autotools = Autotools(self)
        self._configure_autotools(autotools)
        self._make_autotools(autotools, args=["-j1"])
        if not self.conf.get("tools.build:skip_test", default=False, check_type=bool):
            self._make_autotools(autotools, target="check", args=["-j1"])
            self._run_build_smoke()

    def package(self):
        self._prepare_tmpdir()
        autotools = Autotools(self)
        self._install_autotools(autotools, args=["-j1"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        rm(self, "*", os.path.join(self.package_folder, "bin"), recursive=True)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._sign_package_elfs()

    def package_info(self):
        self.cpp_info.libs = ["odbc", "odbcinst", "odbccr"]
        self.cpp_info.set_property("cmake_file_name", "unixodbc")
        self.cpp_info.set_property("cmake_target_name", "unixodbc::unixodbc")
        self.cpp_info.set_property("pkg_config_name", "odbc")
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )

    def _configure_args(self):
        args = []
        if self.settings.os == "OHOS":
            triplet = self._ohos_configure_triplet()
            args.extend([f"--build={triplet}", f"--host={triplet}"])
        args.extend([
            "--sysconfdir=/etc",
            "--disable-gui",
            "--disable-drivers",
            "--disable-driver-config",
            "--disable-readline",
            "--disable-editline",
            "--disable-stats",
            "--disable-iconv",
            "--enable-threads",
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
        ])
        return args

    def _ohos_configure_triplet(self):
        if self.settings.arch == "armv8":
            return "aarch64-unknown-linux-gnu"
        raise ConanInvalidConfiguration(
            f"unixODBC OHOS configure triplet is not mapped for {self.settings.arch}"
        )

    def _prepare_tmpdir(self):
        if self.settings.os != "OHOS":
            return
        shell = self._select_shell()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["CONFIG_SHELL"] = shell
        os.environ["SHELL"] = shell
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMPPREFIX"] = os.path.join(tmpdir, "zsh")

    def _configure_autotools(self, autotools):
        if self.settings.os != "OHOS":
            autotools.configure()
            return
        configure = os.path.join(self.source_folder, "configure")
        command = " ".join(
            part for part in (shlex.quote(configure), autotools._configure_args) if part
        )
        self._run_with_ohos_env(command)

    def _make_autotools(self, autotools, target=None, args=None):
        if self.settings.os != "OHOS":
            autotools.make(target=target, args=args)
            return
        command = [self._make_program()]
        if target:
            command.append(target)
        command.extend(args or [])
        self._run_with_ohos_env(shlex.join(command))

    def _install_autotools(self, autotools, args=None):
        if self.settings.os != "OHOS":
            autotools.install(args=args)
            return
        install_args = [f"DESTDIR={self.package_folder}", "install"]
        install_args.extend(args or [])
        self._make_autotools(autotools, args=install_args)

    def _run_with_ohos_env(self, command, **kwargs):
        if self.settings.os != "OHOS":
            self.run(command, **kwargs)
            return
        self.run(f"{self._ohos_env_prefix()} {command}", **kwargs)

    def _ohos_env_prefix(self):
        shell = self._select_shell()
        tmpdir = os.path.join(self.build_folder, "tmp")
        env = {
            "CONFIG_SHELL": shell,
            "SHELL": shell,
            "TMPDIR": tmpdir,
            "TMPPREFIX": os.path.join(tmpdir, "zsh"),
        }
        return " ".join(f"{key}={shlex.quote(value)}" for key, value in env.items())

    def _make_program(self):
        return self.conf.get("tools.gnu:make_program", default="make")

    def _run_build_smoke(self):
        exe_dir = os.path.join(self.build_folder, "exe")
        for name, args in (
            ("odbc_config", ["--version"]),
            ("odbc_config", ["--ulen"]),
            ("isql", ["--version"]),
            ("odbcinst", ["--version"]),
        ):
            path = os.path.join(exe_dir, self._exe_name(name))
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(f"expected build output is missing: {path}")
            self.run(
                shlex.join([path] + args),
                env="conanautotoolstoolchain",
            )

    def _sign_package_elfs(self):
        if self.settings.os != "OHOS":
            return
        objcopy = self._resolve_tool("llvm-objcopy", aliases=("objcopy",))
        signer = self._resolve_tool("binary-sign-tool")
        patterns = [
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
            os.path.join(self.package_folder, "bin", "*"),
        ]
        paths = []
        for pattern in patterns:
            paths.extend(glob.glob(pattern, recursive=True))
        for path in sorted(set(paths)):
            if os.path.islink(path) or not os.path.isfile(path) or not self._is_elf(path):
                continue
            self._sign_elf_atomically(path, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.unsigned"
        signed = f"{path}.signed"
        try:
            shutil.copy2(path, temporary)
            self.run(
                "{} --remove-section .codesign {} 2>/dev/null || true".format(
                    shlex.quote(objcopy), shlex.quote(temporary)
                )
            )
            self.run(
                shlex.join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        temporary,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ]
                ),
                quiet=True,
            )
            os.chmod(signed, original_mode | 0o755)
            os.replace(signed, path)
        finally:
            for leftover in (temporary, signed):
                if os.path.exists(leftover):
                    os.remove(leftover)

    def _resolve_tool(self, name, aliases=()):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c") or compilers.get("cpp") or ""
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path) if compiler_path else ""

        env_key = name.upper().replace("-", "_")
        candidates = [os.environ.get(env_key), compilers.get(name)]
        for alias in aliases:
            candidates.append(compilers.get(alias))
        if compiler_dir:
            candidates.append(os.path.join(compiler_dir, name))
            for alias in aliases:
                candidates.append(os.path.join(compiler_dir, alias))
        candidates.extend(
            [
                os.path.join("/data/service/hnp/bin", name),
                os.path.join("/storage/Users/currentUser/usr/local/bin", name),
                shutil.which(name) or "",
            ]
        )
        for alias in aliases:
            candidates.append(shutil.which(alias) or "")

        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate) or candidate
            if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                return resolved
        raise ConanInvalidConfiguration(f"required OHOS tool was not found: {name}")

    def _define_compiler_tools(self, env):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        for key, var, fallback in (
            ("c", "CC", "clang"),
            ("cpp", "CXX", "clang++"),
            ("cxx", "CXX", "clang++"),
        ):
            command = compilers.get(key)
            if command:
                env.define(var, self._resolve_configured_tool(command, fallback))
        for key, var in (
            ("ar", "AR"),
            ("ranlib", "RANLIB"),
            ("nm", "NM"),
            ("strip", "STRIP"),
        ):
            command = compilers.get(key) or self._tool_from_compiler_dir(key)
            if command:
                env.define(var, command)

    def _tool_from_compiler_dir(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c") or compilers.get("cpp") or ""
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path) if compiler_path else ""
        llvm_name = "llvm-" + name
        for candidate in (
            os.path.join(compiler_dir, llvm_name) if compiler_dir else "",
            shutil.which(llvm_name) or "",
            shutil.which(name) or "",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def _resolve_configured_tool(self, command, fallback):
        basename = os.path.basename(command)
        for candidate in (
            command,
            os.path.join("/storage/Users/currentUser/usr/local/bin", basename),
            shutil.which(basename) or "",
        ):
            resolved = shutil.which(candidate) or candidate
            if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                return resolved
        return self._resolve_tool(fallback)

    def _select_shell(self):
        for shell in (
            os.path.join(os.path.expanduser("~"), "usr/local", "bin", "bash"),
            "/storage/Users/currentUser/usr/local/bin/bash",
            "/bin/sh",
            "/system/bin/sh",
            "sh",
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
        ):
            if not shell:
                continue
            resolved = shutil.which(shell) or shell
            if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                return resolved
        return "sh"

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _exe_name(name):
        return name + ".exe" if os.name == "nt" else name
