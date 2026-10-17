#!/usr/bin/env python3
"""Functional test for the packaged gcc-11-cross 11.5.0 arm-none-eabi compiler.

gcc-11-cross ships a GNU GCC 11.5.0 C-only cross-compiler that runs on the
HarmonyOS PC aarch64 host (aarch64-linux-ohos) but emits bare-metal
arm-none-eabi objects/executables (built --enable-languages=c
--disable-bootstrap --with-newlib --without-headers).

No emulator exists and arm-none-eabi binaries cannot execute on the OHOS host.
The test therefore verifies the toolchain at the object/ELF level rather than
running the produced program: compile to .o at -O0 and -O2, link freestanding
against the libgcc shipped inside the package, then inspect the resulting ELF
with the target binutils (objdump/nm/size). This deliberately depends on the
real packaged compiler and libgcc (R34), so a stub or missing artifact cannot
pass. Mirrors the avr-gcc-bootstrap test_package approach.
"""

import os
import shlex
import stat
import subprocess
import tempfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class Gcc11CrossTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "smoke.c", "broken.c", "cpp_smoke.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("arm-none-eabi-binutils/2.46.1")

    @property
    def _compiler_root(self):
        return self.dependencies["gcc-11-cross"].package_folder

    @property
    def _binutils_root(self):
        return self.dependencies.build["arm-none-eabi-binutils"].package_folder

    def _tool(self, root, name):
        path = os.path.join(root, "bin", name)
        if not os.path.isfile(path):
            self._fail("Packaged tool was not found: {}".format(path))
        return path

    def _fail(self, message):
        self.output.error("FAIL: {}".format(message))
        raise ConanInvalidConfiguration(message)

    def _target_environment(self):
        environment = os.environ.copy()
        binutils_bin = os.path.join(self._binutils_root, "bin")
        environment["PATH"] = (
            binutils_bin + os.pathsep + environment.get("PATH", "")
        )
        return environment

    def _run(self, command):
        result = subprocess.run(
            command,
            cwd=self.build_folder,
            env=self._target_environment(),
            text=True,
            capture_output=True,
            check=False,
        )
        output = result.stdout + result.stderr
        if output.strip():
            self.output.info(output.strip())
        return result.returncode, output

    def _run_capture(self, command):
        returncode, output = self._run(command)
        if returncode != 0:
            self._fail(
                "Command exited with {}: {}".format(
                    returncode, " ".join(command)
                )
            )
        return output

    @staticmethod
    def _parse_text_size(output):
        for line in output.splitlines():
            tokens = line.split()
            if not tokens:
                continue
            try:
                value = int(tokens[0], 10)
            except ValueError:
                continue  # header line "text data bss dec hex filename"
            return value
        raise ConanInvalidConfiguration(
            "Could not parse a numeric text size from arm-none-eabi-size"
        )

    # ------------------------------------------------------------------ #
    # HarmonyOS-specific assertions (OH-1 .. OH-7)
    # ------------------------------------------------------------------ #
    def _readelf(self):
        import shutil

        for candidate in (
            "llvm-readelf",
            "readelf",
            "/data/service/hnp/bin/llvm-readelf",
            "/data/service/hnp/bin/readelf",
        ):
            resolved = shutil.which(candidate) or (
                candidate if os.path.isfile(candidate) else None
            )
            if resolved:
                return resolved
        self._fail("No readelf/llvm-readelf found to inspect ELF signatures")
        return None  # unreachable; _fail raises

    def _elf_sections(self, path):
        returncode, output = self._run([self._readelf(), "-S", str(path)])
        if returncode != 0:
            self._fail("readelf -S failed for {}".format(path))
        return output

    def _elf_header(self, path):
        returncode, output = self._run([self._readelf(), "-h", str(path)])
        if returncode != 0:
            self._fail("readelf -h failed for {}".format(path))
        return output

    def _run_ohos_specific_tests(self, compiler):
        """HarmonyOS platform mechanism checks (OH-1..OH-7).

        These verify the OHOS-specific mechanisms the recipe must provide for
        a cross compiler to work at all on HarmonyOS, complementing the
        functional assertions above:

          OH-1..OH-3  host executables (driver, cc1, collect2) carry a
                      ``.codesign`` section - OHOS refuses to exec unsigned
                      ELF, so an unsigned host tool would fail at runtime.
          OH-4        target objects stay unsigned REL files - only host
                      executables are signed; signing target objects would
                      break relocatable object consumption.
          OH-5        unprefixed as/ld/collect-ld/nm shims exist and are
                      executable, so the driver never falls back to the host
                      AArch64 assembler.
          OH-6..OH-7  the driver resolves as/ld through its own exec prefix
                      (in-package paths), not the bare host tool names.
        """
        libexec_dir = os.path.join(
            self._compiler_root, "libexec", "gcc", "arm-none-eabi", "11.5.0"
        )
        lib_dir = os.path.join(
            self._compiler_root, "lib", "gcc", "arm-none-eabi", "11.5.0"
        )

        # OH-1..OH-3: host executables are ELF-signed (OHOS rejects unsigned ELF)
        for label, rel in (
            ("gcc.real driver", os.path.join("bin", "arm-none-eabi-gcc.real")),
            ("cc1", os.path.join("libexec", "gcc", "arm-none-eabi", "11.5.0", "cc1")),
            (
                "collect2",
                os.path.join(
                    "libexec", "gcc", "arm-none-eabi", "11.5.0", "collect2"
                ),
            ),
        ):
            path = os.path.join(self._compiler_root, rel)
            if not os.path.isfile(path):
                self._fail(
                    "OHOS test: {} missing: {}".format(label, path)
                )
            sections = self._elf_sections(path)
            if ".codesign" not in sections:
                self._fail(
                    "OHOS test: {} has no .codesign section (unsigned host "
                    "ELF cannot exec on OHOS): {}".format(label, path)
                )

        # OH-4: target objects stay unsigned REL files
        crtbegin = os.path.join(lib_dir, "crtbegin.o")
        header = self._elf_header(crtbegin)
        if "REL" not in header or "Relocatable" not in header:
            self._fail(
                "OHOS test: crtbegin.o is not a REL relocatable: {}".format(
                    header.strip()
                )
            )
        sections = self._elf_sections(crtbegin)
        if ".codesign" in sections:
            self._fail(
                "OHOS test: target crtbegin.o was signed "
                "(only host tools must be signed)"
            )

        # OH-5: unprefixed target-tool shims exist and are executable
        for shim_name in ("as", "ld", "collect-ld", "nm"):
            shim = os.path.join(libexec_dir, shim_name)
            if not os.path.isfile(shim):
                self._fail(
                    "OHOS test: unprefixed shim missing: {}".format(shim)
                )
            mode = os.stat(shim).st_mode
            if not (mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                self._fail(
                    "OHOS test: unprefixed shim not executable: {}".format(shim)
                )

        # OH-6/OH-7: driver resolves as/ld to in-package exec-prefix paths
        for prog in ("as", "ld"):
            output = self._run_capture(
                [compiler, "-print-prog-name={}".format(prog)]
            )
            resolved = output.strip().splitlines()[-1].strip()
            resolved_real = os.path.realpath(resolved)
            root_real = os.path.realpath(self._compiler_root)
            if not os.path.isfile(resolved_real):
                self._fail(
                    "OHOS test: -print-prog-name={} resolved to a non-file: "
                    "{}".format(prog, resolved)
                )
            if os.path.commonpath([root_real, resolved_real]) != root_real:
                self._fail(
                    "OHOS test: -print-prog-name={} resolved OUTSIDE the "
                    "package: {}".format(prog, resolved)
                )
            if os.path.basename(resolved_real) != prog:
                self._fail(
                    "OHOS test: -print-prog-name={} resolved to {!r} instead "
                    "of {}".format(
                        prog, os.path.basename(resolved_real), prog
                    )
                )

    def _run_target_library_tests(self, compiler, objdump, nm):
        """Assertions for the target C library (newlib + libgloss) in the package.

        The package ships the bare-metal C library, so a hosted program must
        compile, link and resolve its startfiles and archives from inside the
        package — nothing may silently fall back to the host.
        """
        root = Path(self._compiler_root).resolve()
        build = Path(self.build_folder)
        hosted = build / "hosted_printf.c"
        hosted.write_text(
            "#include <stdio.h>\n"
            "int main(void) { printf(\"hosted-ok\\n\"); return 0; }\n",
            encoding="utf-8",
        )

        # (TL-1) C headers resolve to the packaged newlib
        preprocess = self._run_capture([compiler, "-E", "-xc", str(hosted)])
        if "No such file or directory" in preprocess or "error:" in preprocess:
            self._fail("Packaged C headers were not usable for #include <stdio.h>")

        # (TL-2) (TL-3) startfile and archive resolution stays inside the package
        for name in ("crt0.o", "libc.a"):
            resolved = self._run_capture(
                [compiler, "-print-file-name=" + name]
            ).strip()
            if not resolved:
                self._fail("-print-file-name={} returned nothing".format(name))
            candidate = Path(resolved)
            if not candidate.is_file():
                self._fail(
                    "-print-file-name={} does not exist: {}".format(name, resolved)
                )
            if root not in candidate.resolve().parents:
                self._fail(
                    "-print-file-name={} resolved outside the package: {}".format(
                        name, resolved
                    )
                )

        # (TL-4) a hosted program links into an ARM ELF32 executable carrying
        # the packaged libc's printf
        hosted_elf = build / "hosted_printf.elf"
        self._run([compiler, "-std=c17", str(hosted), "-o", str(hosted_elf)])
        header = self._run_capture([objdump, "-f", str(hosted_elf)])
        if "elf32-littlearm" not in header and "elf32-little" not in header:
            self._fail("Hosted program did not link into an ARM ELF32 executable")
        symbols = self._run_capture([nm, str(hosted_elf)])
        defined = set()
        for line in symbols.splitlines():
            tokens = line.split()
            if len(tokens) >= 3 and tokens[-2].upper() == "T":
                defined.add(tokens[-1])
        # GCC rewrites printf("literal\n") into puts(), so accept any of the
        # stdio entry points newlib actually provides rather than only printf.
        stdio_entry_points = {
            "printf", "_printf_r", "puts", "_puts_r", "putchar", "_putchar_r",
            "iprintf", "_iprintf_r", "fputs", "_fputs_r",
        }
        if not (defined & stdio_entry_points):
            self._fail(
                "Linked hosted program has no stdio entry point from the "
                "packaged C library (looked for: {})".format(
                    ", ".join(sorted(stdio_entry_points))
                )
            )

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: packaged OHOS host compiler cannot run on "
                "this host - skipping gcc-11-cross smoke test"
            )
            return

        compiler = self._tool(self._compiler_root, "arm-none-eabi-gcc")
        objdump = self._tool(self._binutils_root, "arm-none-eabi-objdump")
        nm = self._tool(self._binutils_root, "arm-none-eabi-nm")
        size = self._tool(self._binutils_root, "arm-none-eabi-size")

        source = Path(self.source_folder) / "smoke.c"
        broken = Path(self.source_folder) / "broken.c"
        for src in (source, broken):
            if not src.is_file():
                self._fail("Test source not found: {}".format(src))

        build = Path(
            tempfile.mkdtemp(
                prefix="gcc-11-cross-test-",
                dir=self.build_folder,
            )
        )

        # (1) --version reports 11.5.0.  This runs through Conan's own
        # ``self.run`` (CI gate L0d requires test() to drive a real command
        # rather than only inspecting state) with the output redirected so the
        # assertion below can still inspect the reported version.
        version_log = build / "gcc-version.txt"
        self.run(
            "{} --version > {}".format(
                shlex.quote(compiler), shlex.quote(str(version_log))
            ),
            env="conanrun",
        )
        version = version_log.read_text(encoding="utf-8", errors="replace")
        first_line = version.splitlines()[0] if version.strip() else ""
        if "11.5.0" not in version:
            self._fail("Unexpected arm-none-eabi-gcc version: {}".format(first_line))

        # (2) -dumpmachine is exactly arm-none-eabi
        machine_output = self._run_capture([compiler, "-dumpmachine"])
        machine = machine_output.strip().splitlines()[-1].strip()
        if machine != "arm-none-eabi":
            self._fail(
                "-dumpmachine returned {!r}, expected 'arm-none-eabi'".format(
                    machine
                )
            )

        # (3) -print-libgcc-file-name resolves libgcc.a inside the package folder
        libgcc_output = self._run_capture([compiler, "-print-libgcc-file-name"])
        libgcc = os.path.realpath(libgcc_output.strip().splitlines()[-1])
        compiler_root = os.path.realpath(self._compiler_root)
        if not os.path.isfile(libgcc):
            self._fail("arm-none-eabi-gcc did not resolve libgcc.a: {}".format(libgcc))
        if os.path.basename(libgcc) != "libgcc.a":
            self._fail("Resolved runtime library is not libgcc.a: {}".format(libgcc))
        if os.path.commonpath([compiler_root, libgcc]) != compiler_root:
            self._fail(
                "arm-none-eabi-gcc selected libgcc outside its package: {}".format(
                    libgcc
                )
            )

        # (4) smoke.c compiles at -O0 and -O2, both non-empty
        obj_o0 = build / "smoke_O0.o"
        obj_o2 = build / "smoke_O2.o"
        self._run_capture(
            [compiler, "-std=c17", "-O0", "-c", str(source), "-o", str(obj_o0)]
        )
        self._run_capture(
            [compiler, "-std=c17", "-O2", "-c", str(source), "-o", str(obj_o2)]
        )
        for obj in (obj_o0, obj_o2):
            if not obj.is_file() or obj.stat().st_size == 0:
                self._fail("Empty object produced: {}".format(obj))

        # (5) freestanding link yields a non-empty ELF
        elf = build / "smoke.elf"
        self._run_capture(
            [
                compiler,
                "-std=c17",
                "-O2",
                "-nostdlib",
                "-nostartfiles",
                "-Wl,-e,_start",
                str(source),
                "-lgcc",
                "-o",
                str(elf),
            ]
        )
        if not elf.is_file() or elf.stat().st_size == 0:
            self._fail("Freestanding link produced no ELF image: {}".format(elf))

        # (6) objdump -f shows elf32-littlearm AND architecture arm
        file_header = self._run_capture([objdump, "-f", str(elf)])
        if (
            "elf32-littlearm" not in file_header
            and "elf32-little" not in file_header
        ):
            self._fail("objdump did not identify elf32-littlearm")
        if "architecture: arm" not in file_header:
            self._fail("objdump did not identify the arm architecture")

        # (7) nm shows _start AND a libgcc division helper
        symbols = self._run_capture([nm, str(elf)])
        defined = {
            line.split()[-1]
            for line in symbols.splitlines()
            if line.split()
        }
        if "_start" not in defined:
            self._fail("Linked ELF does not define the _start entry point")
        if not any(name.startswith("__aeabi_") for name in defined) and (
            "__udivsi3" not in defined
        ):
            self._fail(
                "Linked ELF did not consume a packaged libgcc division helper "
                "(__aeabi_* / __udivsi3)"
            )

        # (8) size text column parsed and > 0
        size_output = self._run_capture([size, str(elf)])
        text_size = self._parse_text_size(size_output)
        if text_size <= 0:
            self._fail(
                "arm-none-eabi-size reported a non-positive text size: {}".format(
                    size_output.strip()
                )
            )

        # (9) broken.c compile exits non-zero (negative control)
        broken_obj = build / "broken.o"
        returncode, _ = self._run(
            [compiler, "-std=c17", "-c", str(broken), "-o", str(broken_obj)]
        )
        if returncode == 0:
            self._fail("Compiler accepted deliberately invalid source broken.c")

        # (10) -mcpu=cortex-m3 accepted, object still elf32-littlearm
        cm3_obj = build / "smoke_cortex_m3.o"
        self._run_capture(
            [
                compiler,
                "-std=c17",
                "-mcpu=cortex-m3",
                "-c",
                str(source),
                "-o",
                str(cm3_obj),
            ]
        )
        cm3_header = self._run_capture([objdump, "-f", str(cm3_obj)])
        if (
            "elf32-littlearm" not in cm3_header
            and "elf32-little" not in cm3_header
        ):
            self._fail("-mcpu=cortex-m3 object is not elf32-littlearm")

        # (11) C++ frontend and libstdc++: compile, link and symbol check.
        # Requires the packaged C++ driver and the libstdc++ archive built with
        # --enable-languages=c,c++; the linked ELF must carry basic_string/vector
        # machinery resolved from the package.
        # -lstdc++: this cross driver does not add libstdc++ automatically
        # (its specs carry no LIBSTDCXX rule for the bare-metal target), so the
        # link must request it explicitly.
        # No _POSIX_THREADS/_UNIX98_THREAD_MUTEX_ATTRIBUTES are needed: the
        # compiler is built with --disable-threads, so the C++ headers use
        # libstdc++'s single-thread gthr-single.h, which never includes
        # <pthread.h>.
        cpp_source = Path(self.source_folder) / "cpp_smoke.cpp"
        if not cpp_source.is_file():
            self._fail("Test source not found: {}".format(cpp_source))
        cpp_elf = build / "cpp_smoke.elf"
        self._run_capture(
            [
                compiler,
                "-x", "c++",
                "-std=c++17",
                "-O2",
                str(cpp_source),
                "-lstdc++",
                "-o",
                str(cpp_elf),
            ]
        )
        if not cpp_elf.is_file() or cpp_elf.stat().st_size == 0:
            self._fail("C++ link produced no ELF image: {}".format(cpp_elf))
        cpp_header = self._run_capture([objdump, "-f", str(cpp_elf)])
        if (
            "elf32-littlearm" not in cpp_header
            and "elf32-little" not in cpp_header
        ):
            self._fail("C++ ELF is not elf32-littlearm")
        cpp_symbols = self._run_capture([nm, str(cpp_elf)])
        # libstdc++ machinery: basic_string (std::string) is the most stable
        # marker across GCC 11's C++11 ABI; vector push_back and operator new
        # are the other members of the same runtime.
        libstdcpp_markers = ("basic_string", "St6vector", "_Znwm")
        if not any(marker in cpp_symbols for marker in libstdcpp_markers):
            self._fail(
                "C++ ELF carries no libstdc++ symbol (looked for: {})".format(
                    ", ".join(libstdcpp_markers)
                )
            )

        # HarmonyOS platform mechanism checks (OH-1..OH-7)
        self._run_ohos_specific_tests(compiler)

        # Target C library shipped with the package (TL-1..TL-4)
        self._run_target_library_tests(compiler, objdump, nm)

        self.output.info(
            "PASS: gcc-11-cross 11.5.0 arm-none-eabi functional smoke test "
            "(version, triplet, packaged libgcc, -O0/-O2 compile, freestanding "
            "link, ELF machine/arch, _start + libgcc division symbol, size, "
            "negative control, cortex-m3, C++17 link + libstdc++ symbols) - "
            "11 assertions; "
            "HarmonyOS-specific checks (host ELF .codesign, unsigned target "
            "objects, unprefixed as/ld/collect-ld/nm shims, in-package "
            "-print-prog-name=as/ld) - 7 assertions; "
            "target C library checks (packaged newlib headers, in-package "
            "crt0.o/libc.a resolution, hosted link to ARM ELF32, libc printf "
            "linked) - 4 assertions"
        )
