#!/usr/bin/env python3
"""Conan recipe — routino 3.4.3 (Makefile build system).

Routino is OpenStreetMap routing software: routers/planetsplitter/filedumper
CLIs plus libroutino/libroutino-slim shared libraries (routino.h API).
Upstream tarball routino-3.4.3.tgz (2653609 bytes, sha256 in conandata.yml).

Build facts (audited from the 3.4.3 tarball):
  * Custom Makefile build (top-level Makefile.conf + src/Makefile). No
    configure, no CMake. Only src/ + xml/ are packaged (library, tools and
    routing data); doc/ is empty targets, web/ is a demo site needing extra
    downloads, extras/ has empty install targets, python/ needs swig.
  * Upstream defaults: CC=gcc, CFLAGS=-std=c99 -O3 -ffast-math -g -pthread
    -DUSE_PTHREADS -DUSE_BZIP2 -DUSE_GZIP, LDFLAGS=-lm -pthread -lpthread
    -lbz2 -lz. FASTMATHS=0 appends -fno-fast-math (Makefile.conf notes
    -ffast-math "makes test cases fail slightly").
  * Deps: zlib (gzip, mandatory) and bzip2 (enabled unless HOST=MINGW),
    both from the ohpcd registry.
  * Upstream tests (both driven here by process exit codes, never by
    counting stdout words): src/test/run-all-tests.sh runs 15 OSM fixtures
    (*.osm -> *.sh) in 6 configs each (normal/lib/pruned x non-slim/slim) =
    90 runs, plus 3 slim-vs-non-slim diff comparisons; src/xml Makefile
    checks test/good*.xml (must parse, 1 file) and test/bad*.xml (must
    reject, 32 files) = 33 checks. Total 126.
  * Install honors DESTDIR + prefix, but install-local depends on all-local
    whose versioned .so targets run `ln -sf` (no HMDFS symlinks, see below),
    so packaging uses explicit conan copy() lists instead of make install.

OHOS notes:
  * Compilers come from Conan conf via generate() into routino_cc_env
    (R33, guide section 4.3; custom name avoids the qqwing-style
    save_script("conanbuild") recursive-source E2BIG);
    CONFIG_SHELL/SHELL from profile buildenv (R5: no /bin/sh on OHOS).
    make runs with -j1 (R9). Shell scripts are invoked via $CONFIG_SHELL
    explicitly (their #!/bin/sh shebang cannot work on OHOS).
  * HMDFS has no symlinks (knowledge: libfreenect draft, bzip2 precedent):
    shared=True is rejected on OHOS in validate(); the static package is
    used. The .so soname links are therefore never created with ln.
  * lib-type routing tests (type 2, router+lib binaries) need libroutino.so
    at build/run time, so build() stages real-file copies (.so.0.0.0 ->
    .so.0 + .so via copy2, never symlinks) purely as build-tree test
    scaffolding; packaged artifacts are static archives + directly-linked
    tools only (router+lib* are NOT packaged: their DT_NEEDED soname could
    not resolve from a static package).
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


# Audited upstream total: 90 routing runs (15 osm x 6 configs) + 3 slim
# comparisons + 33 xml checks (1 good + 32 bad) = 126. See notes.md and
# test_package/MANIFEST.yml audit.
_UPSTREAM_TEST_TOTAL = 126

# Exact lib object lists mirror LIBROUTINO_OBJ / LIBROUTINO_SLIM_OBJ in
# src/Makefile (used for static archives; globbing would mix slim/non-slim
# since "*-lib.o" also matches "*-slim-lib.o").
_LIB_OBJS = [
    "routino-lib.o", "nodes-lib.o", "segments-lib.o", "ways-lib.o",
    "relations-lib.o", "types-lib.o", "fakes-lib.o", "optimiser-lib.o",
    "output-lib.o", "files-lib.o", "profiles-lib.o", "xmlparse-lib.o",
    "results-lib.o", "queue-lib.o", "translations-lib.o",
]
_SLIM_LIB_OBJS = [
    "routino-slim-lib.o", "nodes-slim-lib.o", "segments-slim-lib.o",
    "ways-slim-lib.o", "relations-slim-lib.o", "types-lib.o",
    "fakes-slim-lib.o", "optimiser-slim-lib.o", "output-slim-lib.o",
    "files-lib.o", "profiles-lib.o", "xmlparse-lib.o", "results-lib.o",
    "queue-lib.o", "translations-lib.o",
]

# Tools packaged into bin/ (directly linked; router+lib* need a .so at
# runtime so they stay build-tree-only under the static OHOS package).
_PACKAGED_EXES = [
    "planetsplitter", "planetsplitter-slim",
    "router", "router-slim",
    "filedumperx", "filedumper", "filedumper-slim",
]

# type 2 (lib) + type 3 (prune) matrix from run-all-tests.sh:
# (suffix_tag, mode_arg, extra_arg)
_TEST_MATRIX = [
    ("", "fat", None),
    ("", "slim", None),
    ("+lib", "fat", "lib"),
    ("+lib", "slim", "lib"),
    ("-pruned", "fat", "prune"),
    ("-pruned", "slim", "prune"),
]


class RoutinoConan(ConanFile):
    name = "routino"
    version = "3.4.3"
    description = "OpenStreetMap routing software (router + libroutino)"
    license = "AGPL-3.0-or-later"
    homepage = "https://www.routino.org/"
    url = "https://www.routino.org/"
    topics = ("routing", "openstreetmap", "osm", "router")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1", transitive_headers=True)
        self.requires("bzip2/1.0.8", transitive_headers=True)

    def validate(self):
        if self.settings.os == "OHOS" and self.options.shared:
            raise ConanInvalidConfiguration(
                "routino shared=True is disabled on OHOS because the "
                "versioned .so targets use `ln -sf` soname links that "
                "HMDFS cannot create; use the static package (bzip2 precedent)."
            )

    def layout(self):
        basic_layout(self)
        # Routino builds in-source (Makefile.conf in source dir).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33 (guide 4.3): compiler paths come from Conan conf into a
        # custom env script; build() uses $CC/$CXX/$AR/$RANLIB from it.
        # Must NOT use save_script("conanbuild"): it aggregates with
        # VirtualBuildEnv's own conanbuild script into a recursive
        # self-source loop (qqwing precedent) that ends in
        # `printenv: Argument list too long` (E2BIG) on the真机.
        env = VirtualBuildEnv(self)
        env.generate()
        # OHOS conan (2.29.1/2.30) does not support dotted sub-key syntax
        # ("tools.build:compiler_executables:c" raises "[conf] ... does not
        # exist"); read the dict conf once and take keys from it.
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = self._resolve_tool(_ce.get("c"), ("clang", "cc"))
        cxx = self._resolve_tool(_ce.get("cpp") or _ce.get("cxx"), ("clang++", "c++"))
        ar = self._resolve_tool(_ce.get("ar", "llvm-ar"), ("llvm-ar", "ar"))
        ranlib = self._resolve_tool(_ce.get("ranlib", "llvm-ranlib"), ("llvm-ranlib", "ranlib"))
        self.output.info("routino compilers: CC=%s CXX=%s AR=%s RANLIB=%s" % (cc, cxx, ar, ranlib))
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("AR", ar)
        env.define("RANLIB", ranlib)
        env.vars(self).save_script("routino_cc_env")

    def _build_env(self):
        # Custom script name must be loaded together with conanbuild
        # (zita precedent: env=["conanbuild", "<custom>"]).
        return ["conanbuild", "routino_cc_env"]

    def _config_shell(self):
        # Profile hardcodes /data/service/hnp/bin/bash, but the preflight
        # worker may only provide /bin/sh (HMBS injects SHELL=/bin/sh and
        # puts real tools under /storage/.../usr/local/bin on PATH).
        # Prefer an existing executable, never a stale absolute path.
        for cand in (os.environ.get("CONFIG_SHELL"), os.environ.get("SHELL")):
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        for name in ("bash", "sh"):
            found = shutil.which(name)
            if found:
                return found
        return "/bin/sh"

    @staticmethod
    def _resolve_tool(conf_val, fallbacks):
        # conf absolute paths go stale when the worker toolchain moves
        # (e.g. /data/service/hnp/bin/clang missing on 2026-09-29 preflight:
        # `make: /data/service/hnp/bin/clang: No such file or directory`).
        # Use the conf value only if it exists+executes; otherwise resolve
        # via PATH (HMBS prepends its tool dirs) or keep the bare name so
        # the build-time conanbuild env can resolve it.
        if conf_val:
            if os.path.isabs(conf_val):
                if os.path.isfile(conf_val) and os.access(conf_val, os.X_OK):
                    return conf_val
            else:
                found = shutil.which(conf_val.split()[0])
                if found:
                    return found
                return conf_val
        for name in fallbacks:
            found = shutil.which(name)
            if found:
                return found
        if conf_val and not os.path.isabs(conf_val):
            return conf_val
        return fallbacks[0] if fallbacks else (conf_val or "cc")

    def _dep_flags(self):
        incs, libdirs = [], []
        for name in ("zlib", "bzip2"):
            dep = self.dependencies[name]
            pkg = dep.package_folder
            for d in dep.cpp_info.includedirs:
                p = os.path.join(pkg, d) if not os.path.isabs(d) else d
                if os.path.isdir(p):
                    incs.append(p)
            for d in dep.cpp_info.libdirs:
                p = os.path.join(pkg, d) if not os.path.isabs(d) else d
                if os.path.isdir(p):
                    libdirs.append(p)
        return incs, libdirs

    def _make_args(self):
        # Upstream CFLAGS/LDFLAGS base from Makefile.conf (preserved) plus
        # dependency -I/-L paths. FASTMATHS=0 appends -fno-fast-math so the
        # routing fixtures compare exactly. Passed on the make command line,
        # which overrides the Makefile.conf plain assignments (its += lines
        # append on top, e.g. -fno-fast-math, -pthread defines).
        incs, libdirs = self._dep_flags()
        cflags = (
            "-std=c99 -Wall -Wmissing-prototypes -Wextra "
            "-Wno-unused-parameter -pedantic -O3 -ffast-math -g "
            "-pthread -DUSE_PTHREADS -DUSE_BZIP2 -DUSE_GZIP "
            "-D_FILE_OFFSET_BITS=64 -D_POSIX_C_SOURCE=200809L"
            + "".join(" -I%s" % d for d in incs)
        )
        ldflags = "".join("-L%s " % d for d in libdirs) + "-lm -pthread -lpthread -lbz2 -lz"
        config_shell = self._config_shell()
        return (
            "CC=$CC LD=$CC AR=$AR RANLIB=$RANLIB SHELL=%s "
            'CFLAGS="%s" LDFLAGS="%s" FASTMATHS=0' % (config_shell, cflags, ldflags)
        )

    def _make(self):
        return os.environ.get("HMBS_MAKE", "make")

    def build(self):
        apply_conandata_patches(self)
        # R32: meaningful on Linux and OHOS alike.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("routino is only supported on Linux/OHOS")
        make = self._make()
        args = self._make_args()
        src = self.source_folder
        srcdir = os.path.join(src, "src")
        testdir = os.path.join(src, "src", "test")
        srcxmldir = os.path.join(src, "src", "xml")
        topxmldir = os.path.join(src, "xml")
        # Directly-linked tools first (no .so links involved).
        self.run("%s %s -j1 -C %s %s" % (make, args, srcdir, " ".join(_PACKAGED_EXES)), env=self._build_env())
        self.run("%s %s -j1 -C %s libroutino.so.0.0.0 libroutino-slim.so.0.0.0" % (make, args, srcdir), env=self._build_env())
        self._stage_shared_copies()
        # router+lib* link against the staged real-file .so copies.
        self.run("%s %s -j1 -C %s router+lib router+lib-slim" % (make, args, srcdir), env=self._build_env())
        # Test helpers.
        self.run("%s %s -j1 -C %s is-fast-math" % (make, args, testdir), env=self._build_env())
        self.run("%s %s -j1 -C %s test-skeleton" % (make, args, srcxmldir), env=self._build_env())
        # XML data files (perl-generated tagging variants for share/).
        self.run("%s %s -j1 -C %s all" % (make, args, topxmldir), env=self._build_env())
        if not self.options.shared:
            self._make_static_archives()
        if can_run(self):
            self._run_upstream_tests()
        else:
            self.output.info("cross-building: compile+link check only, upstream tests skipped")

    def _stage_shared_copies(self):
        # Build-tree-only test scaffolding (never packaged): real-file copies
        # standing in for the ln -sf soname links HMDFS cannot create, so the
        # lib-type routing tests can run. Uses copy2, never symlinks.
        srcdir = os.path.join(self.source_folder, "src")
        for base in ("libroutino.so.0.0.0", "libroutino-slim.so.0.0.0"):
            real = os.path.join(srcdir, base)
            if not os.path.isfile(real):
                raise ConanInvalidConfiguration("expected build artifact missing: %s" % base)
            stem = base[: -len(".0.0.0")]
            for alias in (stem + ".0", stem):
                dst = os.path.join(srcdir, alias)
                if os.path.lexists(dst):
                    os.remove(dst)
                shutil.copy2(real, dst)

    def _make_static_archives(self):
        srcdir = os.path.join(self.source_folder, "src")
        for objs, lib in ((_LIB_OBJS, "libroutino.a"), (_SLIM_LIB_OBJS, "libroutino-slim.a")):
            missing = [o for o in objs if not os.path.isfile(os.path.join(srcdir, o))]
            if missing:
                raise ConanInvalidConfiguration("missing lib objects for %s: %s" % (lib, missing))
            out = os.path.join(srcdir, lib)
            if os.path.isfile(out):
                os.remove(out)
            # R33: $AR comes from the generate() routino_cc_env script.
            self.run("$AR rcs %s %s" % (out, " ".join(objs)), cwd=srcdir, env=self._build_env())

    def _run_upstream_tests(self):
        """Run both upstream suites, counting process exit codes only.

        Single deterministic source: each test is one subprocess whose
        return code decides pass/fail (routing run-one-test.sh invocations,
        test-skeleton redirections, diff comparisons). Stdout is captured to
        upstream_tests.log purely as evidence; no verdict is ever derived by
        counting stdout words, and there are no fallback/arithmetic fixup
        branches. Identities hold by construction: every executed run yields
        exactly one of pass/fail; skipped = discovered - executed.
        """
        testdir = os.path.join(self.source_folder, "src", "test")
        xmldir = os.path.join(self.source_folder, "src", "xml")
        config_shell = self._config_shell()
        log_path = os.path.join(self.build_folder, "upstream_tests.log")
        results = []  # list of (name, passed, captured_output)

        def run_case(name, cmd, **kwargs):
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, errors="replace", **kwargs)
            ok = proc.returncode == 0
            results.append((name, ok, proc.stdout or ""))
            return ok

        # Falsification guard (toybox lesson): fixtures must be non-empty, or
        # a pass would be meaningless (empty-vs-empty diffs always match).
        osm_files = sorted(Path(testdir).glob("*.osm"))
        expected = sorted(Path(testdir, "expected").glob("*.txt"))
        if not osm_files or not expected:
            self._emit_marker(_UPSTREAM_TEST_TOTAL, 0, 0, 0, _UPSTREAM_TEST_TOTAL, log_path,
                              "no *.osm fixtures or expected/ outputs in source tree")
            raise ConanInvalidConfiguration("upstream fixtures missing")
        empty = [str(p) for p in list(osm_files) + expected if p.stat().st_size == 0]
        if empty:
            self._emit_marker(_UPSTREAM_TEST_TOTAL, 0, 0, 0, _UPSTREAM_TEST_TOTAL, log_path,
                              "empty fixture files: %s" % empty[:5])
            raise ConanInvalidConfiguration("upstream fixtures empty: %s" % empty[:5])

        # Suite 1: 15 osm x 6 configs = 90 runs via run-one-test.sh.
        # Invoked through $CONFIG_SHELL (shebang #!/bin/sh is absent on OHOS).
        for osm in osm_files:
            script = osm.with_suffix(".sh").name
            if not (Path(testdir) / script).is_file():
                raise ConanInvalidConfiguration("missing test script for %s" % osm.name)
            for suffix, mode, extra in _TEST_MATRIX:
                name = "routing:%s:%s%s" % (osm.stem, mode, suffix or "/base")
                cmd = [config_shell, "./run-one-test.sh", script, mode]
                if extra:
                    cmd.append(extra)
                run_case(name, cmd, cwd=testdir)

        # Suite 1b: 3 slim-vs-non-slim consistency comparisons.
        for suffix in ("", "+lib", "-pruned"):
            a = os.path.join(testdir, "fat" + suffix)
            b = os.path.join(testdir, "slim" + suffix)
            name = "compare:fat%s-vs-slim%s" % (suffix, suffix)
            run_case(name, ["diff", "-q", "-r", a, b], cwd=testdir)

        # Suite 2: xml parser checks (good must parse rc==0, bad must fail).
        good = sorted(Path(xmldir, "test").glob("good*.xml"))
        bad = sorted(Path(xmldir, "test").glob("bad*.xml"))
        if not good or not bad:
            self._emit_marker(_UPSTREAM_TEST_TOTAL, 0, 0, 0, _UPSTREAM_TEST_TOTAL, log_path,
                              "xml test corpus missing")
            raise ConanInvalidConfiguration("xml test corpus missing")
        skel = os.path.join(xmldir, "test-skeleton")
        for f in good:
            with open(f, "rb") as stdin:
                run_case("xml:good:%s" % f.name, [skel], cwd=xmldir, stdin=stdin)
        for f in bad:
            with open(f, "rb") as stdin:
                proc_rc = subprocess.run([skel], stdin=stdin, stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, cwd=xmldir).returncode
            results.append(("xml:bad:%s" % f.name, proc_rc != 0, ""))

        discovered = len(osm_files) * len(_TEST_MATRIX) + 3 + len(good) + len(bad)
        executed = len(results)
        passed = sum(1 for _, ok, _ in results if ok)
        failed = executed - passed
        skipped = _UPSTREAM_TEST_TOTAL - executed if executed <= _UPSTREAM_TEST_TOTAL else 0

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("discovered=%d executed=%d passed=%d failed=%d\n" % (discovered, executed, passed, failed))
            for name, ok, out in results:
                f.write("%s %s\n" % ("PASS" if ok else "FAIL", name))
                if not ok and out:
                    f.write("---- %s output (tail) ----\n" % name)
                    f.write("\n".join(out.splitlines()[-20:]) + "\n")

        audit_note = None
        if discovered != _UPSTREAM_TEST_TOTAL:
            audit_note = ("observed %d test units vs audit total %d "
                          "(osm=%d good=%d bad=%d); audit needs update"
                          % (discovered, _UPSTREAM_TEST_TOTAL,
                             len(osm_files), len(good), len(bad)))
        self._emit_marker(discovered, executed, passed, failed, skipped, log_path, audit_note)
        if failed or skipped:
            self.output.warning(
                "upstream tests completed with failures: passed=%d failed=%d skipped=%d (see marker)"
                % (passed, failed, skipped))

    def _emit_marker(self, discovered, executed, passed, failed, skipped, log_path, audit_note):
        if executed == 0:
            marker = {
                "status": "failed",
                "framework": "routino-shell",
                "command": "run-one-test.sh x90 + diff x3 + test-skeleton x33",
                "discovered": _UPSTREAM_TEST_TOTAL,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": _UPSTREAM_TEST_TOTAL,
                "reason": audit_note or "no test results collected",
            }
        else:
            status = "passed" if (failed == 0 and skipped == 0 and audit_note is None) else "failed"
            marker = {
                "status": status,
                "framework": "routino-shell",
                "command": "run-one-test.sh x90 + diff x3 + test-skeleton x33",
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            }
            if status != "passed":
                gaps = []
                if failed:
                    gaps.append({
                        "count": failed,
                        "category": "test_failure",
                        "detail": "upstream shell runs with nonzero exit (see upstream_tests.log)",
                        "evidence": "upstream_tests.log",
                    })
                if skipped:
                    gaps.append({
                        "count": skipped,
                        "category": "environment",
                        "detail": "audit total minus executed runs; suite aborted early or units missing",
                        "evidence": "upstream_tests.log",
                    })
                if audit_note:
                    # Audit mismatch is reported in `reason`, not as a gap:
                    # gaps must sum to discovered - passed exactly.
                    marker["reason"] = audit_note
                if gaps:
                    marker["gaps"] = gaps
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def package(self):
        # Explicit copy() lists (no `make install`: install-local depends on
        # all-local whose `ln -sf` soname steps cannot run on HMDFS).
        srcdir = os.path.join(self.source_folder, "src")
        pkg = self.package_folder
        for exe in _PACKAGED_EXES:
            src = os.path.join(srcdir, exe)
            if not os.path.isfile(src):
                raise ConanInvalidConfiguration("expected tool missing: %s" % exe)
            copy(self, exe, src=srcdir, dst=os.path.join(pkg, "bin"))
        copy(self, "routino.h", src=srcdir, dst=os.path.join(pkg, "include"))
        if self.options.shared:
            for lib in ("libroutino.so.0.0.0", "libroutino.so.0",
                        "libroutino-slim.so.0.0.0", "libroutino-slim.so.0"):
                copy(self, lib, src=srcdir, dst=os.path.join(pkg, "lib"))
            copy(self, "libroutino.so", src=srcdir, dst=os.path.join(pkg, "lib"))
            copy(self, "libroutino-slim.so", src=srcdir, dst=os.path.join(pkg, "lib"))
        else:
            for lib in ("libroutino.a", "libroutino-slim.a"):
                copy(self, lib, src=srcdir, dst=os.path.join(pkg, "lib"))
        # Routing data files mirror the xml/ install target (standard
        # shipped files + perl-generated tagging variants).
        topdir = self.source_folder
        for f in ("routino-profiles.xml", "routino-translations.xml",
                  "routino-tagging.xml", "tagging-drive.xml",
                  "tagging-ride.xml", "tagging-walk.xml"):
            copy(self, f, src=os.path.join(topdir, "xml"), dst=os.path.join(pkg, "share", "routino"))

    def package_info(self):
        if self.options.shared:
            self.cpp_info.libs = ["routino", "routino-slim"]
        else:
            self.cpp_info.libs = ["routino", "routino-slim"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
