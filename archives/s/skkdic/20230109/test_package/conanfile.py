#!/usr/bin/env python3
"""Conan test_package -- skkdic 20230109 (pure-data SKK dictionary package).

Two layers, both executed against the *installed* package:

1. **Upstream's own test suite.** The 20230109 release tarball ships two Emacs
   ERT cases in ``zipcode/test/zipcode-test.el``; upstream's only test entry
   point is the ``test`` target in ``zipcode/Makefile.in:116-118``::

       $(EMACS) --batch --quick --directory test --load test/all-tests.el \
                 --funcall ert-run-tests-batch-and-exit

   The tarball is fetched here and pinned by sha256 (nothing is vendored into
   the repository) and the cases are run with the published ``emacs/29.1``
   OHOS package, from inside the installed ``share/skk`` tree.  Both cases read
   ``SKK-JISYO.zipcode`` / ``SKK-JISYO.office.zipcode`` from the current
   directory (``coding-system-for-read 'euc-jp``) and compare the complete
   entry line of postal codes 6020033 / 1008926 against the expected string,
   so the dictionaries under test are literally the packaged ones.
2. **Consumer-side checks** (``test_skkdic.py``): the ``skkdic_datadir``
   cpp_info property the recipe publishes, 20 core dictionaries, SKK
   line-format parsing, entry counts and provenance documents.

The first layer is what makes this package's claim "upstream test suite
executed: 2/2" verifiable rather than asserted.
"""
import json
import os
import shlex
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get

# Same release tarball the recipe itself builds from (see conandata.yml).
SKKDIC_URL = ("https://deb.debian.org/debian/pool/main/s/skkdic/"
              "skkdic_20230109.orig.tar.gz")
SKKDIC_SHA256 = ("dc4f1550b84c80882a0db0b7e6db47a1baed7b40a2f821d0355464ed36d"
                 "2ced4")

# emacs ERT cases in zipcode/test/zipcode-test.el of that tarball:
#   jisyo-zipcode/test1        SKK-JISYO.zipcode         entry for 6020033
#   jisyo-office-zipcode/test1 SKK-JISYO.office.zipcode  entry for 1008926
UPSTREAM_TESTS = 2

# test_package/conanfile.py: skkdic_datadir property (1)
# test_package/test_skkdic.py: 58
CONSUMER_ASSERTIONS = 59


class SkkdicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # GNU Emacs 29.1 executes the upstream ERT cases; it is a test-only
        # dependency of this test_package (a published OHOS binary, see the
        # emacs/29.1 recipe).  skkdic itself stays dependency-free.
        self.requires("emacs/29.1")

    # -- helpers ---------------------------------------------------------

    def _bash(self):
        """A usable shell on the OHOS worker (test source is POSIX sh)."""
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
            "/storage/Users/currentUser/usr/local/bin/bash",
            "/bin/bash",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def _run(self, inner):
        """Run `inner` through a shell; on OHOS the default shell is not
        guaranteed to be POSIX sh, so quote it explicitly."""
        if self.settings.os == "OHOS":
            return "%s -c %s" % (shlex.quote(self._bash()), shlex.quote(inner))
        return inner

    @staticmethod
    def _scratch():
        """Writable scratch dir outside the archive tree (T035): the OHOS
        worker's /tmp is read-only, so prefer TMPDIR then ~/tmp."""
        for root in (os.environ.get("TMPDIR"),
                     os.path.join(os.path.expanduser("~"), "tmp")):
            if root:
                try:
                    os.makedirs(root, exist_ok=True)
                    return tempfile.mkdtemp(prefix="skkdic-upstream-", dir=root)
                except OSError:
                    continue
        return tempfile.mkdtemp(prefix="skkdic-upstream-")

    def _upstream_fixture(self, scratch):
        """Fetch the exact release tarball the recipe builds from (sha256
        pinned) and return the directory holding upstream's ERT tests."""
        src = os.path.join(scratch, "upstream")
        get(self, url=SKKDIC_URL, sha256=SKKDIC_SHA256,
            filename="skkdic_20230109.orig.tar.gz", strip_root=True,
            destination=src)
        testdir = os.path.join(src, "zipcode", "test")
        if not os.path.isfile(os.path.join(testdir, "all-tests.el")):
            raise ConanException(
                "upstream test entry point not found in the release tarball: "
                "%s/all-tests.el" % testdir)
        return testdir

    # -- test ------------------------------------------------------------

    def test(self):
        # 1. Locate the dictionary tree through the property the recipe
        #    publishes.  If the property is missing the package is unusable
        #    for consumers.
        pkg = self.dependencies["skkdic"]
        rel = pkg.cpp_info.get_property("skkdic_datadir")
        if not rel:
            raise ConanException(
                "skkdic recipe does not publish the cpp_info property "
                "'skkdic_datadir'; consumers cannot locate the dictionaries")
        data_dir = os.path.join(pkg.package_folder, rel)
        if not os.path.isdir(data_dir):
            raise ConanException("installed data dir not found: %s" % data_dir)

        here = os.path.dirname(os.path.abspath(__file__))
        emacs = os.path.join(self.dependencies["emacs"].package_folder,
                             "bin", "emacs")
        if not os.path.isfile(emacs):
            raise ConanException("emacs executable not found: %s" % emacs)

        scratch = self._scratch()
        rc_upstream = 1
        try:
            upstream_testdir = self._upstream_fixture(scratch)
            runner = os.path.join(here, "run_upstream_tests.sh")
            rc_upstream = self.run(
                self._run(
                    'EMACS_BIN=%s DATADIR=%s UPSTREAM_TESTDIR=%s '
                    'EXPECTED_TESTS=%d TMPDIR=%s sh %s'
                    % (shlex.quote(emacs), shlex.quote(data_dir),
                       shlex.quote(upstream_testdir), UPSTREAM_TESTS,
                       shlex.quote(scratch), shlex.quote(runner))),
                ignore_errors=True, env="conanrun")

            # 2. Consumer-side structural / format checks.
            script = os.path.join(here, "test_skkdic.py")
            rc_consumer = self.run(
                'python3 %s %s' % (shlex.quote(script), shlex.quote(data_dir)),
                ignore_errors=True, env="conanrun")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "executed" if rc_upstream == 0 else "failed",
            "command": ("emacs --batch --quick --directory test "
                        "--load test/all-tests.el "
                        "--funcall ert-run-tests-batch-and-exit "
                        "(zipcode/Makefile.in test target)"),
            "framework": "emacs-ert (emacs/29.1)",
            "discovered": UPSTREAM_TESTS,
            "executed": UPSTREAM_TESTS if rc_upstream == 0 else 0,
            "passed": UPSTREAM_TESTS if rc_upstream == 0 else 0,
            "failed": 0 if rc_upstream == 0 else UPSTREAM_TESTS,
            "skipped": 0,
            "rc": rc_upstream,
        }))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc_consumer == 0),
            "command": "test_skkdic.py (consumer-side dictionary checks)",
            "consumer_passed": CONSUMER_ASSERTIONS if rc_consumer == 0 else 0,
            "consumer_total": CONSUMER_ASSERTIONS,
            "rc": rc_consumer,
        }))

        if rc_upstream != 0:
            raise ConanException(
                "skkdic upstream ERT tests failed (rc=%s)" % rc_upstream)
        if rc_consumer != 0:
            raise ConanException(
                "skkdic consumer test failed (rc=%s)" % rc_consumer)
