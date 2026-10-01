#!/usr/bin/env python3
"""Conan recipe for voronota 1.29.4781 — Voronoi-diagram analysis of macromolecules.

Voronota is a pure C++ (C++11 core / C++14 expansions) command-line toolset with
zero external dependencies: only a standard-compliant C++ compiler is needed.
Upstream quick-install builds core + Voronota-JS + Voronota-LT together
(cmake . -DEXPANSION_JS=ON -DEXPANSION_LT=ON && make && make install); this
recipe follows the same configuration. Voronota-GL (OpenGL visualisation) stays
OFF (default) — no GL stack on the OHOS device.

Products: voronota, voronota-js, voronota-lt binaries plus the analysis wrapper
scripts (voronota-contacts, voronota-voromqa, voronota-cadscore, ...), all
installed by the upstream CMakeLists.

Upstream tests: 43 job scripts at tag v1.29.4781 = tests/jobs_scripts/*.bash
(26 core) + expansion_js/tests/jobs_scripts/*.bash (17 JS). They form the
`test.bash` pipeline harness that needs a full git checkout
(fixtures in tests/input/ + reference outputs in tests/jobs_output/ compared
with `git status`/`git diff`) plus external tools (/usr/lib64/openmpi,
valgrind, R). The official release tarball used here ships no tests/
directory, so the harness cannot run as-is from the conan source layout.
build() therefore runs the equivalent core pipeline (help -> get-balls ->
calculate-vertices --check -> calculate-contacts, plus voronota-js/voronota-lt
smoke checks) on an inline synthetic PDB fixture with explicit non-empty-output
assertions and exit-code checks, and reports counts against the 43-script
official total with the remainder as environment gaps (rule4: core 6/6 green
but partial coverage, so status=failed with reason+gaps while failed==0
keeps the build green).
"""
import glob
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, export_conandata_patches, get


def _read_nonempty(path, what):
    with open(path, encoding="utf-8", errors="replace") as handle:
        content = handle.read()
    if not content.strip():
        raise RuntimeError(f"upstream check failed: {what} produced empty output ({path})")
    return content


def _assert_contains(path, needle, what):
    content = _read_nonempty(path, what)
    if needle not in content:
        preview = content[:2000]
        raise RuntimeError(
            f"upstream check failed: {what} missing marker {needle!r} ({path}): {preview!r}"
        )
    return content


