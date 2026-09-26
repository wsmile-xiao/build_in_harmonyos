#!/usr/bin/env python3
"""Conan recipe — libsgp4 1.0 (CMake / C++11 / static library).

Packaging notes (full rationale in notes.md):

* Upstream builds two library targets — ``sgp4`` (static) and ``sgp4s``
  (shared) — but its ``install()`` rule only exports ``sgp4s``.  The CCI
  recipe for the same version fixes that with a CMake patch; this recipe
  instead stages the static archive and the headers explicitly in
  ``package()``, which keeps the source tree byte identical to upstream v1.0
  (no patch needed) and delivers the same artefact CCI produces with its
  default ``shared=False`` (``libsgp4.a``).
* ``runtest/`` is upstream's verification driver: it walks ``SGP4-VER.TLE``
  (33 TLE verification cases) and prints the TEME position/velocity of each
  case at its own tsince steps.  It is executed and validated inside
  ``build()``, so every build re-runs the upstream verification set.
  See ``_run_upstream_verification`` for the exact PASS rules.
"""
import glob
import math
import os
import subprocess

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class Libsgp4Conan(ConanFile):
    name = "libsgp4"
    version = "1.0"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}
    description = "C++11 SGP4 (Simplified perturbations model) satellite propagation library."
    license = "Apache-2.0"
    homepage = "https://github.com/dnwrnr/sgp4"
    topics = ("sgp4", "satellite", "orbit", "propagation")

    def export_sources(self):
        # No patches for this version (see notes.md); kept so the recipe
        # exposes the standard conandata patch hook.
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMAKE_POSITION_INDEPENDENT_CODE follows options.fPIC (conan default),
        # so the static archive can be linked into shared consumers.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Builds every upstream target: libsgp4.a, libsgp4s.so and the three
        # example/test drivers (sattrack, passpredict, runtest) — the drivers
        # are what the verification step below executes.
        cmake.build()
        self._run_upstream_verification()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        lib_path = self._find_static_lib()
        copy(self, os.path.basename(lib_path), src=os.path.dirname(lib_path),
             dst=os.path.join(self.package_folder, "lib"))
        # Upstream installs these into include/SGP4 (see libsgp4/CMakeLists.txt).
        copy(self, "*.h", src=os.path.join(self.source_folder, "libsgp4"),
             dst=os.path.join(self.package_folder, "include", "SGP4"))

    def package_info(self):
        self.cpp_info.libs = ["sgp4"]
        self.cpp_info.includedirs.append(os.path.join("include", "SGP4"))

    # ── helpers ────────────────────────────────────────────────────────────

    def _find_static_lib(self):
        hits = sorted(glob.glob(os.path.join(self.build_folder, "**", "libsgp4.a"),
                                recursive=True))
        if len(hits) != 1:
            raise Exception("expected exactly one libsgp4.a under %s, found %d: %s"
                            % (self.build_folder, len(hits), hits))
        return hits[0]

    # ── upstream verification driver (runtest/ + SGP4-VER.TLE) ─────────────

    @staticmethod
    def _parse_tle_cases(tle_file):
        """Return ``[(norad, start, end, inc), ...]`` in file order.

        Mirrors runtest/runtest.cc: a case is a line1 (length >= 69) followed
        by its line2; the run window is the three whitespace separated numbers
        appended after column 69 of line2, defaulting to 0/1440/120.
        """
        with open(tle_file, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        cases = []
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            if line.startswith("1 "):
                if idx + 1 >= len(lines):
                    raise Exception("malformed SGP4-VER.TLE: line1 at line %d without line2"
                                    % (idx + 1))
                line2 = lines[idx + 1]
                start, end, inc = 0.0, 1440.0, 120.0
                if len(line2) > 69:
                    tokens = line2[69:].split()
                    if len(tokens) >= 3:
                        start, end, inc = float(tokens[0]), float(tokens[1]), float(tokens[2])
                cases.append((line[2:7].strip(), start, end, inc))
                idx += 2
            else:
                idx += 1
        return cases

    @staticmethod
    def _expected_tsince(start, end, inc):
        """Replay the tsince sequence emitted by runtest's ``RunTle`` loop."""
        out = []
        current = start
        first_run = True
        running = True
        guard = 0
        while running:
            out.append(0.0 if (first_run and current != 0.0) else current)
            if (first_run and current == 0.0) or not first_run:
                if current == end:
                    running = False
                elif current + inc > end:
                    current = end
                else:
                    current += inc
            first_run = False
            guard += 1
            if guard > 1000000:
                raise Exception("tsince emulation for start=%s end=%s inc=%s did not terminate"
                                % (start, end, inc))
        return out

    def _run_upstream_verification(self):
        """Run upstream's runtest driver twice and validate its output.

        PASS rules for each of the 33 TLE verification cases:

        * the driver prints one ``<norad> xx`` header per case, in file order;
        * every row parses as exactly 7 finite doubles (tsince x y z vx vy vz);
        * row tsince values are a prefix of the case's own start/end/inc step
          sequence (step 0 is always tsince=0.0, see runtest.cc);
        * |r| is within [1e3, 1e6] km and |v| within (0, 100) km/s;
        * a case that stops before its final step must be covered one for one
          by a driver error message (SGP4-VER.TLE deliberately contains
          error-code/decay cases — upstream v1.0 yields 26 completed + 7
          error-terminated cases);
        * two consecutive runs are byte identical (determinism).
        """
        build_dir = str(self.build_folder)
        exe = os.path.join(build_dir, "runtest", "runtest")
        tle_file = os.path.join(build_dir, "SGP4-VER.TLE")
        for path in (exe, tle_file):
            if not os.path.isfile(path):
                raise Exception("upstream verification input missing: %s" % path)

        cases = self._parse_tle_cases(tle_file)
        if len(cases) != 33:
            raise Exception("SGP4-VER.TLE yielded %d cases, upstream v1.0 has 33" % len(cases))

        runs = []
        for attempt in (1, 2):
            proc = subprocess.run([exe], cwd=build_dir, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)
            if proc.returncode not in (0, 1):
                raise Exception("runtest attempt %d exited rc=%d; stderr tail:\n%s"
                                % (attempt, proc.returncode, proc.stderr[-2000:]))
            runs.append(proc)
        if runs[0].stdout != runs[1].stdout:
            raise Exception("runtest output differs between two consecutive runs "
                            "(non deterministic)")

        proc = runs[0]
        blocks = []
        for line in proc.stdout.splitlines():
            if line.endswith(" xx"):
                blocks.append([line.split()[0], []])
            elif line.strip():
                if not blocks:
                    raise Exception("runtest emitted data before any case header: %r" % line)
                blocks[-1][1].append(line.split())
        if len(blocks) != len(cases):
            raise Exception("runtest emitted %d case blocks, expected %d"
                            % (len(blocks), len(cases)))

        err_lines = [l for l in proc.stderr.splitlines() if l.strip()]
        rows_total = 0
        complete = 0
        early = 0
        for idx, (norad, start, end, inc) in enumerate(cases):
            header, rows = blocks[idx]
            if header != str(int(norad)):
                raise Exception("case %d header %r != expected norad %s" % (idx, header, norad))
            expected = self._expected_tsince(start, end, inc)
            if len(rows) > len(expected):
                raise Exception("case %d (%s): %d rows exceed the %d expected steps"
                                % (idx, header, len(rows), len(expected)))
            for ridx, fields in enumerate(rows):
                if len(fields) != 7:
                    raise Exception("case %d row %d has %d fields, expected 7: %r"
                                    % (idx, ridx, len(fields), fields))
                try:
                    values = [float(f) for f in fields]
                except ValueError:
                    raise Exception("case %d row %d is not numeric: %r" % (idx, ridx, fields))
                if not all(math.isfinite(v) for v in values):
                    raise Exception("case %d row %d has non finite values: %r"
                                    % (idx, ridx, fields))
                if abs(values[0] - expected[ridx]) > 1e-6:
                    raise Exception("case %d row %d tsince %.8f != expected %.8f"
                                    % (idx, ridx, values[0], expected[ridx]))
                pos = values[1:4]
                vel = values[4:7]
                rnorm = math.sqrt(sum(c * c for c in pos))
                vnorm = math.sqrt(sum(c * c for c in vel))
                if not 1.0e3 <= rnorm <= 1.0e6:
                    raise Exception("case %d row %d |r|=%.6f km outside [1000, 1000000]"
                                    % (idx, ridx, rnorm))
                if not 0.0 < vnorm < 100.0:
                    raise Exception("case %d row %d |v|=%.6f km/s outside (0, 100)"
                                    % (idx, ridx, vnorm))
            rows_total += len(rows)
            if len(rows) == len(expected):
                complete += 1
            else:
                early += 1

        # runtest stops a case on the first exception and prints exactly one
        # error line for it, so the two counts must agree one for one.
        if early != len(err_lines):
            raise Exception("%d case(s) ended before their final step but runtest "
                            "reported %d error line(s): %s"
                            % (early, len(err_lines), err_lines))
        # SGP4-VER.TLE composition of upstream v1.0: 26 cases run to their final
        # step, 7 stop early on the fixture's documented error-code/decay cases
        # (SL-6 R/B "decayed 2006-04-04", MINOTAUR R/B "perigee=-51km lost in 50
        # minutes", SL-14 DEB "lost in under 420 min", "check error code 4",
        # "try and check error code 2", …).  Fewer completed cases means the
        # driver lost cases — fail rather than report a smaller suite.
        if complete < 26:
            raise Exception("only %d/33 cases reached their final step "
                            "(upstream v1.0 fixture yields 26 + 7 error-terminated)"
                            % complete)

        self.output.info(
            "runtest: cases=%d completed=%d error-terminated=%d rows=%d stderr=%d "
            "rc=%d deterministic=2x-identical"
            % (len(cases), complete, early, rows_total, len(err_lines), proc.returncode))
        if blocks[0][1]:
            self.output.info("runtest first case norad=%s first row=%s last row=%s"
                             % (blocks[0][0], " ".join(blocks[0][1][0]),
                                " ".join(blocks[0][1][-1])))
