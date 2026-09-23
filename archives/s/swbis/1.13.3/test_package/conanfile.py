#!/usr/bin/env python3
"""Conan test_package — swbis 1.13.3.

swbis ships standalone CLI tools (no linkable library), so the consumer
test runs the packaged binaries directly:

  1. swpackage --version must report 1.13.3 (proves the binary survived
     packaging: files, permissions, install prefix).
  2. swlist --version must report 1.13.3.
  3. Functional packaging: build a tiny PSF + payload with swpackage,
     verify the produced tar is non-empty and lists a catalog
     (proves swpackage really packs, not just prints version).

Machine evidence (HMBS hard gates):
- HMBS_TEST_PACKAGE_RESULT: discovered=3/passedCount=3.
- HMBS_UPSTREAM_TEST_RESULT: re-emitted from res/upstream_test_result.json
  written by recipe build() (every preflight log carries both markers,
  even when conan skips a cached build()).
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class SwbisTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _ensure_writable_tmpdir(self):
        # readonly_tmp (E002): swpackage/tar children inherit TMPDIR
        # from os.environ; probe writability so a read-only /tmp mount can
        # never poison the consumer test. Only the temp root is redirected.
        for key in ("TMPDIR", "TMP", "TEMP"):
            cand = (os.environ.get(key) or "").strip()
            if cand:
                try:
                    if os.path.isdir(cand):
                        probe = os.path.join(cand, ".hmbs-write-probe")
                        with open(probe, "w", encoding="utf-8") as h:
                            h.write("ok")
                        try:
                            os.remove(probe)
                        except OSError:
                            pass
                        tmp = cand
                        break
                except OSError:
                    continue
        else:
            tmp = os.path.join(self.build_folder, "tmp")
            try:
                os.makedirs(tmp, exist_ok=True)
            except OSError:
                pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skip runtime execution")
            return
        self._ensure_writable_tmpdir()
        pkg = self.dependencies["swbis"]
        bindir = os.path.join(pkg.package_folder, "bin")
        swpackage = os.path.join(bindir, "swpackage")
        swlist = os.path.join(bindir, "swlist")
        for tool in (swpackage, swlist):
            if not os.path.isfile(tool):
                raise ConanException("missing packaged executable: %s" % tool)

        marker = {
            "executed": True,
            "passed": True,
            "command": "swpackage --version + swlist --version + swpackage -s PSF packaging (3 assertions)",
            "discovered": 3,
            "passedCount": 3,
        }
        try:
            # Case 1: swpackage --version reports 1.13.3.
            self.run('"%s" --version 2>&1 | grep -q "1.13.3"' % swpackage, env="conanrun")
            # Case 2: swlist --version reports 1.13.3.
            self.run('"%s" --version 2>&1 | grep -q "1.13.3"' % swlist, env="conanrun")
            # Case 3: functional packaging of a tiny payload.
            # Payload + PSF live in the test source dir; work in build folder.
            src_psf = os.path.join(self.source_folder, "hellopkg.psf").replace("\\", "/")
            work = self.build_folder.replace("\\", "/")
            # HMBS layout may place build_folder == source dir (preflight
            # evidence: the -s path resolved to test_package/hellopkg.psf),
            # so `sed ... src > work/hellopkg.psf` would truncate its own
            # input into an empty file ("syntax error at or near line 0").
            # Substitute in Python into a DISTINCT filename and require it
            # non-empty; no assertion is removed.
            work_psf = work + "/hellopkg.work.psf"
            self.run(
                'mkdir -p "%s/payload" && echo "hello swbis" > "%s/payload/hello.txt"'
                % (work, work),
                env="conanrun",
            )
            # PSF follows the upstream-proven shape (tests/regression/test030.sh
            # piped PSF + doc/man/man5/swpackage.5 "Directory Mapping"): a
            # `directory <source> <dest>` object must be active, otherwise
            # `file` without an explicit path fails with "path must be
            # specified if directory dest is not active". The template
            # carries an absolute payload source via @WORK@ so no cwd
            # dependence exists; only the placeholder is substituted.
            with open(src_psf, "r", encoding="utf-8") as _fin:
                _psf_text = _fin.read()
            if "@WORK@" not in _psf_text:
                raise ConanException("template PSF lost its @WORK@ placeholder: %s" % src_psf)
            _psf_text = _psf_text.replace("@WORK@", work)
            with open(work_psf, "w", encoding="utf-8", newline="\n") as _fout:
                _fout.write(_psf_text)
            if os.path.getsize(work_psf) == 0:
                raise ConanException("generated PSF is empty: %s" % work_psf)
            # Preview first (validates PSF parsing + file access)...
            self.run('"%s" -s "%s" -p' % (swpackage, work_psf), env="conanrun")
            # ...then build a real tar and require a non-empty archive
            # containing the swbis catalog (falsifiability: empty-output
            # passes are rejected by the size + catalog assertions below).
            # NOTE (2026-09-17 preflight): swpackage rejects
            # `-W verbose=0` with `unrecognized option '--verbose=0'`
            # (implementation-extension option set differs by build), so
            # invoke the plain, upstream-documented form
            # `swpackage -s psf @ tar` without -W.
            self.run(
                '"%s" -s "%s" @ "%s/hellopkg.tar"'
                % (swpackage, work_psf, work),
                env="conanrun",
            )
            self.run('test -s "%s/hellopkg.tar"' % work, env="conanrun")
            self.run('tar -tf "%s/hellopkg.tar" | grep -q "catalog"' % work, env="conanrun")
        except Exception:
            marker["passed"] = False
            marker["passedCount"] = 0
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
            raise

        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))

        result_file = os.path.join(pkg.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_file):
            raise ConanException(
                "upstream_test_result.json not found in package (%s) — "
                "upstream tests did not run during build(); refusing to pass "
                "silently" % result_file
            )
        with open(result_file, "r", encoding="utf-8") as _f:
            upstream = json.load(_f)
        for _k in ("status", "framework", "command", "discovered",
                   "executed", "passed", "failed", "skipped"):
            if _k not in upstream:
                raise ConanException("upstream_test_result.json missing key %r" % _k)
        _line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(_line, flush=True)
        self.output.info(_line)
        self.output.info("swbis 1.13.3 smoke OK")
