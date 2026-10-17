#!/usr/bin/env python3
"""Conan recipe - re-flex 6.3.0 (autotools, C++17 lexer generator).

re-flex (RE/flex, Genivia) is a modern flex alternative: the `reflex`
scanner generator plus the `libreflex` / `libreflexmin` regex matcher
libraries.  The upstream tag archive ships a pre-generated bootstrap
(configure / Makefile.in), so no autoreconf/automake runs at build time.

HarmonyOS PC (aarch64) build notes:
  * Upstream config.guess cannot classify the HongMeng kernel ("cannot
    guess build type; you must specify one"), so configure is invoked with
    explicit --build/--host <arch>-linux-ohos triplets (native build:
    build == host).
  * E011: autotools config.status creates confXXXX temp directories whose
    restrictive-permission semantics HMDFS cannot host ("./confXXXX/subs1.awk:
    Permission denied"), so the whole build runs from a work directory under
    /data/storage/el2/base.  Source is materialized with shutil.copytree
    (copy2 preserves mtimes), which keeps the automake maintainer-mode
    rebuild rules dormant - no aclocal/automake is needed on the device or
    the CI worker (a plain mtime-losing copy triggers "aclocal-1.18: command
    not found" because the versioned rebuild rule fires).
  * E077: OHOS refuses to exec an ELF without a .codesign section; every ELF
    that gets executed (the upstream self-contained test programs) is signed
    with binary-sign-tool before it runs, and bin/reflex is signed in
    package().
  * Optional Boost.Regex / PCRE2 backends are NOT enabled: <boost/regex.hpp>
    and <pcre2.h> are only needed by four upstream test programs (test,
    lorem, ptest, btest) and the optional matcher headers; neither the
    reflex tool nor libreflex links them.  build() runs the six
    self-contained upstream test programs instead (see _selfcontained_tests).
"""
import hashlib
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ReFlexConan(ConanFile):
    name = "re-flex"
    version = "6.3.0"
    description = ("RE/flex - regex pattern matching library and lexical "
                   "analyzer generator (modern flex alternative)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/Genivia/RE-flex"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("lexer", "regex", "scanner", "code-generator")

    # Upstream builds only static libraries (lib_LIBRARIES = libreflex.a
    # libreflexmin.a, no libtool), so there is no shared option; the
    # static-library type satisfies R26 (system-name libraries default to
    # static) and Conan 2's graph rule that a plain "library" package_type
    # must declare a shared option.
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    _ohos_work_root = "/data/storage/el2/base"
    _ohos_bash = "/data/service/hnp/bin/bash"

    # Self-contained upstream tests run in build(): the tests/Make programs
    # that need only libreflex.  rtest is built by the default make target;
    # stest keeps upstream's -std=c++11 (std::regex semantics baseline).
    _selfcontained_tests = [
        ("test_bits", "gnu++17"),
        ("test_ranges", "gnu++17"),
        ("streams", "gnu++17"),
        ("lazytest", "gnu++17"),
        ("stest", "c++11"),
    ]

    def export_sources(self):
        # conandata.yml declares an empty patch set; this hook keeps the
        # recipe template-complete (G1) and exports any future patches.
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # -- helpers -----------------------------------------------------

    def _gnu_triplet(self):
        arch = {"armv8": "aarch64"}.get(str(self.settings.arch),
                                        str(self.settings.arch))
        return "{0}-linux-ohos".format(arch)

    def _work_dir(self):
        """Deterministic per-build working dir under non-HMDFS storage (E011)."""
        key = hashlib.sha256(
            os.path.abspath(self.build_folder).encode("utf-8")
        ).hexdigest()[:12]
        return os.path.join(
            self._ohos_work_root,
            ".conan-build-re-flex-{0}-{1}".format(self.version, key),
        )

    def _reset_dir(self, path):
        if os.path.lexists(path):
            if os.path.islink(path):
                os.unlink(path)
            else:
                shutil.rmtree(path)

    def _compiler(self, lang):
        execs = self.conf.get("tools.build:compiler_executables") or {}
        return execs.get(lang) or lang

    def _has_ohos_signature(self, path):
        """True if the ELF already carries a .codesign/.note.ohos section."""
        try:
            with open(path, "rb") as binary:
                data = binary.read()
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

    def _sign_elf_if_ohos(self, path):
        """Four-step OHOS post-install sign flow (order is not negotiable):

        copy to tmp -> llvm-objcopy --remove-section .codesign (best-effort)
        -> binary-sign-tool sign -selfSign 1 -> move back -> chmod 755.
        """
        if not os.path.isfile(path):
            return
        # Already signed: only restore the exec bit (E077: sign tool cannot
        # overwrite an existing signature section).
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
                "OHOS packaging requires binary-sign-tool and llvm-objcopy")

        tmp_in = "{0}.unsigned".format(path)
        tmp_out = "{0}.signed".format(path)
        shutil.copy2(path, tmp_in)
        # Remove any stale signature before (re)signing; failure is fine when
        # no .codesign section is present yet.
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

    # -- build ---------------------------------------------------------

    def build(self):
        apply_conandata_patches(self)
        work = self._work_dir()
        self._reset_dir(work)
        # E011: copy the source out of the HMDFS conan cache before
        # configure/make.  copytree -> copy2 preserves mtimes so the automake
        # maintainer-mode rebuild rules (aclocal-1.18 etc.) stay dormant.
        shutil.copytree(self.source_folder, work, symlinks=True)

        triplet = self._gnu_triplet()
        cc = self._compiler("c")
        cxx = self._compiler("cpp")
        bash = self._ohos_bash

        def run(cmd):
            self.run(cmd, cwd=work)

        # 1) configure - native OHOS build (build == host); explicit triplets
        #    because upstream config.guess cannot classify the HongMeng kernel.
        #    CXXFLAGS mirrors upstream's default (-Wall -Wextra -Wunused -O2)
        #    plus an explicit C++17 standard (profile cppstd=17).
        run("{0} configure --prefix=/usr/local "
            "--build={1} --host={2} "
            "CC='{3}' CXX='{4}' "
            "CXXFLAGS='-O2 -Wall -Wextra -Wunused -std=gnu++17' "
            "LDFLAGS='-Wl,-z,relro,-z,now'"
            .format(bash, triplet, triplet, cc, cxx))

        # 2) make - standard parallel-safe autotools; jobs capped at 2 for
        #    the shared device.  The default target also builds tests/rtest.
        run("make -j2")

        # 3) compile the remaining self-contained upstream tests (rtest is
        #    already built) and run all six with positive per-program
        #    evidence (exit code + OK/ERRORFAIL counters, kept in the log).
        tests_dir = os.path.join(work, "tests")
        for name, std in self._selfcontained_tests:
            self.run(
                "{0} -std={1} -O2 -I. -I../include "
                "-o {2} {2}.cpp ../lib/libreflex.a"
                .format(cxx, std, name),
                cwd=tests_dir,
            )
        built = [name for name, _ in self._selfcontained_tests] + ["rtest"]
        for name in built:
            self._sign_elf_if_ohos(os.path.join(tests_dir, name))
        runner = os.path.join(tests_dir, "ohos_run_selfcontained.sh")
        with open(runner, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(_RUNNER_SH)
        os.chmod(runner, 0o755)
        self.run("{0} ohos_run_selfcontained.sh".format(self._ohos_bash),
                 cwd=tests_dir)

        # 4) install into a private DESTDIR staging tree (the default goal is
        #    `all`, so `install` must be passed explicitly).
        stage = os.path.join(work, "stage")
        self._reset_dir(stage)
        os.makedirs(stage, exist_ok=True)
        run("make install DESTDIR={0}".format(stage))

    def package(self):
        stage_root = os.path.join(self._work_dir(), "stage", "usr", "local")
        # NB: conan's copy() keeps each file's path relative to src, so the
        # dst is always package_folder itself - adding "bin"/"lib" here would
        # nest them (bin/bin, lib/lib) and silently skip the E077 signature.
        copy(self, "bin/reflex", src=stage_root, dst=self.package_folder)
        copy(self, "include/reflex/*.h",
             src=stage_root, dst=self.package_folder)
        copy(self, "lib/*.a", src=stage_root, dst=self.package_folder)
        copy(self, "lib/pkgconfig/*.pc",
             src=stage_root, dst=self.package_folder)
        copy(self, "share/man/man1/reflex.1",
             src=stage_root, dst=self.package_folder)
        copy(self, "LICENSE.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # E077: sign the packaged executable (restore +x after signing).
        self._sign_elf_if_ohos(
            os.path.join(self.package_folder, "bin", "reflex"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # libreflex.a is the full matcher library; libreflexmin.a is the
        # reduced variant (no optional-backend wrappers) - consumers that
        # want the minimal runtime link it explicitly instead.
        self.cpp_info.libs = ["reflex"]
        self.cpp_info.bindirs = ["bin"]


_RUNNER_SH = """#!/bin/sh
# Runs the self-contained RE/flex upstream test programs (the tests/Make
# targets that need only libreflex - the four Boost.Regex / PCRE2 backend
# programs are not part of this subset).  Prints one UPSTREAM_TEST line per
# program with exit code + OK/ERRORFAIL counters and exits non-zero if any
# program fails; per-program output is kept in <name>.out next to the
# binaries.  POSIX sh; no nested command substitution inside $(( )).
set -u
fail=0
for name in test_bits test_ranges streams lazytest stest rtest; do
    ./"$name" > "$name.out" 2>&1
    rc=$?
    oks=$(grep -c '^OK$' "$name.out")
    errs=$(grep -cE 'ERROR|FAIL' "$name.out")
    echo "UPSTREAM_TEST $name exit=$rc OK=$oks ERRORFAIL=$errs"
    if [ "$rc" -ne 0 ]; then
        fail=1
    fi
    if [ "$errs" -ne 0 ]; then
        fail=1
    fi
done
exit $fail
"""
