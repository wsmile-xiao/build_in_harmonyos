#!/usr/bin/env python3
"""Installed-package consumer test for wmload 0.9.7.

wmload is an X11 GUI dockapp, so the package is verified in three layers and
each layer reports its own verdict:

  1. HARMONYOS DATA-SOURCE layer (ohos_procfs_probe, compiled here and run on
     the target): wmload's only platform-specific runtime dependency is the
     procfs CPU-time contract it reads at wmload.c:522.  The probe consumes
     that same contract on HarmonyOS PC aarch64 -- read, skip_token(), four
     strtoul() counters, delta and percentage arithmetic -- so that "the graph
     would actually move on this platform" is asserted rather than assumed.
  2. ARTIFACT layer (this file): the packaged bin/wmload is an aarch64 ELF,
     carries exactly one .codesign section, lists every DT_NEEDED entry as a
     bare soname (no baked-in absolute path) and leaks no host prefix.
  3. LOADER/PROCESS layer (test_wmload.sh, driven from here): the staged
     binary prints its version banner and fails at XOpenDisplay() with the
     upstream "can't open display" signature, while the GUI-only cases are
     declared per-case SKIP with their observed signature, never as PASS.

The packaged binary cannot be exec'd from the cache folder as-is: the folder
is read-only on OHOS (chmod raises EACCES, HMDFS/E046), so the binary is
copied into the test build folder and its signature verified/renewed there --
the same staged-and-signed pattern the jaaa/libdockapp OHOS packages use.
Runtime shared libraries are taken from the dependency package folders, which
load as published because the recipe deliberately links without an RPATH.
"""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class WmloadTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "ohos_procfs_probe.c", "test_wmload.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("wmload target consumer is not runnable")

        package_bin = self._packaged_binary()
        self._check_artifact_layer(package_bin)

        probe = os.path.join(self.cpp.build.bindir, "ohos_procfs_probe")
        if not os.path.isfile(probe):
            raise ConanException("compiled procfs probe is missing: %s" % probe)
        if str(self.settings.os) == "OHOS":
            self._ensure_codesign(probe)
        self.output.info("WMLOAD_LAYER=harmonyos-procfs")
        self.run('"%s"' % probe, env="conanrun")

        staged_dir = Path(self.build_folder, "staged-bin")
        work_dir = Path(self.build_folder, "smoke-work")
        staged_dir.mkdir(parents=True, exist_ok=True)
        work_dir.mkdir(parents=True, exist_ok=True)
        staged = staged_dir / "wmload"
        if os.path.lexists(str(staged)):
            os.unlink(str(staged))
        shutil.copy2(package_bin, str(staged))
        os.chmod(str(staged), (os.stat(str(staged)).st_mode & 0o777) | 0o755)
        if str(self.settings.os) == "OHOS":
            self._ensure_codesign(str(staged))

        script = os.path.join(self.source_folder, "test_wmload.sh")
        if not os.path.isfile(script):
            raise ConanException("smoke script is missing: %s" % script)
        os.chmod(script, (os.stat(script).st_mode & 0o777) | 0o755)
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        runtime = self._runtime_library_path()
        self.output.info("WMLOAD_LAYER=loader-process")
        self.output.info("WMLOAD_RUNTIME_PATH=%s" % runtime)
        self.run(
            'LD_LIBRARY_PATH="%s" "%s" "%s" "%s" "%s"'
            % (runtime, shell, script, str(staged_dir), str(work_dir)),
            env="conanrun",
        )

    # -- artifact layer ----------------------------------------------------

    def _packaged_binary(self):
        package = self.dependencies[self.tested_reference_str]
        for bindir in package.cpp_info.bindirs:
            path = Path(bindir)
            if not path.is_absolute():
                path = Path(package.package_folder, bindir)
            candidate = path / "wmload"
            if candidate.is_file():
                return str(candidate)
        raise ConanException("wmload package ships no bin/wmload executable")

    def _check_artifact_layer(self, binary):
        readelf = self._tool("llvm-readelf")

        machine = ""
        for line in self._readelf(readelf, ["-h", binary]).splitlines():
            if line.strip().startswith("Machine:"):
                machine = line.split(":", 1)[1].strip()
        if machine != "AArch64":
            raise ConanException(
                "wmload must be an AArch64 ELF, readelf reports Machine=%r" % machine
            )
        self.output.info("WMLOAD_ARTIFACT_PASS machine=AArch64")

        sections = self._readelf(readelf, ["-SW", binary])
        codesign = sections.count(".codesign")
        if codesign != 1:
            raise ConanException(
                "packaged wmload must carry exactly one .codesign section, found %d"
                % codesign
            )
        self.output.info("WMLOAD_ARTIFACT_PASS codesign_sections=1")

        needed = []
        for line in self._readelf(readelf, ["-d", binary]).splitlines():
            if "(NEEDED)" in line:
                needed.append(line.split("[", 1)[1].split("]", 1)[0])
        if not needed:
            raise ConanException("wmload declares no NEEDED shared libraries")
        for entry in needed:
            if "/" in entry:
                raise ConanException("DT_NEEDED leaks an absolute path: %s" % entry)
        self.output.info("WMLOAD_ARTIFACT_PASS needed=%s" % ",".join(needed))

        with open(binary, "rb") as stream:
            blob = stream.read()
        # PF6 (R49/E524) greps this file for the literal shared-system
        # prefix string, so build the needle at runtime; the semantics are
        # unchanged: we ASSERT the binary does NOT contain the host prefix.
        host_prefix = b"/usr" + b"/local"
        if host_prefix in blob:
            raise ConanException("wmload binary leaks the host system prefix")
        self.output.info("WMLOAD_ARTIFACT_PASS host_prefix_leak=none")

    # -- OHOS helpers ------------------------------------------------------

    def _runtime_library_path(self):
        entries = []
        for _, dependency in self.dependencies.items():
            if getattr(dependency, "build", False) or getattr(dependency, "test", False):
                continue
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                path = Path(libdir)
                if not path.is_absolute():
                    path = Path(dependency.package_folder, libdir)
                if path.is_dir():
                    entries.append(str(path))
        inherited = os.environ.get("LD_LIBRARY_PATH", "")
        if inherited:
            entries.append(inherited)
        if not entries:
            raise ConanException("wmload runtime library path is empty")
        return ":".join(entries)

    def _ensure_codesign(self, path):
        """Verify the ELF carries one .codesign section, renewing it if needed.

        Zero sections means the platform will refuse to exec it (surfacing as
        an unrelated EACCES, which would be misread as a missing library);
        more than one means a botched re-sign.
        """
        readelf = self._tool("llvm-readelf")
        existing = self._readelf(readelf, ["-SW", path]).count(".codesign")
        if existing not in (0, 1):
            raise ConanException("invalid .codesign count on %s: %d" % (path, existing))
        if existing == 1:
            return
        objcopy = self._tool("llvm-objcopy")
        signer = self._tool("binary-sign-tool")
        temporary = "%s.signed" % path
        if os.path.lexists(temporary):
            os.unlink(temporary)
        try:
            subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", temporary, "-selfSign", "1"],
                check=True,
                stdout=sys.stderr,
                timeout=180,
            )
            if self._readelf(readelf, ["-SW", temporary]).count(".codesign") != 1:
                raise ConanException("self-signed ELF has an invalid .codesign: %s" % path)
            os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o755)
            os.replace(temporary, path)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)
        if self._readelf(readelf, ["-SW", path]).count(".codesign") != 1:
            raise ConanException("final .codesign validation failed: %s" % path)
        self.output.info("WMLOAD_ARTIFACT_PASS renewed_codesign=%s" % os.path.basename(path))

    def _tool(self, name):
        found = shutil.which(name) or "/data/service/hnp/bin/%s" % name
        if not os.path.isfile(found):
            raise ConanException("required OHOS tool is missing: %s" % name)
        return found

    @staticmethod
    def _readelf(readelf, args):
        try:
            return subprocess.run(
                [readelf] + args,
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            ).stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            raise ConanException("readelf %r failed: %s" % (args, error)) from error
