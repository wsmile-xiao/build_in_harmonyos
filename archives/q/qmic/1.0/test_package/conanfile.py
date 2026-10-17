#!/usr/bin/env python3
"""Conan test_package for qmic 1.0 — HarmonyOS consumer test.

Runs two shell scripts against the installed binary:

  test_qmic.sh       upstream corpus conformance (18 tests/*.qmi inputs,
                     accept/reject asserted individually) + CLI contract.
  ohos_qmic_test.sh  HarmonyOS platform-specific checks for the musl
                     adaptation (program_invocation_short_name -> __progname).

The upstream tests/ corpora are not shipped in the package (qmic is an
application package: only bin/qmic is installed), so they are staged from the
recipe's source export and passed to the scripts explicitly.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class QmicTestConan(ConanFile):
    settings = 'os', 'arch', 'compiler', 'build_type'
    generators = 'VirtualRunEnv'
    test_type = 'explicit'

    def requirements(self):
        # run=True so VirtualRunEnv injects the packaged bin/ into PATH.
        self.requires(self.tested_reference_str, run=True)

    def _bindir(self):
        dep = self.dependencies.get('qmic')
        if dep is None:
            return ''
        rel = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else 'bin'
        cand = rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)
        if os.path.isdir(cand):
            return cand
        return os.path.join(dep.package_folder, 'bin')

    def _tmpdir(self):
        tmpdir = (os.environ.get('TMPDIR') or os.environ.get('TMP')
                  or os.environ.get('TEMP') or '')
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, 'tmp')
        os.makedirs(tmpdir, exist_ok=True)
        os.environ['TMPDIR'] = tmpdir
        os.environ['TMP'] = tmpdir
        os.environ['TEMP'] = tmpdir
        os.environ['TEMPDIR'] = tmpdir
        return tmpdir

    def test(self):
        if not can_run(self):
            self.output.info('cross-building: skipping runtime execution')
            return

        bindir = self._bindir()
        self.output.info('qmic bindir=%s' % bindir)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # The 18 upstream tests/*.qmi corpora are shipped verbatim under
        # test_package/corpus/ (byte-identical to the v1.0 tarball). Keeping them
        # next to the scripts makes the test self-contained and offline-safe
        # (the application package itself only installs bin/qmic).
        corpus = os.path.join(script_dir, 'corpus')
        self._tmpdir()
        shell = os.environ.get('CONFIG_SHELL') or '/bin/sh'

        self.run('"%s" "%s" "%s" "%s"'
                 % (shell, os.path.join(script_dir, 'test_qmic.sh'), bindir, corpus),
                 env='conanrun')
        self.run('"%s" "%s" "%s" "%s"'
                 % (shell, os.path.join(script_dir, 'ohos_qmic_test.sh'),
                    bindir, corpus),
                 env='conanrun')
