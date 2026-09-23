#!/usr/bin/env python3
"""Conan test_package for changetrack 4.7 — pure Perl script test.

Verifies that the changetrack command is functional after installation:
  1. smoke: -v prints the version, -h prints the usage text
     (-h exits 1 by upstream design, so content is asserted, not rc)
  2. functional loopback in no-RCS mode (-r): monitor a file, detect a
     modification, verify the change log, the .yesterday snapshot and the
     ed script produced by GNU `diff -e`
  3. real RCS loopback via the rcs/5.10.1 dependency: direct ci -i/co
     roundtrip, then changetrack full mode (two runs) producing a ,v file
     with two revisions
  4. upstream `make test` equivalence: the exact checks of upstream
     test.sh (5 perl core module `use` probes + `rcs -V`)

All commands run under the conanbuild environment: the CI profile buildenv
PATH puts the device GNU userland (perl, GNU diffutils) ahead of toybox,
whose diff does not support -e. The rcs package bindir is prepended
explicitly (buildenv_info reaches direct consumers only), with LOGNAME
defaulted non-empty as required by RCS checkin.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class ChangetrackTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["changetrack"]
        ct = os.path.join(dep.package_folder, "bin", "changetrack")
        rcs_dep = self.dependencies["rcs"]
        rcs_bin = os.path.join(rcs_dep.package_folder, "bin")

        # /tmp is read-only on OHOS; work inside the test build folder
        base = self.build_folder or os.getcwd()
        work = os.path.join(base, "changetrack_work")
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work)

        # rcs bindir first (not guaranteed in conanbuild env: buildenv_info
        # reaches direct consumers only); LOGNAME must be non-empty for ci/co.
        prefix = f'PATH="{rcs_bin}:$PATH" LOGNAME="${{LOGNAME:-$(id -un 2>/dev/null || echo ohos)}}"'

        def out_path(name):
            return os.path.join(work, name)

        # ---- Test 1: changetrack -v prints the version (exit 0) ----
        vout = out_path("version.out")
        rc = self.run(f'"{ct}" -v > "{vout}"', env="conanbuild")
        content = open(vout).read()
        if rc != 0:
            raise Exception(f"changetrack -v exited with {rc}")
        if "4.7" not in content:
            raise Exception(f"changetrack -v did not print 4.7, got: {content[:100]}")
        self.output.info("changetrack -v: PASS (version 4.7)")

        # ---- Test 2: changetrack -h prints usage (exits 1 by design) ----
        hout = out_path("help.out")
        self.run(f'"{ct}" -h > "{hout}" 2>&1', env="conanbuild", ignore_errors=True)
        content = open(hout).read()
        if "This is changetrack, version" not in content:
            raise Exception(f"changetrack -h did not print banner, got: {content[:200]}")
        if "display this help and exit" not in content:
            raise Exception("changetrack -h usage text incomplete")
        self.output.info("changetrack -h: PASS (usage text, exit 1 is upstream behavior)")

        # ---- Test 3: functional loopback, no-RCS mode (-r) ----
        target = os.path.join(work, "target.txt")
        conf = os.path.join(work, "ct.conf")
        histdir = os.path.join(work, "history")
        with open(target, "w") as f:
            f.write("line1\nline2\nline3\n")
        with open(conf, "w") as f:
            f.write(target + "\n")

        # changetrack encodes the monitored file's absolute path into artifact
        # names by mapping '/' -> ':' (and ' ' -> '_'), stripping the leading ':'
        base_name = target.replace("/", ":").replace(" ", "_").lstrip(":")
        history = os.path.join(histdir, base_name + ".history")
        yesterday = os.path.join(histdir, base_name + ".yesterday")
        edfile = os.path.join(histdir, base_name + ".ed")

        cmd = f'"{ct}" -r -q -c "{conf}" -d "{histdir}" -e'

        # first pass: record the new file
        rc = self.run(cmd, env="conanbuild")
        if rc != 0:
            raise Exception(f"first changetrack run exited with {rc}")
        for path in (history, yesterday):
            if not os.path.isfile(path):
                raise Exception(f"missing artifact after first run: {os.path.basename(path)}")
        first = open(history).read()
        if "New file" not in first:
            raise Exception(f"first run did not record 'New file': {first[:200]}")
        self.output.info("changetrack first run: PASS (New file recorded, snapshot written)")

        # modify the monitored file, run again: change must be detected
        with open(target, "w") as f:
            f.write("line1\nCHANGED\nline3\n")
        rc = self.run(cmd, env="conanbuild")
        if rc != 0:
            raise Exception(f"second changetrack run exited with {rc}")

        second = open(history).read()
        if "Changes made on" not in second:
            raise Exception("second run did not record 'Changes made on'")
        if "CHANGED" not in second or "line2" not in second:
            raise Exception("second run history lacks the old/new diff content")
        self.output.info("changetrack change detection: PASS (history log updated)")

        # ed script must contain the diff -e commands for the modification
        if not os.path.isfile(edfile):
            raise Exception("missing .ed script (diff -e output)")
        ed = open(edfile).read()
        if "2c" not in ed or "CHANGED" not in ed:
            raise Exception(
                "ed script lacks expected '2c'/'CHANGED' commands — "
                "GNU diffutils diff -e missing or shadowed by toybox diff on PATH"
            )
        if open(yesterday).read() != "line1\nCHANGED\nline3\n":
            raise Exception(".yesterday snapshot was not updated to the new content")
        self.output.info("changetrack functional loopback: PASS (diff -e ed script + snapshot)")

        # ---- Test 4: direct ci -i / co roundtrip via the rcs package ----
        rcsdir = os.path.join(work, "rcs_check")
        os.makedirs(rcsdir)
        hello = os.path.join(rcsdir, "hello.txt")
        with open(hello, "w") as f:
            f.write("hello rcs\n")
        rc = self.run(f'cd "{rcsdir}" && {prefix} ci -i -t-"initial import" hello.txt',
                      env="conanbuild")
        if rc != 0:
            raise Exception(f"rcs ci -i exited with {rc}")
        if not os.path.isfile(os.path.join(rcsdir, "hello.txt,v")):
            raise Exception("ci -i did not create the ,v file")
        rc = self.run(f'cd "{rcsdir}" && {prefix} co -q -u hello.txt', env="conanbuild")
        if rc != 0:
            raise Exception(f"rcs co exited with {rc}")
        if open(hello).read() != "hello rcs\n":
            raise Exception("co did not restore the checked-in content")
        self.output.info("rcs ci -i/co roundtrip: PASS (,v created, content restored)")

        # ---- Test 5: changetrack full mode (RCS revision storage) ----
        target2 = os.path.join(work, "tracked.txt")
        conf2 = os.path.join(work, "ct-rcs.conf")
        hist2 = os.path.join(work, "history-rcs")
        with open(target2, "w") as f:
            f.write("alpha\nbeta\n")
        with open(conf2, "w") as f:
            f.write(target2 + "\n")
        base2 = target2.replace("/", ":").replace(" ", "_").lstrip(":")
        vfile = os.path.join(hist2, "RCS", base2 + ",v")
        histfile2 = os.path.join(hist2, base2 + ".history")

        cmd2 = f'"{ct}" -q -c "{conf2}" -d "{hist2}" -e'
        rc = self.run(f'{prefix} {cmd2}', env="conanbuild")
        if rc != 0:
            raise Exception(f"changetrack full-mode first run exited with {rc}")
        if not os.path.isfile(vfile):
            raise Exception("full-mode first run did not create the RCS ,v file")

        with open(target2, "w") as f:
            f.write("alpha\nGAMMA\n")
        rc = self.run(f'{prefix} {cmd2}', env="conanbuild")
        if rc != 0:
            raise Exception(f"changetrack full-mode second run exited with {rc}")
        # count revisions via rlog (the ,v format stores bare revision numbers)
        rlog_out = out_path("rlog.out")
        self.run(f'{prefix} rlog "{vfile}" > "{rlog_out}"', env="conanbuild",
                 ignore_errors=True)
        rlog = open(rlog_out).read()
        if rlog.count("revision 1.") < 2:
            raise Exception(f"expected 2 revisions in the ,v file after the change: {rlog[:300]}")
        if "Changes made on" not in open(histfile2).read():
            raise Exception("full-mode second run did not record the change in history")
        self.output.info("changetrack RCS mode: PASS (,v file with 2 revisions + history log)")

        # ---- Test 6: upstream `make test` equivalence (exact test.sh checks) ----
        # upstream test.sh: `which perl`, 5x `perl -e "use <module>"`, `rcs -V`
        rc = self.run(f'{prefix} which perl', env="conanbuild")
        if rc != 0:
            raise Exception("which perl not found (upstream test.sh check 1)")
        rc = self.run(f'{prefix} perl -e \'use File::Copy; use Getopt::Std; '
                      f'use File::Path; use FileHandle; use strict;\'', env="conanbuild")
        if rc != 0:
            raise Exception("perl core modules check failed (upstream test.sh checks 2-6)")
        rc = self.run(f'{prefix} rcs -V', env="conanbuild")
        if rc != 0:
            raise Exception("rcs -V failed (upstream test.sh final check) — "
                            "upstream make test would report 'RCS is not installed'")
        self.output.info("upstream make test equivalence: PASS (which perl + 5 modules + rcs -V)")
