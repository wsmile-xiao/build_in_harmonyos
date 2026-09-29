#!/usr/bin/env python3
"""test_package — consumer verification for the pc6001vx application package.

Upstream ships no test suite at all (audited in test_package/MANIFEST.yml), so
this test_package carries the consumer-side evidence:

* packaging / HarmonyOS checks on the installed binary — AArch64 ELF64 PIE,
  musl interpreter, RELRO + non-executable stack, `.codesign` section (the
  recipe re-signs the binary), and the DT_NEEDED whitelist including the fact
  that SDL2 is linked statically for the joystick input path;
* test_pc6001vx.sh — the real headless smoke test that executes the freshly
  installed bin/PC6001VX (offscreen/minimal QPA plugins, --version/--help,
  argument errors, and the missing-platform-plugin diagnostic path).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class Pc6001vxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ------------------------------------------------------------------ tools
    @staticmethod
    def _tool(name):
        candidates = [shutil.which(name), os.path.join("/data/service/hnp/bin", name)]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None

    def _readelf(self, args):
        readelf = self._tool("readelf")
        if readelf is None:
            raise ConanInvalidConfiguration("readelf is required for the ELF checks")
        result = subprocess.run([readelf] + args, capture_output=True, text=True)
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                f"readelf {' '.join(args)} failed: {result.stderr.strip()}"
            )
        return result.stdout

    # ------------------------------------------------------------------ tests
    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        binary = os.path.join(dep.package_folder, "bin", "PC6001VX")

        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(f"installed binary missing: {binary}")
        if not os.access(binary, os.X_OK):
            raise ConanInvalidConfiguration(f"installed binary is not executable: {binary}")
        self.output.info("packaged binary: {}".format(binary))

        self._check_elf_header(binary)
        self._check_program_headers(binary)
        self._check_sections(binary)
        self._check_dynamic_dependencies(binary)
        self._check_sdl2_joystick(binary)

        # The CI worker is the target platform (OHOS PC aarch64, the same
        # machine class that runs qmake/moc/lrelease during the build), so the
        # packaged binary is executed directly. `can_run()` is deliberately not
        # consulted: the platform Conan configuration sets
        # `tools.build.cross_building:can_run=False`, which would silently skip
        # this smoke test instead of running it.
        bash = os.environ.get("CONFIG_SHELL") or self._tool("bash") or "/bin/sh"
        script = os.path.join(self.recipe_folder, "test_pc6001vx.sh")
        self.run(
            '{} "{}" "{}"'.format(bash, script, os.path.join(dep.package_folder, "bin")),
            env="conanrun",
        )

    def _check_elf_header(self, binary):
        with open(binary, "rb") as handle:
            header = handle.read(64)
        if header[:4] != b"\x7fELF":
            raise ConanInvalidConfiguration("bin/PC6001VX is not an ELF file")
        if header[4] != 2:
            raise ConanInvalidConfiguration("bin/PC6001VX is not ELF64")
        if header[5] != 1:
            raise ConanInvalidConfiguration("bin/PC6001VX is not little endian")
        # e_type at 0x10 (ET_DYN = 3 => PIE), e_machine at 0x12 (0xB7 = AArch64)
        if int.from_bytes(header[16:18], "little") != 3:
            raise ConanInvalidConfiguration("bin/PC6001VX is not a PIE executable (ET_DYN)")
        if int.from_bytes(header[18:20], "little") != 0xB7:
            raise ConanInvalidConfiguration("bin/PC6001VX is not built for AArch64 (e_machine)")
        self.output.info("ELF check: AArch64 ELF64 little endian PIE")

    def _check_program_headers(self, binary):
        headers = self._readelf(["-lW", binary])
        if "INTERP" not in headers or "ld-musl-aarch64.so.1" not in headers:
            raise ConanInvalidConfiguration(
                "bin/PC6001VX has no musl aarch64 interpreter"
            )
        if "GNU_RELRO" not in headers:
            raise ConanInvalidConfiguration("bin/PC6001VX is missing GNU_RELRO")
        stack_line = [line for line in headers.splitlines() if "GNU_STACK" in line]
        if not stack_line or " E " in stack_line[0]:
            raise ConanInvalidConfiguration(
                "bin/PC6001VX has an executable stack (NX missing)"
            )
        # readelf prints `Type: DYN (Position-Independent Executable file)`;
        # verify from the tool output as well, not only from the header bytes.
        if "DYN" not in self._readelf(["-h", binary]):
            raise ConanInvalidConfiguration("bin/PC6001VX is not a PIE executable")
        self.output.info("ELF check: PIE + RELRO + non-executable stack + musl interpreter")

    def _check_sections(self, binary):
        sections = self._readelf(["-SW", binary])
        if ".codesign" not in sections:
            raise ConanInvalidConfiguration(
                "bin/PC6001VX has no .codesign section (OHOS signature missing)"
            )
        self.output.info("ELF check: .codesign section present (binary re-signed for OHOS)")

    def _check_dynamic_dependencies(self, binary):
        dynamic = self._readelf(["-dW", binary])
        needed = []
        for line in dynamic.splitlines():
            if "(NEEDED)" in line and "[" in line:
                needed.append(line.split("[", 1)[1].split("]", 1)[0])
        if not needed:
            raise ConanInvalidConfiguration("bin/PC6001VX declares no DT_NEEDED entries")
        for entry in needed:
            if entry.startswith("/") or entry.startswith("../"):
                raise ConanInvalidConfiguration(
                    f"bin/PC6001VX has a non-portable DT_NEEDED entry: {entry}"
                )
        required = {
            "libQt6Core.so.6",
            "libQt6Gui.so.6",
            "libQt6Widgets.so.6",
            "libQt6Network.so.6",
            "libQt6Multimedia.so",
        }
        missing = sorted(required.difference(needed))
        if missing:
            raise ConanInvalidConfiguration(
                "bin/PC6001VX misses expected Qt libraries: " + ", ".join(missing)
            )
        # SDL2 is consumed as a static archive: it must not become a runtime
        # dependency of the emulator.
        sdl_runtime = [entry for entry in needed if entry.startswith("libSDL2")]
        if sdl_runtime:
            raise ConanInvalidConfiguration(
                "SDL2 must be linked statically, found: " + ", ".join(sdl_runtime)
            )
        self.output.info("ELF check: DT_NEEDED whitelist ok ({} entries, SDL2 static)"
                         .format(len(needed)))

    def _check_sdl2_joystick(self, binary):
        with open(binary, "rb") as handle:
            blob = handle.read()
        for symbol in (b"SDL_JoystickOpen", b"SDL_NumJoysticks"):
            if symbol not in blob:
                raise ConanInvalidConfiguration(
                    "SDL2 joystick support is missing from the packaged binary "
                    "(symbol {} not found)".format(symbol.decode())
                )
        self.output.info("ELF check: SDL2 joystick entry points linked in")
