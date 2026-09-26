#!/usr/bin/env python3
"""Conan test_package for libambix/0.1.2.

Builds and runs a small C consumer that exercises the installed libambix
API (channel-count utilities and the matrix helpers) without needing any
audio fixture files.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibambixTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_compiler(self, conf_key, names):
        """Prefer the profile-configured compiler only if it really exists.

        The ohos-aarch64 profile bakes ``/data/service/hnp/bin/clang``
        into ``tools.build:compiler_executables`` and the generated
        conan_toolchain.cmake, but that path is "inaccessible or not
        found" on the preflight host (this round's evidence); the real
        compiler lives on PATH (harmonybrew clang). Keep the configured
        value when its first token is an existing file, else fall back
        to PATH lookup (cubelib/4.9.1 precedent). Never aborts.
        """
        try:
            conf = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        configured = None
        try:
            configured = conf.get(conf_key)
        except Exception:
            configured = None
        if configured:
            first = str(configured).split()[0].strip("\"'")
            try:
                if first and os.path.isfile(first):
                    self.output.info("libambix test_package keeps configured %s=%s"
                                     % (conf_key, configured))
                    return str(configured).strip()
            except OSError:
                pass
            self.output.info("libambix test_package configured %s=%s missing, PATH fallback"
                             % (conf_key, configured))
        for name in names:
            found = shutil.which(name)
            if found:
                self.output.info("libambix test_package %s PATH fallback: %s" % (conf_key, found))
                return found
        self.output.info("libambix test_package %s bare fallback: %s" % (conf_key, names[0]))
        return names[0]

    def _scrub_toolchain_stale_compilers(self, cc, cxx):
        """Replace stale hnp compiler paths baked into conan_toolchain.cmake.

        Double insurance next to the explicit -D overrides in build():
        only rewrites when the stale path is referenced AND missing on
        this host, so a healthy CI worker keeps its own compiler.
        """
        try:
            toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        except Exception:
            return
        try:
            if not (toolchain and os.path.isfile(toolchain)):
                return
            with open(toolchain, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return
        rewrote = False
        for stale, good in (("/data/service/hnp/bin/clang", cc),
                            ("/data/service/hnp/bin/clang++", cxx)):
            if stale in content:
                try:
                    missing = not os.path.isfile(stale)
                except OSError:
                    missing = True
                if missing and good and good != stale:
                    content = content.replace(stale, good)
                    rewrote = True
                    self.output.info("libambix test_package scrubbed stale %s -> %s"
                                     % (stale, good))
        if rewrote:
            try:
                with open(toolchain, "w", encoding="utf-8") as f:
                    f.write(content)
            except OSError:
                pass

    def build(self):
        cc = self._resolve_compiler("c", ("clang", "cc", "gcc"))
        cxx = self._resolve_compiler("cpp", ("clang++", "c++", "g++"))
        self._scrub_toolchain_stale_compilers(cc, cxx)
        self.output.info("libambix test_package CMAKE_C_COMPILER=%s CMAKE_CXX_COMPILER=%s"
                         % (cc, cxx))
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": cc,
                                   "CMAKE_CXX_COMPILER": cxx})
        cmake.build()

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException("Missing consumer executable: " + path)
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".libambix-signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed consumer has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def test(self):
        if not can_run(self):
            raise Exception("test_package requires running the built binary")
        executable = os.path.join(self.cpp.build.bindir, "test_libambix")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(executable)
        command = executable
        # The C program performs 6 ordered CHECKs (see test.c); the marker
        # must carry those real counts for the device-test gate.
        result = {
            "executed": True,
            "passed": False,
            "command": command,
            "discovered": 6,
            "passedCount": 0,
        }
        try:
            self.run(command, env="conanrun")
        except Exception:
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
            )
            raise
        result["passed"] = True
        result["passedCount"] = 6
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
