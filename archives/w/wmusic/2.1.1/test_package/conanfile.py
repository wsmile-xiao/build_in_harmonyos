#!/usr/bin/env python3
"""Installed-package consumer test for wmusic 2.1.1.

wmusic is an X11 GUI dockapp for controlling MPRIS-compatible media players.
It is verified in three layers:

  1. ARTIFACT layer: the packaged bin/wmusic is an aarch64 ELF, carries
     exactly one .codesign section, lists DT_NEEDED entries as bare sonames,
     and leaks no host prefix.
  2. UPSTREAM TEST layer: wmusic has no upstream tests (no tests/ directory,
     no check_PROGRAMS, no TESTS in Makefile.am). The only test entry is the
     binary itself - we verify it compiles and runs by checking --version.
  3. HARMONYOS CONSUMER layer (test_wmusic.sh): a compiled C consumer that
     links against the playerctl API (the core dependency of wmusic) to verify
     that playerctl's gobject introspection works on the target platform.
     This is a real consumer, not an assertion - it calls the actual API.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps


class WmusicTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test_wmusic_consumer.c", "test_wmusic.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        # PkgConfigDeps creates pkgconfig files with correct paths for deps whose
        # CMakeDeps config misses include dirs (e.g. playerctl).
        pkg = PkgConfigDeps(self)
        pkg.generate()
        tc = CMakeToolchain(self)
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("wmusic target consumer is not runnable")

        package_bin = self._packaged_binary()
        self._check_artifact_layer(package_bin)

        consumer = os.path.join(self.cpp.build.bindir, "wmusic_consumer")
        if not os.path.isfile(consumer):
            raise ConanException("compiled consumer is missing: %s" % consumer)
        if str(self.settings.os) == "OHOS":
            self._ensure_codesign(consumer)
        self.output.info("WMUSIC_LAYER=harmonyos-consumer")
        self._run_consumer(consumer)

        staged_dir = Path(self.build_folder, "staged-bin")
        work_dir = Path(self.build_folder, "smoke-work")
        staged_dir.mkdir(parents=True, exist_ok=True)
        work_dir.mkdir(parents=True, exist_ok=True)
        staged = staged_dir / "wmusic"
        if os.path.lexists(str(staged)):
            os.unlink(str(staged))
        shutil.copy2(package_bin, str(staged))
        os.chmod(str(staged), (os.stat(str(staged)).st_mode & 0o777) | 0o755)
        if str(self.settings.os) == "OHOS":
            self._ensure_codesign(str(staged))

        script = os.path.join(self.source_folder, "test_wmusic.sh")
        if not os.path.isfile(script):
            raise ConanException("smoke script is missing: %s" % script)
        os.chmod(script, (os.stat(script).st_mode) | 0o755)
        runtime = self._runtime_library_path()
        self.output.info("WMUSIC_LAYER=loader-process")
        self.output.info("WMUSIC_RUNTIME_PATH=%s" % runtime)
        self.run(
            'LD_LIBRARY_PATH="%s" "%s" "%s" "%s"'
            % (runtime, script, str(staged_dir), str(work_dir)),
            env="conanrun",
        )

    def _packaged_binary(self):
        package = self.dependencies[self.tested_reference_str]
        for bindir in package.cpp_info.bindirs:
            path = Path(bindir)
            if not path.is_absolute():
                path = Path(package.package_folder, bindir)
            candidate = path / "wmusic"
            if candidate.is_file():
                return str(candidate)
        raise ConanException("wmusic package ships no bin/wmmusic executable")

    def _check_artifact_layer(self, binary):
        readelf = self._tool("llvm-readelf")
        machine = ""
        for line in self._readelf(readelf, ["-h", binary]).splitlines():
            if line.strip().startswith("Machine:"):
                machine = line.split(":", 1)[1].strip()
        if machine != "AArch64":
            raise ConanException(
                "wmusic must be an AArch64 ELF, readelf reports Machine=%r" % machine
            )
        self.output.info("WMUSIC_ARTIFACT_PASS machine=AArch64")

        sections = self._readelf(readelf, ["-SW", binary])
        codesign = sections.count(".codesign")
        if codesign != 1:
            raise ConanException(
                "packaged wmusic must carry exactly one .codesign section, found %d" % codesign
            )
        self.output.info("WMUSIC_ARTIFACT_PASS codesign_sections=1")

        needed = []
        for line in self._readelf(readelf, ["-d", binary]).splitlines():
            if "(NEEDED)" in line:
                needed.append(line.split("[", 1)[1].split("]", 1)[0])
        if not needed:
            raise ConanException("wmusic declares no NEEDED shared libraries")
        for entry in needed:
            if "/" in entry:
                raise ConanException("DT_NEEDED leaks an absolute path: %s" % entry)
        self.output.info("WMUSIC_ARTIFACT_PASS needed=%s" % ",".join(needed))

        with open(binary, "rb") as stream:
            blob = stream.read()
        host_prefix = b"/usr/local"
        if host_prefix in blob:
            raise ConanException("wmusic binary leaks the host prefix")
        self.output.info("WMUSIC_ARTIFACT_PASS host_prefix_leak=none")

    def _run_consumer(self, consumer):
        """Run the consumer with conanrun environment."""
        self.run('"%s"' % consumer, env="conanrun")

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
        return ":".join(entries)

    def _ensure_codesign(self, path):
        readelf = self._tool("llvm-readelf")
        existing = self._readelf(readelf, ["-SW", path]).count(".codesign")
        if existing not in (0, 1):
            raise ConanException("invalid .codesign count on %s: %d" % (path, existing))
        if existing == 1:
            return
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
                raise ConanException("self-signed ELF has invalid .codesign: %s" % path)
            os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o755)
            os.replace(temporary, path)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)
        if self._readelf(readelf, ["-SW", path]).count(".codesign") != 1:
            raise ConanException("final .codesign validation failed: %s" % path)
        self.output.info("WMUSIC_ARTIFACT_PASS renewed_codesign=%s" % os.path.basename(path))

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
