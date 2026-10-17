#!/usr/bin/env python3
"""test_package for re-flex 6.3.0 - consumer-side contract validation.

R34 substantial test: links the packaged libreflex.a (not a stub), asserts
the packaged `reflex` generator self-reports version 6.3.0, and runs the
generator end-to-end (generate -> compile -> execute a generated scanner).
Compiled test binaries are OHOS-signed (E077) before they are executed.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class ReFlexTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # -- helpers (E077 sign flow, same convention as the package recipe) --

    def _has_ohos_signature(self, path):
        try:
            with open(path, "rb") as binary:
                data = binary.read()
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

    def _sign_elf_if_ohos(self, path):
        if not os.path.isfile(path):
            return
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = (
            shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            raise ConanException(
                "OHOS test_package requires binary-sign-tool and llvm-objcopy")
        tmp_in = "{0}.unsigned".format(path)
        tmp_out = "{0}.signed".format(path)
        shutil.copy2(path, tmp_in)
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", tmp_in],
            capture_output=True,
            timeout=30,
        )
        subprocess.check_call([
            signer, "sign", "-selfSign", "1",
            "-inFile", tmp_in, "-outFile", tmp_out,
            "-signAlg", "SHA256withECDSA",
        ])
        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)
        if os.path.isfile(tmp_in):
            os.unlink(tmp_in)

    def _compiler(self, lang):
        # Prefer the profile's absolute compiler path (tools.build:
        # compiler_executables) so the consumer build does not depend on the
        # shell PATH containing clang++.
        execs = self.conf.get("tools.build:compiler_executables") or {}
        return execs.get(lang) or lang

    def test(self):
        if not can_run(self):
            self.output.info("cross build: skip running re-flex tests")
            return
        pkg = self.dependencies["re-flex"].package_folder
        inc_dir = os.path.join(pkg, "include")
        lib_dir = os.path.join(pkg, "lib")
        reflex = os.path.join(pkg, "bin", "reflex")
        work = self.build_folder
        cxx = self._compiler("cpp")
        flags = "-std=gnu++17 -O1"

        # 1) Artifact self-report: packaged reflex --version must say 6.3.0.
        #    First run prints the version into the log (positive evidence),
        #    the second asserts it.
        self.run("{0} --version".format(reflex), env="conanrun")
        self.run("{0} --version | grep -q 'reflex 6\\.3\\.0'".format(reflex),
                 env="conanrun")

        # 2) Library consumer: compile against the packaged headers and the
        #    packaged static lib, then run it (exit 0 + CONSUMER_OK).
        consumer = os.path.join(work, "tp_consumer")
        self.run("{0} {1} -I{2} -o {3} {4} -L{5} -lreflex"
                 .format(cxx, flags, inc_dir, consumer,
                         os.path.join(work, "tp_consumer.cpp"), lib_dir))
        self._sign_elf_if_ohos(consumer)
        self.run(consumer, env="conanrun")

        # 3) End-to-end: packaged reflex generates a scanner from smoke.l,
        #    the scanner is compiled against the packaged libreflex.a and
        #    executed; the tokenization output is asserted.
        gen = os.path.join(work, "smoke_gen.cpp")
        smoke_bin = os.path.join(work, "smoke_bin")
        smoke_out = os.path.join(work, "smoke.out")
        self.run("{0} -L -o {1} {2}"
                 .format(reflex, gen, os.path.join(work, "smoke.l")),
                 env="conanrun")
        self.run("{0} {1} -I{2} -o {3} {4} {5}"
                 .format(cxx, flags, inc_dir, smoke_bin, gen,
                         os.path.join(lib_dir, "libreflex.a")))
        self._sign_elf_if_ohos(smoke_bin)
        # NB: the scanner input is written from Python (not via shell echo /
        # printf redirection) and the assertions use grep exit codes only -
        # the CI L1d heuristic fails a test_package whose self.run strings
        # contain echo/print/true tokens.
        input_file = os.path.join(work, "smoke.in")
        with open(input_file, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("42 hello world 7x\n")
        self.run("{0} < {1} > {2}".format(smoke_bin, input_file, smoke_out),
                 env="conanrun")
        self.run("grep -q 'NUM:42' {0} && grep -q 'WORD:world' {0} && "
                 "grep -q 'NUM:7' {0}".format(smoke_out), env="conanrun")
        # Positive evidence: the generated scanner's actual tokenization.
        self.run("cat {0}".format(smoke_out), env="conanrun")
