#!/usr/bin/env python3
"""Conan recipe for libodb 2.4.0 (ODB core object-relational mapping runtime).

Standalone adaptation of the libodb 2.4.0 core runtime (the real test suite
is the separate odb-tests-2.4.0 package; see test_package/MANIFEST.yml).
Zero external dependencies: the core runtime only needs a C++ compiler and
(optionally) POSIX threads. The package installs into the conan package
folder only, so no R26 system-name static override is applied — the shared
library keeps the upstream libtool -release 2.4 naming (libodb-2.4.so),
matching the libodb-pgsql/2.4.0 bundle precedent.
"""

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
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

doc_files = ["GPLv2", "LICENSE", "NEWS", "README"]


class LibodbConan(ConanFile):
    name = "libodb"
    version = "2.4.0"
    description = (
        "ODB object-relational mapping (ORM) runtime core library "
        "(common, database-profile independent part)"
    )
    license = "GPL-2.0-only"
    homepage = "https://www.codesynthesis.com/products/odb/"
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
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libodb recipe is currently adapted for Linux/OHOS only"
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
        # The plain-text `version` doc file at the source root shadows
        # libc++'s <version> header (pulled by <memory>/<new>) under
        # -I$(top_srcdir); removing it here is idempotent with the patch.
        version_shadow = os.path.join(self.source_folder, "version")
        if os.path.isfile(version_shadow):
            os.remove(version_shadow)
        self._prepare_tmpdir()
        self._run_configure(self.source_folder, self._configure_args())
        self._run_make(args=["-j1"])

    def package(self):
        self._prepare_tmpdir()
        # "/" prefix + make install DESTDIR=<dir> puts files in <dir>/lib,
        # <dir>/include, <dir>/share (same scheme as unixodbc/2.3.12).
        self._run_make(args=["-j1", f"DESTDIR={self.package_folder}", "install"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        for name in doc_files:
            if os.path.isfile(os.path.join(self.source_folder, name)):
                copy(self, name, self.source_folder,
                     os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._sign_package_elfs()

    def package_info(self):
        self.cpp_info.libs = ["odb"]
        self.cpp_info.set_property("cmake_file_name", "libodb")
        self.cpp_info.set_property("cmake_target_name", "libodb::libodb")
        self.cpp_info.set_property("pkg_config_name", "libodb")
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )

    # ------------------------------------------------------------------
    # OHOS autotools machinery (aligned with archives/u/unixodbc/2.3.12)
    # ------------------------------------------------------------------

    def _configure_args(self):
        args = []
        if self.settings.os == "OHOS":
            triplet = self._ohos_configure_triplet()
            args.extend([f"--build={triplet}", f"--host={triplet}"])
        # "/" prefix + make install DESTDIR=<dir> puts files in <dir>/lib,
        # <dir>/include, <dir>/share (same scheme as unixodbc/2.3.12).
        args.append("--prefix=/")
        args.extend([
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
        ])
        return args

    def _ohos_configure_triplet(self):
        if self.settings.arch == "armv8":
            return "aarch64-unknown-linux-gnu"
        raise ConanInvalidConfiguration(
            f"libodb OHOS configure triplet is not mapped for {self.settings.arch}"
        )

    def _prepare_tmpdir(self):
        if self.settings.os != "OHOS":
            return
        # E011: HMDFS + inherited umask 077 makes autoconf's confXXXX temp
        # dirs unusable (config.status: Permission denied on subs*.awk).
        # Normalize to 022 for the whole build process tree (children inherit);
        # the patches additionally fix the explicit umask 077 inside configure
        # and config/config.guess.
        os.umask(0o022)
        shell = self._select_shell()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["CONFIG_SHELL"] = shell
        os.environ["SHELL"] = shell
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMPPREFIX"] = os.path.join(tmpdir, "zsh")

    def _run_configure(self, source_folder, args):
        configure = os.path.join(source_folder, "configure")
        command = " ".join([shlex.quote(configure)] + [shlex.quote(a) for a in args])
        self._run(command)

    def _run_make(self, target=None, args=None):
        command = [self._make_program()]
        if target:
            command.append(target)
        command.extend(args or [])
        self._run(shlex.join(command))

    def _run(self, command, **kwargs):
        if self.settings.os != "OHOS":
            self.run(command, **kwargs)
            return
        self.run(command, env="conanautotoolstoolchain", **kwargs)

    def _make_program(self):
        return self.conf.get("tools.gnu:make_program", default="make")

    def _sign_package_elfs(self):
        if self.settings.os != "OHOS":
            return
        objcopy = self._resolve_tool("llvm-objcopy", aliases=("objcopy",))
        signer = self._resolve_tool("binary-sign-tool")
        patterns = [
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
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
            "/data/service/hnp/bin/bash",
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
