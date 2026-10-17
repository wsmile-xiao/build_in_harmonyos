#!/usr/bin/env python3
"""Conan test_package for libsecret 0.21.8 — Conan L1 official test.

Consumer-perspective verification:
  1. builds test_package.c against the packaged headers + libsecret-1.so
     (pkg-config driven, same resolution meson/cmake consumers use);
  2. runs it on the OHOS host (version macros, attribute schema builder,
     SecretValue lifecycle, well-known schemas);
  3. smoke-runs the shipped secret-tool binary end-to-end through the
     file backend (store/lookup/clear on a temp keyring).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


class LibsecretTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _pkgconfig(self, what):
        pc = "libsecret-1"
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = self.generators_folder + os.pathsep + env.get("PKG_CONFIG_PATH", "")
        exe = shutil.which("pkg-config", path=env.get("PATH", os.defpath))
        if not exe:
            for cand in ("/data/service/hnp/bin/pkg-config", "/usr/bin/pkg-config"):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    exe = cand
                    break
        if not exe:
            return ""
        try:
            out = subprocess.run([exe, what, pc], capture_output=True,
                                 text=True, env=env, timeout=60)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return ""

    def build(self):
        if not can_run(self):
            return
        dep = self.dependencies["libsecret"]
        cflags = self._pkgconfig("--cflags")
        if not cflags:
            # fallback: assemble include dirs from the dependency graph
            incs = []
            for ref, d in self.dependencies.items():
                for inc in d.cpp_info.includedirs:
                    incs.append(os.path.join(d.package_folder, inc) if not os.path.isabs(inc) else inc)
            cflags = " ".join(f"-I{p}" for p in incs)
        libs = self._pkgconfig("--libs")
        if not libs:
            libdir = os.path.join(dep.package_folder, "lib")
            libs = f"-L{libdir} -lsecret-1"
        cc = (self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}).get("c", "clang")
        src = os.path.join(self.source_folder, "test_package.c")
        out = os.path.join(self.build_folder, "test_package")
        self.run(f'{cc} {cflags} "{src}" -o "{out}" {libs} -Wl,--no-as-needed -Wl,--allow-shlib-undefined', env="conanbuild")

    def test(self):
        if not can_run(self):
            self.output.warning("cross-building: skipping runtime test")
            return
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(f'{bash} -c "./test_package"', env="conanrun")
        # secret-tool end-to-end smoke through the file backend (same env the
        # upstream test-secret-tool.sh uses: SECRET_BACKEND=file).
        self.run(
            f'{bash} -c \'export SECRET_BACKEND=file SECRET_FILE_TEST_PASSWORD=test '
            'KEYRING="$(mktemp -d)/keyring" SECRET_FILE_TEST_PATH="$KEYRING"; '
            'echo libsecret-test | secret-tool store --label smoke com.example libsecret;'
            'GOT="$(secret-tool lookup com.example libsecret)"; '
            '[ "$GOT" = "libsecret-test" ] || { echo "FAIL: lookup got [$GOT]"; exit 1; }; '
            'secret-tool clear com.example libsecret; '
            'AFTER="$(secret-tool lookup com.example libsecret)"; '
            '[ -z "$AFTER" ] || { echo "FAIL: clear left [$AFTER]"; exit 1; }; '
            'echo "secret-tool file-backend smoke: PASS"\'',
            env="conanrun",
        )
