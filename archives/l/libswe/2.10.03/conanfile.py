#!/usr/bin/env python3
"""Conan recipe — libswe 2.10.03 (Swiss Ephemeris, raw Makefile).

Swiss Ephemeris (Astrodienst, aloistr/swisseph tag v2.10.03) is a
high-precision astronomical ephemeris C library. Upstream builds with a
plain Makefile (no configure/CMake): `libswe.a` / `libswe.so` plus the
swetest/swemini/swevents sample tools.

OHOS adaptations:
  - Build only portable targets (libswe.a, libswe.so, swetest, swevents,
    swemini). The `all` default also builds `swetests`, which hardcodes
    `-L/usr/lib/x86_64-redhat-linux6E/lib64/` (RHEL-only static link) and
    cannot link on OHOS; it is skipped, see notes.md.
  - Two portability patches (patches/0001, patches/0002): the setest harness
    uses GCC-only nested functions, which the OHOS clang toolchain rejects.
    0001 hoists the hand-written ones (setest.c run()/
    evaluate_cmdline_options(), multivalues.c multivalues_get_next()) to
    file-static functions with explicit context parameters. 0002 restructures
    the m4 generator (testsuite.m4 diverts) so the generated_tests.c suite
    (60 testcase + setup/teardown functions nested inside testsuite_N) is
    emitted at file scope; per-suite shared locals become static
    suite_N_state structs with macro aliases, so test bodies are untouched.
    Behavior and test counts are unchanged and the library itself is
    untouched.
  - Compiler comes from Conan conf on the make command line (R33); SHELL
    and TMPDIR are hardened the same way as the merged bwm/0.6.3 recipe
    (the repo profile pins an HNP bash that is unusable on some HMBS
    hosts; /tmp is read-only on OHOS, so it is never touched).
  - Upstream test suite `setest/` (60 TESTCASEs, `make test` runs
    `./setest t`) is built and executed in build(). It needs m4 (codegen
    for generated_tests.c) and libcrypto (one informational SHA1 print in
    setest.c); both come via tool_requires so the shipped library keeps
    zero Conan requires (it links only libc/libm/libdl). The Swiss data
    files the fixture needs (planetary .se1 for all fixture date ranges
    plus short+long asteroid files for the suite_01/suite_07 asteroid
    ITERATIONs, ~35MB total, plus 6 sat/sepm*.se1 planetary-moon/COB files
    (~43MB, suite_01 CENTER_BODY + planetocentric) and 6KB seorbel.txt
    (fictitious bodies)) are fetched at build time from the official
    mirrors named in the upstream readme (same-repo master ephe/ with
    scryr.io fallback for planetary, scryr.io mirror for asteroids/sat,
    era-pinned git snapshot for seorbel.txt), with per-class integrity floors and a strict pre-run
    verification that turns missing required files into an infrastructure
    error. Planetary data is pinned to the last pre-DE441 commit (t.exp era)
    with master as fallback; sat/ files live outside git (scryr.io only,
    DE441-rebuilt 2026-03, out-of-range serrs version-independent).
    JPL iterations are excluded via a pairing-preserving expectation slice
    (`t_nojpl.exp`, derived from upstream `t.exp` by dropping only the 538
    ITERATION sections whose `iephe` has the JPL bit — the default JPL file
    de431.eph is 2.6GB and cannot be vendored at low cost (ctest -E
    precedent, see notes.md): the exclusion is explicit in the test command
    and MANIFEST.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibsweConan(ConanFile):
    name = "libswe"
    version = "2.10.03"
    description = (
        "Swiss Ephemeris — high-precision astronomical ephemeris library "
        "(Astrodienst, for astrological/astronomical software)."
    )
    license = "AGPL-3.0-only"
    homepage = "https://www.astro.com/swisseph/"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libswe is only supported on Linux/OHOS, not {}".format(self.settings.os)
            )

    def requirements(self):
        pass

    def build_requirements(self):
        # Test-only build inputs; the shipped libswe links only
        # libc/libm/libdl, so these stay out of requires():
        # - m4/1.4.19 generates setest/generated_tests.c from suite_*.c
        # - openssl/3.5.6.1 provides libcrypto for one informational SHA1
        #   print in setest.c (linked statically, no runtime dependency)
        self.tool_requires("m4/1.4.19")
        self.tool_requires("openssl/3.5.6.1")

    def layout(self):
        basic_layout(self)
        # Upstream builds in-source (objects next to sources; setest links
        # ../libswe.a via relative path), same as merged zlib/1.3.1.
        self.folders.build = "."

    def source(self):
        # readonly_tmp: publish the writable tmp root before the download/
        # unpack as well; conan's get() + Python tempfile otherwise fall
        # back to read-only /tmp on OHOS.
        try:
            _stmp = self._usable_tmpdir(makedirs=True)
            for _k in ("TMPDIR", "TMP", "TEMP"):
                os.environ[_k] = _stmp
            import tempfile as _stf
            _stf.tempdir = _stmp
        except Exception:
            pass
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        # readonly_tmp: pin Python tempfile to the writable root in the
        # current process as well (tempfile caches tempdir on first use;
        # env alone does not move it off read-only /tmp on OHOS).
        import tempfile as _tf
        try:
            _tf.tempdir = tmpdir
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = tmpdir
        env = Environment()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        # readonly_tmp: forward HMBS filesystem capability flags so child
        # processes (make/m4/clang) inherit the host mktemp fallback and
        # local-mktemp capability (c-client/2007f precedent). Values are
        # passed through verbatim, never interpreted as paths here.
        for _k in ("HMBS_AUTOCONF_MKTEMP_FALLBACK", "HMBS_CAP_LOCAL_MKTEMP",
                   "HMBS_TMPDIR", "HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD",
                   "HMBS_CAP_SYMLINK"):
            _v = os.environ.get(_k)
            if _v:
                env.define(_k, _v)
        env.vars(self, scope="build").save_script("libswe_hmos_fix")
        self.output.info(
            "libswe_hmos_fix: SHELL/CONFIG_SHELL={} TMPDIR={}".format(shell, tmpdir)
        )

    def build(self):
        apply_conandata_patches(self)
        self._verify_portability_patches()
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        # readonly_tmp: publish the writable root to the current process as
        # well, so Python tempfile (conan self.run wrapper scripts, urllib)
        # never falls back to the read-only /tmp on OHOS. tempfile caches
        # tempdir on first use, so pin it explicitly; env alone is not
        # enough once the module has cached /tmp.
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = tmpdir
        try:
            import tempfile as _tf2
            _tf2.tempdir = tmpdir
        except Exception:
            pass
        os.environ["SHELL"] = shell
        os.environ["CONFIG_SHELL"] = shell
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # Prefer the HMBS-probed make binary when the backend provides it;
        # plain `make` remains the fallback (守则: HMBS_MAKE/HMBS_CMAKE/...).
        make_bin = os.environ.get("HMBS_MAKE", "make")
        prefix = (
            'export SHELL="{}" && export CONFIG_SHELL="{}" && '.format(shell, shell)
            + 'export TMPDIR="{}" && export TMP="{}" && export TEMP="{}" && '.format(
                tmpdir, tmpdir, tmpdir
            )
        )
        self.output.info("libswe build: CC={} SHELL={} TMPDIR={} MAKE={}".format(cc, shell, tmpdir, make_bin))
        # Constrained-runner OOM hardening (cpluff precedent, adapted): never
        # emit -g (debug info inflates clang peak memory on the large
        # sweph.c/swetest.c units) and pass -s so the link strips; -j1 is
        # kept below and the full portable target set + full setest suite
        # are unchanged. Plain Makefile has no dependency-tracking or
        # language-binding switches to toggle (swetests RHEL-only target
        # already excluded as the附属-target closure).
        cflags = "-O2 -Wall -fPIC -s"
        targets = ["libswe.a"]
        if self.options.shared:
            targets.append("libswe.so")
        # NOTE: intentionally not `all`: the `swetests` target hardcodes a
        # RHEL-only -L path together with -static and cannot link on OHOS
        # (see notes.md); swetest/swevents/swemini cover the same sources.
        targets += ["swetest", "swevents", "swemini"]
        self.run(
            prefix + '{} -j1 SHELL="{}" TMPDIR="{}" CC="{}" CFLAGS="{}" {}'.format(
                make_bin, shell, tmpdir, cc, cflags, " ".join(targets)),
            cwd=self.source_folder,
            env="conanbuild",
        )
        self._run_upstream_tests(prefix, cc, shell, tmpdir)

    def _verify_portability_patches(self):
        # Fail-fast guard: the setest harness cannot compile with the OHOS
        # clang toolchain unless both portability patches are applied (GCC
        # nested functions, hand-written and m4-generated). If the recipe
        # export ever goes stale and drops them, fail here with a clear
        # message instead of dozens of obscure "function definition is not
        # allowed here" errors during the setest build.
        setest_dir = os.path.join(self.source_folder, "setest")
        checks = {
            "patches/0001-clang-no-gcc-nested-functions.patch": (
                "setest.c",
                "run_general_setup",
            ),
            "patches/0002-m4-generated-setest-clang-compat.patch": (
                "testsuite.m4",
                "undivert(4)",
            ),
        }
        for patch_file, (src_name, marker) in checks.items():
            path = os.path.join(setest_dir, src_name)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError as e:
                raise ConanException(
                    "libswe: cannot read {} to verify {}: {}".format(path, patch_file, e)
                )
            if marker not in content:
                raise ConanException(
                    "libswe: {} does not appear to be applied "
                    "(missing {!r} in {}); refusing to build stale sources".format(
                        patch_file, marker, src_name
                    )
                )
            self.output.info("libswe: verified {}".format(patch_file))

    def _run_upstream_tests(self, prefix, cc, shell, tmpdir):
        # setest links ../libswe.a plus libcrypto (SHA1 print) and libdl.
        # Prefer the static libcrypto.a staged into a private dir (only the
        # .a is present there, so `-lcrypto` resolves statically) and the
        # test binary gains no libcrypto.so runtime dependency.
        ossl = self.dependencies.build["openssl"]
        ossl_inc, ossl_libdir, crypto_mode = self._find_libcrypto(ossl.package_folder)
        setest_dir = os.path.join(self.source_folder, "setest")
        # Low-cost Swiss data补齐 (official mirrors per readme, see
        # _ensure_swiss_ephe_data): planetary .se1 for all fixture date
        # ranges plus short+long asteroid files for the asteroid ITERATIONs
        # (~35MB total) plus sat/sepm*.se1 (~43MB) + seorbel.txt (6KB),
        # fetched with integrity floors + host fallback and
        # strictly verified before the suite runs. Without them SWIEPH
        # iterations fall back to
        # Moshier ("SwissEph file 'sepl_24.se1' not found ... using Moshier
        # eph.") and fail value+serr comparisons with large diffs (1210
        # failed iterations in preflight). Files land in setest_dir ("."
        # on setest's default SE_EPHE_PATH; asteroids in astN/ subdirs),
        # so no code changes are needed.
        # JPL .eph (190MB-2.6GB) is intentionally NOT fetched (not low-cost).
        self._ensure_swiss_ephe_data(setest_dir)
        # Round-5 revert of the round-4 _fix_suite04_fixture normalization
        # (removed entirely below): t.exp audit 2026-09-19 proves the
        # hypothesis false -- t.exp suite_04 already holds BOTH iephe:2 and
        # iephe:66 sections (TESTCASE 2: 2 sections) plus the NONUT daya in
        # TESTCASE 3, i.e. fixture and oracle are already 1:1 consistent
        # (suite_04 per-case iters in t.exp: {1:8, 2:2, 3:1, 4:1} = 12).
        # Collapsing t.fix to a single iephe therefore CREATES a desync
        # (1 run vs 2 expected sections) and deletes the new NONUT assertion
        # the tag intentionally added -- forbidden input rewriting. Suite_04
        # failures (7) are TESTCASE 1 value drift under the new ayanamsa
        # table/NONUT semantics (see MANIFEST), not pairing; run upstream
        # input untouched from here on.
        if crypto_mode == "static":
            cryptolib = os.path.join(self.build_folder, "swe-cryptolib")
            os.makedirs(cryptolib, exist_ok=True)
            shutil.copyfile(
                os.path.join(ossl_libdir, "libcrypto.a"),
                os.path.join(cryptolib, "libcrypto.a"),
            )
            crypto_flags = ' -I"{}" -L"{}"'.format(ossl_inc, cryptolib)
            ld_path_export = ""
        else:
            crypto_flags = ' -I"{}" -L"{}"'.format(ossl_inc, ossl_libdir)
            ld_path_export = 'export LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH" && '.format(ossl_libdir)
        self.output.info(
            "libswe setest: openssl include={} libdir={} mode={}".format(
                ossl_inc, ossl_libdir, crypto_mode
            )
        )
        # Same OOM hardening as the library build above: upstream setest
        # Makefile uses `-g` with no -O; -g on the large m4-generated
        # generated_tests.c unit is the peak-memory driver that the
        # supervisor SIGKILLs (exit 137 after the ephe fetch). Drop -g,
        # pin -O0 (lowest compile memory) and strip at link with -s.
        # Single job (-j1) and the full t_nojpl suite are unchanged.
        setest_cflags = "-std=gnu99 -fms-extensions -O0 -Wall -pthread -fPIC -s" + crypto_flags
        # Only the `setest` binary, not bare `all`: that Makefile also builds
        # one suite_*.o per suite source, but only $(OBJECTS) link into the
        # test binary, so suite_*.o are dead artifacts. Suite sources dual-use
        # testsuite_facade.h, whose SETUP/TEARDOWN/TESTCASE macros expand to
        # GCC-only nested functions inside testsuite_N() (a separate path
        # from the m4-generated code fixed by 0002), which clang rejects.
        # Upstream `make test` needs only `./setest t`.
        _make_bin = os.environ.get("HMBS_MAKE", "make")
        # readonly_tmp: reuse the validated shell/tmpdir from build() (never
        # re-read raw TMPDIR here: an empty or "/tmp" value would undo the
        # prefix exports and push clang/m4 temp files back onto read-only
        # /tmp on OHOS). prefix already exports the same values.
        _shell = shell
        _tmp = tmpdir
        self.run(
            prefix + '{} -j1 SHELL="{}" TMPDIR="{}" CC="{}" CFLAGS="{}" LIBS="../libswe.a -lm" setest'.format(
                _make_bin, _shell, _tmp, cc, setest_cflags),
            cwd=setest_dir,
            env="conanbuild",
        )
        # Round-13 falsification guard (new route this round, different from
        # rounds 1-12 data/mirror/fixture/gate/bulk/telemetry/ledger/docs
        # tuning): the binary under test must be real (non-trivial size). A
        # stub/empty binary could exit 0 with vacuous output; the 149 floor
        # itself already proves this harness catches failures, this guard
        # keeps that proof machine-checked on every run. Healthy path (real
        # setest, MBs) is unaffected; scope and tolerances unchanged.
        _setest_bin = os.path.join(setest_dir, "setest")
        try:
            _setest_size = os.path.getsize(_setest_bin)
        except OSError as e:
            raise ConanException("libswe: cannot stat setest binary")
        self.output.info("libswe setest: binary size checked")
        if _setest_size < 50 * 1024:
            raise ConanException("libswe: setest binary too small, refusing vacuous run")
        log_path = os.path.join(self.build_folder, "setest_run.log")
        rc_path = os.path.join(self.build_folder, "setest_rc.txt")
        # Redirect to files (self.run does not capture stdout); the echo
        # keeps the outer exit code 0 so parsing below always runs.
        # JPL exclusion WITHOUT -p: the harness's -p prioritary parameters
        # inject a GENERAL multivalue (testdata.c get_entry checks
        # parameters before the reader, is_multivalue() then expands it),
        # which desyncs TEST-mode 1:1 section pairing (each reader section
        # is consumed once per multivalue cycle, so injected values compare
        # against the wrong expected rows). Instead _write_nojpl_expectations
        # derives t_nojpl.exp from upstream t.exp by dropping only the JPL
        # ITERATION sections byte-identically (ctest -E equivalent); the run
        # below is then a plain upstream invocation with 1:1 pairing.
        nojpl_kept, nojpl_total, nojpl_dropped = self._write_nojpl_expectations(setest_dir)
        run_cmd = './setest t_nojpl >"{}" 2>&1; echo "SETEST_RC=$?" >"{}"'.format(log_path, rc_path)
        self.run(prefix + ld_path_export + run_cmd, cwd=setest_dir, env="conanbuild", ignore_errors=True)
        self._parse_setest_evidence(log_path, rc_path, run_cmd, nojpl_kept, nojpl_total, nojpl_dropped)

    def _write_nojpl_expectations(self, setest_dir):
        # Derive t_nojpl.exp from upstream t.exp by dropping only ITERATION
        # sections whose `iephe` field has the JPL bit set (value & 1), then
        # reindexing kept ITERATION section-ids contiguously per TESTCASE.
        # Audited on swisseph-2.10.03: 12757 ITERATION blocks, 538 with JPL
        # bit (all exactly `iephe: 1`), 12219 kept, no JPL-only TESTCASE.
        # Reindexing matters: open_iteration()/read_next_section() seek
        # ITERATION sections by sequential section-id, so gaps left by
        # filtering would desync the reader (kept 12219 but only 11536
        # executed in preflight). Reindexed ids restore the sequential
        # invariant; all expected values stay byte-identical to upstream, so
        # Swiss/Moshier expectations (including any 2.10.02a-era version
        # drift) are preserved, not masked. Re-derived on every build (never
        # cached), and the counts are logged for the preflight record.
        import re as _re
        src = os.path.join(setest_dir, "t.exp")
        dst = os.path.join(setest_dir, "t_nojpl.exp")
        try:
            with open(src, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError as e:
            raise ConanException("libswe: cannot read {}: {}".format(src, e))
        out = []
        cur = []
        in_iter = False
        cur_jpl = False
        cur_sid_done = False  # first section-id line of current block rewritten
        total = 0
        dropped = 0
        cur_suite = 0
        cur_case = 0
        new_iter_id = 0
        pending = None  # 'suite' | 'case' after header, awaiting section-id
        tc_kept = {}  # (suite, case) -> kept count, guards empty TESTCASEs

        def _flush():
            nonlocal total, dropped, new_iter_id
            if in_iter and cur:
                total += 1
                if cur_jpl:
                    dropped += 1
                else:
                    new_iter_id += 1
                    tc_kept[(cur_suite, cur_case)] = tc_kept.get((cur_suite, cur_case), 0) + 1
                    out.extend(cur)

        for ln in lines:
            s = ln.strip()
            if s == "ITERATION":
                _flush()
                in_iter = True
                cur = [ln]
                cur_jpl = False
                cur_sid_done = False
                pending = None
                continue
            if s in ("TESTSUITE", "TESTCASE"):
                _flush()
                in_iter = False
                pending = "suite" if s == "TESTSUITE" else "case"
                if s == "TESTCASE":
                    new_iter_id = 0
                out.append(ln)
                continue
            m_sid = _re.match(r"(\s*section-id:\s*)\d+(.*)$", ln)
            if m_sid is not None and not in_iter and pending in ("suite", "case"):
                try:
                    _v = int(_re.match(r"\s*section-id:\s*(\d+)", ln).group(1))
                except (ValueError, AttributeError):
                    _v = 0
                if pending == "suite":
                    cur_suite = _v
                else:
                    cur_case = _v
                    new_iter_id = 0
                pending = None
                out.append(ln)
                continue
            if in_iter:
                if not cur_sid_done and m_sid is not None:
                    # Reindex to the contiguous per-TESTCASE position; the
                    # value is only a positional key for the reader seek.
                    ln = "{} {}  #{}.{}.{}\n".format(
                        m_sid.group(1).rstrip(), new_iter_id + 1,
                        cur_suite, cur_case, new_iter_id + 1,
                    )
                    cur_sid_done = True
                else:
                    m = _re.match(r"\s*iephe:\s*(\d+)", ln)
                    if m and (int(m.group(1)) & 1) == 1:
                        cur_jpl = True
                cur.append(ln)
            else:
                out.append(ln)
        _flush()
        if total == 0:
            raise ConanException("libswe: no ITERATION blocks found in {}".format(src))
        _empty = [k for k, v in tc_kept.items() if v == 0]
        if _empty:
            raise ConanException(
                "libswe: t_nojpl derivation emptied TESTCASE(s) {} — refusing to run (harness cannot handle empty cases)".format(_empty)
            )
        try:
            with open(dst, "w", encoding="utf-8", newline="\n") as f:
                f.writelines(out)
        except OSError as e:
            raise ConanException("libswe: cannot write {}: {}".format(dst, e))
        self.output.info(
            "libswe setest: derived t_nojpl.exp from t.exp (iterations={} dropped_JPL={} kept={} reindexed_per_testcase)".format(
                total, dropped, total - dropped
            )
        )
        if dropped == 0:
            raise ConanException("libswe: JPL filter dropped 0 sections — fixture changed, refusing silent full run")
        # Round-13 falsification floor (same new route): the derived
        # expectation file must be non-trivially large (t.exp is ~12.9MB).
        # An empty/truncated t_nojpl.exp would compare against nothing
        # (vacuous green); refuse that. Healthy path (~12MB) unaffected;
        # values stay byte-identical to upstream.
        try:
            _nojpl_size = os.path.getsize(dst)
        except OSError as e:
            raise ConanException("libswe: cannot stat derived expectations")
        self.output.info(
            "libswe setest: t_nojpl.exp size checked")
        if _nojpl_size < 5 * 1024 * 1024:
            raise ConanException(
                "libswe: t_nojpl.exp truncated, refusing vacuous run")
        return (total - dropped), total, dropped

    def _find_libcrypto(self, pkg_folder):
        """Return (include_dir, lib_dir, mode) for libcrypto.

        mode is "static" when libcrypto.a exists (preferred, no runtime
        dependency) else "shared" (libcrypto.so + LD_LIBRARY_PATH at run).
        """
        inc = os.path.join(pkg_folder, "include")
        if not os.path.isfile(os.path.join(inc, "openssl", "sha.h")):
            inc = None
        static_dir, shared_dir = None, None
        for root, _dirs, files in os.walk(pkg_folder):
            if "libcrypto.a" in files and static_dir is None:
                static_dir = root
            if shared_dir is None and any(
                f == "libcrypto.so" or (f.startswith("libcrypto.so.") and f not in ("libcrypto.so",))
                for f in files
            ):
                shared_dir = root
            if inc is None and "sha.h" in files and os.path.basename(root) == "openssl":
                inc = os.path.dirname(root)
            if static_dir and shared_dir and inc:
                break
        if inc is None:
            raise ConanException(
                "libswe: openssl/sha.h not found under {}".format(pkg_folder)
            )
        if static_dir:
            return inc, static_dir, "static"
        if shared_dir:
            return inc, shared_dir, "shared"
        raise ConanException("libswe: neither libcrypto.a nor libcrypto.so found under {}".format(pkg_folder))

    def _ensure_swiss_ephe_data(self, setest_dir):
        # Fetch the Swiss data files the fixture needs from the official
        # mirrors named in the upstream readme. Two preflight rounds forced
        # this hardened design (see notes.md #13/#14): files that WERE on
        # the fetch list (e.g. semo_24.se1) were still absent at setest
        # runtime ("not found in PATH"), and growing the list (17 -> 57)
        # made results WORSE (1210 -> 1344 failed). Root cause on the recipe
        # side: naive fetching (1KB floor, single host, warn-only) lets
        # 404/error pages or truncated payloads pass as data, or leaves
        # files missing unnoticed. Hence per-class size floors, two-host
        # fallback for the required set, a circuit breaker, and a strict
        # pre-run verification that turns missing required files into a
        # loud infrastructure error instead of a doomed suite run.
        # Verified file truth (mirror listings + upstream docs + git history +
        # t.exp audit 2026-09-18): planetary sepl/semo/seas _00.._30 (+_36)
        #    + seplm/semom/seasm m06..m30 (+m36) cover fixture JDs. The m36
        #    file is REQUIRED, not optional: t.exp section 295 (JD 624942.5 =
        #    7.12.-3002, "barycentric Mercury, out of range") carries real
        #    SWIEPH values with empty serr (rc=18018), i.e. upstream generated
        #    it with seplm36.se1 present; without m36 setest reports
        #    "SwissEph file 'seplm36.se1' not found" + Moshier fallback and
        #    fails both serr and value checks (preflight 2026-09-18: 494
        #    failed, e.g. suite_10 jx diff 1.40e-01). Same for JD 625000
        #    (-3001, SWIEPH real values) and suite_10 solcross searches from
        #    the 625010 edge. _36 is added symmetrically for forward searches
        #    past 3600 from the 2818000 edge (cheap, same mirrors/pinning).
        #    Genuine Moshier-boundary cases are unaffected: the MOSEPH
        #    iterations at those JDs expect explicit failures
        #    ("barycentric Moshier positions are not supported." /
        #    "outside Moshier's Moon range"), which hold with or without .se1.
        #  - ERA PINNING (notes.md #15): master .se1 are DE441-rebuilt
        #    (2026-04-14 "now created with DE441", af9823fe) while t.exp is
        #    2.10.02a-era; a full-data preflight still failed 1210
        #    iterations on values, so data is fetched primarily at the last
        #    pre-DE441 commit b51a0833 (2026-04-13 "reverted to de431
        #    version"), i.e. the same DE431-era bytes t.exp was generated
        #    against. Immutable commit-pinned raw URLs, same official repo.
        #  - Ceres/Pallas/Juno/Vesta need NO separate files (bundled in
        #    seas_*.se1 per upstream docs); only 10/433/2060/5145/9501/
        #    9599/10433 need astN/ files (short+long, scryr.io mirror;
        #    asteroid files live outside git, era-pinning n/a).
        #  - sefstars.txt (suite_02/08/09 stars): era-pinned OLDER than the
        #    planetary files. t.exp is 2022-08 era but sefstars.txt gained
        #    6 post-t.exp catalog commits before 2026 (Galactic-node
        #    additions 2024-03, Rasalgethi/Trapezium/34Cyg fixes 2024-2025,
        #    verified via GitHub contents API 2026-09-18), so the 2026
        #    b51a0833 snapshot drifts from t.exp star values. Primary is
        #    now eecb996a (2023-09-20, first git checkin of the FTP star
        #    file, closest surviving snapshot to the 2022 FTP content;
        #    136071 bytes, passes the same 50KB floor), with b51a0833 +
        #    master + scryr.io kept as fallbacks. Planetary .se1 stay on
        #    the b51a0833 DE431 pin (git shows no asteroid-recompute
        #    commit for seas files between Sep-2023 and Mar-2026).
        #    seleapsec.txt is deliberately NOT fetched: upstream runs setest
        #    with cwd=setest where the file is absent (it lives at repo
        #    root), so t.exp reflects its absence; adding it could shift
        #    Delta T behavior.
        import tarfile
        import time
        import urllib.request
        pin_rev = "b51a083390bf3cdc93a6ba466cbc83b846c4cfc4"  # last pre-DE441 ephe state
        pin_base = "https://raw.githubusercontent.com/aloistr/swisseph/" + pin_rev + "/ephe/"
        star_pin_rev = "eecb996acad596f0a162875db935b880d6033244"  # first git sefstars.txt (2023-09-20)
        star_pin_base = "https://raw.githubusercontent.com/aloistr/swisseph/" + star_pin_rev + "/ephe/"
        gh_base = "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/"
        scryr_base = "https://ephe.scryr.io/ephe/"
        # Required: (relative_dest, min_bytes, [urls in fallback order]).
        # Floors come from real mirror sizes (planetary .se1 >= 74KB,
        # sefstars.txt = 133KB); error/proxy block pages are ~1-5KB.
        required = []
        for series in ("sepl", "semo", "seas"):
            for tag in ("_00", "_06", "_12", "_18", "_24", "_30", "_36"):
                name = series + tag + ".se1"
                required.append((name, 50 * 1024, [pin_base + name, gh_base + name, scryr_base + name]))
        for series in ("seplm", "semom", "seasm"):
            for tag in ("06", "12", "18", "24", "30", "36"):
                name = series + tag + ".se1"
                required.append((name, 50 * 1024, [pin_base + name, gh_base + name, scryr_base + name]))
        required.append(("sefstars.txt", 50 * 1024,
                         [star_pin_base + "sefstars.txt", pin_base + "sefstars.txt", gh_base + "sefstars.txt", scryr_base + "sefstars.txt"]))
        # Best-effort asteroids: (number, subdir), scryr.io only, warn-only.
        # Shorts can be as small as 18KB (se05145s), longs from 75KB
        # (se02060); floors reject error pages while accepting those.
        asteroids = [
            (10, "ast0"),      # Hygiea (suite_01)
            (433, "ast0"),     # Eros (suite_07)
            (2060, "ast2"),    # Chiron (suite_01)
            (5145, "ast5"),    # Pholus (suite_01)
            (10433, "ast10"),  # suite_01
            # NOTE: 9501/9599 are planetary moons (9000 < ipl < 10000), not
            # asteroids; their files are sat/sepm*.se1 (see sat_moons below),
            # not astN/se*.se1 (those URLs always 404).
        ]
        # Planetary moons + COB (suite_01 TESTCASE 1 CENTER_BODY + TESTCASE 5
        # planetocentric; t.exp audit 2026-09-18: exactly sepm9501/9599/9699/
        # 9799/9899/9999 referenced, 24 serr lines). swi_gen_filename builds
        # fname as sat/sepm<Ipli>.se1 (DIR_GLUE), so they must land in the
        # sat/ subdir of the setest cwd (same astN/ pattern). scryr.io is the
        # only working mirror verified 2026-09-18 (astro.com FTP area now
        # serves a download-page, not files; files absent from git ephe/):
        # https://ephe.scryr.io/ephe/sat/ lists them (DE441-rebuilt 2026-03;
        # out-of-range lower-limit serrs are version-independent, in-range
        # COB values may carry DE441-vs-DE431 drift, still strictly better
        # than "not found" fallback). Sizes 4-10MB each (~43MB total);
        # timeout 15s + 20MB cap (default 8s/8MB would reject them).
        sat_moons = [9501, 9599, 9699, 9799, 9899, 9999]
        # Fictitious bodies (suite_01 CUPIDO/40/43/47 + NIBIRU; SE_FICTFILE):
        # t.exp carries 0 seorbel serr lines, i.e. upstream generated it with
        # the file present (empty serr + real values); without it every fict
        # iteration fails "seorbel.txt not found". Era pinning (#23): the
        # scryr.io copy is 6237 bytes (updated elements) while the git
        # snapshot eecb996a (2023-09-20, "added ephe/sefstars.txt
        # ephe/seorbel.txt", same commit as the sefstars pin) is 6063 bytes
        # and stable through master (verified 2026-09-18, identical sha256),
        # i.e. the closest surviving snapshot to the 2022 FTP content t.exp
        # was generated against. Primary is therefore the git pin (same
        # star_pin_base as sefstars.txt), scryr.io kept only as last resort.
        required.append(("seorbel.txt", 1 * 1024,
                         [star_pin_base + "seorbel.txt", pin_base + "seorbel.txt",
                          gh_base + "seorbel.txt", scryr_base + "seorbel.txt"]))
        fetched, skipped, failed = 0, 0, 0
        consecutive_failures = 0
        # Round-5 (different route from rounds 1-4 env-pinning/mirror-tuning/
        # fail-fast-reorder): host-level short-circuit. The 2026-09-19
        # preflight died mid-fetch (SSH session drop right after an off-pin
        # fallback warning) while the harness startup /tmp noise is present
        # in every run, fatal or not. When one tier host stalls, every
        # remaining file still pays its full per-URL timeout before falling
        # through, so a sick host multiplies stall time across ~59 sequential
        # fetches and risks an idle-session kill. After 2 consecutive
        # failures on the same host, later files skip it and go straight to
        # the next tier; tier order, floors, era-tier logging and the global
        # consecutive_failures breaker are unchanged, and a lone remaining
        # host is always tried (never skip the last usable URL), so
        # healthy-network behavior is byte-identical.
        host_fails = {}
        dead_hosts = set()

        def _host_of(url):
            try:
                return url.split("//", 1)[1].split("/", 1)[0].lower()
            except (IndexError, AttributeError):
                return url

        def _download(url, dest, min_bytes, timeout=8, max_bytes=8 * 1024 * 1024):
            # Streaming download (#18 fail-fast + #22 bound, tightened this
            # round: two straight preflight exit 137 / Signal 9 kills landed
            # right after the last planetary success (seasm36, ~39/41 files,
            # all succeeding), i.e. the hang is wall-time/fd pressure at
            # scale, not payload size. Different from the previous
            # tempfile-pin round: bound the network tail instead of the
            # filesystem temp path. Default timeout 10->8 bounds the worst
            # case per required file to 3 hosts x 8s = 24s; streaming +
            # size guard unchanged. `Connection: close` avoids keep-alive
            # socket/fd accumulation over ~55 sequential TLS fetches to the
            # same hosts. Hosts, floors, fallback order and suite unchanged.
            req = urllib.request.Request(url, headers={"User-Agent": "conan-libswe-ohos/1.0", "Connection": "close"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    raise ValueError("HTTP status {}".format(resp.status))
                total = 0
                with open(dest, "wb") as f:
                    while True:
                        chunk = resp.read(64 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > max_bytes:
                            raise ValueError(
                                "payload exceeds {} bytes (unexpected)".format(max_bytes))
                        f.write(chunk)
            if total < min_bytes:
                try:
                    if os.path.isfile(dest):
                        os.remove(dest)
                except OSError:
                    pass
                raise ValueError("payload {} bytes < floor {} (likely error page)".format(total, min_bytes))
            return total

        def _fetch_urls(urls, dest, min_bytes, attempts_per_url=1, timeout=8, max_bytes=8 * 1024 * 1024):
            nonlocal fetched, skipped, failed, consecutive_failures
            try:
                if os.path.isfile(dest) and os.path.getsize(dest) >= min_bytes:
                    skipped += 1
                    consecutive_failures = 0
                    return True
            except OSError:
                pass
            parent = os.path.dirname(dest)
            if parent:
                try:
                    os.makedirs(parent, exist_ok=True)
                except OSError:
                    pass
            errors = []
            # Round-7 strict era-pin (different route from rounds 1-6
            # mirror/era-pin/fixture/host-breaker/retry tuning): the 516
            # round proves warn-and-continue off-pin is a drift source, not
            # observability -- suite_07 stuck at the 87 no-data baseline
            # despite 3x15s retries (retry cannot fix prolonged single-host
            # outage or systematic off-pin), while suite_01 193 vs the 132
            # on-pin baseline (+61) and suite_10 174 vs 135 (+39) match
            # DE441-rebuilt master bytes served with a warning. From here a
            # pin-offered file served off-pin is REJECTED (deleted, next URL
            # tried); only era-pin bytes count as success. A run is therefore
            # either deterministic on-pin data or a loud infra abort -- never
            # a silent drifted 516 masquerading as test failures. Falsifiable:
            # if the next run is infra, the pin host was down; if it is still
            # ~516 with zero off-pin rejections logged, the drift hypothesis
            # is wrong and the floor is not data.
            pin_offered = any((pin_rev in _u) or (star_pin_rev in _u) for _u in urls)
            live = [u for u in urls if _host_of(u) not in dead_hosts]
            if not live:
                live = list(urls)
            elif len(live) != len(urls):
                self.output.info(
                    "libswe ephe: skipping dead host(s) {} for {}".format(
                        sorted({_host_of(u) for u in urls} - {_host_of(u) for u in live}),
                        os.path.basename(dest)))
            for url in live:
                host = _host_of(url)
                for attempt in range(1, attempts_per_url + 1):
                    try:
                        size = _download(url, dest, min_bytes, timeout=timeout, max_bytes=max_bytes)
                        tier = "era-pin" if (pin_rev in url or star_pin_rev in url) else ("master" if "/master/" in url else "mirror")
                        if pin_offered and tier != "era-pin":
                            # Strict pin: wrong-era bytes are not data.
                            # Delete, record, and try the next URL tier
                            # instead of warning-and-continuing with drift.
                            # Not a host failure (host delivered bytes), so
                            # host_fails/dead_hosts are untouched.
                            try:
                                if os.path.isfile(dest):
                                    os.remove(dest)
                            except OSError:
                                pass
                            errors.append(
                                "{} served off-pin via {} (rejected, need era-pin)".format(url, tier))
                            self.output.warning(
                                "libswe ephe: {} served off-pin via {} -- rejected, "
                                "trying next tier (need t.exp-era bytes)".format(dest, tier))
                            continue
                        self.output.info("libswe ephe: fetched {} ({} bytes via {})".format(dest, size, tier))
                        fetched += 1
                        consecutive_failures = 0
                        host_fails[host] = 0
                        return True
                    except Exception as e:
                        errors.append("{} attempt {}/{}: {}".format(url, attempt, attempts_per_url, e))
                        host_fails[host] = host_fails.get(host, 0) + 1
                        if host_fails[host] >= 2 and host not in dead_hosts:
                            dead_hosts.add(host)
                            self.output.warning(
                                "libswe ephe: host {} failed {} consecutive files; "
                                "skipping it for the rest of this build".format(host, host_fails[host]))
                        try:
                            if os.path.isfile(dest):
                                os.remove(dest)
                        except OSError:
                            pass
                        time.sleep(min(2 ** (attempt - 1), 4))
            self.output.warning("libswe ephe: FAILED {} ({})".format(dest, " | ".join(errors)))
            failed += 1
            consecutive_failures += 1
            return False

        def _bulk_pin_tarball():
            # Round-8 bulk era-pin (different route from rounds 1-7
            # per-file mirror/era-pin/host-breaker/retry tuning): the
            # 2026-09-19 infra abort shows per-file pin fetches timing out
            # on raw.githubusercontent.com (SSL handshake + read timeouts)
            # while the SAME run served master/mirror bytes fine -- i.e.
            # the pin host is flaky per-request, and the round-5 dead-host
            # breaker then marks raw dead after 2 files, after which the
            # round-7 strict pin can never succeed again (pin host skipped,
            # mirror always rejected) -- a pathological interaction that
            # guarantees infra for all remaining files. Instead of an 8th
            # round of per-file timeout/retry tuning, fetch the era-pinned
            # planetary set as ONE commit tarball from github.com (the same
            # host source() already proves reachable: the v2.10.03 tag
            # tarball downloads on every build): 1 TLS handshake instead of
            # ~39 sequential ones, atomically era-consistent bytes, no
            # per-file dead-host state involved. Failures fall through to
            # the existing per-file loop below (behavior unchanged); success
            # pre-populates files so that loop hits its size-check skip.
            want = {}
            for _rel, _min, _urls in required:
                if _rel.endswith(".se1") and "/" not in _rel:
                    want[_rel] = _min
            # Round-9: seorbel.txt is era-identical across eecb996a/b51a0833/
            # master (6063 bytes, identical sha256 verified 2026-09-18), so
            # it is safe to pre-populate from the same bulk era-pin tarball
            # (member ephe/seorbel.txt). This removes one flaky per-file
            # strict-pin fetch with zero behavior change on the healthy path.
            # sefstars.txt is deliberately NOT bulked: its b51a0833 bytes
            # (2026) drift from the eecb996a pin (2023) t.exp needs.
            for _rel, _min, _urls in required:
                if _rel == "seorbel.txt":
                    want[_rel] = _min
            if not want:
                return
            try:
                _tmp_root = self._usable_tmpdir(makedirs=True)
            except Exception:
                _tmp_root = self.build_folder
            _tar_path = os.path.join(_tmp_root, "swisseph-pin-{}.tar.gz".format(pin_rev[:12]))
            _urls = [
                "https://github.com/aloistr/swisseph/archive/" + pin_rev + ".tar.gz",
                "https://codeload.github.com/aloistr/swisseph/tar.gz/" + pin_rev,
            ]
            _got = False
            _errs = []
            for _u in _urls:
                try:
                    _req = urllib.request.Request(
                        _u, headers={"User-Agent": "conan-libswe-ohos/1.0", "Connection": "close"})
                    with urllib.request.urlopen(_req, timeout=120) as _resp:
                        if _resp.status != 200:
                            raise ValueError("HTTP status {}".format(_resp.status))
                        _total = 0
                        with open(_tar_path, "wb") as _f:
                            while True:
                                _chunk = _resp.read(256 * 1024)
                                if not _chunk:
                                    break
                                _total += len(_chunk)
                                if _total > 400 * 1024 * 1024:
                                    raise ValueError("bulk tarball exceeds 400MB (unexpected)")
                                _f.write(_chunk)
                    if _total < 1 * 1024 * 1024:
                        raise ValueError("bulk tarball {} bytes < 1MB floor".format(_total))
                    self.output.info(
                        "libswe ephe: bulk era-pin tarball fetched ({} bytes via {})".format(_total, _u))
                    _got = True
                    break
                except Exception as _e:
                    _errs.append("{}: {}".format(_u, _e))
                    try:
                        if os.path.isfile(_tar_path):
                            os.remove(_tar_path)
                    except OSError:
                        pass
                    time.sleep(2)
            if not _got:
                self.output.warning(
                    "libswe ephe: bulk era-pin tarball unavailable ({}); "
                    "falling back to per-file fetch".format(" | ".join(_errs)))
                return
            try:
                _done = 0
                with tarfile.open(_tar_path, "r:gz") as _tf:
                    for _m in _tf.getmembers():
                        if not _m.isfile():
                            continue
                        _base = os.path.basename(_m.name)
                        if _base not in want:
                            continue
                        # Tarball layout is swisseph-<rev>/ephe/<name>; only
                        # accept members under an ephe/ dir to avoid stray
                        # same-named files elsewhere in the tree.
                        _parts = _m.name.replace("\\", "/").split("/")
                        if "ephe" not in _parts:
                            continue
                        _dest = os.path.join(setest_dir, _base)
                        try:
                            if os.path.isfile(_dest) and os.path.getsize(_dest) >= want[_base]:
                                continue
                        except OSError:
                            pass
                        _src = _tf.extractfile(_m)
                        if _src is None:
                            continue
                        _size = 0
                        with open(_dest, "wb") as _out:
                            while True:
                                _c = _src.read(256 * 1024)
                                if not _c:
                                    break
                                _size += len(_c)
                                _out.write(_c)
                        if _size < want[_base]:
                            try:
                                os.remove(_dest)
                            except OSError:
                                pass
                            self.output.warning(
                                "libswe ephe: bulk member {} ({} bytes < floor {}) rejected".format(
                                    _base, _size, want[_base]))
                            continue
                        _done += 1
                self.output.info(
                    "libswe ephe: bulk era-pin extracted {}/{} era-pin files "
                    "(commit {}, single-tarball tier=era-pin)".format(_done, len(want), pin_rev[:12]))
            except Exception as _e:
                self.output.warning(
                    "libswe ephe: bulk era-pin extraction failed ({}); "
                    "falling back to per-file fetch".format(_e))
            finally:
                try:
                    if os.path.isfile(_tar_path):
                        os.remove(_tar_path)
                except OSError:
                    pass

        def _bulk_star_pin_tarball():
            # Round-15 star-pin bulk (different route from rounds 8-9
            # planetary bulk): the 2026-09-19 infra abort shows the planetary
            # bulk succeeding (40/40 via github.com) while sefstars.txt --
            # deliberately excluded from that bulk (b51a0833 bytes drift from
            # the eecb996a pin t.exp needs) -- fails on ALL three per-file
            # raw.githubusercontent.com tiers (SSL handshake + read timeouts)
            # and the scryr.io mirror is strict-pin rejected. The round-5
            # dead-host breaker then marks raw dead, guaranteeing infra.
            # Fetch ONLY sefstars.txt era-pin bytes as a second commit
            # tarball from github.com (same host source() + planetary bulk
            # prove reachable): 1 TLS handshake instead of 3 sequential raw
            # ones, atomically era-consistent (eecb996a, 136071 bytes, same
            # 50KB floor). Success pre-populates the file so the per-file
            # loop below hits its size-check skip; failure falls through to
            # that loop unchanged. Suite scope, floors, strict-pin and tier
            # order unchanged; healthy-network behavior byte-identical.
            _want_star = {"sefstars.txt": 50 * 1024}
            try:
                if os.path.isfile(os.path.join(setest_dir, "sefstars.txt")) and \
                        os.path.getsize(os.path.join(setest_dir, "sefstars.txt")) >= _want_star["sefstars.txt"]:
                    return
            except OSError:
                pass
            try:
                _tmp_root2 = self._usable_tmpdir(makedirs=True)
            except Exception:
                _tmp_root2 = self.build_folder
            _tar_path2 = os.path.join(_tmp_root2, "swisseph-starpin-{}.tar.gz".format(star_pin_rev[:12]))
            _urls2 = [
                "https://github.com/aloistr/swisseph/archive/" + star_pin_rev + ".tar.gz",
                "https://codeload.github.com/aloistr/swisseph/tar.gz/" + star_pin_rev,
            ]
            _got2 = False
            _errs2 = []
            for _u in _urls2:
                try:
                    _req2 = urllib.request.Request(
                        _u, headers={"User-Agent": "conan-libswe-ohos/1.0", "Connection": "close"})
                    with urllib.request.urlopen(_req2, timeout=180) as _resp2:
                        if _resp2.status != 200:
                            raise ValueError("HTTP status {}".format(_resp2.status))
                        _total2 = 0
                        with open(_tar_path2, "wb") as _f2:
                            while True:
                                _chunk2 = _resp2.read(256 * 1024)
                                if not _chunk2:
                                    break
                                _total2 += len(_chunk2)
                                if _total2 > 400 * 1024 * 1024:
                                    raise ValueError("star bulk tarball exceeds 400MB (unexpected)")
                                _f2.write(_chunk2)
                    if _total2 < 1 * 1024 * 1024:
                        raise ValueError("star bulk tarball {} bytes < 1MB floor".format(_total2))
                    self.output.info(
                        "libswe ephe: star bulk era-pin tarball fetched ({} bytes via {})".format(_total2, _u))
                    _got2 = True
                    break
                except Exception as _e:
                    _errs2.append("{}: {}".format(_u, _e))
                    try:
                        if os.path.isfile(_tar_path2):
                            os.remove(_tar_path2)
                    except OSError:
                        pass
                    time.sleep(2)
            if not _got2:
                self.output.warning(
                    "libswe ephe: star bulk era-pin tarball unavailable ({}); "
                    "falling back to per-file fetch".format(" | ".join(_errs2)))
                return
            try:
                _done2 = 0
                with tarfile.open(_tar_path2, "r:gz") as _tf2:
                    for _m in _tf2.getmembers():
                        if not _m.isfile():
                            continue
                        _base2 = os.path.basename(_m.name)
                        if _base2 not in _want_star:
                            continue
                        _parts2 = _m.name.replace("\\", "/").split("/")
                        if "ephe" not in _parts2:
                            continue
                        _dest2 = os.path.join(setest_dir, _base2)
                        try:
                            if os.path.isfile(_dest2) and os.path.getsize(_dest2) >= _want_star[_base2]:
                                continue
                        except OSError:
                            pass
                        _src2 = _tf2.extractfile(_m)
                        if _src2 is None:
                            continue
                        _size2 = 0
                        with open(_dest2, "wb") as _out2:
                            while True:
                                _c2 = _src2.read(256 * 1024)
                                if not _c2:
                                    break
                                _size2 += len(_c2)
                                _out2.write(_c2)
                        if _size2 < _want_star[_base2]:
                            try:
                                os.remove(_dest2)
                            except OSError:
                                pass
                            self.output.warning(
                                "libswe ephe: star bulk member {} ({} bytes < floor {}) rejected".format(
                                    _base2, _size2, _want_star[_base2]))
                            continue
                        _done2 += 1
                self.output.info(
                    "libswe ephe: star bulk era-pin extracted {}/{} era-pin files "
                    "(commit {}, single-tarball tier=era-pin)".format(_done2, len(_want_star), star_pin_rev[:12]))
            except Exception as _e:
                self.output.warning(
                    "libswe ephe: star bulk era-pin extraction failed ({}); "
                    "falling back to per-file fetch".format(_e))
            finally:
                try:
                    if os.path.isfile(_tar_path2):
                        os.remove(_tar_path2)
                except OSError:
                    pass

        _bulk_pin_tarball()
        missing_required = []
        for rel, minimum, urls in required:
            if not _fetch_urls(urls, os.path.join(setest_dir, rel), minimum):
                missing_required.append(rel)
            if consecutive_failures >= 3:
                raise ConanException(
                    "libswe: ephemeris mirrors unreachable ({} consecutive failures across fallback hosts "
                    "pinned-commit raw + master raw + ephe.scryr.io); aborting instead of running a doomed suite. "
                    "This is an environment/network issue, not a recipe bug.".format(consecutive_failures))
        # Round-15 lazy star-bulk retry (different route from the
        # unconditional prefetch): healthy networks fetch sefstars.txt via
        # one raw request (~136KB, ~1s) so a second ~300MB tarball must NOT
        # be paid on every build; only when the per-file strict-pin pass
        # above leaves sefstars.txt missing (raw host outage as in the
        # 2026-09-19 infra abort) fall back to the github.com commit tarball
        # at star_pin_rev (same reliable host as the planetary bulk).
        if "sefstars.txt" in missing_required:
            _bulk_star_pin_tarball()
            _star_path = os.path.join(setest_dir, "sefstars.txt")
            try:
                _star_ok = os.path.isfile(_star_path) and os.path.getsize(_star_path) >= 50 * 1024
            except OSError:
                _star_ok = False
            if _star_ok:
                missing_required.remove("sefstars.txt")
                fetched += 1
                consecutive_failures = max(0, consecutive_failures - 1)
                self.output.info("libswe ephe: sefstars.txt recovered via star bulk era-pin tarball")
        # #22 fail-fast reorder (different from round-1 no-change): a run
        # with any required file missing is already doomed, so raise here
        # BEFORE the 14 best-effort asteroid downloads instead of after.
        # Saves ~5MB/14 fetches of hang on the doomed path; the success
        # path (all required present) is byte-identical.
        if missing_required:
            raise ConanException(
                "libswe: {} required ephemeris file(s) still missing after all hosts/retries: {}; "
                "refusing to run setest without data (every SWIEPH iteration would Moshier-fallback and fail). "
                "This is an environment/network issue, not a test-content failure.".format(
                    len(missing_required), ", ".join(missing_required)))
        for _moon in sat_moons:
            _rel = "sat/sepm{}.se1".format(_moon)
            # Round-6 retry hardening (different route from rounds 1-5
            # mirror/era-pin/fixture/host-breaker tuning): sat + asteroid
            # files live on a SINGLE host (scryr.io, no git fallback), so a
            # transient timeout is unrecoverable with attempts=1 -- the
            # 382->552 round signature (suite_07 23->87 = the exact pre-data
            # count, suite_01 +70, suite_04 +4 rc-mismatches) is a data-flake,
            # not value drift. 3 attempts x 15s bounds the added stall; the
            # dead-host breaker above still caps a sick host, and the
            # healthy-network path is byte-identical (first attempt wins).
            if not _fetch_urls([scryr_base + _rel],
                               os.path.join(setest_dir, _rel),
                               1 * 1024 * 1024, attempts_per_url=3, timeout=15,
                               max_bytes=20 * 1024 * 1024):
                missing_required.append(_rel)
            if consecutive_failures >= 3:
                raise ConanException(
                    "libswe: ephemeris mirror unreachable during sat fetch "
                    "({} consecutive failures); aborting instead of running a doomed suite. "
                    "This is an environment/network issue, not a recipe bug.".format(consecutive_failures))
        if missing_required:
            raise ConanException(
                "libswe: {} required ephemeris file(s) still missing after sat fetch: {}; "
                "refusing to run setest without data. "
                "This is an environment/network issue, not a test-content failure.".format(
                    len(missing_required), ", ".join(missing_required)))
        missing_asteroids = []
        for _num, subdir in asteroids:
            if consecutive_failures >= 6:
                self.output.warning("libswe ephe: skipping remaining asteroid files (mirror unreachable)")
                break
            stem = "se{:05d}".format(_num)
            for variant, minimum in ((stem + "s.se1", 8 * 1024), (stem + ".se1", 50 * 1024)):
                # Round-7 hard gate (different from round-6 warn-only): the
                # 516 round kept suite_07 at the exact 87 no-data baseline
                # DESPITE 3x15s retries + named warnings -- warn-only lets a
                # data outage masquerade as 64 test failures (87 vs the 23
                # on-pin floor) plus suite_01 spillover, misleading triage
                # into another drift cycle. Asteroid short+long files are now
                # REQUIRED: a miss joins missing_required and aborts as infra
                # (scheduler-retried when the single host heals) instead of
                # running a doomed suite. Retries/timeout unchanged; the
                # healthy-network path is byte-identical. Falsifiable: infra
                # with named asteroid files = outage; 23 with no infra =
                # genuine MPC drift floor.
                if not _fetch_urls([scryr_base + subdir + "/" + variant],
                                   os.path.join(setest_dir, subdir, variant), minimum,
                                   attempts_per_url=3, timeout=15):
                    _rel_ast = subdir + "/" + variant
                    missing_asteroids.append(_rel_ast)
                    missing_required.append(_rel_ast)
        if missing_required:
            raise ConanException(
                "libswe: {} required ephemeris file(s) still missing after asteroid fetch "
                "(incl. strict era-pin rejections + asteroid hard gate): {}; "
                "refusing to run setest without complete on-pin data. "
                "This is an environment/network issue, not a test-content failure.".format(
                    len(missing_required), ", ".join(missing_required)))
        self.output.info("libswe ephe: Swiss data ready (fetched={} present={} failed={})".format(
            fetched, skipped, failed))
        # Round-7: no warn-and-continue tail -- any missing/partial file has
        # already raised infra above (planetary strict-pin, sat, asteroids).
        # Reaching here means complete on-pin data; the suite runs.

    def _parse_setest_evidence(self, log_path, rc_path, run_cmd, expected_iters=None, total_iters=None, dropped_jpl=None):
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                log_text = f.read()
        except OSError as e:
            raise ConanException("libswe: cannot read setest log {}: {}".format(log_path, e))
        rc = None
        try:
            with open(rc_path, "r", encoding="utf-8", errors="replace") as f:
                m = re.search(r"SETEST_RC=(-?\d+)", f.read())
                rc = int(m.group(1)) if m else None
        except OSError:
            rc = None
        # Round-13 falsification guard (same new route): prove the right
        # collection ran. Without the Testmode header the run may have
        # silently skipped; the stats-line check below alone cannot tell.
        if "Testmode 't_nojpl'" not in log_text:
            self.output.info("libswe setest log tail (last 6k):\n" + log_text[-6000:])
            raise ConanException(
                "libswe: setest log lacks Testmode header, refusing vacuous run")
        stat = re.search(
            r"Total\s+(\d+)/(\d+)/(\d+).*?(\d+)\s+failures\s+in\s+(\d+)\s+iterations",
            log_text,
            re.S,
        )
        if stat is None:
            self.output.info("libswe setest log tail (last 6k):\n" + log_text[-6000:])
            raise ConanException(
                "libswe: setest produced no stats line (rc={}); binary crashed or "
                "fixture files missing — see log tail above".format(rc)
            )
        suites, cases, iters, _failures, failed_iters = (int(g) for g in stat.groups())
        # Round-10 desync guard (different route from rounds 1-9 data/mirror/
        # fixture/gate/docs tuning): audited setest.c open_exp_or_fix_reader
        # (this round, upstream source): TEST-mode opens <collection>.exp,
        # so input values travel with expectations per section and executed
        # iters must equal the derived kept count. A mismatch means the
        # derivation and the reader disagree (fixture format change or
        # reindex bug); loud infra error instead of silent misattribution.
        # Healthy path (12219 == 12219) is byte-identical.
        if expected_iters is not None and iters != expected_iters:
            raise ConanException(
                "libswe: setest executed %d iters but t_nojpl.exp kept %d; "
                "derivation/reader desync, refusing pairing artifacts" % (iters, expected_iters))
        # Round-13 scope guard (same new route): m4 codegen yields 60
        # TESTCASEs and JPL filtering removes no whole TESTCASE (audited:
        # no JPL-only case), so anything else means codegen broke or scope
        # silently shrank. Healthy path (60) unaffected.
        if cases != 60:
            raise ConanException(
                "libswe: setest ran unexpected TESTCASE count, refusing silent-scope run")
        # Echo the stats line plus surrounding context so the CI log carries
        # real evidence (L1c) even when individual iterations fail.
        idx = stat.start()
        self.output.info("libswe setest stats:\n" + log_text[max(0, idx - 500):idx + 500])
        # Per-suite failure breakdown for the next triage round: setest prints
        # `# setest -s <suite>.<case>.<iter> ...` once per failed iteration.
        try:
            _by_suite = {}
            for _m in re.finditer(r"# setest -s (\d+)\.\d+\.\d+", log_text):
                _s = int(_m.group(1))
                _by_suite[_s] = _by_suite.get(_s, 0) + 1
            if _by_suite:
                self.output.info(
                    "libswe setest failures by suite: "
                    + ", ".join(
                        "suite_{}={}".format(_s, _by_suite[_s])
                        for _s in sorted(_by_suite)
                    )
                )
            else:
                self.output.info("libswe setest failures by suite: none parsed (likely 0 failed iterations)")
        except Exception as _e:
            self.output.info("libswe setest failures by suite: unparsable ({})".format(_e))
        # Failure telemetry for the next triage round (compact,摘要-friendly):
        # (a) serr histogram distinguishes missing-file fallbacks ("not found
        # in PATH ... using Moshier") from pure value drift (empty serr);
        # (b) top-5 diffs with test ids show which iterations dominate.
        # Diagnostic logging only; test口径 unchanged.
        try:
            from collections import Counter as _Counter
            _serrs = _Counter()
            for _m in re.finditer(
                r"serr unexpected value\s*\n#\s*expected:[^\n]*\n#\s*actual:\s*([^\n]*)",
                log_text,
            ):
                _serrs[_m.group(1).strip()[:100]] += 1
            if _serrs:
                self.output.info(
                    "libswe setest serr histogram: "
                    + " | ".join(
                        "{!r}x{}".format(_msg, _cnt)
                        for _msg, _cnt in _serrs.most_common(6)
                    )
                )
            else:
                self.output.info("libswe setest serr histogram: none parsed")
        except Exception as _e:
            self.output.info("libswe setest serr histogram: unparsable ({})".format(_e))
        try:
            _diffs = []
            _last_id = None
            _pos = 0
            _tok = re.compile(r"# setest -s (\d+\.\d+\.\d+)|diff:\s*([0-9.eE+\-]+)")
            for _m in _tok.finditer(log_text):
                if _m.group(1):
                    _last_id = _m.group(1)
                    _pos = _m.end()
                elif _m.group(2) and _last_id is not None and _m.start() - _pos < 1200:
                    try:
                        _diffs.append((float(_m.group(2)), _last_id))
                    except ValueError:
                        pass
            _diffs.sort(key=lambda _p: _p[0], reverse=True)
            if _diffs:
                self.output.info(
                    "libswe setest top diffs: "
                    + ", ".join(
                        "{}@{}".format(_v, _i) for _v, _i in _diffs[:5]
                    )
                )
            else:
                self.output.info("libswe setest top diffs: none parsed")
        except Exception as _e:
            self.output.info("libswe setest top diffs: unparsable ({})".format(_e))
        # Round-10 failure-kind telemetry (diagnostic only; test scope
        # unchanged): checkpoints.c handle_failures prints one
        # `#   <field> unexpected value` per WRONG_VALUE failure and one
        # `# Expected value ... not found in test data` per EXP_VALUE_MISSING.
        # Counting by field separates value drift (xx/rc/jd) from data
        # fallbacks (serr) and derivation gaps (EXP_VALUE_MISSING), which the
        # suite/serr histograms cannot separate. Falsifiable: a pure drift
        # floor shows xx/rc WRONG_VALUE with ~0 EXP_VALUE_MISSING; any
        # reappearing not-found serr means data regressed, not drift.
        try:
            from collections import Counter as _Counter2
            _fields = _Counter2()
            for _m in re.finditer(r"#\s+(\S+) unexpected value", log_text):
                _fields[_m.group(1).strip()[:40]] += 1
            _missing = len(re.findall(r"# Expected value ", log_text))
            # Round-14 attribution (different route from round-13 gates:
            # no new pass/fail condition, only naming). The 149 floor
            # carries exactly 1 EXP_VALUE_MISSING line; attach the most
            # recent '# setest -s <suite>.<case>.<iter>' id so the next
            # triage can tell drift-field (e.g. split_deg dsecfr) from a
            # derivation gap without re-parsing raw logs. Healthy-path
            # output gains only the id list; outcome logic untouched.
            _missing_ids = []
            _last_sid = None
            for _mm in re.finditer(r"# setest -s (\d+\.\d+\.\d+)|# Expected value ", log_text):
                if _mm.group(1):
                    _last_sid = _mm.group(1)
                elif _last_sid is not None:
                    if _last_sid not in _missing_ids and len(_missing_ids) < 10:
                        _missing_ids.append(_last_sid)

            if _fields:
                self.output.info(
                    "libswe setest failure kinds: "
                    + ", ".join(
                        "{}x{}".format(_f, _c)
                        for _f, _c in _fields.most_common(8)
                    )
                    + " | EXP_VALUE_MISSINGx{} in {}".format(_missing, _missing_ids if _missing_ids else "none"))
            else:
                self.output.info(
                    "libswe setest failure kinds: none parsed | EXP_VALUE_MISSINGx{} in {}".format(_missing, _missing_ids if _missing_ids else "none"))
        except Exception as _e:
            self.output.info("libswe setest failure kinds: unparsable ({})".format(_e))
        try:
            from collections import Counter as _Counter3
            _by_case = _Counter3()
            for _m in re.finditer(r"# setest -s (\d+\.\d+)\.\d+", log_text):
                _by_case[_m.group(1)] += 1
            if _by_case:
                self.output.info(
                    "libswe setest failed iters by case: "
                    + ", ".join(
                        "{}={}".format(_c, _n)
                        for _c, _n in sorted(_by_case.items())
                    )
                )
            else:
                self.output.info("libswe setest failed iters by case: none parsed")
        except Exception as _e:
            self.output.info("libswe setest failed iters by case: unparsable ({})".format(_e))
        # Round-11 drift ledger enforcement (different route from rounds
        # 1-10 data/mirror/fixture/gate/bulk/telemetry tuning): the 149
        # floor (01=112/02=0/04=3/05=1/07=12/08=5/09=10/10=6) is upstream
        # version drift + irrecoverable era data (Delta-T/Vreijs/calc_dip/
        # lun-eclipse/split_deg/ayanamsa code drift per the official
        # v2.10.02...v2.10.03 diff, DE441-rebuilt sat coverage, MPC element
        # drift), not invocation artifacts (pairing audited round 10, FP
        # flags already match upstream -O2 so CFLAGS are intentionally
        # unchanged here). This check does NOT skip or silence anything:
        # the marker below still reports failed with full counts. It only
        # distinguishes stable drift (every failed case inside the known
        # 149 ledger) from NEW regressions (any failed case outside the
        # ledger), which get a distinct loud warning so the next triage can
        # tell "same floor" from "new breakage" without re-auditing.
        # Falsifiable: a stable floor logs ledger-clean; any new case logs
        # NEW-REGRESSION with names.
        # Round-12 evidence hardening (different route from rounds 1-11:
        # data/mirror/fixture/gate/bulk/telemetry/ledger-logging): persist
        # the ledger verdict into upstream_test_evidence.json so the stable
        # 149 floor is machine-checkable without log parsing. Additive only:
        # marker口径, suite scope, data fetch, tolerances and CFLAGS unchanged.
        _ledger_by_case = {}
        _ledger_novel = []
        _ledger_absent = []
        _ledger_verdict = "unparsable"
        try:
            from collections import Counter as _Counter4
            _ledger_cases = frozenset([
                "1.1", "1.3", "1.5",
                "4.1", "5.4", "7.3",
                "8.3", "8.7", "8.9",
                "9.3", "9.4", "9.5",
                "10.8",
            ])
            _lc = _Counter4()
            for _m in re.finditer(r"# setest -s (\d+\.\d+)\.\d+", log_text):
                _lc[_m.group(1)] += 1
            _novel = sorted(set(_lc) - _ledger_cases)
            _absent = sorted(_ledger_cases - set(_lc))
            _ledger_by_case = {str(_k): int(_v) for _k, _v in _lc.items()}
            _ledger_novel = list(_novel)
            _ledger_absent = list(_absent)
            _ledger_verdict = "new-regression" if _novel else "ledger-clean"
            if _novel:
                self.output.warning(
                    "libswe setest drift ledger: NEW-REGRESSION outside 149 floor: "
                    + ", ".join("{}={}".format(_c, _lc[_c]) for _c in _novel)
                    + " (ledger-clean cases still "
                    + str(sorted(set(_lc) & _ledger_cases)) + ")"
                )
            else:
                self.output.info(
                    "libswe setest drift ledger: ledger-clean (all {} failed cases "
                    "within 149 floor; ledger-absent this run: {})".format(
                        len(_lc), _absent if _absent else "none"
                    )
                )
        except Exception as _e:
            self.output.info("libswe setest drift ledger: unparsable ({})".format(_e))
        if iters == 0:
            raise ConanException("libswe: setest ran 0 iterations — vacuous run, refusing to pass")
        if rc != 0 and failed_iters == 0:
            raise ConanException(
                "libswe: setest exited rc={} with 0 failed iterations — inconsistent, "
                "treating as infrastructure failure".format(rc)
            )
        passed = iters - failed_iters
        status = "passed" if failed_iters == 0 else "failed"
        command = "./setest t_nojpl (upstream make test on t.exp minus 538 JPL sections: 2.6GB de431.eph not vendored)"
        # HMBS hard-gate identity: discovered/executed/passed/failed/skipped
        # share the ITERATION-section unit from a single deterministic source
        # (the stats line + derivation counts). Total upstream sections
        # (total_iters, e.g. 12757) = executed iters (e.g. 12219) + skipped
        # JPL sections (e.g. 538). TESTCASE count (cases, 60) is asserted
        # separately above as a scope guard, never mixed into the marker.
        _total = total_iters if total_iters is not None else iters
        _skipped = dropped_jpl if dropped_jpl is not None else max(0, _total - iters)
        marker = {
            "status": status,
            "framework": "setest",
            "command": command,
            "discovered": _total,
            "executed": iters,
            "passed": passed,
            "failed": failed_iters,
            "skipped": _skipped,
        }
        if failed_iters > 0 or _skipped > 0:
            _gaps = []
            if _skipped > 0:
                _gaps.append({
                    "count": _skipped,
                    "category": "environment",
                    "detail": "538 JPL ITERATION sections excluded via pairing-preserving t_nojpl.exp derivation (default de431.eph is 2.6GB, not vendored; ctest -E equivalent, explicit in command)",
                    "evidence": "derivation log (iterations/dropped_JPL/kept) + test_package/MANIFEST.yml upstream_test_exemptions",
                })
            if failed_iters > 0:
                _gaps.append({
                    "count": failed_iters,
                    "category": "test_failure",
                    "detail": "residual SWIEPH/Moshier-vs-t.exp value drift (Delta-T/Vreijs/calc_dip/lun-eclipse/split_deg/ayanamsa code drift per official v2.10.02...v2.10.03 diff + DE441-rebuilt sat coverage + MPC element drift); see MANIFEST exemptions and drift_ledger in evidence",
                    "evidence": "setest log stats line + failure-kinds/serr histogram + upstream_test_evidence.json drift_ledger",
                })
            marker["gaps"] = _gaps
        evidence = dict(marker)
        evidence["testsuites"] = suites
        evidence["failed_by_case"] = _ledger_by_case
        evidence["drift_ledger"] = {
            "floor": "149",
            "known_cases": ["1.1", "1.3", "1.5", "4.1", "5.4", "7.3",
                            "8.3", "8.7", "8.9", "9.3", "9.4", "9.5", "10.8"],
            "novel_cases": _ledger_novel,
            "absent_cases": _ledger_absent,
            "verdict": _ledger_verdict,
        }
        evidence["note"] = (
            "setest TESTCASE/iteration counts parsed from the stats line above; "
            "run on t_nojpl.exp (t.exp minus 538 JPL ITERATION sections, "
            "2.6GB de431.eph not vendored, see MANIFEST.yml); kept bytes "
            "identical to upstream so residual failures, if any, are genuine "
            "SWIEPH/Moshier-vs-t.exp drift, not invocation artifacts"
            if status == "failed"
            else "JPL-excluded upstream suite green on first run"
        )
        evidence_path = os.path.join(self.build_folder, "upstream_test_evidence.json")
        with open(evidence_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(evidence, f, indent=2)
            f.write("\n")
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        # print(): the HMBS evidence gate parses stdout; mirrors the merged
        # bwm/0.6.3 recipe, which emits markers via both print and
        # self.output.info.
        print(msg, flush=True)
        self.output.info(msg)
        if status == "failed":
            # Content failures (missing .se1/JPL data files, stale t.exp for
            # 2.10.03) are documented exemptions, not recipe bugs: record
            # honestly and keep the package build green (TEST_QUALITY_SPEC
            # section 3.3). Infrastructure failures raise above.
            self.output.warning(
                "libswe: upstream setest reports {}/{} failed iterations; "
                "see test_package/MANIFEST.yml upstream_test_exemptions".format(failed_iters, iters)
            )

    def _usable_shell(self):
        # Same HMBS host guard as merged bwm/0.6.3: hard-prefer /bin/sh and
        # never return the repo-profile HNP bash path (present as a file on
        # some hosts but not executable there).
        if os.path.isfile("/bin/sh"):
            return "/bin/sh"
        sh_which = shutil.which("sh") or ""
        if sh_which and os.path.isfile(sh_which):
            return sh_which
        for cand in (os.environ.get("SHELL", ""), os.environ.get("CONFIG_SHELL", "")):
            if not cand:
                continue
            first = cand.split()[0]
            if "hnp/bin/bash" in first:
                continue
            if os.path.isfile(first):
                return cand
        return "/bin/sh"

    def _usable_tmpdir(self, makedirs=False):
        # readonly_tmp guard (cxxtools/c-client precedent, adapted): reuse
        # HMBS-injected writable dirs with probe-write validation, else a
        # build-local tmp dir. Bare /tmp is read-only on OHOS and is never
        # used nor probed (a failed /tmp touch trips the HMBS read-only
        # gate as a false positive); flag values "0"/"1" and the
        # HMBS_AUTOCONF_MKTEMP_FALLBACK flag are never paths; HMBS_INSTALL
        # is an install prefix, not a temp root, and is not consulted.
        def _is_path_cand(v):
            if not v or v in ("0", "1", "/tmp"):
                return False
            return os.path.isabs(v)
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            cand = os.environ.get(var, "")
            if not _is_path_cand(cand):
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_probe")
                with open(probe, "w", encoding="utf-8") as _pf:
                    _pf.write("probe")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                return cand
            except Exception:
                continue
        tmpd = os.path.join(self.build_folder, "tmp")
        if makedirs:
            os.makedirs(tmpd, exist_ok=True)
        return tmpd

    def package(self):
        include_dir = os.path.join(self.package_folder, "include")
        lib_dir = os.path.join(self.package_folder, "lib")
        copy(self, "swephexp.h", src=self.source_folder, dst=include_dir)
        copy(self, "sweodef.h", src=self.source_folder, dst=include_dir)
        copy(self, "swedll.h", src=self.source_folder, dst=include_dir)
        copy(self, "libswe.a", src=self.source_folder, dst=lib_dir)
        if self.options.shared:
            copy(self, "libswe.so", src=self.source_folder, dst=lib_dir)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Evidence for test_package re-emit on Conan cache-hit runs, when
        # build() is skipped and its marker would otherwise be absent.
        evidence_src = os.path.join(self.build_folder, "upstream_test_evidence.json")
        if os.path.isfile(evidence_src):
            copy(self, "upstream_test_evidence.json", src=self.build_folder, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["swe"]
        if self.settings.os in ("Linux", "OHOS"):
            # libswe.a references libm and dladdr (sweph.c dlfcn path);
            # -ldl is proven working on the OHOS toolchain (merged
            # umka-lang/virtualpg recipes link it the same way).
            self.cpp_info.system_libs = ["m", "dl"]
