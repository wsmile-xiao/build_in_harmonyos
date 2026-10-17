#!/usr/bin/env python3
"""Conan recipe for libodb-pgsql 2.4.0 (bundles the libodb 2.4.0 core runtime).

libodb-pgsql is the PostgreSQL profile of the ODB ORM runtime. It needs the
libodb core runtime both to configure (--with-libodb, real link test against
-lodb) and to run. libodb/2.4.0 was never adapted or published in this repo,
and CI gate L0i (R36) rejects any requires() that is missing from the
registry, so this recipe bundles both: build() first builds libodb-2.4.0
into a staging tree, assembles the --with-libodb layout the LIBODB autoconf
macro expects (-I<dir> -L<dir>/odb -lodb), then builds libodb-pgsql against
it. package() ships both header trees and both libraries from a single
package (multi-component precedent: archives/p/postgresql/18.3).
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

required_odb_version = "2.4.0"

doc_files = ["GPLv2", "LICENSE", "NEWS", "README"]


class LibodbPgsqlConan(ConanFile):
    name = "libodb-pgsql"
    version = "2.4.0"
    description = (
        "ODB object-relational mapping (ORM) runtime for PostgreSQL, "
        "bundled with the libodb core runtime"
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

    def requirements(self):
        # Provides libpq-fe.h, -lpq and pg_config for the configure LIBPQ
        # link test and the shared library link.
        self.requires("postgresql/18.3")

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libodb-pgsql recipe is currently adapted for Linux/OHOS only"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        # No strip_root: each tarball must keep its own root directory
        # (libodb-pgsql-2.4.0/, libodb-2.4.0/) side by side — the patches
        # and build() reference both trees relative to source_folder.
        get(self, **self.conan_data["sources"]["libodb-pgsql"])
        get(self, **self.conan_data["sources"]["libodb"])

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            env = tc.environment()
            shell = self._select_shell()
            tmpdir = os.path.join(self.build_folder, "tmp")
            env.define("CONFIG_SHELL", shell)
            env.define("SHELL", shell)
            env.define("TMPDIR", tmpdir)
            env.define("TMPPREFIX", os.path.join(tmpdir, "zsh"))
            self._define_compiler_tools(env)
            # The libodb-pgsql configure LIBPQ macro runs a real
            # #include <libpq-fe.h> + -lpq link test with the default
            # CPPFLAGS/LDFLAGS before it tries pg_config discovery.
            pg = self.dependencies["postgresql"]
            env.append(
                "CPPFLAGS",
                [
                    f"-I{p}"
                    for p in self._abs_paths(
                        pg.package_folder, pg.cpp_info.includedirs or ["include"]
                    )
                ],
            )
            env.append(
                "LDFLAGS",
                [
                    f"-L{p}"
                    for p in self._abs_paths(
                        pg.package_folder, pg.cpp_info.libdirs or ["lib"]
                    )
                ],
            )
            tc.generate(env=env)
        else:
            tc.generate()
            from conan.tools.gnu import AutotoolsDeps

            AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        self._prepare_tmpdir()

        odb_src = os.path.join(self.source_folder, f"libodb-{required_odb_version}")
        odb_install = os.path.join(self.build_folder, "libodb-install")
        odb_root = os.path.join(self.build_folder, "odb-staging")

        # 1. Build + stage the bundled libodb core runtime.
        odb_args = self._configure_args()
        self._run_configure(odb_src, odb_args)
        self._run_make(args=["-j1"])
        self._run_make(args=["-j1", f"DESTDIR={odb_install}", "install"])
        self._assemble_libodb_root(odb_install, odb_root)

        # 2. Build libodb-pgsql against the staged core runtime.
        pgsql_src = os.path.join(self.source_folder, "libodb-pgsql-2.4.0")
        pgsql_args = self._configure_args()
        pgsql_args.append(f"--with-libodb={odb_root}")
        self._run_configure(pgsql_src, pgsql_args)
        self._run_make(args=["-j1"])

    def package(self):
        self._prepare_tmpdir()
        # libodb-pgsql: library, odb/pgsql headers, pkgconfig, docs.
        self._run_make(args=["-j1", f"DESTDIR={self.package_folder}", "install"])

        # Bundled libodb core runtime: odb/** headers and libraries.
        odb_install = os.path.join(self.build_folder, "libodb-install")
        copy(self, "odb/*", os.path.join(odb_install, "include"),
             os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "libodb*", os.path.join(odb_install, "lib"),
             os.path.join(self.package_folder, "lib"), keep_path=True)

        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)

        pgsql_src = os.path.join(self.source_folder, "libodb-pgsql-2.4.0")
        odb_src = os.path.join(self.source_folder, f"libodb-{required_odb_version}")
        for name in doc_files:
            if os.path.isfile(os.path.join(pgsql_src, name)):
                copy(self, name, pgsql_src,
                     os.path.join(self.package_folder, "licenses", "libodb-pgsql"),
                     keep_path=False)
            if os.path.isfile(os.path.join(odb_src, name)):
                copy(self, name, odb_src,
                     os.path.join(self.package_folder, "licenses", "libodb"),
                     keep_path=False)

        self._sign_package_elfs()

    def package_info(self):
        self.cpp_info.libs = ["odb-pgsql", "odb"]
        self.cpp_info.set_property("cmake_file_name", "libodb-pgsql")
        self.cpp_info.set_property("cmake_target_name", "libodb-pgsql::libodb-pgsql")
        self.cpp_info.set_property("pkg_config_name", "libodb-pgsql")
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
            f"libodb-pgsql OHOS configure triplet is not mapped for {self.settings.arch}"
        )

    def _prepare_tmpdir(self):
        if self.settings.os != "OHOS":
            return
        # E011: HMDFS + inherited umask 077 makes autoconf's confXXXX temp
        # dirs unusable (config.status: Permission denied on subs*.awk).
        # Normalize to 022 for the whole build process tree (children inherit).
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

    def _assemble_libodb_root(self, odb_install, odb_root):
        """Build the --with-libodb layout the LIBODB autoconf macro expects.

        m4/libodb.m4 adds -I<dir> (needs odb/** headers, including the
        generated odb/details/config.h) and -L<dir>/odb -lodb (needs the
        libodb library files directly inside <dir>/odb).
        """
        odb_root_odb = os.path.join(odb_root, "odb")
        os.makedirs(odb_root_odb, exist_ok=True)
        copy(self, "odb/*", os.path.join(odb_install, "include"), odb_root, keep_path=True)
        lib_dir = os.path.join(odb_install, "lib")
        if self.options.shared:
            # libtool -release names the shared library libodb-2.4.so and
            # ships a libodb.so -> libodb-2.4.so symlink next to it; copy
            # both so -lodb resolves to a loadable library.
            for entry in sorted(os.listdir(lib_dir)):
                if not entry.startswith("libodb") or entry.endswith(".la"):
                    continue
                src = os.path.join(lib_dir, entry)
                dst = os.path.join(odb_root_odb, entry)
                if os.path.islink(src):
                    if not os.path.lexists(dst):
                        os.symlink(os.readlink(src), dst)
                elif os.path.isfile(src):
                    shutil.copy2(src, dst)
            if not os.path.exists(os.path.join(odb_root_odb, "libodb.so")):
                release_libs = sorted(
                    name
                    for name in os.listdir(odb_root_odb)
                    if name.startswith("libodb")
                    and name.endswith(".so")
                    and os.path.isfile(os.path.join(odb_root_odb, name))
                )
                if release_libs:
                    os.symlink(release_libs[-1], os.path.join(odb_root_odb, "libodb.so"))
        else:
            for entry in sorted(os.listdir(lib_dir)):
                if entry.startswith("libodb") and entry.endswith(".a"):
                    shutil.copy2(os.path.join(lib_dir, entry), os.path.join(odb_root_odb, entry))

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
    def _abs_paths(base, paths):
        result = []
        for path in paths:
            result.append(path if os.path.isabs(path) else os.path.join(base, path))
        return result

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False
