#!/usr/bin/env python3
"""Consumer test for src-highlite 3.1.9.

Compiles a C++ consumer directly against the packaged srchilite library
(static) and its boost::regex dependency, then runs it against the packaged
language data directory. Direct-compile instead of CMakeDeps because the
package name contains a dash ("src-highlite"), which leaks into generated
CMake variable names and breaks the config (same approach as the
libodb-pgsql 2.4.0 precedent).
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class SrcHighliteTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        include_dirs = []
        lib_dirs = []
        libs = []
        system_libs = []
        for dep in self.dependencies.values():
            package_folder = dep.package_folder
            if package_folder is None:
                # Not materialized in this context (e.g. skipped auxiliary
                # dep) — nothing to add for compile/link.
                continue
            include_dirs.extend(
                self._absolute_paths(package_folder, dep.cpp_info.includedirs or ["include"])
            )
            lib_dirs.extend(
                self._absolute_paths(package_folder, dep.cpp_info.libdirs or ["lib"])
            )
            libs.extend(dep.cpp_info.libs or [])
            system_libs.extend(dep.cpp_info.system_libs or [])
            for component in dep.cpp_info.components.values():
                libs.extend(component.libs or [])
                system_libs.extend(component.system_libs or [])

        output = os.path.join(self.build_folder, "consumer_test")
        # The packaged headers use 2015-era dynamic exception specifications
        # (throw(X)); consumer must match the library's -std=c++14 build.
        command = [
            self._compiler("cpp"),
            os.path.join(self.source_folder, "test.cpp"),
        ]
        command.extend(f"-I{path}" for path in dict.fromkeys(include_dirs))
        command.extend(f"-L{path}" for path in dict.fromkeys(lib_dirs))
        if lib_dirs and self.settings.os in ("Linux", "OHOS"):
            command.append(f"-Wl,-rpath,{lib_dirs[0]}")
        command.extend(f"-l{lib}" for lib in dict.fromkeys(libs))
        command.extend(f"-l{lib}" for lib in dict.fromkeys(system_libs))
        command.extend(["-std=c++14", "-o", output])
        self.run(shlex.join(command), env="conanbuild")
        self.output.info("consumer_test compiled against libsrchilite/boost_regex")

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile/link test only")
            return

        dep = self.dependencies["src-highlite"]
        datadir = self._absolute_paths(
            dep.package_folder, dep.cpp_info.resdirs or []
        )[-1]
        test_bin = os.path.join(self.build_folder, "consumer_test")
        if self.settings.os == "OHOS":
            self._sign_executable(test_bin)
        self.run(shlex.join([test_bin, datadir]), env="conanrun")

    # ── helpers (libodb-pgsql 2.4.0 precedent) ──────────────────────────
    def _absolute_paths(self, package_folder, dirs):
        return [
            path if os.path.isabs(path) else os.path.join(package_folder, path)
            for path in dirs
        ]

    def _compiler(self, key):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        fallback = "clang++" if key in ("cpp", "cxx") else "clang"
        command = compilers.get(key) or fallback
        return self._resolve_command(command, fallback)

    def _resolve_command(self, command, fallback):
        basename = os.path.basename(command)
        for candidate in (
            command,
            os.path.join("/storage/Users/currentUser/usr/local/bin", basename),
            shutil.which(basename) or "",
            shutil.which(fallback) or "",
        ):
            resolved = shutil.which(candidate) or candidate
            if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                return resolved
        return fallback

    def _find_ohos_tool(self, name, aliases=()):
        for tool in (name,) + tuple(aliases):
            resolved = shutil.which(tool)
            if resolved:
                return resolved
        search_dirs = (
            "/data/service/hnp/bin",
            "/storage/Users/currentUser/usr/local/bin",
        )
        for directory in search_dirs:
            for tool in (name,) + tuple(aliases):
                candidate = os.path.join(directory, tool)
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
        return name

    def _sign_executable(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy", aliases=("objcopy",))
        signer = self._find_ohos_tool("binary-sign-tool")
        temporary = f"{path}.unsigned"
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
                    "-selfSign",
                    "1",
                    "-signAlg",
                    "SHA256withECDSA",
                    "-inFile",
                    temporary,
                    "-outFile",
                    path,
                ]
            )
        )
        if os.path.isfile(path):
            os.chmod(path, 0o755)
        if os.path.isfile(temporary):
            os.remove(temporary)
