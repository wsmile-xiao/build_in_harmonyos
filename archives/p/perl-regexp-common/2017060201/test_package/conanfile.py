#!/usr/bin/env python3
"""Conan test_package for perl-regexp-common 2017060201.

Consumer validation against the *installed* package:
  A. packaged module layout + version marker (Python assertions)
  B. Regexp::Common loads, $Regexp::Common::VERSION == 2017060201
  C. submodules load (net/number/URI/delimited/comment/balanced/whitespace/zip/list/profanity)
  D. functional TAP suite (test_regexp_common.pl, 18 assertions)
  E. full upstream TAP suite: 73 .t files via Test::Harness

Uses the perl interpreter from PATH, falling back to the hnp perl install
(not on the runner's default PATH on HarmonyOS PC devices).
"""
import glob
import os
import shutil
import subprocess
import sys

from conan import ConanFile

PERL_FALLBACK = "/data/service/hnp/bin/perl"


def _perl():
    return shutil.which("perl") or PERL_FALLBACK


def _perl_env(lib_dir):
    env = os.environ.copy()
    parts = [lib_dir]
    parts.append(env.get("PERL5LIB", ""))
    env["PERL5LIB"] = ":".join(p for p in parts if p)
    return env


class PerlRegexpCommonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-regexp-common"]
        pkg_folder = dep.package_folder

        # ---- Test A: static inventory of the packaged artifact ----------
        script = os.path.join(self.recipe_folder, "test_perl_regexp_common.py")
        self.run(f'"{sys.executable}" "{script}" "{pkg_folder}"')

        # Locate installed Regexp/Common.pm dynamically (site_perl/<ver>/...).
        pm_files = glob.glob(
            os.path.join(pkg_folder, "lib", "perl5", "**", "Regexp", "Common.pm"),
            recursive=True,
        )
        if not pm_files:
            raise Exception("packaged Regexp/Common.pm not found")
        # lib_dir is the directory that must appear in PERL5LIB
        # (.../site_perl/<version>), i.e. two levels above Regexp/.
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))
        env = _perl_env(lib_dir)

        def run_or_fail(args, label):
            result = subprocess.run(args, env=env, capture_output=True, text=True)
            if result.returncode != 0:
                self.output.error(f"{label} failed: {result.stderr}")
                raise Exception(f"{label} failed with exit code {result.returncode}")
            self.output.success(f"{label}: {result.stdout.strip()}")

        # ---- Test B: load + version ------------------------------------
        run_or_fail(
            [_perl(), "-MRegexp::Common", "-e",
             'die unless $Regexp::Common::VERSION eq "2017060201"; print "Version OK\\n"'],
            "Regexp::Common load + version",
        )

        # ---- Test C: submodules load ------------------------------------
        run_or_fail(
            [_perl(), "-MRegexp::Common::net", "-MRegexp::Common::number",
             "-MRegexp::Common::URI", "-MRegexp::Common::delimited",
             "-MRegexp::Common::comment", "-MRegexp::Common::balanced",
             "-MRegexp::Common::whitespace", "-MRegexp::Common::zip",
             "-MRegexp::Common::list", "-MRegexp::Common::profanity",
             "-e", "print \"Submodules OK\\n\""],
            "Submodules",
        )

        # ---- Test D: functional TAP suite --------------------------------
        run_or_fail(
            [_perl(), os.path.join(self.recipe_folder, "test_regexp_common.pl")],
            "Functional TAP suite (15 assertions)",
        )

        # ---- Test E: full upstream TAP suite (73 .t files) ---------------
        share = os.path.join(pkg_folder, "share", "perl-regexp-common")
        upstream_root = os.path.join(self.build_folder, "upstream")
        if os.path.isdir(upstream_root):
            shutil.rmtree(upstream_root)
        os.makedirs(upstream_root)
        shutil.copytree(lib_dir, os.path.join(upstream_root, "lib"))
        shutil.copytree(os.path.join(share, "t"), os.path.join(upstream_root, "t"))
        for meta in ("META.json", "META.yml"):
            shutil.copy2(os.path.join(share, meta), upstream_root)

        test_files = sorted(
            glob.glob(os.path.join(upstream_root, "t", "*.t"))
            + glob.glob(os.path.join(upstream_root, "t", "*", "*.t"))
        )
        self.output.info(f"Running upstream TAP suite: {len(test_files)} test files")
        harness = (
            "use Test::Harness; $Test::Harness::verbose=0;"
            "runtests(@ARGV);"
        )
        result = subprocess.run(
            [_perl(), "-e", harness] + test_files,
            env=env, capture_output=True, text=True,
            cwd=upstream_root,
        )
        tail = "\n".join(result.stdout.strip().splitlines()[-6:])
        if result.returncode != 0:
            self.output.error(f"Upstream TAP suite failed:\n{tail}\n{result.stderr[-2000:]}")
            raise Exception("Upstream TAP suite failed")
        self.output.success(f"Upstream TAP suite PASS:\n{tail}")
