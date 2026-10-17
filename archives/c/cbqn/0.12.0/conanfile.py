#!/usr/bin/env python3
"""Conan recipe — CBQN 0.12.0 (Makefile): ``bqn`` interpreter + ``libcbqn`` library for BQN.

Verified on HarmonyOS PC aarch64 (clang 15, GNU Make 4.4.1, Conan 2.29.1, profile
``ci/conan/profiles/ohos-aarch64``).  Notes worth the reader's attention:

* **The build bootstraps itself.**  ``make o3`` first compiles a small C-only interpreter
  (``make for-build``) and *runs* it to execute ``build/src/build.bqn``, which drives the real
  compilation.  That nested call hard-codes ``i_CC=cc`` and OHOS has no bare ``cc`` (only
  ``/data/service/hnp/bin/clang``), so the recipe issues ``make for-build`` explicitly with
  ``CC=<profile compiler>``: a make command-line variable overrides the makefile's own
  assignment, which is also how the compiler reaches every nested invocation (R33 - the path
  comes from ``tools.build:compiler_executables``, never from a shell ``$CC``).
* **The tag archive ships empty submodule directories.**  ``build/bytecodeSubmodule``
  (dzaima/cbqnBytecode) is mandatory - ``src/vm/load.c`` compiles in
  ``../../build/<BYTECODE_DIR>/gen/*`` - and ``build/singeliSubmodule`` (mlochbaum/Singeli) is
  upstream's default code generator.  Both are downloaded at the commits pinned by the tag and
  unpacked into the ``build/<name>Local`` fallback directories documented in the upstream
  README, together with ``nogit=1`` so no git call happens at build time.
* **``singeli=1`` is a test-visible requirement, not a tuning knob:**
  ``test/cases/perf.bqn`` asserts an amortized ``\u234b`` fast path (measured 13/14 with
  ``singeli=0``: 3742 timed calls at ~1.28 ms each, cumulative 5.00 s against the test's 5 s
  budget; 14/14 with ``singeli=1``), and mode 298 of ``•internal.Temp``
  (``test/cases/build-specific/test_group_stat.bqn``) is guarded by ``#if TEST_UTILS && SINGELI``.
* **``REPLXX=0``** (the option upstream's own ``shared-o3``/``static-lib``/``wasi`` targets
  force): keeping the optional C++ line-editor submodule out means every artifact depends only on
  ``libc.so`` - a replxx build adds ``NEEDED libc++_shared.so`` - while ``cli/basic.bqn`` and
  ``cli/repl-commands.bqn`` (66 cases) still pass.
* **``FFI=1``** resolves libffi through a Conan-generated ``libffi.pc`` (``PkgConfigDeps`` +
  ``AutotoolsToolchain`` build environment), never through a host prefix.  ``libffi/3.5.2`` is
  published in the ohpcd registry together with an OHOS armv8 binary package.
* **No upstream source file is patched** (``patches: []``): everything is expressed through
  upstream's own make variables.

Upstream's own suites are executed from ``build()`` so that both the local W3 gate and the remote
CI run them: ``test/run.bqn`` over ``test/cases`` in the shipped configuration, plus the two
additional build configurations upstream designed the remaining case files for
(``-DTEST_UTILS`` and ``-DUSZ_32``), plus the ``test/ffi`` golden-output comparisons.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs, can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
)
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# Case files whose assertions upstream only registers in another build configuration.  They are
# executed too - in that configuration (see _run_variant in build()).
TEST_UTILS_CASES = (
    "build-specific/test_range.bqn",      # •internal.Temp mode 203: #if TEST_UTILS
    "build-specific/test_group_stat.bqn",  # mode 298: #if TEST_UTILS && SINGELI
    "fuzz/bitarr-fill.bqn",               # mode 201: #if TEST_UTILS
    "fuzz/bitcpy.bqn",                    # mode 202: #if TEST_UTILS
)
USZ32_CASES = ("usz32.bqn",)             # needs -DUSZ_32 (usz64 builds answer with "Out of memory")

# Upstream expectations that cannot hold for this tag on any platform or configuration.  They are
# still executed and pinned to the exact observed result, so anything else still fails the build;
# the source-level proof is in notes.md and in the PR description.
KNOWN_STALE = {
    "proper-fills.bqn": {
        "summary": "13/15",
        "failing": ["proper-fills.bqn:20", "proper-fills.bqn:21"],
        "reason": "unreachable upstream expectation: sfns.c shift_powm() returns early for "
                  "IA(x)==0 and the expected message exists neither in this tag nor in "
                  "upstream master (see notes.md); reproduced in 4 build configurations",
    },
}

# Signatures that mean "this host was too slow", used **only** to make the failure message tell a
# wall-clock budget miss apart from a code regression.  Nothing here tolerates the failure: the
# build still stops, because silently accepting ``perf.bqn`` would hide a lost fast path.
TIMING_SIGNATURES = {
    "perf.bqn": ("wasn't fast enough",),
}


# The two submodule build inputs (dzaima/cbqnBytecode and mlochbaum/Singeli, at the commits
# pinned by the tag itself) are declared in conandata.yml under ``submodules``, together with the
# checksums verified from two independent machines.  They must stay there - not in this file - so
# the CI pre-download warms them and the source-URL gate covers them; the invariant that keeps
# that safe is enforced by _sources_block() and explained in notes.md item 9.

_OK_RE = re.compile(r"^(?:(?P<label>\S+): )?(?P<passed>\d+) passed!?"
                    r"(?: \((?P<skipped>\d+) skipped test[s]*\))?$")
_FAIL_RE = re.compile(r"^(?P<passed>\d+)/(?P<executed>\d+)"
                      r"(?: \((?P<skipped>\d+) skipped test[s]*\))?$")


def _tally(summary):
    """Interpret one ``test/run.bqn`` summary line into ledger counters."""
    m = _OK_RE.match(summary)
    if m:
        passed = int(m.group("passed"))
        skipped = int(m.group("skipped") or 0)
        return dict(entries=passed + skipped, executed=passed, passed=passed, failed=0,
                    skipped=skipped)
    m = _FAIL_RE.match(summary)
    if m:
        passed = int(m.group("passed"))
        executed = int(m.group("executed"))
        skipped = int(m.group("skipped") or 0)
        return dict(entries=executed + skipped, executed=executed, passed=passed,
                    failed=executed - passed, skipped=skipped)
    return dict(entries=0, executed=0, passed=0, failed=0, skipped=0)


class CbqnConan(ConanFile):
    name = "cbqn"
    version = "0.12.0"
    description = (
        "CBQN is an implementation of the BQN array programming language in C, providing the bqn "
        "interpreter and the embeddable libcbqn library exposed through the public bqnffi.h FFI"
    )
    license = ("LGPL-3.0-only", "GPL-3.0-only", "MPL-2.0")
    homepage = "https://github.com/dzaima/CBQN"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("bqn", "array-programming", "interpreter", "language", "apl", "ffi")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_ffi": [True, False],
        "upstream_tests": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_ffi": True,
        "upstream_tests": True,
    }

    # ------------------------------------------------------------------ graph

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.with_ffi:
            # •ffi is part of the language runtime.  Consumers of libcbqn.so do not need libffi
            # (it is linked in); consumers of libcbqn.a still have to link it.
            self.requires("libffi/3.5.2", visible=not self.options.shared)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cbqn's target_os mapping is only validated for linux-like systems (Linux, OHOS)"
            )
        if str(self.settings.arch) not in ("armv8", "x86_64"):
            raise ConanInvalidConfiguration(
                "cbqn is validated for armv8 (HarmonyOS PC) and x86_64 hosts only"
            )

    def layout(self):
        # CBQN builds in-tree (objects and Singeli-generated code land under ./build/obj inside
        # the source tree), so all make invocations run in the source folder; keep Conan's own
        # build/generators area outside of that tree to avoid clashing with upstream's ./build.
        basic_layout(self, src_folder="src")

    # ------------------------------------------------------------------ source

    def source(self):
        get(
            self,
            **self._sources_block(),
            filename="cbqn-{}-src.tar.gz".format(self.version),
            destination=self.source_folder,
            strip_root=True,
        )
        for entry in self.conan_data["submodules"]:
            get(
                self,
                url=entry["url"],
                sha256=entry["sha256"],
                filename="cbqn-{}-{}.tar.gz".format(self.version, entry["target"]),
                destination=os.path.join(self.source_folder, "build", entry["target"]),
                strip_root=True,
            )

    def _sources_block(self):
        """``sources`` plus a machine guard for the CI pre-download rewriting rule.

        ``ci/conan/build_and_test.sh`` collects every http(s) literal in conandata.yml and
        rewrites them one by one with a plain string replacement.  If one URL happens to be a
        prefix of another (the classic case: a repository-home URL next to its own archive URL),
        the shorter replacement corrupts the longer line and the download then dies inside
        ``source()`` with a malformed ``.../predl_cache/<hash>_repo/archive/<sha>.tar.gz`` path.
        Checking it here turns that into an actionable message instead of a build failure and
        keeps the invariant in code rather than only in the notes.
        """
        urls = []
        for value in [self.conan_data["sources"]["url"]] + [
                entry["url"] for entry in self.conan_data["submodules"]]:
            # a plain string normally; the CI mirror-injection step may have turned it into a
            # fallback list, so compare every element of that too
            urls.extend(value if isinstance(value, (list, tuple)) else [value])
        urls = [str(u) for u in urls]
        for a in urls:
            for b in urls:
                if a != b and b.startswith(a):
                    raise ConanException(
                        "cbqn conandata.yml must not carry URLs that are prefixes of each other "
                        "({} is a prefix of {}): the CI pre-download step replaces URLs by plain "
                        "string matching and would corrupt the longer entry. Keep only the "
                        "download URLs - see notes.md item 9.".format(a, b))
        return self.conan_data["sources"]

    # ------------------------------------------------------------------ generate

    def generate(self):
        AutotoolsToolchain(self).generate()
        if self.options.with_ffi:
            # upstream's build.bqn asks pkg-config for the libffi cflags/libs
            PkgConfigDeps(self).generate()

    # ------------------------------------------------------------------ build

    def _cc(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c")
        if not cc:
            raise ConanException(
                "cbqn needs tools.build:compiler_executables:c; upstream's default 'cc' does "
                "not exist on OHOS"
            )
        return cc

    def _cxx(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("cpp") or self._cc()

    def _target_arch(self):
        return {"armv8": "aarch64", "x86_64": "x86-64"}.get(str(self.settings.arch), "generic")

    def _target_os(self):
        # Upstream's build.bqn only knows ``linux``/``macos``/``windows``; OHOS is a linux-like
        # system for it (musl + ELF + POSIX), so both map to the same upstream branch.  Making
        # the mapping explicit keeps the R32 "OHOS must not be left out" question answerable
        # from the code instead of only from validate().
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cbqn has no upstream target_os mapping for {}".format(self.settings.os))
        return "linux"

    def _make_flags(self, output=None, usz=None, soname=None):
        flags = [
            "CC={}".format(self._cc()),
            "CXX={}".format(self._cxx()),
            "REPLXX=0",
            "FFI={}".format(1 if self.options.with_ffi else 0),
            "singeli=1",
            "target_arch={}".format(self._target_arch()),
            "target_os={}".format(self._target_os()),
            "version={}".format(self.version),
            "nogit=1",
            "j={}".format(max(1, min(4, build_jobs(self) or 1))),
        ]
        if output:
            flags.append("OUTPUT={}".format(output))
        if usz:
            flags.append("usz={}".format(usz))
        if soname:
            # Upstream links with plain ``-shared`` and no SONAME, which the CI L5 gate rejects
            # ("下游链接器无法按 SONAME 寻址").  ``lf`` is upstream's own "extra linking flags"
            # variable (ALL_LD_FLAGS = LDFLAGS lf i_lf i_PIE i_LIBS_LD), so this stays a
            # build-argument level fix without touching any source file.
            flags.append("lf=-Wl,-soname,{}".format(soname))
        return flags

    def _bootstrap_flags(self):
        # ``make for-build`` goes through build/makefile's makefile-only path, which refuses
        # ``singeli=1`` ("makefile-only builds don't support Singeli") and needs neither libffi
        # nor a C++ compiler; the only thing it *does* need is an explicit CC, because its recipe
        # hard-codes i_CC=cc and OHOS has no bare cc.
        return ["CC={}".format(self._cc()), "REPLXX=0"]

    def _make(self, target, flags=None, **flag_kwargs):
        if flags is None:
            flags = self._make_flags(**flag_kwargs)
        self.run(
            "make {} {}".format(target, " ".join(flags)),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def build(self):
        apply_conandata_patches(self)
        # 1) bootstrap interpreter (pure C: no libffi, no C++) - needed by every other target
        self._make("for-build", flags=self._bootstrap_flags())
        # 2) shipped configuration: interpreter + library
        self._make("o3")
        if self.options.shared:
            # Upstream's ``-shared`` link has no SONAME, which the CI L5 gate rejects
            self._make("shared-o3", soname="libcbqn.so")
        else:
            self._make("static-lib")
        # 3) upstream suites
        if self.options.upstream_tests:
            self._run_upstream_suites()
        else:
            self.output.info("upstream_tests=False: upstream suites skipped by option")

    # ------------------------------------------------ upstream test integration

    def _case_files(self):
        """Upstream's own inventory: test/cases/**.bqn minus the Windows-only directory.

        ``test/run.bqn`` resolves case names relative to ``test/cases`` and its CLI helpers
        need ``bin=<interpreter>``; ``test/cases/windows/`` is guarded by its location -
        those 62 assertions encode Windows path semantics (drive letters, backslash
        separators) and are not applicable to a Linux-like port (documented in notes.md).
        """
        root = os.path.join(self.source_folder, "test", "cases")
        cases = []
        for current, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d != "windows")
            for name in sorted(files):
                if name.endswith(".bqn"):
                    rel = os.path.relpath(os.path.join(current, name), root)
                    cases.append(rel.replace(os.sep, "/"))
        return sorted(cases)

    def _run_case(self, runner, case, ledger):
        """Execute one case file through upstream's own runner and record its tally."""
        args = [runner, "test/run.bqn", "slow"]
        if case.startswith("cli/"):
            # cli/*.bqn drive the interpreter end-to-end; without bin= all 66 cases self-skip
            args.append("bin={}".format(runner))
        args.append('"{}"'.format(case))
        log = os.path.join(self.build_folder, "upstream-tests",
                           case.replace("/", "_") + ".log")
        self.run(
            "mkdir -p '{}'; {{ {} > '{}' 2>&1; echo \"rc=$?\" >> '{}'; }}".format(
                os.path.dirname(log), " ".join(args), log, log),
            cwd=self.source_folder,
            env="conanbuild",
        )
        text = load(self, log) or ""
        rc = ""
        summary = ""
        failures = []
        for line in (l.strip() for l in text.splitlines()):
            if line.startswith("rc="):
                rc = line[3:]
            elif _OK_RE.match(line) or _FAIL_RE.match(line):
                summary = line
            elif ": " in line and ".bqn:" in line:
                failures.append(line.split(":")[0].rstrip() + ":" + line.split(":")[1].strip().split(" ")[0])
        known = KNOWN_STALE.get(case)
        if known is None:
            # a fully green case prints "<case>: N passed!" optionally followed by the
            # runner's own "(M skipped tests)" note, and exits 0
            if rc != "0" or not _OK_RE.match(summary):
                hint = ""
                for signature in TIMING_SIGNATURES.get(case, ()):
                    if signature in text:
                        hint = (
                            "\n\nNOTE: this failure is upstream's wall-clock budget "
                            "({!r}). It is NOT tolerated here, but it is distinguishable from a "
                            "code regression: the shipped configuration builds with singeli=1, "
                            "which is what installs the amortized \u234b fast path this case "
                            "measures. Reproduce with `./BQN test/run.bqn slow perf.bqn` and "
                            "compare against the reference device log in notes.md before "
                            "touching the recipe.".format(signature))
                        break
                raise ConanException("cbqn upstream case {} failed (rc={}): {}\n{}{}".format(
                    case, rc, summary, text[-2500:], hint))
        else:
            # known-stale file: still executed, but pinned to the exact documented outcome so a
            # change in upstream behaviour breaks the build instead of being silently accepted
            if summary != known["summary"] or sorted(set(failures)) != sorted(known["failing"]):
                raise ConanException(
                    "cbqn {}: expected the documented upstream-stale outcome {} with {} but saw "
                    "{} with {}; log tail: {}".format(case, known["summary"],
                                                      sorted(known["failing"]), summary,
                                                      sorted(set(failures)), text[-2000:]))
            self.output.warning("UPSTREAM KNOWN-STALE {}: {} ({})".format(
                case, summary, known["reason"]))
        tally = _tally(summary)
        ledger["files"] += 1
        for key in ("entries", "executed", "passed", "skipped"):
            ledger[key] += tally[key]
        ledger["failed"] += tally["failed"]
        self.output.info("UPSTREAM CASE {} {} entries={} executed={} passed={} skipped={}".format(
            runner, case, tally["entries"], tally["executed"], tally["passed"],
            tally["skipped"]))

    def _run_upstream_suites(self):
        if not can_run(self):
            # Never let a cross-build report the upstream ledger it did not produce: the suites
            # run the target binary, so a machine that cannot execute it has no evidence to
            # publish.  Fail loudly; opting out must be an explicit option, not a silent skip.
            raise ConanInvalidConfiguration(
                "cbqn executes its upstream suites from build(), which needs to run the target "
                "binary; this build cannot (can_run() is false). Build natively on the OHOS "
                "worker, or opt out explicitly with -o cbqn/*:upstream_tests=False"
            )
        ledger = dict(files=0, entries=0, executed=0, passed=0, failed=0, skipped=0)
        gated = set(TEST_UTILS_CASES) | set(USZ32_CASES)
        for case in self._case_files():
            if case not in gated:
                self._run_case("./BQN", case, ledger)

        # upstream registers these assertions only under other build configurations
        # (TEST_UTILS := DEBUG in src/builtins/internal.c; mode 298 needs SINGELI too;
        #  usz32.bqn needs -DUSZ_32), so they are executed in exactly those variants.
        self._make("debug", output="cbqn-debug")
        for case in TEST_UTILS_CASES:
            self._run_case("./cbqn-debug", case, ledger)
        self._make("o3", output="cbqn-usz32", usz=32)
        for case in USZ32_CASES:
            self._run_case("./cbqn-usz32", case, ledger)

        self.output.info(
            "UPSTREAM LEDGER cbqn/{} files={} entries={} executed={} passed={} failed={} "
            "skipped_by_upstream_flags={}".format(
                self.version, ledger["files"], ledger["entries"], ledger["executed"],
                ledger["passed"], ledger["failed"], ledger["skipped"]))
        if ledger["entries"] != ledger["passed"] + ledger["failed"] + ledger["skipped"]:
            raise ConanException("cbqn upstream ledger does not add up: {}".format(ledger))

        if self.options.shared:
            # upstream's FFI sub-suite: golden output comparisons for the public C ABI
            cc = self._cc()
            # ``clean`` is idempotent and legitimately fails on a first run (nothing built yet),
            # so only its exit code is ignored; the real gate is the next command
            self.run(
                "make -C test/ffi CC={} clean >/dev/null 2>&1 || true".format(cc),
                cwd=self.source_folder,
                env="conanbuild",
            )
            log = os.path.join(self.build_folder, "upstream-ffi.log")
            self.run(
                "make -C test/ffi CC={} > '{}' 2>&1".format(cc, log),
                cwd=self.source_folder,
                env="conanbuild",
            )
            # report what the tool actually printed rather than a fixed sentence
            identical = len(re.findall(r"are identical$", load(self, log) or "", re.MULTILINE))
            if identical != 3:
                raise ConanException(
                    "cbqn test/ffi expected 3 identical golden comparisons, saw {}: {}".format(
                        identical, (load(self, log) or "")[-1500:]))
            self.output.info("UPSTREAM FFI GOLDEN SUITE: {}/3 targets byte-identical".format(
                identical))

    # ------------------------------------------------------------------ package

    def package(self):
        copy(self, "bqnffi.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "libcbqn.so", self.source_folder,
                 os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libcbqn.a", self.source_folder,
                 os.path.join(self.package_folder, "lib"))
        # Upstream's install rule is ``cp -f BQN $(PREFIX)/bin/bqn``.  A case-only rename cannot
        # express that here: on HMDFS ``BQN`` and ``bqn`` are the same directory entry, so
        # ``os.rename`` is a silent no-op and ``shutil.copy2`` inside one directory raises
        # SameFileError (both probed on the device).  Copying into the fresh ``bin`` directory
        # does create the documented lowercase name.
        interpreter = os.path.join(self.source_folder, "BQN")
        if os.path.isfile(interpreter):
            installed = os.path.join(self.package_folder, "bin", "bqn")
            os.makedirs(os.path.dirname(installed), exist_ok=True)
            shutil.copy2(interpreter, installed)
            os.chmod(installed, 0o755)
        copy(self, "LICENSE-*", os.path.join(self.source_folder, "licenses"),
             os.path.join(self.package_folder, "licenses"))
        for required in ("bin/bqn", "include/bqnffi.h"):
            if not os.path.isfile(os.path.join(self.package_folder, required)):
                raise ConanException("cbqn package is missing {}".format(required))
        if self.options.shared and not os.path.isfile(
                os.path.join(self.package_folder, "lib", "libcbqn.so")):
            raise ConanException("cbqn package is missing lib/libcbqn.so")

    def package_info(self):
        self.cpp_info.libs = ["cbqn"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "cbqn")
        self.cpp_info.set_property("cmake_target_name", "cbqn::cbqn")
        self.cpp_info.set_property("pkg_config_name", "cbqn")
        if not self.options.shared:
            # libcbqn.a is not self-contained (libffi + libm/libdl/libpthread)
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
