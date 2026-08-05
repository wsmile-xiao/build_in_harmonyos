#!/usr/bin/env python3
"""Conan recipe for xmlformat 1.04 — Perl/Ruby XML document formatter.

xmlformat is a script-only tool (no compilation): it ships two
interpreters of the same formatter (xmlformat.pl in Perl, xmlformat.rb
in Ruby) plus a test suite under tests/ and bad*.xml negative cases.
Build system: custom (runtest shell driver, `make test`).

The recipe installs xmlformat.pl as `bin/xmlformat` (Perl is available
on HarmonyOS; Ruby is not, so the Ruby variant is not installed) and
runs the upstream test suite (`./runtest -p all` + the 5 bad*.xml
negative cases) inside build().
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class XmlformatConan(ConanFile):
    name = "xmlformat"
    version = "1.04"
    description = "XML document formatter — reformats XML documents with configurable line wrapping/indentation."
    license = "BSD-2-Clause"
    homepage = "http://www.kitebird.com/software/xmlformat/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # conandata.yml sources is a *list* of mappings; unpack the first
        # entry. Using ** on the list directly raises TypeError.
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R32: only on supported platforms
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

        # xmlformat is a Perl script tool — no compilation step.
        # Resolve the absolute Perl interpreter path on the build host.
        # The upstream xmlformat.pl shebang is `#!/usr/bin/perl -w`, but
        # HarmonyOS PC may not have /usr/bin/perl (perl lives elsewhere),
        # which makes mksh report `./xmlformat.pl: No such file or
        # directory` (execve ENOENT on the shebang interpreter, not the
        # script itself).  We rewrite the shebang to the real perl path
        # so `./xmlformat.pl` execs correctly.  R9: do not fake a pass.
        perl_path = shutil.which("perl")
        if not perl_path:
            raise ConanInvalidConfiguration(
                "Perl interpreter not found on PATH — required to run "
                "xmlformat's upstream test suite"
            )
        perl_path = os.path.abspath(perl_path)
        self.run(f"'{perl_path}' -e 'print 1'")

        # xmlformat's upstream test harness (runtest, tests/*.xml, bad*.xml,
        # bad*.res) all live at the tarball root and reference each other by
        # relative path (`./xmlformat.pl`, `./runtest`, `tests/`, `bad1.xml`).
        # Conan 2.x's basic_layout puts the unpacked source in source_folder
        # and runs build() with cwd=build_folder — a *different* directory.
        # Copy the whole source tree into build_folder so every relative
        # path in runtest/bad*.xml resolves to a real file.  The runtest
        # shell driver and xmlformat.pl script are then executed from
        # build_folder.
        copy(self, "*", src=self.source_folder, dst=self.build_folder)

        # Rewrite the shebang of the copied xmlformat.pl to the actual perl
        # path on this host.  Upstream ships `#!/usr/bin/perl -w`; on
        # HarmonyOS PC /usr/bin/perl may not exist (perl is at a different
        # absolute path), which makes the kernel refuse to exec the script
        # with ENOENT — mksh surfaces this as
        # `./xmlformat.pl: No such file or directory`.  Pointing the
        # shebang at the resolved perl path fixes the exec.  We only
        # rewrite the shebang of the copy in build_folder, leaving the
        # original source untouched.
        self._rewrite_perl_shebang(
            os.path.join(self.build_folder, "xmlformat.pl"), perl_path
        )

        # ── Upstream official test suite (必做) ──
        # runtest -p <name> → runs tests/<name>.xml through xmlformat.pl,
        # diffing the .out against the committed .res expected output.
        # runtest never returns non-zero on a diff (it ignores diff's
        # exit code), so we wrap it to surface real failures: any non-
        # empty diff output means a regression.  The 5 bad*.xml cases
        # are negative tests (malformed XML) kept in the top dir; we
        # run them directly and diff against bad*.res.
        #
        # We count discovered / executed / passed / failed / skipped
        # honestly and emit the HMBS_UPSTREAM_TEST_RESULT JSON marker
        # (one line, machine-readable) so the hmbs hard gate can verify
        # the upstream suite actually ran.  discovered = number of
        # tests/*.xml fixtures + 5 bad*.xml negative cases (per the
        # upstream Makefile `test` target).  A case is "passed" only
        # when its diff output is empty; "failed" when non-empty.  No
        # case is ever skipped (every discovered case is executed).
        #
        # Note on `set -e`: the `out=$(./runtest ...)` command
        # substitution returns runtest's exit code.  runtest can exit
        # non-zero for reasons unrelated to test pass/fail (e.g. a
        # trailing `exit $?` after a per-case diff).  Under `set -e`
        # that non-zero would kill the whole recipe before any test
        # body runs — observed on the HarmonyOS device where upstream
        # tests reported "discovered 0, executed 0".  We therefore do
        # NOT use `set -e` here; each command's failure is handled
        # explicitly (`|| out=` to swallow runtest's exit code, the
        # `if ! diff` form to surface bad-case regressions).
        self.run(
            "set -uo pipefail; "
            "discovered=0; executed=0; passed=0; failed=0; skipped=0; "
            "for t in $(cd tests && ls *.xml | sed 's/\\.xml//'); do "
            "discovered=$((discovered+1)); "
            "executed=$((executed+1)); "
            "out=$(./runtest -p \"$t\" 2>&1) || out=$out; "
            "if [ -n \"$out\" ]; then echo \"FAIL $t\"; echo \"$out\"; failed=$((failed+1)); else passed=$((passed+1)); fi; "
            "done; "
            "for i in 1 2 3 4 5; do "
            "discovered=$((discovered+1)); "
            "executed=$((executed+1)); "
            "./xmlformat.pl bad$i.xml > bad$i.out 2>&1 || true; "
            "if ! diff -u bad$i.res bad$i.out; then echo \"FAIL bad$i\"; failed=$((failed+1)); else passed=$((passed+1)); fi; "
            "done; "
            "if [ $failed -eq 0 ]; then status=\"passed\"; else status=\"failed\"; fi; "
            "printf 'HMBS_UPSTREAM_TEST_RESULT={\"status\":\"%s\",\"framework\":\"runtest\",\"command\":\"runtest -p all + bad*.xml\",\"discovered\":%d,\"executed\":%d,\"passed\":%d,\"failed\":%d,\"skipped\":%d}\\n' \"$status\" \"$discovered\" \"$executed\" \"$passed\" \"$failed\" \"$skipped\" >&2; "
            "exit $failed",
            cwd=self.build_folder,
        )

    def _rewrite_perl_shebang(self, script_path, perl_path):
        """Rewrite the shebang of a Perl script to the absolute perl path.

        Upstream ships `#!/usr/bin/perl -w`; on HarmonyOS PC /usr/bin/perl
        may not exist (perl lives at a different absolute path), which
        makes the kernel refuse to exec the script with ENOENT — mksh
        surfaces this as `./xmlformat.pl: No such file or directory`.
        Pointing the shebang at the resolved perl path fixes the exec.
        Only the shebang interpreter path is changed; flags (-w) preserved.
        """
        with open(script_path, "r", encoding="latin-1") as fh:
            text = fh.read()
        if text.startswith("#!"):
            nl = text.find("\n")
            first = text[:nl] if nl != -1 else text
            rest = first[2:].strip()
            parts = rest.split(None, 1)
            flags = " " + parts[1] if len(parts) > 1 else ""
            new_shebang = f"#!{perl_path}{flags}"
            text = new_shebang + text[nl:] if nl != -1 else new_shebang
            with open(script_path, "w", encoding="latin-1") as fh:
                fh.write(text)
        try:
            os.chmod(script_path, 0o755)
        except OSError:
            pass

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        perl_path = os.path.abspath(shutil.which("perl") or "perl")

        # Install the Perl script as bin/xmlformat (INSTALL: rename so the
        # .pl extension need not be typed on every invocation).
        os.makedirs(os.path.join(pkg, "bin"), exist_ok=True)
        installed = os.path.join(pkg, "bin", "xmlformat")
        shutil.copy2(os.path.join(src, "xmlformat.pl"), installed)
        # Rewrite shebang so the installed binary execs on HarmonyOS PC
        # where /usr/bin/perl may be absent (perl is at a different path).
        self._rewrite_perl_shebang(installed, perl_path)

        # Ship the Ruby variant too (for environments that have ruby); harmless
        # if ruby is absent — only invoked when explicitly called.
        shutil.copy2(os.path.join(src, "xmlformat.rb"),
                     os.path.join(pkg, "bin", "xmlformat.rb"))
        os.chmod(os.path.join(pkg, "bin", "xmlformat.rb"), 0o755)

        # Man page and docs
        man_dir = os.path.join(pkg, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        if os.path.exists(os.path.join(src, "docs", "xmlformat.1")):
            shutil.copy2(os.path.join(src, "docs", "xmlformat.1"),
                         os.path.join(man_dir, "xmlformat.1"))

        # Config example shipped upstream as docs/xmlformat.conf
        conf_dir = os.path.join(pkg, "share", "xmlformat")
        os.makedirs(conf_dir, exist_ok=True)
        if os.path.exists(os.path.join(src, "docs", "xmlformat.conf")):
            shutil.copy2(os.path.join(src, "docs", "xmlformat.conf"),
                         os.path.join(conf_dir, "xmlformat.conf"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
