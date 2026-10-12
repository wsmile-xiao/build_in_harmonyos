#!/usr/bin/env python3
"""Consumer / HarmonyOS-specific feasibility test for the opari package.

This test proves the WHOLE opari pipeline is usable on aarch64 OpenHarmony:

  1. Run the packaged ``opari`` tool to instrument a C OpenMP program
     (source-to-source rewrite -> ``consumer.ohos.mod.c`` + ``.opari.inc``).
  2. Compile the instrumented source together with a minimal POMP runtime-table
     definition (``pomp_rt.c``), using the OHOS clang with ``-fopenmp``.
  3. Link against libpomp (opari runtime, from the package) and libomp (OHOS
     OpenMP runtime). The OHOS clang embeds RUNPATH to the SDK llvm/lib, so
     libomp.so resolves at runtime without extra LD_LIBRARY_PATH.
  4. Run the binary on aarch64 OHOS and check the reduction result.

The ``test()`` method then asserts the **HarmonyOS-specific mechanisms** (not
just "it ran"), so this case is falsifiable — it cannot pass on a non-OHOS
host:

  A. Platform gate: ``settings.os == "OHOS"`` and ``settings.arch == "armv8"``.
  B. Target-architecture gate: the produced executable must be an ELF64
     AArch64 object (EM_AARCH64 == 183), i.e. built for the OHOS PC target.
  C. OHOS OpenMP runtime gate: the instrumented program must emit POMP region
     events (``begin parallel`` / ``enter for`` / ``finalize``) produced by the
     OHOS libomp worker threads, not merely the correct arithmetic result.

All work happens in the build folder (never in the source tree), so the
checkout stays clean. The test genuinely depends on the package: if the opari
tool, libpomp, or the OpenMP runtime were broken, build/link/run would fail
(R34 — W3 confirmed this with the L1e destructive negative test).
"""
import io
import os
import re
import struct

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.layout import basic_layout

# ELF constants used by the target-architecture assertion.
ELFCLASS64 = 2
EM_AARCH64 = 183


def _read_elf_identity(path):
    """Return (ei_class, e_machine) parsed from an ELF file header.

    Pure-Python parsing: no external readelf binary is needed, so the
    assertion works anywhere the package is consumed.
    """
    with open(path, "rb") as fh:
        hdr = fh.read(64)
    if len(hdr) < 20 or hdr[:4] != b"\x7fELF":
        return (None, None)
    ei_class = hdr[4]
    e_machine = struct.unpack_from("<H", hdr, 18)[0]
    return (ei_class, e_machine)


class OpariTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["opari"]
        opari_bin = os.path.join(dep.cpp_info.bindirs[0], "opari")
        incdir = dep.cpp_info.includedirs[0]
        libdir = dep.cpp_info.libdirs[0]
        comp = self.conf.get(
            "tools.build:compiler_executables", check_type=dict, default={}
        )
        cc = comp.get("c", "clang")
        src = self.source_folder
        bf = self.build_folder

        # Copy the test sources into the build folder: opari writes its
        # generated .mod.c / .opari.inc next to the input file, and keeping
        # them out of the source tree avoids polluting the checkout.
        copy(self, "*.c", src, bf)

        # 1. Instrument the consumer C OpenMP source with the opari tool.
        self.run(f"{opari_bin} consumer.ohos.c", cwd=bf, env="conanrun")

        # 2. Compile the instrumented source + the minimal POMP runtime table.
        self.run(
            f"{cc} -fopenmp -O2 -I{incdir} -c consumer.ohos.mod.c "
            f"-o consumer.ohos.mod.o",
            cwd=bf, env="conanbuild",
        )
        self.run(
            f"{cc} -fopenmp -O2 -I{incdir} -c pomp_rt.c -o pomp_rt.o",
            cwd=bf, env="conanbuild",
        )

        # 3. Link with libpomp (opari runtime) + libomp (OHOS OpenMP runtime).
        self.run(
            f"{cc} -fopenmp consumer.ohos.mod.o pomp_rt.o "
            f"-o consumer -L{libdir} -lpomp -lomp",
            cwd=bf, env="conanbuild",
        )

    def test(self):
        bf = self.build_folder
        consumer = os.path.join(bf, "consumer")

        # --- A. HarmonyOS platform gate -------------------------------------
        # The pipeline (OHOS clang -fopenmp + OHOS libomp) only exists on
        # OpenHarmony; asserting it makes the case non-portable on purpose.
        assert str(self.settings.os) == "OHOS", (
            f"opari OHOS consumer test requires os=OHOS, got {self.settings.os}"
        )
        assert str(self.settings.arch) == "armv8", (
            f"opari OHOS consumer test requires arch=armv8, "
            f"got {self.settings.arch}"
        )
        self.output.info(
            f"[ohos-assert] platform ok: os={self.settings.os} "
            f"arch={self.settings.arch} compiler={self.settings.compiler}"
        )

        # --- B. Target-architecture gate (ELF64 / AArch64) -------------------
        ei_class, e_machine = _read_elf_identity(consumer)
        assert ei_class == ELFCLASS64, (
            f"consumer must be an ELF64 object, got ei_class={ei_class}"
        )
        assert e_machine == EM_AARCH64, (
            f"consumer must be built for AArch64 (EM_AARCH64=183), "
            f"got e_machine={e_machine}"
        )
        self.output.info(
            f"[ohos-assert] artifact ok: ELF64 / EM_AARCH64 ({e_machine})"
        )

        # --- C. OHOS OpenMP runtime gate (POMP region events) ----------------
        out_buf, err_buf = io.StringIO(), io.StringIO()
        self.run(f'"{consumer}"', cwd=bf, env="conanrun",
                 stdout=out_buf, stderr=err_buf)
        stdout, stderr = out_buf.getvalue(), err_buf.getvalue()
        self.output.info(f"[consumer stdout]\n{stdout}")
        self.output.info(
            f"[consumer stderr] {len(stderr.splitlines())} lines"
        )

        assert "sum=4950" in stdout, (
            f"wrong reduction result, stdout={stdout!r}"
        )

        events = [ln for ln in stderr.splitlines() if re.match(r"^\s*\d+: ", ln)]
        assert len(events) > 0, (
            "no POMP region events on stderr — the instrumented OHOS OpenMP "
            "runtime did not execute"
        )
        kinds = {e.split(":", 1)[1].strip() for e in events}
        for required in ("begin parallel", "enter for", "finalize"):
            assert any(required in k for k in kinds), (
                f"missing POMP event {required!r}; kinds={sorted(kinds)}"
            )
        threads = {int(e.split(":", 1)[0].strip()) for e in events}
        shown = sorted(threads)[:8]
        self.output.info(
            f"[ohos-assert] runtime ok: {len(events)} POMP events, "
            f"{len(threads)} OHOS libomp thread(s): {shown}"
            f"{'...' if len(threads) > 8 else ''}"
        )
        self.output.info(
            "[ohos-assert] all HarmonyOS-specific assertions passed"
        )
