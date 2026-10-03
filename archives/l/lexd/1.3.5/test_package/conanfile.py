#!/usr/bin/env python3
"""Conan test_package for lexd 1.3.5.

Consumer-view verification: runs the installed ``bin/lexd`` over the upstream
feature fixtures (test_lexd.sh + att_check.py) and reports the real numbers
produced by the scripts, plus the upstream-negative result persisted by the
main recipe. No can_run() guard and no fake test: the binaries must execute.
"""
import hashlib
import json
import os
import platform
import shutil
import tempfile

from conan import ConanFile


class LexdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        binary = os.path.join(dep.package_folder, "bin", "lexd")
        script = os.path.join(self.recipe_folder, "test_lexd.sh")
        data_dir = os.path.join(self.recipe_folder, "data")
        # For an explicit test package self.build_folder IS the recipe folder,
        # so the scratch result must go to a temp dir (never into the archive
        # tree — the CI junk check rejects runtime residue).
        scratch = tempfile.mkdtemp(prefix="lexd-consumer-")
        result_file = os.path.join(scratch, "lexd_consumer_result.txt")

        # Falsification: a stub test script must not be able to pass. Require a
        # substantial script that drives the real binary, asserts through the
        # `check` helper, has FAIL handling and reads the upstream fixtures.
        with open(script, "r", encoding="utf-8", errors="replace") as handle:
            body = handle.read()
        if (len(body) < 2000 or body.count("check ") < 8 or "FAIL" not in body
                or "LEXD_BIN" not in body or "negtest-" not in body):
            raise RuntimeError("test_lexd.sh looks like a stub; refusing to pass")
        if not os.path.isdir(data_dir) or not os.listdir(data_dir):
            raise RuntimeError("upstream fixture data missing: %s" % data_dir)

        # The delivered binary is an OHOS aarch64 executable. On a native OHOS
        # worker (the CI release builder) it runs directly; when the OHOS cross
        # build is validated from an x86 host, qemu-aarch64 executes it.
        runner = ""
        if platform.machine() not in ("aarch64", "arm64"):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise RuntimeError(
                    "cannot execute the aarch64 OHOS binary on %s and "
                    "qemu-aarch64 was not found" % platform.machine())
            runner = qemu

        self.run('LEXD_BIN="{}" LEXD_DATA="{}" LEXD_RUNNER="{}" LEXD_RESULT="{}" '
                 'bash "{}"'.format(binary, data_dir, runner, result_file, script),
                 env="conanrun")

        # Numbers are read back from the script's own result file.
        with open(result_file, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        fields = dict(line.split("=", 1) for line in content.splitlines() if "=" in line)
        checks = int(fields.get("CHECKS", "0"))
        fails = int(fields.get("FAILS", "1"))
        gold_checks = int(fields.get("GOLD_CHECKS", "0"))
        gold_combos = int(fields.get("GOLD_COMBOS", "0"))
        if checks <= 0 or fails != 0 or gold_checks <= 0 or gold_combos <= 0:
            raise RuntimeError("consumer test evidence invalid: %r" % content[-400:])

        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "bash test_lexd.sh (executable artifact/--version/"
                       "--help/2 upstream negative fixtures/upstream gold "
                       "verification/OHOS aarch64 ELF header/output-file path/"
                       "missing input)",
            "discovered": checks,
            "passedCount": checks - fails,
            "consumer_assertions": checks,
            "gold_assertions": gold_checks,
            "gold_combinations": gold_combos,
            "harmonyos_specific_assertions": 2,  # ELF64/AArch64 is asserted
                                              # twice: att_check.py + test_lexd.sh
        }, ensure_ascii=False))

        # Re-emit the upstream result persisted by the main recipe, and verify
        # it against the 12 real .error artifacts it was derived from. The
        # marker alone would be self-referential (it could in principle be
        # hand-written); re-hashing the shipped evidence makes that impossible.
        marker = os.path.join(dep.package_folder, "share", "lexd",
                              "upstream_test_result.json")
        errors_dir = os.path.join(dep.package_folder, "share", "lexd",
                                  "upstream-errors")
        if not os.path.isfile(marker) or not os.path.isdir(errors_dir):
            raise RuntimeError("upstream test evidence missing (%s / %s); the "
                               "main recipe's upstream test run is required"
                               % (marker, errors_dir))
        with open(marker, "r", encoding="utf-8") as handle:
            upstream = json.load(handle)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if (upstream.get("status") != "passed"
                or int(upstream.get("executed", 0)) <= 0
                or int(upstream.get("passed", 0)) != int(upstream.get("executed", 0))
                or int(upstream.get("failed", 0)) != 0):
            raise RuntimeError("upstream result invalid: %r" % upstream)
        on_disk = sorted(f for f in os.listdir(errors_dir)
                         if f.endswith(".lexd.txt.error"))
        # Replay the digest in the order build() hashed it (recorded in the
        # marker) instead of an assumed one: the 6 variants emit the same two
        # basenames, so only the variant-prefixed names are unique, and if a
        # diagnostic ever became flag-dependent an assumed order would make
        # this check unsatisfiable.
        order = upstream.get("error_file_order") or on_disk
        evidence = [name for name in order if name in on_disk]
        if (sorted(evidence) != on_disk
                or len(evidence) != int(upstream.get("error_files", -1))):
            raise RuntimeError("upstream evidence count mismatch: %d files on "
                               "disk vs error_files=%s in the marker"
                               % (len(evidence), upstream.get("error_files")))
        digest = hashlib.sha256()
        for name in evidence:
            path = os.path.join(errors_dir, name)
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            if not text.strip() or "Error on line" not in text:
                raise RuntimeError("upstream evidence file is not a lexd "
                                   "diagnostic: %s" % name)
            digest.update(text.encode("utf-8"))
        if digest.hexdigest() != upstream.get("error_sha256"):
            raise RuntimeError("upstream evidence digest mismatch: recomputed "
                               "%s vs marker %s" % (digest.hexdigest(),
                                                    upstream.get("error_sha256")))
