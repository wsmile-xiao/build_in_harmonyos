#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_package — libaribcaption 1.1.2
#
# Consumes the installed libaribcaption package through CMakeDeps and runs
# two real consumers:
#   test_package  (C API)    — decode + text/DRCS/malformed checks
#   test_cpp_api  (C++ API)  — Decoder/Caption std::string checks
#
# On OHOS (HarmonyOS PC) the shared build additionally:
#   - assembles a runtime closure directory (libaribcaption.so plus the
#     fontconfig/freetype/libxml2 libs renamed to their SONAMEs) and runs
#     the binaries with LD_LIBRARY_PATH (the harmonyos pc runs signed
#     aarch64 binaries natively);
#   - signs every binary and library with binary-sign-tool (.codesign);
#   - provides a generated fonts.conf + writable cache via FONTCONFIG_FILE /
#     XDG_CACHE_HOME pointing at /system/fonts so renderer-path checks can
#     resolve real CJK fonts.

import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


def _sign_tool():
    cand = os.path.expanduser("~/usr/local/bin/binary-sign-tool")
    if Path(cand).exists():
        return cand
    return shutil.which("binary-sign-tool")


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # --- OHOS helpers ---------------------------------------------------

    def _ohos_runtime_setup(self):
        """Assemble the runtime closure dir: package libs renamed to SONAMEs."""
        runlibs = Path(self.build_folder) / "runlibs"
        runlibs.mkdir(parents=True, exist_ok=True)
        for dep in self.dependencies.values():
            if not dep.cpp_info:
                continue
            for libdir in dep.cpp_info.libdirs:
                libdir = Path(libdir)
                for so in libdir.glob("*.so*"):
                    soname = self._soname_of(so)
                    if not soname:
                        continue
                    dst = runlibs / soname
                    if not dst.exists():
                        shutil.copy2(so, dst)
                        self._ohos_sign(dst)
        return runlibs

    def _soname_of(self, libpath):
        readelf = shutil.which("readelf")
        if not readelf:
            return None
        ret = subprocess.run([readelf, "-d", str(libpath)],
                             capture_output=True, text=True)
        for line in ret.stdout.splitlines():
            if "Library soname:" in line:
                return line.split("[")[-1].rstrip("]").strip()
        return None

    def _ohos_sign(self, path):
        sign = _sign_tool()
        if not sign:
            self.output.warning("binary-sign-tool not found, skipping signature")
            return
        out = str(path) + ".signed"
        ret = subprocess.run(
            [sign, "sign", "-inFile", str(path), "-outFile", out, "-selfSign", "1"],
            capture_output=True, text=True,
        )
        if ret.returncode == 0:
            os.replace(out, path)
            os.chmod(path, os.stat(path).st_mode | 0o111)
        else:
            self.output.warning(f"sign failed for {path.name}: {ret.stderr[:200]}")

    def _make_fonts_env(self, base: Path):
        fcdir = base / "fc" / "cache"
        fcdir.mkdir(parents=True, exist_ok=True)
        fonts_conf = base / "fc" / "fonts.conf"
        # HarmonyOS PC: /system/fonts ships NotoSansCJK but not the Japanese
        # broadcast families the renderer prefers; alias them (same file the
        # recipe uses for the upstream rendering tests).
        fonts_conf.write_text(
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
            '<fontconfig>\n'
            '  <dir>/system/fonts</dir>\n'
            f'  <cachedir>{fcdir}</cachedir>\n'
            '  <match target="pattern">\n'
            '    <test qual="any" name="family"><string>Hiragino Maru Gothic ProN</string></test>\n'
            '    <edit name="family" mode="prepend" binding="strong"><string>Noto Sans CJK JP</string></edit>\n'
            '  </match>\n'
            '  <match target="pattern">\n'
            '    <test qual="any" name="family"><string>Hiragino Sans</string></test>\n'
            '    <edit name="family" mode="prepend" binding="strong"><string>Noto Sans CJK JP</string></edit>\n'
            '  </match>\n'
            '  <match target="pattern">\n'
            '    <test qual="any" name="family"><string>YuGothic</string></test>\n'
            '    <edit name="family" mode="prepend" binding="strong"><string>Noto Sans CJK JP</string></edit>\n'
            '  </match>\n'
            '  <match target="pattern">\n'
            '    <test qual="any" name="family"><string>Rounded M+ 1m for ARIB</string></test>\n'
            '    <edit name="family" mode="prepend" binding="strong"><string>Noto Sans CJK JP</string></edit>\n'
            '  </match>\n'
            '</fontconfig>\n'
        )
        return {"FONTCONFIG_FILE": str(fonts_conf), "XDG_CACHE_HOME": str(fcdir)}

    # ---------------------------------------------------------------------

    def test(self):
        cmds = [str(Path(self.build_folder) / n) for n in ("test_package", "test_cpp_api")]

        if str(self.settings.os) == "OHOS":
            runlibs = self._ohos_runtime_setup()
            fonts_env = self._make_fonts_env(Path(self.build_folder))
            env = Environment()
            env.define("LD_LIBRARY_PATH", str(runlibs))
            for k, v in fonts_env.items():
                env.define(k, v)
            with env.vars(self).apply():
                for c in cmds:
                    self._ohos_sign(Path(c))
                    # NOTE: env="conanrun" is deliberately NOT used here: it
                    # would override the runlibs LD_LIBRARY_PATH closure that
                    # carries the signed SONAME-named libraries.
                    self.run(c)
        else:
            for c in cmds:
                self.run(c, env="conanrun")
