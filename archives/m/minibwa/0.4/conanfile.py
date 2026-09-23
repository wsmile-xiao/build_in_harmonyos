#!/usr/bin/env python3
"""Conan recipe for minibwa 0.4.

minibwa is a small C aligner built by a plain Makefile. The package ships the
`minibwa` executable only; the internal libminibwa.a is a build artifact.

Upstream: https://github.com/lh3/minibwa (tag v0.4).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class MinibwaConan(ConanFile):
    name = "minibwa"
    version = "0.4"
    description = "Short-read aligner combining bwa-mem seeding with minimap2 chaining"
    license = "MIT AND GPL-2.0-or-later"
    homepage = "https://github.com/lh3/minibwa"
    url = "https://github.com/lh3/minibwa"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        self.requires("zlib/1.3.1")

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

        # Upstream ships test data without a stored checksum in the tarball;
        # verify it here because test_package relies on it being intact.
        testdata = os.path.join(self.source_folder, "test", "chrM-human.fa.gz")
        if not os.path.isfile(testdata):
            raise ConanException(
                "test/chrM-human.fa.gz missing from source tree")

    def _compiler_tools(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # The profile's compiler_executables point at the CI worker layout
        # (/data/service/hnp/bin); on machines where that path does not exist
        # fall back to resolving the compiler from PATH (the profile also
        # prepends the real toolchain bin/ to PATH).
        if not os.path.isfile(cc):
            cc = shutil.which("clang") or cc
        toolchain_bin = os.path.dirname(cc) if os.path.dirname(cc) else None
        ar = compilers.get("ar") or (
            os.path.join(toolchain_bin, "llvm-ar") if toolchain_bin else "ar"
        )
        ranlib = compilers.get("ranlib") or (
            os.path.join(toolchain_bin, "llvm-ranlib") if toolchain_bin else "ranlib"
        )
        for tool in (ar, ranlib):
            # Same PATH fallback for the binutils.
            if not os.path.isfile(tool):
                base = os.path.basename(tool)
                resolved = shutil.which(base)
                if resolved:
                    if tool == ar:
                        ar = resolved
                    else:
                        ranlib = resolved
        return cc, ar, ranlib

    def _sign_elf(self, path):
        """Ensure the executable carries an OHOS identity.

        The OHOS clang toolchain already embeds `.note.ohos.ident` via its
        default `-Wl,--code-sign`; when that marker is present the binary is
        already properly identified. On workers where the toolchain does not
        add it, sign explicitly with binary-sign-tool (repo precedent:
        abbtr). No-op for non-OHOS hosts.
        """
        if str(self.settings.os) != "OHOS" or not os.path.exists(path):
            return

        with open(path, "rb") as f:
            data = f.read()
        if b".note.ohos" in data or b".codesign" in data:
            os.chmod(path, 0o755)
            return

        sign_tool = shutil.which("binary-sign-tool") \
            or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(sign_tool):
            # Nothing we can do here; keep the toolchain-default binary.
            os.chmod(path, 0o755)
            return

        objcopy = shutil.which("llvm-objcopy") \
            or "/data/service/hnp/bin/llvm-objcopy"
        signed = path + ".signed"
        if os.path.isfile(objcopy):
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" || true',
                     quiet=True)
        self.run(f'"{sign_tool}" sign -inFile "{path}" -outFile "{signed}" '
                 f"-selfSign 1", quiet=True)
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def build(self):
        cc, ar, ranlib = self._compiler_tools()
        toolchain_bin = os.path.dirname(cc)
        if toolchain_bin:
            os.environ["PATH"] = toolchain_bin + os.pathsep + os.environ.get("PATH", "")

        zlib_info = self.dependencies["zlib"].cpp_info
        zlib_inc = " ".join(f"-I{d}" for d in zlib_info.includedirs)
        zlib_lib = " ".join(f"-L{d}" for d in zlib_info.libdirs)

        # E210 (mimalloc MI_OVERRIDE SIGSEGV on OHOS): upstream default links
        # mimalloc with -DMI_MALLOC_OVERRIDE, which crashes at startup on
        # HarmonyOS. mimalloc=0 is the upstream-supported switch to drop it.
        # INCLUDES is the only Makefile variable without a `+=` append, so it
        # is the single injection point for the zlib headers: passing CPPFLAGS
        # on the command line would make the Makefile's own `CPPFLAGS+=`
        # (which adds -DLIBSAIS_OPENMP / -DHAVE_KALLOC) a no-op.
        self.run(
            " ".join(
                [
                    "make -j1",
                    f'CC="{cc}"',
                    f'AR="{ar}"',
                    f'RANLIB="{ranlib}"',
                    "mimalloc=0",
                    f'INCLUDES="{zlib_inc}"',
                    f'LDFLAGS="{zlib_lib}"',
                    "minibwa",
                ]
            ),
            cwd=self.source_folder,
        )

        # Upstream CI (build.yml) verifies the build with `make -C api-test`,
        # which compiles the mbmap-one/mbmap-batch consumer programs against
        # libminibwa.a. The api-test Makefile builds its own CFLAGS with only
        # -I.., so the zlib paths must go through CFLAGS there.
        self.run(
            " ".join(
                [
                    "make -C api-test",
                    f'CC="{cc}"',
                    f'CFLAGS="-std=gnu99 -Wall -O3 {zlib_inc} {zlib_lib}"',
                ]
            ),
            cwd=self.source_folder,
        )

        # Real end-to-end verification on the upstream-shipped chrM test data,
        # following the documented workflows:
        #   1. `minibwa index` builds the .mbw/.l2b index files (README quick
        #      start), in a scratch dir so the source tree stays pristine.
        #   2. `minibwa map` runs the paired-end alignment (README quick
        #      start); assert real SAM records mapped to chrM.
        #   3. mbmap-one/mbmap-batch are the upstream API examples
        #      (api-test/ex-one.c: `mbmap-one <idxPrefix> <query.fa>`); they
        #      consume the index produced in step 1 and must emit PAF
        #      alignments.
        test_dir = os.path.join(self.source_folder, "test")
        run_dir = os.path.join(self.build_folder, "upstream-test-run")
        if os.path.isdir(run_dir):
            shutil.rmtree(run_dir)
        os.makedirs(run_dir)
        shutil.copy(os.path.join(test_dir, "chrM-human.fa.gz"), run_dir)
        bin_path = os.path.join(self.source_folder, "minibwa")

        self.run(
            f'"{bin_path}" index "{run_dir}/chrM-human.fa.gz" '
            f'> "{run_dir}/index.log" 2>&1',
            cwd=run_dir,
        )

        self.run(
            f'"{bin_path}" map "{run_dir}/chrM-human.fa.gz" '
            f'{test_dir}/chrM-read_1.fa.gz {test_dir}/chrM-read_2.fa.gz '
            f'> "{run_dir}/map.sam" 2> "{run_dir}/map.err"',
            cwd=run_dir,
        )
        with open(os.path.join(run_dir, "map.sam"), "r") as f:
            sam = [line for line in f if line.strip() and not line.startswith("@")]
        if not sam:
            raise ConanException("minibwa map produced no SAM records")
        first_sam = sam[0].split("\t")
        if len(first_sam) < 11 or first_sam[2] != "chrM":
            raise ConanException(
                f"first SAM record not mapped to chrM: {sam[0][:120]}")

        for prog in ("mbmap-one", "mbmap-batch"):
            exe = os.path.join(self.source_folder, "api-test", prog)
            out_file = os.path.join(run_dir, prog + ".out")
            self.run(
                f'"{exe}" "{run_dir}/chrM-human.fa.gz" '
                f'{test_dir}/chrM-read_1.fa.gz '
                f'> "{out_file}" 2>> "{run_dir}/{prog}.err"',
                cwd=run_dir,
            )
            with open(out_file, "r") as f:
                lines = [line for line in f if line.strip()]
            if not lines:
                raise ConanException(
                    f"upstream api-test {prog} produced no output")
            first = lines[0].split("\t")
            # PAF fields: query, qlen, qs, qe, strand, ctg, ctglen, ts, te,
            # mlen, blen, mapq, cg:Z:... First read must map to chrM.
            if (len(first) < 12 or first[5] != "chrM"
                    or first[4] not in ("+", "-")
                    or not first[-1].startswith("cg:Z:")):
                raise ConanException(
                    f"{prog} output not a chrM PAF alignment: {lines[0][:120]}")

    def package(self):
        copy(self, "minibwa", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        bin_path = os.path.join(self.package_folder, "bin", "minibwa")
        self._sign_elf(bin_path)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
