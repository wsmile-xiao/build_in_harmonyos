#!/usr/bin/env python3
"""Conan recipe — pit 0.1.0 (Makefile)."""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# System Ruby used to run the upstream Ruby test suite (test/pit_test.rb).
# Same pattern as the pandocomatic recipe: HNP provides a system Ruby
# runtime on HarmonyOS PC; PATH ruby is preferred when available.
HNP_RUBY = "/data/service/hnp/bin/ruby"


class PitConan(ConanFile):
    name = "pit"
    version = "0.1.0"
    description = "Project manager from hell (integrates with Git)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/michaeldv/pit"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._patch_current_user_fallback()
        # R33: compiler comes from Conan conf, never from shell env vars.
        # (L0h forbids dollar-brace compiler refs inside self.run calls;
        # "CC=<path>" below carries no dollar sign so it is safe.)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"
        self.run("make CC=\"%s\" -j1" % cc, cwd=self.source_folder)
        self._run_upstream_tests()

    def _patch_current_user_fallback(self):
        """Idempotent in-recipe fix for src/util.c current_user().

        HarmonyOS PC (HNP conan build user) may have no passwd entry for
        the current uid, so getpwuid() returns NULL and upstream kills
        every pit command with 'no username?!'. Fall back to
        $USER/$LOGNAME/getlogin() and finally a static name.

        Anchored text replacement (no unified-diff offsets) so it cannot
        suffer 'extra lines for hunk' parse failures. Raises loudly if
        the upstream anchor disappears.
        """
        util = os.path.join(self.source_folder, "src", "util.c")
        with open(util, "rb") as handle:
            content = handle.read().decode("utf-8")
        if "HMBS current_user fallback" in content:
            return
        anchor = (
            "char *current_user() {\n"
            "    static char *username = NULL;\n"
            "\n"
            "    if (!username) {\n"
            "        struct passwd *pws = getpwuid(geteuid());\n"
            "        if (!pws) {\n"
            "            perish(\"no username?!\");\n"
            "        } else {\n"
            "            username = pws->pw_name;\n"
            "        }\n"
            "    }\n"
            "    return username;\n"
        )
        replacement = (
            "char *current_user() {\n"
            "    static char *username = NULL;\n"
            "    static char fallback[64]; /* HMBS current_user fallback */\n"
            "\n"
            "    if (!username) {\n"
            "        struct passwd *pws = getpwuid(geteuid());\n"
            "        if (pws && pws->pw_name && pws->pw_name[0]) {\n"
            "            username = pws->pw_name;\n"
            "        } else {\n"
            "            const char *env = getenv(\"USER\");\n"
            "            if (!env || !*env) env = getenv(\"LOGNAME\");\n"
            "            if (!env || !*env) env = getlogin();\n"
            "            if (!env || !*env) env = \"ohos\";\n"
            "            strncpy(fallback, env, sizeof(fallback) - 1);\n"
            "            fallback[sizeof(fallback) - 1] = '\\0';\n"
            "            username = fallback;\n"
            "        }\n"
            "    }\n"
            "    return username;\n"
        )
        if anchor not in content:
            raise ConanException("HMBS current_user fallback anchor not found in src/util.c")
        with open(util, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content.replace(anchor, replacement, 1))

    def _find_ruby(self):
        found = shutil.which("ruby")
        if found:
            return found
        if os.path.isfile(HNP_RUBY):
            return HNP_RUBY
        return None

    def _run_upstream_tests(self):
        """Run the upstream test suite (test/pit_test.rb, same suite as `make test`).

        Upstream tiny_should prints '.' per passing assertion but NEVER sets a
        non-zero exit code on failure (Hand#oops only prints "match failed" /
        "equal failed" and continues), so exit code alone is a false-pass
        oracle: the previous "1/1 passed on rc==0" fallback reported success
        while the log contained real match failures. This wrapper therefore
        loads the exact upstream suite file with lightweight success/failure
        counters (no assertion added, none removed, none skipped), prints a
        machine-readable HMBS_UPSTREAM_SUMMARY line, and exits non-zero when
        anything failed. Counts are cross-checked against the failure-message
        lines so failures can never be undercounted. The verdict is persisted
        to upstream_test_result.json so test_package can re-emit it as
        HMBS_UPSTREAM_TEST_RESULT.
        """
        ruby = self._find_ruby()
        if ruby is None:
            marker = {
                "status": "skipped",
                "framework": "ruby test/pit_test.rb",
                "command": "ruby hmbs_run_upstream.rb (loads test/pit_test.rb)",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "no system ruby found; upstream suite requires a ruby interpreter",
            }
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)
            raise ConanInvalidConfiguration("ruby not found; cannot run upstream test/pit_test.rb")
        # Make sure both the ruby interpreter and the freshly built pit
        # binary resolve by name inside the upstream suite.
        extra_path = os.pathsep.join(
            path for path in (os.path.dirname(ruby), os.path.join(self.source_folder, "bin")) if path
        )
        if extra_path:
            os.environ["PATH"] = extra_path + os.pathsep + os.environ.get("PATH", "")
        test_dir = os.path.join(self.source_folder, "test").replace("\\", "/")
        wrapper = os.path.join(self.build_folder, "hmbs_run_upstream.rb")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "# HMBS counting wrapper: runs the exact upstream suite file\n"
                "# (test/pit_test.rb, the same file `make test` executes) with\n"
                "# honest success/failure counters. No assertion is added,\n"
                "# removed, or skipped; counters only observe.\n"
                "$hmbs_passed = 0\n"
                "$hmbs_failed = 0\n"
                "require \"%s/tiny_should\"\n" % test_dir
                + "module Kernel\n"
                "  alias_method :hmbs_orig_print, :print\n"
                "  def print(*args)\n"
                "    $hmbs_passed += 1 if args == [\".\"]\n"
                "    hmbs_orig_print(*args)\n"
                "  end\n"
                "  private :print\n"
                "end\n"
                "class Hand\n"
                "  alias_method :hmbs_orig_oops, :oops\n"
                "  def oops(msg)\n"
                "    $hmbs_failed += 1\n"
                "    hmbs_orig_oops(msg)\n"
                "  end\n"
                "end\n"
                "load \"%s/pit_test.rb\"\n" % test_dir
                + "puts \"HMBS_UPSTREAM_SUMMARY passed=#{$hmbs_passed} failed=#{$hmbs_failed}\"\n"
                "exit($hmbs_failed == 0 ? 0 : 1)\n"
            )
        log = os.path.join(self.build_folder, "upstream_test.log")
        rc = self.run("\"%s\" \"%s\" > \"%s\" 2>&1" % (ruby, wrapper, log),
                      cwd=self.source_folder, ignore_errors=True)
        with open(log, encoding="utf-8", errors="replace") as handle:
            out = handle.read()
        # Echo the real test output into the conan log so CI keeps the evidence.
        print(out)
        # Mirror `make test` cleanup: drop the suite database file.
        stale_db = os.path.join(self.source_folder, "test", "test.pitfile")
        try:
            if os.path.isfile(stale_db):
                os.remove(stale_db)
        except OSError:
            pass
        command = "ruby hmbs_run_upstream.rb (loads test/pit_test.rb; same suite as 'make test')"
        summary = re.search(r"HMBS_UPSTREAM_SUMMARY passed=(\d+) failed=(\d+)", out)
        fail_lines = len(re.findall(r"(?:match|equal) failed", out))
        unit = re.search(
            r"(\d+)\s+tests?,\s+(\d+)\s+assertions?,\s+(\d+)\s+failures?,\s+(\d+)\s+errors?", out
        )
        if summary:
            passed = int(summary.group(1))
            failed = int(summary.group(2))
            # Never undercount failures: trust the larger of the counter and
            # the failure-message lines visible in the log.
            failed = max(failed, fail_lines)
            discovered = executed = passed + failed
            passed = discovered - failed
            status = "passed" if (rc == 0 and failed == 0 and discovered > 0) else "failed"
        elif unit:
            tests = int(unit.group(1))
            failed = int(unit.group(3)) + int(unit.group(4))
            discovered = executed = tests
            passed = discovered - failed
            status = "passed" if (rc == 0 and failed == 0) else "failed"
            command = "make test"
        else:
            # Unrecognized harness output must NEVER be reported as passed:
            # visible failure lines fail the build, anything else is an
            # honest failure with the reason recorded.
            failed = fail_lines
            if failed > 0:
                discovered = executed = failed
                passed = 0
            else:
                discovered = executed = 0
                passed = 0
            status = "failed"
            marker_reason = "unrecognized harness output (no HMBS_UPSTREAM_SUMMARY); rc=%s" % rc
            marker = {
                "status": status,
                "framework": "ruby test/pit_test.rb",
                "command": command,
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": 0,
                "reason": marker_reason,
            }
            with open(os.path.join(self.build_folder, "upstream_test_result.json"), "w", encoding="utf-8") as handle:
                json.dump(marker, handle)
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)
            raise ConanException("upstream tests failed: " + json.dumps(marker))
        marker = {
            "status": status,
            "framework": "ruby test/pit_test.rb",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        with open(os.path.join(self.build_folder, "upstream_test_result.json"), "w", encoding="utf-8") as handle:
            json.dump(marker, handle)
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)
        if status != "passed":
            raise ConanException("upstream tests failed: " + json.dumps(marker))

    def package(self):
        # Upstream "make install" has no DESTDIR support (it copies straight
        # to $(PREFIX)/bin), so package the built binary directly instead.
        copy(self, "pit", src=os.path.join(self.source_folder, "bin"), dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "upstream_test_result.json", src=self.build_folder, dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
