#!/usr/bin/env python3
"""test_package for xqilla — consumer view (R34).

Builds test_xqilla against the packaged headers plus the propagated
xerces-c flags resolved from self.dependencies (compilers from Conan conf
per R33), signs every OHOS ELF, then runs test_xqilla.sh: the consumer API
test (XQilla parse/execute "1 to 100") plus the packaged xqilla CLI
(-h and a "1 to 3" query file). Counters track real executions; the HMBS
markers below report exactly those counters. Upstream ships no automated
suite (see MANIFEST.yml), so the upstream marker declares no_tests.
"""

import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class XqillaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.cpp", "test_xqilla.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_tool(self, configured, names):
        if configured and os.path.isfile(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                self.output.info(
                    "xqilla test: conf tool path unusable ({}), "
                    "fall back to PATH: {}".format(configured, found)
                )
                return found
        return configured or names[0]

    def _compilers(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = self._resolve_tool(
            compilers.get("cpp") or compilers.get("c"), ("clang++",)
        )
        return cxx

    def _include_dirs(self):
        seen = set()
        ordered = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            candidates = []
            candidates.extend(getattr(dep.cpp_info, "includedirs", []) or [])
            for component in getattr(dep.cpp_info, "components", {}).values():
                candidates.extend(getattr(component, "includedirs", []) or [])
            for entry in candidates:
                if not isinstance(entry, str) or not entry:
                    continue
                path = entry
                if not os.path.isabs(path):
                    path = os.path.normpath(
                        os.path.join(dep.package_folder, entry)
                    )
                if path not in seen and os.path.isdir(path):
                    seen.add(path)
                    ordered.append(path)
        return ordered

    def _link_flags(self):
        flags = []
        seen_dir = set()
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            candidates = []
            candidates.extend(getattr(dep.cpp_info, "libdirs", []) or [])
            for component in getattr(dep.cpp_info, "components", {}).values():
                candidates.extend(getattr(component, "libdirs", []) or [])
            for entry in candidates:
                if not isinstance(entry, str) or not entry:
                    continue
                path = entry
                if not os.path.isabs(path):
                    path = os.path.normpath(
                        os.path.join(dep.package_folder, entry)
                    )
                if path not in seen_dir and os.path.isdir(path):
                    seen_dir.add(path)
                    flags.append("-L{}".format(path))
        libs = []
        systems = []
        deps = sorted(
            self.dependencies.values(),
            key=lambda d: (0 if d.ref.name == "xqilla" else 1, d.ref.name),
        )
        for dep in deps:
            libs.extend(getattr(dep.cpp_info, "libs", []) or [])
            systems.extend(getattr(dep.cpp_info, "system_libs", []) or [])
            for component in getattr(dep.cpp_info, "components", {}).values():
                libs.extend(getattr(component, "libs", []) or [])
                systems.extend(getattr(component, "system_libs", []) or [])
        seen = set()
        for lib in libs:
            if lib not in seen:
                seen.add(lib)
                flags.append("-l{}".format(lib))
        seen_sys = set()
        for lib in systems:
            if lib not in seen_sys:
                seen_sys.add(lib)
                flags.append("-l{}".format(lib))
        return flags

    def _sign_program(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanException(
                "OHOS test execution requires binary-sign-tool: {}".format(path)
            )
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
        signed = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
            check=True,
        )
        os.replace(signed, path)
        os.chmod(
            path,
            stat.S_IMODE(os.stat(path).st_mode)
            | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
        )

    def build(self):
        cxx = self._compilers()
        cflags = ["-I{}".format(d) for d in self._include_dirs()]
        cflags.append("-std=c++14")
        cflags.append("-stdlib=libc++")
        ldflags = self._link_flags()
        ldflags.append("-stdlib=libc++")
        self.output.info("test_package cflags: {}".format(" ".join(cflags)))
        self.output.info("test_package ldflags: {}".format(" ".join(ldflags)))
        src = os.path.join(self.source_folder, "test.cpp")
        exe = os.path.join(self.build_folder, "test_xqilla")
        self.run(
            '{cxx} -o "{exe}" "{src}" {cflags} {ldflags}'.format(
                cxx=cxx, exe=exe, src=src,
                cflags=" ".join(cflags), ldflags=" ".join(ldflags),
            ),
            cwd=self.build_folder, env="conanbuild",
        )
        self._sign_program(exe)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: helper compiled and linked; execution skipped")
            return
        package = self.dependencies["xqilla"].package_folder
        binary = os.path.join(package, "bin", "xqilla")
        if not os.path.isfile(binary):
            raise ConanException(
                "The packaged xqilla binary was not found: {}".format(binary)
            )
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        driver = os.path.join(self.source_folder, "test_xqilla.sh")
        helper = os.path.join(self.build_folder, "test_xqilla")
        self.run(
            '{} "{}" "{}" "{}"'.format(shell, driver, binary, helper),
            env="conanrun",
        )