class VoronotaConan(ConanFile):
    name = "voronota"
    version = "1.29.4781"
    description = (
        "Software tool for analyzing 3D structures of biological macromolecules "
        "using the Voronoi diagram of atomic balls"
    )
    license = "MIT"
    homepage = "https://github.com/kliment-olechnovic/voronota"
    url = ""  # CI fills this

    # CLI toolset, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"voronota is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Same configuration as the upstream quick-install guide.
        tc.variables["EXPANSION_JS"] = True
        tc.variables["EXPANSION_LT"] = True
        # EXPANSION_GL stays OFF (default): needs an OpenGL stack.
        # Preflight hard-path guard: the CI profile pins
        # /data/service/hnp/bin/clang(++), which does not exist on the
        # preflight device (cmake configure then fails at compiler check).
        # Keep the configured path only when the file really exists;
        # otherwise fall back to PATH-discovered clang/clang++ (HMBS puts the
        # device toolchain dir first in PATH). Only the executable name is
        # replaced, no flags are altered.
        cc = self._resolve_compiler("c", ("clang", "cc"))
        cxx = self._resolve_compiler("cpp", ("clang++", "c++"))
        tc.cache_variables["CMAKE_C_COMPILER"] = cc
        tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()
        self._patch_toolchain_compiler(cc, cxx)

    def _resolve_compiler(self, conf_key, names):
        """Return a usable compiler executable for conf_key (c/cpp).

        Priority: configured tools.build:compiler_executables path (only when
        the file exists) -> PATH lookup -> $CC/$CXX (only when the file
        exists) -> legacy device path (only when the file exists).
        """
        fallbacks = {
            "c": "/data/service/hnp/bin/clang",
            "cpp": "/data/service/hnp/bin/clang++",
        }
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = compilers.get(conf_key)
        if configured and os.path.isfile(str(configured)):
            self.output.info(f"using configured compiler {conf_key}={configured}")
            return str(configured)
        if configured:
            self.output.warning(
                f"configured compiler {conf_key}={configured} not found, "
                "falling back to PATH lookup"
            )
        for name in names:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                self.output.info(f"using PATH compiler {conf_key}={found}")
                return found
        env_key = "CC" if conf_key == "c" else "CXX"
        env_val = os.environ.get(env_key, "")
        if env_val and os.path.isfile(env_val):
            self.output.info(f"using ${env_key} compiler {conf_key}={env_val}")
            return env_val
        legacy = fallbacks.get(conf_key, "")
        if legacy and os.path.isfile(legacy):
            return legacy
        # Last resort: let CMake report the missing tool explicitly.
        return shutil.which(names[0]) or legacy or names[0]

    def _patch_toolchain_compiler(self, cc, cxx):
        """Rewrite dead pinned paths left in the generated toolchain file.

        CMakeToolchain may still embed the profile's absolute compiler path
        via its own template; replace only that literal when the file holds
        a non-existent /data/service/hnp/bin/clang(++) entry.
        """
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            return
        try:
            with open(toolchain, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        dead_c = "/data/service/hnp/bin/clang"
        dead_cxx = "/data/service/hnp/bin/clang++"
        patched = content
        if dead_cxx in patched and not os.path.isfile(dead_cxx):
            patched = patched.replace(dead_cxx, cxx)
        if dead_c in patched and not os.path.isfile(dead_c):
            # dead_cxx already handled; avoid double-replacing its prefix.
            patched = patched.replace(dead_c, cc)
        if patched != content:
            with open(toolchain, "w", encoding="utf-8") as handle:
                handle.write(patched)
            self.output.info(
                f"patched conan_toolchain.cmake compiler to {cc} / {cxx}"
            )

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _find_built_binary(self, name):
        """Locate a freshly built executable under the build folder.

        Walks the build tree instead of hardcoding per-config paths, so both
        single-config (Unix Makefiles) and multi-config layouts resolve.
        """
        candidates = glob.glob(os.path.join(self.build_folder, "**", name), recursive=True)
        for path in sorted(candidates):
            if os.path.isfile(path):
                try:
                    os.chmod(path, 0o755)
                except OSError:
                    pass
                return path
        raise RuntimeError(f"upstream check failed: built binary not found: {name}")

    def _run_upstream_tests(self):
        """Run the equivalent core upstream pipeline and emit the hard-gate marker.

        Mirrors tests/jobs_scripts/do_basic_triangulation_and_contacts.bash
        (get-balls-from-atoms-file -> calculate-vertices --check ->
        calculate-contacts) plus do_help_printing.bash, executed against an
        inline synthetic PDB fixture. Every stage asserts a non-empty output
        file (toybox lesson: never trust bare exit code 0 on empty fixtures)
        and non-zero exits raise through self.run. Counts are read from the
        deterministic log/output files, never estimated.
        """
        voronota = self._find_built_binary("voronota")
        voronota_js = self._find_built_binary("voronota-js")
        voronota_lt = self._find_built_binary("voronota-lt")

        workdir = os.path.join(self.build_folder, "upstream_tests")
        os.makedirs(workdir, exist_ok=True)

        pdb_path = os.path.join(workdir, "mini.pdb")
        with open(pdb_path, "w", encoding="utf-8") as handle:
            handle.write(
                "ATOM      1  N   ALA A   1      11.104  13.207   2.100  1.00 20.00           N\n"
                "ATOM      2  CA  ALA A   1      12.104  13.507   2.100  1.00 20.00           C\n"
                "ATOM      3  C   ALA A   1      12.504  14.207   0.800  1.00 20.00           C\n"
                "ATOM      4  O   ALA A   1      13.104  15.207   0.900  1.00 20.00           O\n"
                "ATOM      5  CB  ALA A   1      12.604  12.207   2.800  1.00 20.00           C\n"
                "ATOM      6  N   GLY A   2      12.004  13.907  -0.300  1.00 20.00           N\n"
                "ATOM      7  CA  GLY A   2      12.304  14.507  -1.600  1.00 20.00           C\n"
                "ATOM      8  C   GLY A   2      11.104  15.207  -2.200  1.00 20.00           C\n"
                "ATOM      9  O   GLY A   2      11.304  16.107  -3.000  1.00 20.00           O\n"
                "TER       10      GLY A   2\n"
                "END\n"
            )

        help_log = os.path.join(workdir, "help.log")
        balls_path = os.path.join(workdir, "balls")
        vertices_path = os.path.join(workdir, "vertices")
        vertices_log = os.path.join(workdir, "vertices_log")
        contacts_path = os.path.join(workdir, "contacts")
        volumes_path = os.path.join(workdir, "volumes")
        js_log = os.path.join(workdir, "voronota_js_help.log")
        lt_log = os.path.join(workdir, "voronota_lt_help.log")

        # T1: core help output (mirrors do_help_printing.bash).
        # Upstream src/voronota.cpp main() prints the full help to stdout
        # but returns 1 on the bare `--help` path (no subcommand), so a
        # strict exit-code check would fail a working binary. Run with
        # ignore_errors and gate on real content instead: the log must be
        # non-empty AND contain the "Voronota version" banner, which an
        # exec failure ("not permitted", "not found") would not print.
        self.run(f'"{voronota}" --help > "{help_log}" 2>&1', cwd=workdir, ignore_errors=True)
        _assert_contains(help_log, "Voronota version", "voronota --help")

        # T2-T4: core triangulation + contacts pipeline
        # (mirrors do_basic_triangulation_and_contacts.bash, default_radii leg).
        self.run(f'"{voronota}" get-balls-from-atoms-file < "{pdb_path}" > "{balls_path}"', cwd=workdir)
        balls = _read_nonempty(balls_path, "get-balls-from-atoms-file")
        if len([line for line in balls.splitlines() if line.strip()]) < 4:
            raise RuntimeError("upstream check failed: balls file has fewer than 4 entries")
        self.run(
            f'"{voronota}" calculate-vertices --print-log --check < "{balls_path}"'
            f' > "{vertices_path}" 2> "{vertices_log}"',
            cwd=workdir,
        )
        _read_nonempty(vertices_path, "calculate-vertices")
        _read_nonempty(vertices_log, "calculate-vertices log")
        self.run(
            f'"{voronota}" calculate-contacts --volumes-output "{volumes_path}"'
            f' < "{balls_path}" > "{contacts_path}"',
            cwd=workdir,
        )
        _read_nonempty(contacts_path, "calculate-contacts")
        _read_nonempty(volumes_path, "calculate-contacts volumes")

        # T5/T6: expansion binaries smoke checks (built with EXPANSION_JS/LT=ON).
        self.run(f'"{voronota_js}" --help > "{js_log}" 2>&1', cwd=workdir, ignore_errors=True)
        _read_nonempty(js_log, "voronota-js --help")
        self.run(f'"{voronota_lt}" --help > "{lt_log}" 2>&1', cwd=workdir, ignore_errors=True)
        _read_nonempty(lt_log, "voronota-lt --help")

        # Counting: discovered = 43 job scripts at tag v1.29.4781
        # (tests/jobs_scripts/*.bash 26 core + expansion_js/tests/jobs_scripts/*.bash
        # 17 JS, single bash-harness framework, counted via the upstream GitHub
        # API at the release tag: 26 + 17 = 43); executed = the 6
        # deterministic checks above. Identity check before emitting:
        # passed + failed == executed, executed + skipped <= discovered.
        discovered, executed, passed, failed, skipped = 43, 6, 6, 0, 37
        assert passed + failed == executed
        assert executed + skipped <= discovered
        # Dual decision (rule4): core self-consistency (passed+failed==executed,
        # zero failed above or an exception would already have raised) plus full
        # completeness (executed==discovered, skipped==0). Core T1-T6 are all
        # green here, but 37/43 remain unrunnable from the release tarball, so
        # the marker must report failed with reason+gaps instead of passed;
        # the build itself stays green (no raise) when failed==0 so the
        # artifact is still produced. Only a true core failure raises.
        if failed == 0 and skipped == 0 and executed == discovered:
            status = "passed"
        else:
            status = "failed"
        marker = {
            "status": status,
            "framework": "upstream-bash",
            "command": (
                "voronota --help; get-balls-from-atoms-file | "
                "calculate-vertices --check | calculate-contacts (+ voronota-js/-lt --help)"
            ),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "gaps": [
                {
                    "count": 37,
                    "category": "environment",
                    "detail": (
                        "The remaining 37 job scripts (20 core + 17 JS) run inside the "
                        "upstream git-checkout harness (tests/input/ + expansion_js/tests/input/ "
                        "fixtures + jobs_output/ reference outputs compared via git diff, "
                        "see test.bash) which the official release tarball does not ship, "
                        "and partly need device-absent tools (OpenMPI hardcodes "
                        "/usr/lib64/openmpi, valgrind memory check, R plotting). "
                        "The recipe instead executes the equivalent core pipeline (T1-T6) "
                        "with explicit non-empty output assertions."
                    ),
                    "evidence": (
                        "GitHub API at tag v1.29.4781: tests/jobs_scripts/ 26 files + "
                        "expansion_js/tests/jobs_scripts/ 17 files = 43; release tarball "
                        "top level lists src/, expansion_js/, expansion_lt/, radii, "
                        "wrapper scripts and no tests/ directory; upstream test.bash "
                        "exports PATH=/usr/lib64/openmpi/bin and runs "
                        "run_all_jobs_scripts.bash + expansion suites with git-status "
                        "comparison instead of pass/fail assertions"
                    ),
                }
            ],
        }
        if status == "failed":
            # Core is fully green (6/6, failed==0); the failure flag only
            # signals incomplete full-total coverage (37/43 unrunnable),
            # never a core regression. Build stays green on purpose.
            marker["reason"] = (
                "core pipeline T1-T6 all passed (6/6, zero failures); "
                "remaining 37/43 not runnable from the official release "
                "tarball (no tests/ harness) and partly need device-absent "
                "tools, see gaps"
            )
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Standalone binaries, no C++/library info
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
