import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class ClpbarTestConan(ConanFile):
    """test_package for clpbar — executes the installed `bar` binary.

    3 checks live in test.sh (see MANIFEST.yml): a --version smoke test, a
    stdin/stdout pipe round-trip verified with cmp, and a -if/-of file
    round-trip verified with cmp (mirrors upstream test-002 semantics).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # [shell_getcwd] HMDFS: conan test cwd may have inaccessible
        # parents (shell-init/job-working-directory getcwd warnings, then
        # `bar` resolves to 127). Recover to a forward-resolvable dir and
        # export a valid PWD before spawning any shell (backuppc-rsync /
        # nspr precedent). Previous round only fixed the main recipe's
        # build(); this round fixes the test driver itself.
        try:
            if self.build_folder and os.path.isdir(self.build_folder):
                os.chdir(self.build_folder)
                os.environ["PWD"] = self.build_folder
        except OSError as exc:
            self.output.warning("clpbar test: chdir PWD recovery failed: %s" % exc)

        bar_bin = os.path.join(
            self.dependencies["clpbar"].package_folder, "bin", "bar")
        if not os.path.isfile(bar_bin):
            pkg = self.dependencies["clpbar"].package_folder
            try:
                listing = sorted(os.listdir(os.path.join(pkg, "bin")))
            except OSError:
                listing = ["<bin missing>"]
            raise ConanException(
                "clpbar test: bar binary not found in package: %s "
                "(package bin: %s)" % (bar_bin, listing))

        # Prefer hmbs/profile-injected shell (SHELL/CONFIG_SHELL); HNP bash
        # is only a fallback. Previous round hardcoded HNP bash first.
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL")
                 or "/data/service/hnp/bin/bash")
        if not (os.path.isfile(shell) or shell == "sh"):
            shell = "/data/service/hnp/bin/bash"

        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            tmpdir = self.build_folder

        test_script = os.path.join(self.recipe_folder, "test.sh")
        command = '"%s" "%s"' % (shell, test_script)
        # hmbs hard gate: the marker must carry the real test_package counts
        # (3 checks in test.sh, per MANIFEST.yml).
        result = {"executed": True, "passed": False, "command": command,
                  "discovered": 3, "passedCount": 0}
        env_vars = Environment()
        env_vars.define("BAR_BIN", bar_bin)
        env_vars.define("TMPDIR", tmpdir)
        env_vars.define("TMP", tmpdir)
        env_vars.define("TEMP", tmpdir)
        try:
            with env_vars.vars(self).apply():
                self.run(command, env="conanrun", cwd=self.build_folder)
        except Exception:
            self.output.info("HMBS_TEST_PACKAGE_RESULT="
                             + json.dumps(result))
            raise
        result["passed"] = True
        result["passedCount"] = 3
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(result))
        # Re-emit upstream evidence on EVERY run: `conan create` skips
        # build() when the binary is cached ("Already installed!"), so the
        # build()-only marker disappears. build() persists
        # upstream_test_result.json into res/; re-print it here so the
        # gate always sees HMBS_UPSTREAM_TEST_RESULT (abuild-sudo precedent).
        # Counts come from the real `make check` device run in build().
        upstream_path = os.path.join(
            self.dependencies["clpbar"].package_folder, "res",
            "upstream_test_result.json")
        if not os.path.isfile(upstream_path):
            raise ConanException(
                "clpbar test: upstream_test_result.json not found in "
                "package (%s) -- upstream tests did not run during build(); "
                "refusing to pass silently" % upstream_path)
        with open(upstream_path, "r", encoding="utf-8") as fh:
            upstream = json.load(fh)
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
