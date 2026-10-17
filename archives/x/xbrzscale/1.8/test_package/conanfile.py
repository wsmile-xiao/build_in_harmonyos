#!/usr/bin/env python3
"""test_package for xbrzscale — consumer view (R34).

Builds three helpers against the packaged artifacts (headers +
libxbrzscale.a plus the propagated SDL2/SDL2_image flags resolved from
self.dependencies, compilers from Conan conf per R33), signs every OHOS
ELF, then runs test_xbrzscale.sh: 9 end-to-end cases covering CLI argument
validation, 2x/3x PNG file scaling with dimension checks, and the
in-memory libxbrzscale API test (6 assertions in test_lib).
"""

import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class XbrzscaleTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = (
        "test_lib.cpp",
        "test_makepng.c",
        "test_checkpng.c",
        "test_xbrzscale.sh",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Consumer-side explicit transitive deps (aligned with the main
        # recipe): libxbrzscale.h publicly pulls SDL/SDL_image headers, so
        # the test helpers must resolve the same sdl2/sdl2_image revisions
        # directly instead of relying on implicit propagation. sdl2_image
        # installs headers to include/SDL2, hence the <SDL.h>/<SDL_image.h>
        # spelling (its own test_package precedent); the test sources keep
        # a __has_include fallback to <SDL2/...> for either layout.
        self.requires("sdl2/2.30.10.1")
        self.requires("sdl2_image/2.6.0.1")

    def _resolve_tool(self, configured, names):
        # Same worker-path fallback as the main recipe: the conf compiler
        # path may be inaccessible on the executing worker (Error 127).
        if configured and os.path.isfile(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                self.output.info(
                    "xbrzscale test: conf tool path unusable ({}), "
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
        cc = self._resolve_tool(compilers.get("c"), ("clang",))
        return cxx, cc

    def _include_dirs(self):
        seen = set()
        ordered = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                # Override-only / unresolved node: contributes no paths.
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
            key=lambda d: (0 if d.ref.name == "xbrzscale" else 1, d.ref.name),
        )
        for dep in deps:
            libs.extend(getattr(dep.cpp_info, "libs", []) or [])
            systems.extend(getattr(dep.cpp_info, "system_libs", []) or [])
            for comp_name, component in getattr(
                dep.cpp_info, "components", {}
            ).items():
                if dep.ref.name == "sdl2" and comp_name != "SDL2":
                    continue
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
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
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
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH,
        )

    def build(self):
        cxx, cc = self._compilers()
        cflags = ["-I{}".format(d) for d in self._include_dirs()]
        cflags.append("-D_REENTRANT")
        ldflags = self._link_flags()
        self.output.info("test_package cflags: {}".format(" ".join(cflags)))
        self.output.info("test_package ldflags: {}".format(" ".join(ldflags)))

        def compile_one(compiler, std, src, exe, extra_libs):
            cmd = "{comp} {std} {src} -o {exe} {cflags} {ldflags} {extra}".format(
                comp=compiler,
                std=std,
                src=src,
                exe=exe,
                cflags=" ".join(cflags),
                ldflags=" ".join(ldflags),
                extra=" ".join(extra_libs),
            )
            self.run(cmd, cwd=self.build_folder, env="conanbuild")

        srcdir = self.source_folder
        builddir = self.build_folder
        compile_one(
            cxx,
            "-std=c++17",
            os.path.join(srcdir, "test_lib.cpp"),
            os.path.join(builddir, "test_lib"),
            [],
        )
        compile_one(
            cc,
            "-std=c11",
            os.path.join(srcdir, "test_makepng.c"),
            os.path.join(builddir, "test_makepng"),
            [],
        )
        compile_one(
            cc,
            "-std=c11",
            os.path.join(srcdir, "test_checkpng.c"),
            os.path.join(builddir, "test_checkpng"),
            [],
        )
        for helper in ("test_lib", "test_makepng", "test_checkpng"):
            self._sign_program(os.path.join(builddir, helper))

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: helpers compiled and linked; execution skipped"
            )
            return
        package = self.dependencies["xbrzscale"].package_folder
        binary = os.path.join(package, "bin", "xbrzscale")
        if not os.path.isfile(binary):
            raise ConanException(
                "The packaged xbrzscale binary was not found: {}".format(binary)
            )
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        driver = os.path.join(self.source_folder, "test_xbrzscale.sh")
        self.run(
            '{} "{}" "{}" "{}"'.format(shell, driver, binary, self.build_folder),
            env="conanrun",
        )
