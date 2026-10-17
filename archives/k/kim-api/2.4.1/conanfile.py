#!/usr/bin/env python3
"""Conan recipe for kim-api 2.4.1 on native HarmonyOS PC (aarch64).

kim-api is the system-level C/C++/Fortran library of the Open Knowledgebase
of Interatomic Models (OpenKIM). Build system: CMake (minimum 3.10).

Key points:
- Upstream ``project()`` enables the C, C++ AND Fortran languages, so a
  Fortran compiler is mandatory. HarmonyOS ships no Fortran compiler; this
  recipe uses ``tool_requires("flang-ohos/20.1.0")`` (the LLVM Flang
  toolchain already published for openblas/acepack) and points
  ``CMAKE_Fortran_COMPILER`` at its ``bin/flang``.
- flang-ohos is a frontend-only package (no OHOS CRT/sysroot/libunwind/
  compiler-rt); a bare ``bin/flang`` link fails with Scrt1.o/crti.o/
  libunwind/libclang_rt.builtins errors. Following the lapack/3.12.1 and
  DRAFT-flang-minimal-runtime-link-contract precedent, generate() injects
  ``--target/--sysroot/-resource-dir`` into ``CMAKE_Fortran_FLAGS``,
  Fortran-runtime link flags into EXE/SHARED/MODULE linker flags, and sets
  ``CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`` so the Fortran compiler
  check compiles without linking an executable. build() exports
  LD_LIBRARY_PATH for the flang/lld runtime.
- ``KIM_API_BUILD_EXAMPLES`` stays ON on purpose: the examples host the
  entire upstream ctest suite (46 ``ctest -N`` registrations on the true
  machine: 33 ``add_kim_api_test()`` runs in
  ``examples/simulators/CMakeLists.txt``: 3 collections-example runs +
  3 ex_test simulators x 9 models + 3 simulator-model-example runs, 6 of
  them WILL_FAIL-expected-fail, plus 13 ``shared_library_test_*``
  item-build checks from the model-driver/portable-model/
  simulator-model item helpers). With OFF, ``ctest -N`` discovers 0 and
  the preflight evidence gate rejects ``no_tests`` (2026-09-29
  incomplete: "清单表明上游存在测试"). The 2026-09-29 SIGKILL (Signal 9)
  round predates the Fortran sysroot/runtime-link fix; the follow-up
  round built the same examples graph to 93%, so the suite is attempted
  with hmbs jobs=1 and any shortfall is reported via gaps, not hidden.
- source() strips hardcoded ``-std=gnu`` from example/item CMake files:
  flang-new (flang-ohos/20.1.0, LLVM 20) accepts only ``-std=f2018``
  ("error: Only -std=f2018 is allowed currently"), while upstream pins
  ``target_compile_options(... PRIVATE "-std=gnu")`` on the
  simulator-model-example-fortran target (a gfortran flag applied without
  a compiler probe). Removal is a no-op for gfortran (its default is GNU
  mode), so Linux behavior is unchanged (Spack nvhpc precedent).
- Fortran runtime conformance: upstream library modules assign a
  ``(1:n)`` pointer section to a whole caller array (4 sites in
  ``fortran/include/kim_collections_module.f90`` and
  ``fortran/include/kim_model_module.f90``), which is
  non-conforming when the caller buffer is larger; gfortran
  release builds tolerate it while flang-new aborts (2026-09-30
  preflight: ``Run_collections-example-fortran`` died at
  ``kim_collections_module.f90:638`` with Signal 6).
  ``source()`` rewrites each LHS as an explicit ``(1:n)`` section
  (exact-match, 4-hit assertion); every site is size-guarded, so
  gfortran/Linux behavior is unchanged.
- Upstream tests run in ``build()`` via a deterministic ctest runner:
  ``ctest -N`` for discovered, per-line ``Test #N ... Passed|Failed``
  parsing for executed/passed/failed (single source, no arithmetic
  patch-ups), ``Testing/Temporary/LastTest.log`` only as a consistency
  witness. Build-tree simulator executables are OHOS self-signed before
  ctest (HongMeng kills unsigned execs); the result payload is persisted
  to ``res/hmbs_upstream.json`` for cache-hit re-emit (zydis precedent).
- Not a system-name library, so the shared build is kept (no R26 static
  forcing). Headers install to ``include/kim-api``; ``package_info()``
  exposes both ``include`` and ``include/kim-api``.
"""

import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, export_conandata_patches, get


class KimApiConan(ConanFile):
    name = "kim-api"
    version = "2.4.1"
    description = (
        "An Application Programming Interface (API) for the Knowledgebase "
        "of Interatomic Models (KIM)"
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://openkim.org/kim-api"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("kim", "interatomic-models", "molecular-simulation", "ohos")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kim-api supports Linux and OHOS, not {self.settings.os}"
            )

    def build_requirements(self):
        # Upstream builds C, C++ and Fortran sources; OHOS provides no
        # Fortran compiler, flang-ohos fills that gap (same as acepack).
        self.tool_requires("flang-ohos/20.1.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # flang-new (flang-ohos/20.1.0, LLVM 20) rejects every Fortran
        # -std value except f2018 ("error: Only -std=f2018 is allowed
        # currently"). Upstream hardcodes
        # target_compile_options(${PROJECT_NAME}-fortran PRIVATE "-std=gnu")
        # in examples/simulators/simulator-model-example/CMakeLists.txt
        # (a gfortran GNU-extensions flag, applied without a compiler probe,
        # so DefaultCompilerFlags' Failed checks cannot filter it). The
        # 2026-09-29 preflight died at 165/272 on exactly that flag while
        # preprocessing simulator-model-example-fortran.f90. Spack's nvhpc
        # precedent simply strips "-std=gnu"; gfortran's default is GNU
        # mode, so removal is a no-op there and Linux behavior is unchanged.
        # Unconditional (not OHOS-gated): the conan source cache is shared
        # across configurations, so an OS-conditional patch would be
        # order-dependent. A tree-wide sweep covers the one known file plus
        # any other example/item CMake file hardcoding the same flag; each
        # hit is logged for evidence.
        patched = 0
        for root, _ds, files in os.walk(self.source_folder):
            for fn in files:
                if fn != "CMakeLists.txt" and not fn.endswith(".cmake"):
                    continue
                path = os.path.join(root, fn)
                try:
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as f:
                        text = f.read()
                except OSError:
                    continue
                if "-std=gnu" not in text:
                    continue
                # Remove the whole target_compile_options statement when it
                # carries the flag (avoids leaving PRIVATE "" empty args);
                # fall back to a bare token strip for any other context.
                # NOTE: the inserted comment must NOT contain the literal
                # "-std=gnu" token, otherwise the fallback replace below
                # would eat it (cosmetic only, but keep logs clean).
                new_lines = []
                line_hits = 0
                for line in text.splitlines(keepends=True):
                    if "target_compile_options" in line and "-std=gnu" in line:
                        new_lines.append(
                            "# kim-api OHOS: GNU std flag stripped for "
                            "flang-new (only f2018 allowed)\n"
                        )
                        line_hits += 1
                    else:
                        new_lines.append(line)
                new_text = "".join(new_lines)
                if "-std=gnu" in new_text:
                    new_text = new_text.replace("-std=gnu", "")
                if new_text != text:
                    try:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(new_text)
                    except OSError as e:
                        self.output.warning(
                            f"kim-api: cannot patch {path}: {e}")
                        continue
                    rel = os.path.relpath(path, self.source_folder)
                    self.output.info(
                        f"kim-api: stripped -std=gnu in {rel} "
                        f"(lines={line_hits})")
                    patched += 1
        self.output.info(f"kim-api: -std=gnu strip hits={patched}")

        # flang-new runtime conformance fix (2026-09-30 preflight: 45/46,
        # only Run_collections-example-fortran failed with "fatal Fortran
        # runtime error(.../kim_collections_module.f90:638): Assign:
        # mismatching element counts in array assignment (to 10000,
        # from 39)", Signal 6). Upstream Fortran library code assigns a
        # (1:n) pointer section to a whole caller array, which is
        # non-conforming when the caller buffer is larger; gfortran
        # release builds silently write the leading elements while
        # flang-new (flang-ohos/20.1.0, LLVM 20) aborts. Every site is
        # guarded by an explicit size check (short buffer -> ierr=1 and
        # return), so spelling the LHS as an explicit (1:n) section is
        # semantics-preserving on gfortran/Linux and aborts nowhere.
        # Four identical instances in two shipped library modules
        # (upstream v2.4.2 leaves them unchanged); exact-match rewrites
        # with a total hit-count assertion so layout drift fails loudly
        # instead of shipping a partial fix. Unconditional, same
        # shared-source-cache rationale as the -std=gnu sweep above.
        _conform_rewrites = [
            ("      file_raw_data = "
             "file_raw_data_fpointer(1:file_length)",
             "      file_raw_data(1:file_length) = "
             "file_raw_data_fpointer(1:file_length)"),
            ("      cutoffs = "
             "cutoffs_fpointer(1:number_of_neighbor_lists)",
             "      cutoffs(1:number_of_neighbor_lists) = "
             "cutoffs_fpointer(1:number_of_neighbor_lists)"),
            ("      model_will_not_request_neighbors_of_noncontributing"
             "_particles = &",
             "      model_will_not_request_neighbors_of_noncontributing"
             "_particles(1:number_of_neighbor_lists) = &"),
        ]
        _conform_hits = 0
        for _rel in (os.path.join("fortran", "include",
                                  "kim_collections_module.f90"),
                     os.path.join("fortran", "include",
                                  "kim_model_module.f90")):
            _path = os.path.join(self.source_folder, _rel)
            try:
                with open(_path, "r", encoding="utf-8",
                          errors="replace") as _f:
                    _text = _f.read()
            except OSError as _e:
                raise ConanException(
                    f"kim-api: cannot read {_rel} for Fortran conformance "
                    f"fix: {_e}")
            _new_text = _text
            for _old, _new_line in _conform_rewrites:
                _c = _new_text.count(_old)
                if _c:
                    _new_text = _new_text.replace(_old, _new_line)
                    _conform_hits += _c
                    self.output.info(
                        f"kim-api: Fortran conformance rewrite x{_c} "
                        f"in {_rel}")
            if _new_text != _text:
                with open(_path, "w", encoding="utf-8") as _f:
                    _f.write(_new_text)
        # v2.4.1 has exactly 4 instances (2 in the collections module, 2
        # in the model module); anything else means the upstream layout
        # moved and this fix must be re-audited, not silently skipped.
        if _conform_hits != 4:
            raise ConanException(
                "kim-api: Fortran conformance rewrite hit "
                f"{_conform_hits}/4; upstream layout changed, re-audit")
        self.output.info(
            f"kim-api: Fortran conformance rewrites total={_conform_hits}")

    def _probe_compiler(self, cc):
        """True if cc exists and executes --version successfully."""
        if not cc:
            return False
        p = cc.strip().strip('"').strip("'").split(" ")[0]
        if not p:
            return False
        exe = p if os.path.isfile(p) else shutil.which(p)
        if not exe:
            return False
        try:
            r = subprocess.run(
                [exe, "--version"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return r.returncode == 0
        except Exception:
            return False

    def _select_compilers(self):
        """Pick working C/C++ compilers, falling back from dead conf paths.

        metashell/5.0.0 precedent: the profile compiler
        (/data/service/hnp/bin/clang{,++}) can be a dead path inside the
        preflight container (present but unable to compile anything). Probe
        it; only when it is missing or fails --version, fall back to the
        PATH-discovered clang/clang++ (HMBS prepends the real toolchain
        dirs). Returns (c, cxx, fell_back).
        """
        try:
            conf = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            conf = {}
        conf = conf if isinstance(conf, dict) else {}
        c_conf = conf.get("c")
        cxx_conf = conf.get("cpp")
        c_path = shutil.which("clang")
        cxx_path = shutil.which("clang++")
        c = c_conf
        cxx = cxx_conf
        fell_back = False
        if not self._probe_compiler(c_conf):
            if c_path and self._probe_compiler(c_path):
                self.output.warning(
                    "kim-api: configured C compiler "
                    f"{c_conf!r} is dead, falling back to PATH {c_path}"
                )
                c = c_path
                fell_back = True
            else:
                self.output.warning(
                    f"kim-api: configured C compiler {c_conf!r} is dead "
                    f"and no working PATH clang ({c_path!r}); keeping config"
                )
        if not self._probe_compiler(cxx_conf):
            if cxx_path and self._probe_compiler(cxx_path):
                self.output.warning(
                    "kim-api: configured C++ compiler "
                    f"{cxx_conf!r} is dead, falling back to PATH {cxx_path}"
                )
                cxx = cxx_path
                fell_back = True
            else:
                self.output.warning(
                    f"kim-api: configured C++ compiler {cxx_conf!r} is dead "
                    f"and no working PATH clang++ ({cxx_path!r}); keeping config"
                )
        if fell_back:
            self.output.info(f"kim-api: compilers selected C={c} CXX={cxx}")
        return c, cxx, fell_back

    def _dump_cmake_logs(self):
        """Emit CMake configure failure forensics into the conan output."""
        patterns = (
            "**/CMakeFiles/CMakeError.log",
            "**/CMakeFiles/CMakeOutput.log",
        )
        for pat in patterns:
            for log in sorted(glob.glob(os.path.join(self.build_folder, pat))):
                try:
                    with open(log, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.read().splitlines()
                except OSError as e:
                    self.output.error(f"kim-api: cannot read {log}: {e}")
                    continue
                tail = lines[-60:] if len(lines) > 60 else lines
                self.output.error(
                    f"kim-api: --- {log} ({len(lines)} lines, tail) ---"
                )
                for line in tail:
                    self.output.error(f"kim-api: {line.rstrip()}"[:2000])

    def _is_valid_sdk_llvm(self, llvm):
        """True only for a genuine OHOS SDK llvm dir.

        A bare LLVM install (e.g. the harmonybrew cellar top dir, which also
        ships bin/clang + lib/clang) is NOT enough: the OHOS layout markers
        (ohos/native/llvm in the path, a sibling sysroot, or the
        aarch64-linux-ohos lib dir) must be present. The previous round
        accepted the brew cellar root and injected its bogus -L paths into
        every link line (observed: "OHOS SDK llvm at .../Cellar/ohos-sdk/
        26.0.0.18_1" followed by C/CXX compiler checks failing).
        """
        if not llvm or not os.path.isdir(llvm):
            return False
        if not os.path.isfile(os.path.join(llvm, "bin", "clang")):
            return False
        if "ohos/native/llvm" in llvm.replace("\\", "/"):
            return True
        parent = os.path.dirname(os.path.normpath(llvm))
        if os.path.isdir(os.path.join(parent, "sysroot")):
            return True
        if os.path.isdir(os.path.join(llvm, "lib", "aarch64-linux-ohos")):
            return True
        return False

    def _expand_sdk_candidate(self, cand):
        """Resolve a candidate root to a valid SDK llvm dir, or None.

        SDK roots discovered via compiler paths may point at a wrapper dir
        (e.g. the harmonybrew cellar root) whose real llvm tree lives nested
        at <root>/ohos/native/llvm (harmbrew ohos layout) or
        <root>/native/llvm (harmonybrew cellar layout:
        .../Cellar/ohos-sdk/<ver>/native/llvm, observed on the 2026-09-29
        preflight via -L.../Cellar/ohos-sdk/26.0.0.18_1/native/llvm/...).
        Prefer the nested trees, fall back to the candidate itself; every
        candidate must pass _is_valid_sdk_llvm.
        """
        if not cand:
            return None
        nested_ohos = os.path.join(cand, "ohos", "native", "llvm")
        nested_native = os.path.join(cand, "native", "llvm")
        for path in (nested_ohos, nested_native, cand):
            if self._is_valid_sdk_llvm(path):
                return path
        return None

    def _derive_llvm_from_path(self, path):
        """Derive an OHOS SDK llvm dir from a compiler/file path, or None."""
        if not path:
            return None
        p = path.strip().strip('"').strip("'")
        if not p:
            return None
        # Resolve symlinks (e.g. /data/service/hnp/bin/clang -> SDK llvm/bin).
        try:
            real = os.path.realpath(p)
        except OSError:
            real = p
        cands = []
        # Direct hit: path already contains native/llvm with or without the
        # intermediate ohos/ segment (harmonybrew cellar omits ohos/).
        for candidate in (real, p):
            for marker in (os.path.join("native", "llvm"),
                            os.path.join("ohos", "native", "llvm")):
                idx = candidate.find(marker)
                if idx != -1:
                    cands.append(candidate[: idx + len(marker)])
        # Layout hit: <llvm>/bin/<compiler> -> parent of bin is llvm.
        bindir = os.path.dirname(real)
        if os.path.basename(bindir) == "bin":
            cands.append(os.path.dirname(bindir))
        # The compiler dir itself may be an SDK wrapper root (cellar).
        cands.append(os.path.dirname(real))
        for cand in cands:
            llvm = self._expand_sdk_candidate(cand)
            if llvm:
                return llvm
        return None

    def _ohos_sdk_llvm(self):
        """Locate a validated OHOS SDK llvm dir, or None.

        Round 2 (strict): filesystem globs for genuine SDK trees come first
        (authoritative layout), compiler-derived candidates only count after
        OHOS-layout validation, and every rejection is recorded so the
        generate() warning shows what was probed. Unvalidated fallbacks
        (e.g. brew cellar top dir) previously poisoned all link lines.
        """
        tried = []
        rejected = []
        globs = [
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm",
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm",
            os.path.join(
                os.path.expanduser("~"),
                ".harmonybrew/Cellar/ohos-sdk/*/ohos/native/llvm",
            ),
            "/storage/Users/currentUser/.harmonybrew/Cellar/ohos-sdk/*/ohos/native/llvm",
            "/opt/ohos-sdk/*/ohos/native/llvm",
            # Harmonybrew cellar layout without the ohos/ segment
            # (observed 2026-09-29: .../Cellar/ohos-sdk/26.0.0.18_1/native/llvm
            # in the flang -L lines while the ohos/ globs stayed empty).
            os.path.join(
                os.path.expanduser("~"),
                ".harmonybrew/Cellar/ohos-sdk/*/native/llvm",
            ),
            "/storage/Users/currentUser/.harmonybrew/Cellar/ohos-sdk/*/native/llvm",
            "/opt/ohos-sdk/*/native/llvm",
        ]
        for pat in globs:
            tried.append(f"glob:{pat}")
            for cand in sorted(glob.glob(pat)):
                if self._is_valid_sdk_llvm(cand):
                    return cand
                rejected.append(cand)
        # conan profile compiler (tools.build:compiler_executables).
        try:
            conf = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            conf = {}
        for key in ("c", "cpp"):
            cc = (conf or {}).get(key) if isinstance(conf, dict) else None
            if cc:
                tried.append(f"conf:{cc}")
                llvm = self._derive_llvm_from_path(cc)
                if llvm:
                    return llvm
                rejected.append(f"conf-derived:{cc}")
        # clang on PATH (HMBS prepends real toolchain dirs).
        for name in ("clang", "clang++"):
            found = shutil.which(name)
            if found:
                tried.append(f"PATH:{found}")
                llvm = self._derive_llvm_from_path(found)
                if llvm:
                    return llvm
                rejected.append(f"PATH-derived:{found}")
        # CC/CXX env.
        for env_key in ("CC", "CXX"):
            val = (os.environ.get(env_key) or "").strip().split(" ")[0]
            if val:
                tried.append(f"env:{env_key}={val}")
                llvm = self._derive_llvm_from_path(val)
                if llvm:
                    return llvm
                which = shutil.which(val)
                if which and which != val:
                    llvm = self._derive_llvm_from_path(which)
                    if llvm:
                        return llvm
                rejected.append(f"env-derived:{env_key}={val}")
        self._sdk_search_tried = tried
        self._sdk_search_rejected = rejected
        return None

    def _ohos_sdk_resdir(self, sdk_llvm):
        """Newest lib/clang/<ver> under the SDK llvm dir, or None."""
        cands = sorted(glob.glob(os.path.join(sdk_llvm, "lib", "clang", "*")))
        dirs = [c for c in cands if os.path.isdir(c)]
        if dirs:
            return dirs[-1]
        legacy = os.path.join(sdk_llvm, "lib", "clang", "15.0.4")
        return legacy if os.path.isdir(legacy) else None

    def _derive_sysroot_from_known(self, resdir, lib_dirs, exe_real=""):
        """Derive an OHOS sysroot sibling from known SDK paths, or None.

        2026-09-29 preflight: clang --print-sysroot was empty, so the
        clang-query branch emitted Fortran flags with --target/--resource-dir
        but WITHOUT --sysroot; every Fortran executable link then failed
        with ``ld.lld: cannot open Scrt1.o/crti.o/crtn.o``. Any path
        containing ``native/llvm`` implies a sibling ``native/sysroot``
        (harmonybrew cellar: .../Cellar/ohos-sdk/<ver>/native/llvm ->
        .../native/sysroot); accept it only when the directory exists and
        carries usr/lib (the CRT home). Purely additive: never invents a
        sysroot, returns None when nothing validates.
        """
        cands = []
        for base in ([resdir] if resdir else []) + list(lib_dirs or []) + (
            [exe_real] if exe_real else []
        ):
            if not base:
                continue
            norm = str(base).replace("\\", "/")
            for marker in ("native/llvm", "ohos/native/llvm"):
                idx = norm.find(marker)
                if idx == -1:
                    continue
                # Sibling sysroot: <prefix>/native/sysroot.
                prefix = norm[:idx]
                cands.append(os.path.join(prefix, "native", "sysroot"))
        for cand in cands:
            try:
                if os.path.isdir(cand) and os.path.isdir(
                    os.path.join(cand, "usr", "lib")
                ):
                    return cand
            except Exception:
                continue
            try:
                if os.path.isdir(cand):
                    # Accept bare sysroot dirs too (evidence-logged by caller).
                    return cand
            except Exception:
                continue
        return None

    def _query_clang_sdk(self, c_compiler):
        """Derive OHOS sysroot/resource-dir/lib dirs from working clang.

        The preflight container's working clang (harmonybrew bin/clang)
        carries its sysroot implicitly, so C links succeed while the bare
        flang frontend fails with Scrt1.o/crti.o/libunwind/builtins
        errors. Query that clang directly (--print-sysroot,
        --print-resource-dir, -print-search-dirs) instead of relying
        solely on the /data/service/hnp glob layout, which is absent in
        some preflight containers (2026-09-29 round: all globs empty,
        only conf/PATH-derived candidates rejected). Returns a dict with
        sysroot/resdir/lib_dirs (any may be missing); never raises.
        """
        found = {"sysroot": None, "resdir": None, "lib_dirs": []}
        exe = None
        try:
            cand = (c_compiler or "").strip().strip('"').strip("'").split(" ")[0]
            if cand:
                exe = cand if os.path.isfile(cand) else shutil.which(cand)
                if exe is None and os.path.isfile(cand):
                    exe = cand
        except Exception:
            exe = None
        if not exe:
            exe = shutil.which("clang")
        if not exe or not os.path.isfile(exe):
            self.output.info("kim-api: clang query skipped (no clang exe)")
            return found
        try:
            real = os.path.realpath(exe)
        except OSError:
            real = exe
        self.output.info(f"kim-api: clang query exe={exe} real={real}")

        def _run(args):
            try:
                r = subprocess.run(
                    [exe] + args,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if r.returncode == 0:
                    return (r.stdout or "").strip()
            except Exception as e:
                self.output.info(f"kim-api: clang {' '.join(args)} failed: {e}")
            return ""

        sysroot = _run(["--print-sysroot"])
        if sysroot and os.path.isdir(sysroot):
            found["sysroot"] = sysroot
        self.output.info(f"kim-api: clang --print-sysroot={sysroot!r}")
        resdir = _run(["--print-resource-dir"])
        if resdir and os.path.isdir(resdir):
            found["resdir"] = resdir
        self.output.info(f"kim-api: clang --print-resource-dir={resdir!r}")
        search = _run(["-print-search-dirs"])
        lib_dirs = []
        for line in search.splitlines():
            if line.strip().startswith("libraries:"):
                _, _, rest = line.partition("=")
                for token in rest.replace(";", ":").split(":"):
                    t = token.strip().strip('"').strip("'")
                    if not t:
                        continue
                    # Strip leading '=' that clang prepends.
                    t = t.lstrip("=")
                    if os.path.isdir(t) and t not in lib_dirs:
                        lib_dirs.append(t)
        self.output.info(
            f"kim-api: clang search lib dirs ({len(lib_dirs)}): "
            f"{'; '.join(lib_dirs[:12])}"
        )
        # Climb from the real compiler path: <root>/bin/clang ->
        # <root>/sysroot or <root>/ohos/native/llvm sibling layouts.
        try:
            cur = os.path.dirname(real)
            for _ in range(5):
                for cand_dir in (
                    os.path.join(cur, "sysroot"),
                    os.path.join(cur, "ohos", "native", "llvm"),
                ):
                    if os.path.isdir(cand_dir) and "sysroot" in cand_dir:
                        if found["sysroot"] is None:
                            found["sysroot"] = cand_dir
                    if (
                        cand_dir.endswith(os.path.join("ohos", "native", "llvm"))
                        and found["resdir"] is None
                    ):
                        rd = self._ohos_sdk_resdir(cand_dir)
                        if rd:
                            found["resdir"] = rd
                # Any Scrt1.o-bearing dir near the toolchain is a lib dir.
                for pat in (
                    os.path.join(cur, "sysroot", "usr", "lib", "aarch64-linux-ohos"),
                    os.path.join(cur, "sysroot", "usr", "lib"),
                    os.path.join(cur, "lib", "aarch64-linux-ohos"),
                ):
                    if os.path.isdir(pat) and pat not in lib_dirs:
                        lib_dirs.append(pat)
                parent = os.path.dirname(cur)
                if parent == cur:
                    break
                cur = parent
        except Exception as e:
            self.output.info(f"kim-api: toolchain climb failed: {e}")
        # If the clang resource dir carries the OHOS builtins/lib, expose
        # its lib subdirs as link dirs (fixes libclang_rt.builtins.a +
        # libunwind.a not found when flang defaults to its own empty
        # lib/clang/20 tree).
        if found["resdir"] and os.path.isdir(found["resdir"]):
            for sub in (
                os.path.join(found["resdir"], "lib", "aarch64-linux-ohos"),
                os.path.join(found["resdir"], "lib", "linux"),
                os.path.join(found["resdir"], "lib"),
            ):
                if os.path.isdir(sub) and sub not in lib_dirs:
                    lib_dirs.append(sub)
        if found["sysroot"] and os.path.isdir(found["sysroot"]):
            for sub in (
                os.path.join(found["sysroot"], "usr", "lib", "aarch64-linux-ohos"),
                os.path.join(found["sysroot"], "usr", "lib"),
                os.path.join(found["sysroot"], "lib", "aarch64-linux-ohos"),
                os.path.join(found["sysroot"], "lib"),
            ):
                if os.path.isdir(sub) and sub not in lib_dirs:
                    lib_dirs.append(sub)
        if found["sysroot"] is None:
            # Shim clang (e.g. /storage/.../usr/local/bin/clang) climbs to
            # nowhere, but resdir/-L paths still pin
            # .../Cellar/ohos-sdk/<ver>/native/llvm. Derive the sibling
            # native/sysroot here too so every caller benefits.
            try:
                _d = self._derive_sysroot_from_known(
                    found["resdir"], lib_dirs, real
                )
            except Exception:
                _d = None
            if _d is not None:
                found["sysroot"] = _d
                for sub in (
                    os.path.join(_d, "usr", "lib", "aarch64-linux-ohos"),
                    os.path.join(_d, "usr", "lib"),
                ):
                    if os.path.isdir(sub) and sub not in lib_dirs:
                        lib_dirs.append(sub)
                self.output.info(f"kim-api: derived sysroot {_d} (query tail)")
        found["lib_dirs"] = lib_dirs
        self.output.info(
            f"kim-api: clang query result sysroot={found['sysroot']} "
            f"resdir={found['resdir']} lib_dirs={len(lib_dirs)}"
        )
        return found

    def generate(self):
        # tmx/1.10.1 + rnp/0.18.1 precedent: cap fork/memory peak on the
        # small shared true machine with an explicit serial level. HMBS
        # already injects tools.build:jobs=1, but the env pin is what the
        # CMake/Make/Ninja drivers actually honor (E074 jobserver lesson).
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        tc = CMakeToolchain(self)
        # 2026-09-29 Signal 9 第 2 次（同指纹复现）：上一轮串行 + -g0/-fno-lto/
        # section-GC 已在树内仍被 OOM kill，按防重复要求不得原样重复，本轮换
        # 与之正交的驱动层维度：Unix Makefiles 在 OHOS 上每个 TU/链接都 fork
        # /bin/sh（E346；OHOS 无原生 /bin/sh，HMBS 注入 SHELL=/bin/sh 兜底），
        # 驱动自身常驻内存 + fork 峰值先触顶；Ninja 直接 spawn、无 shell 中介
        # （rnp/0.18.1 #14 同指纹经 Ninja + -j1 收敛）。zbackup/aws-lc-tools
        # 同式 `tc.generator = "Ninja"`。可用性守卫：HMBS_NINJA →
        # user.hmbs:ninja_path → PATH，发现且 --version 存活才切，否则回落
        # 默认生成器（Linux/CI 行为不变）。
        _ninja = (os.environ.get("HMBS_NINJA") or "").strip()
        if not _ninja:
            try:
                _ninja = (
                    self.conf.get(
                        "user.hmbs:ninja_path", default="", check_type=str)
                    or "")
            except Exception:
                _ninja = ""
        if not _ninja:
            _ninja = shutil.which("ninja") or ""
        _use_ninja = False
        if _ninja and os.path.isfile(_ninja):
            try:
                _r = subprocess.run(
                    [_ninja, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                _use_ninja = (_r.returncode == 0)
            except Exception as _e:
                self.output.info(f"kim-api: ninja probe failed: {_e}")
        if _use_ninja:
            tc.generator = "Ninja"
            tc.variables["CMAKE_MAKE_PROGRAM"] = _ninja
            self.output.info(f"kim-api: using Ninja generator ({_ninja})")
        else:
            self.output.info(
                "kim-api: ninja unavailable, default CMake generator")
        tc.variables["BUILD_SHARED_LIBS"] = (
            "ON" if self.options.shared else "OFF"
        )
        # KIM_API_BUILD_EXAMPLES stays ON: examples/simulators/CMakeLists.txt
        # registers the whole upstream ctest suite via add_kim_api_test()
        # (3 collections-example + 27 ex_test matrix + 3
        # simulator-model-example = 33 simulator runs + 13 shared-library
        # item checks = 46 total; the 9-model _test_models list and the
        # WILL_FAIL marks for ex_model_Ar_P_Morse_MultiCutoff /
        # ex_model_Ar_SLJ_MultiCutoff live there). With OFF, ctest discovers
        # 0 and the preflight evidence gate rejects no_tests (2026-09-29
        # incomplete: "清单表明上游存在测试"). The 2026-09-29 SIGKILL round
        # predates the Fortran sysroot/runtime-link fix and the follow-up
        # round reached 93% on the same graph, so the suite is attempted
        # under hmbs jobs=1; any shortfall is reported via gaps, not hidden.
        # Belt and suspenders (both variables and cache_variables): -D via
        # variables alone once failed to propagate on the true machine.
        tc.variables["KIM_API_BUILD_EXAMPLES"] = "ON"
        tc.cache_variables["KIM_API_BUILD_EXAMPLES"] = "ON"
        flang = self.dependencies.build["flang-ohos"]
        flang_cc = os.path.join(flang.package_folder, "bin", "flang")
        tc.variables["CMAKE_Fortran_COMPILER"] = flang_cc.replace("\\", "/")
        if str(self.settings.os) == "OHOS":
            # metashell/5.0.0 precedent: the profile compiler can be a dead
            # path inside the preflight container (the C/C++ "is broken"
            # failure persists even with zero Fortran flag pollution, so the
            # compiler binary itself is the failure domain). Probe it and,
            # only when dead, pin the working PATH compiler into the
            # toolchain plus CC/CXX (recorded for build() env sync).
            c_sel, cxx_sel, fell_back = self._select_compilers()
            if fell_back:
                if c_sel:
                    tc.variables["CMAKE_C_COMPILER"] = c_sel
                if cxx_sel:
                    tc.variables["CMAKE_CXX_COMPILER"] = cxx_sel
            # flang-ohos ships only the frontend + static Fortran runtime.
            # Without the SDK sysroot/resource-dir and runtime link path,
            # every Fortran link (including CMake's compiler check) fails
            # with Scrt1.o/crti.o/libunwind/libclang_rt.builtins errors
            # (lapack/3.12.1 precedent, device P2-A evidence).
            sdk_llvm = self._ohos_sdk_llvm()
            flang_lib = os.path.join(flang.package_folder, "lib")
            if sdk_llvm is None:
                # No validated SDK llvm tree via globs (2026-09-29 round:
                # all globs empty in this preflight container). Before
                # falling back to target-only flags (which cannot link
                # Fortran executables: Scrt1.o/crti.o/libunwind/builtins),
                # query the working clang for its implicit sysroot /
                # resource-dir / search lib dirs and reuse them for flang.
                clang_sdk = self._query_clang_sdk(c_sel)
                q_sysroot = clang_sdk.get("sysroot")
                q_resdir = clang_sdk.get("resdir")
                q_libs = [
                    d for d in clang_sdk.get("lib_dirs", []) if os.path.isdir(d)
                ]
                if q_sysroot is None:
                    # --print-sysroot is empty on the harmonybrew shim clang,
                    # but resdir/-L paths still pin the SDK
                    # (.../Cellar/ohos-sdk/<ver>/native/llvm/...). Derive the
                    # sibling native/sysroot so flang links find Scrt1.o/
                    # crti.o/crtn.o (2026-09-29 collections-example-fortran
                    # failure). Validated-only: None when nothing exists.
                    try:
                        _exe_real = ""
                        _exe = shutil.which(
                            (c_sel or "").strip().split(" ")[0]
                        ) if c_sel else shutil.which("clang")
                        if _exe:
                            _exe_real = os.path.realpath(_exe)
                    except Exception:
                        _exe_real = ""
                    _derived = self._derive_sysroot_from_known(
                        q_resdir, q_libs, _exe_real
                    )
                    if _derived is not None:
                        self.output.info(
                            f"kim-api: derived sysroot {_derived} from "
                            f"resdir={q_resdir}"
                        )
                        q_sysroot = _derived
                        for _sub in (
                            os.path.join(_derived, "usr", "lib",
                                         "aarch64-linux-ohos"),
                            os.path.join(_derived, "usr", "lib"),
                        ):
                            if os.path.isdir(_sub) and _sub not in q_libs:
                                q_libs.append(_sub)
                if q_sysroot is not None or q_resdir is not None or q_libs:
                    self.output.info(
                        "kim-api: using clang-queried SDK for Fortran "
                        f"(sysroot={q_sysroot} resdir={q_resdir} "
                        f"lib_dirs={len(q_libs)})"
                    )
                    for_flags = "-fPIC --target=aarch64-linux-ohos"
                    if q_sysroot is not None:
                        for_flags += f" --sysroot={q_sysroot}"
                    if q_resdir is not None:
                        for_flags += f" -resource-dir={q_resdir}"
                    tc.variables["CMAKE_Fortran_FLAGS"] = for_flags
                    tc.variables["CMAKE_Fortran_STANDARD_LIBRARIES"] = (
                        f"-L{flang_lib} -lFortranRuntime -lFortranDecimal"
                    )
                    link_dirs = [d for d in (q_libs + [flang_lib]) if os.path.isdir(d)]
                    runtime_link = " ".join(f"-L{d}" for d in link_dirs)
                    runtime_link += " -lFortranRuntime -lFortranDecimal -lm"
                    tc.variables["CMAKE_EXE_LINKER_FLAGS"] = runtime_link
                    tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = runtime_link
                    tc.variables["CMAKE_MODULE_LINKER_FLAGS"] = runtime_link
                    self.output.info(
                        f"kim-api: Fortran flags from clang query: {for_flags}"
                    )
                else:
                    # No validated SDK tree on this machine: keep the C/C++
                    # compiler checks pristine (no -L/-l pollution) and give
                    # the Fortran frontend target-only flags. Any genuine
                    # missing-SDK link error then surfaces with evidence at
                    # configure/build time instead of masquerading as
                    # "C compiler is broken".
                    tried = getattr(self, "_sdk_search_tried", [])
                    rejected = getattr(self, "_sdk_search_rejected", [])
                    self.output.warning(
                        "kim-api: no validated OHOS SDK llvm "
                        f"(searched: {'; '.join(tried)}; "
                        f"rejected: {'; '.join(rejected)}); clang query also "
                        "empty; using Fortran-only flags without SDK sysroot"
                    )
                    tc.variables["CMAKE_Fortran_FLAGS"] = (
                        "-fPIC --target=aarch64-linux-ohos"
                    )
                    # devicexlib precedent: feed the flang static runtime
                    # through the Fortran-scoped standard libraries so C/C++
                    # compiler checks never see Fortran link flags.
                    # CMAKE_TRY_COMPILE is STATIC_LIBRARY so EXE/SHARED
                    # flags below do not pollute the compiler checks either.
                    tc.variables["CMAKE_Fortran_STANDARD_LIBRARIES"] = (
                        f"-L{flang_lib} -lFortranRuntime -lFortranDecimal"
                    )
                    # The final libkim-api.so mixes C/C++/Fortran objects and
                    # its link driver is C/C++ (Fortran STANDARD_LIBRARIES
                    # do not apply), while utils/ executables link against
                    # the just-built shared lib under
                    # --no-allow-shlib-undefined. Without the runtime on the
                    # shared/exe link lines the 2026-09-29 preflight failed
                    # at 53% with undefined _FortranA* (ATrim/AInitialize/
                    # AAssign/AIsContiguous/ACopyInAssign/ACopyOutAssign/
                    # ACharacterCompareScalar1) referenced by libkim-api.so.
                    # Close the runtime here with only the validated flang
                    # lib dir (no SDK paths invented).
                    if os.path.isdir(flang_lib):
                        runtime_link = (
                            f"-L{flang_lib} "
                            "-lFortranRuntime -lFortranDecimal -lm"
                        )
                    else:
                        runtime_link = "-lFortranRuntime -lFortranDecimal -lm"
                    tc.variables["CMAKE_EXE_LINKER_FLAGS"] = runtime_link
                    tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = runtime_link
                    tc.variables["CMAKE_MODULE_LINKER_FLAGS"] = runtime_link
                    self.output.info(
                        "kim-api: SDK llvm missing, Fortran flags target-only"
                    )
            else:
                self.output.info(f"kim-api: OHOS SDK llvm at {sdk_llvm}")
                sdk_sysroot = os.path.normpath(
                    os.path.join(sdk_llvm, "..", "sysroot")
                )
                sdk_resdir = self._ohos_sdk_resdir(sdk_llvm)
                sdk_lib = os.path.join(sdk_llvm, "lib", "aarch64-linux-ohos")
                for_flags = "-fPIC --target=aarch64-linux-ohos"
                if os.path.isdir(sdk_sysroot):
                    for_flags += f" --sysroot={sdk_sysroot}"
                if sdk_resdir is not None:
                    for_flags += f" -resource-dir={sdk_resdir}"
                tc.variables["CMAKE_Fortran_FLAGS"] = for_flags
                tc.variables["CMAKE_Fortran_STANDARD_LIBRARIES"] = (
                    f"-L{flang_lib} -lFortranRuntime -lFortranDecimal"
                )
                # The final libkim-api.so mixes C/C++/Fortran objects, so the
                # shared/exe links also close the Fortran runtime. Only -L
                # dirs that exist are advertised (bogus -L paths previously
                # accompanied the "C compiler is broken" failure).
                link_dirs = [
                    d
                    for d in (
                        sdk_lib,
                        os.path.join(sdk_llvm, "lib"),
                        flang_lib,
                    )
                    if os.path.isdir(d)
                ]
                runtime_link = " ".join(f"-L{d}" for d in link_dirs)
                runtime_link += " -lFortranRuntime -lFortranDecimal -lm"
                tc.variables["CMAKE_EXE_LINKER_FLAGS"] = runtime_link
                tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = runtime_link
                tc.variables["CMAKE_MODULE_LINKER_FLAGS"] = runtime_link
            # The flang frontend can compile .f/.f90 to .o; only executable
            # linking needs the CRT. Compiling the try_compile probe as a
            # static library skips that link (lapack precedent).
            tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
            # 2026-09-29 Signal 9 (compile-phase SIGKILL, empty stdout/stderr
            # tail): OOM-killer signature on the shared true machine, not a
            # recipe syntax error. rnp/0.18.1 precedent, memory-slim only:
            # keep -O level, sources, and test scope unchanged; strip debug
            # info, disable LTO, enable section GC, and tell lld to drop its
            # in-memory symbol cache. Fortran keeps its --target/--sysroot
            # (append -g0 only: -fno-lto/-ffunction-sections are not proven
            # safe on the flang frontend); the Fortran runtime closure above
            # is preserved, memory opts are purely additive.
            try:
                _fort_flags = str(
                    tc.variables.get("CMAKE_Fortran_FLAGS", ""))
            except Exception:
                _fort_flags = ""
            if _fort_flags and "-g0" not in _fort_flags:
                tc.variables["CMAKE_Fortran_FLAGS"] = _fort_flags + " -g0"
            tc.variables["CMAKE_C_FLAGS"] = (
                "-g0 -fno-lto -ffunction-sections -fdata-sections")
            tc.variables["CMAKE_CXX_FLAGS"] = (
                "-g0 -fno-lto -ffunction-sections -fdata-sections")
            _mem_link = (" -Wl,--no-keep-memory -Wl,--gc-sections"
                         " -Wl,--exclude-libs,ALL -Wl,--as-needed")
            for _lk in ("CMAKE_EXE_LINKER_FLAGS",
                        "CMAKE_SHARED_LINKER_FLAGS",
                        "CMAKE_MODULE_LINKER_FLAGS"):
                try:
                    _cur = str(tc.variables.get(_lk, ""))
                except Exception:
                    _cur = ""
                if _cur and "--no-keep-memory" not in _cur:
                    tc.variables[_lk] = _cur + _mem_link
        tc.generate()

    def build(self):
        # Explicit serial level for the actual build driver (lammps/uvw
        # precedent: cli_args --parallel 1 + build_tool_args -j1). Set for
        # every OS so a cache-hit Linux round cannot reintroduce parallel
        # pressure on the shared box either.
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        if str(self.settings.os) == "OHOS":
            # Sync the compiler fallback into the build env so the toolchain
            # cache and CC/CXX-driven probes agree (recomputed here: conan
            # does not guarantee attribute carry-over from generate()).
            c_sel, cxx_sel, fell_back = self._select_compilers()
            if fell_back:
                if c_sel:
                    os.environ["CC"] = c_sel
                if cxx_sel:
                    os.environ["CXX"] = cxx_sel
                self.output.info(
                    f"kim-api: build env CC={c_sel} CXX={cxx_sel}"
                )
            # TMPDIR passthrough (HMBS injects a per-task dir); log it for
            # evidence, never override.
            for key in ("TMPDIR", "TMP", "TEMP"):
                val = os.environ.get(key)
                if val:
                    self.output.info(f"kim-api: {key}={val}")
            # flang/lld need their LLVM/MLIR/clang-cpp runtime plus the SDK
            # llvm lib (lld's libxml2) at compiler-execution time.
            flang_pkg = self.dependencies.build["flang-ohos"].package_folder
            sdk_llvm = self._ohos_sdk_llvm()
            paths = []
            if sdk_llvm is not None:
                paths.append(os.path.join(sdk_llvm, "lib"))
            else:
                # Same container issue as generate(): no glob SDK tree, but
                # the working clang's search lib dirs may hold lld's
                # libxml2. Reuse the query (read-only, logs evidence).
                try:
                    q = self._query_clang_sdk(c_sel)
                    for d in q.get("lib_dirs", []):
                        if os.path.isdir(d) and d not in paths:
                            paths.append(d)
                except Exception as e:
                    self.output.info(f"kim-api: clang query for LD path failed: {e}")
            paths.append(os.path.join(flang_pkg, "lib"))
            old = os.environ.get("LD_LIBRARY_PATH", "")
            if old:
                paths.append(old)
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(paths)
        cmake = CMake(self)
        try:
            cmake.configure()
        except Exception:
            # Configure forensics: the preflight summary omits the actual
            # compiler error text, so persist the CMake check logs into the
            # conan output to define the next failure domain precisely.
            self._dump_cmake_logs()
            raise
        # lammps/uvw precedent on OHOS: explicit -j1 at both the cmake and
        # native-tool layers so link-time lld threads/forks cannot spike
        # past the shared runner's cgroup (Signal 9 domain).
        cmake.build(cli_args=["--parallel", "1"], build_tool_args=["-j1"])
        # Upstream test step: run the real 46-case ctest suite (33 simulator
        # runs in examples/simulators/CMakeLists.txt plus 13
        # shared_library_test item checks, all under
        # KIM_API_BUILD_EXAMPLES=ON).
        # cmake.test() is NOT used directly: build-tree simulator
        # executables must be OHOS self-signed first (HongMeng SIGKILLs
        # unsigned execs) and counts must come from deterministic parsing.
        self._run_upstream_ctest()

    def _sign_build_exe(self, path):
        """OHOS self-sign one build-tree executable, or raise."""
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanInvalidConfiguration(
                "kim-api: required OHOS signing tools are missing "
                f"(signer={signer} readelf={readelf})"
            )
        temporary = f"{path}.signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary,
             "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanInvalidConfiguration(
                f"kim-api: signed build exe has invalid .codesign: {path}"
            )
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)

    def _sign_upstream_test_binaries(self):
        """Self-sign every build-tree ELF executable (no .so/.a/.o).

        ctest execs the example simulators from the build tree; unsigned
        ones die with SIGKILL on HongMeng. Shared libs load fine unsigned
        (installed libkim-api.so proves it in test_package), so only
        executables are signed. Returns the signed count.
        """
        if str(self.settings.os) != "OHOS":
            return 0
        signed = 0
        for root, _ds, files in os.walk(self.build_folder):
            for fn in files:
                if fn.endswith((".so", ".a", ".o", ".cmake", ".log",
                                ".txt", ".json", ".in", ".h", ".hpp",
                                ".f90", ".cpp", ".c", ".params", ".dat")):
                    continue
                path = os.path.join(root, fn)
                try:
                    with open(path, "rb") as f:
                        magic = f.read(4)
                except OSError:
                    continue
                if magic != b"\x7fELF":
                    continue
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if not (st.st_mode & 0o111):
                    continue
                if ".so" in fn:
                    continue
                self._sign_build_exe(path)
                signed += 1
        self.output.info(f"kim-api: OHOS-signed {signed} build-tree exes")
        return signed

    def _hmbs_emit_upstream(self, payload):
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            payload, separators=(",", ":")
        )
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception as e:
            self.output.warning(f"kim-api: persist upstream failed: {e}")
        return line

    def _run_upstream_ctest(self):
        """Run upstream ctest with deterministic evidence (OHOS-aware).

        Counts come from exactly one source each: ``ctest -N`` for
        discovered, per-line ``Test #N ... Passed|Failed`` for
        executed/passed/failed. The ``N% tests passed`` summary line and
        ``Testing/Temporary/LastTest.log`` are consistency witnesses only
        and never overwrite the parsed counts.
        """
        ctest = shutil.which("ctest") or "ctest"
        # Witness 0: the option really propagated (round-2 precedent: -D via
        # variables alone once did not take effect on the true machine).
        try:
            cache = os.path.join(self.build_folder, "CMakeCache.txt")
            with open(cache, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "KIM_API_BUILD_EXAMPLES" in line:
                        self.output.info(f"kim-api: cache {line.strip()}")
        except OSError as e:
            self.output.warning(f"kim-api: cannot read CMakeCache: {e}")
        # Source 1 (discovered): ctest -N.
        proc = subprocess.run(
            [ctest, "-N"],
            cwd=self.build_folder,
            capture_output=True,
            text=True,
            timeout=120,
        )
        out_n = (proc.stdout or "") + (proc.stderr or "")
        m = re.search(r"Total Tests:\s*(\d+)", out_n)
        discovered = int(m.group(1)) if m else 0
        self.output.info(f"kim-api: ctest -N discovered={discovered}")
        for line in out_n.splitlines()[-8:]:
            self.output.info(f"kim-api: ctest -N | {line.rstrip()}"[:2000])
        if discovered <= 0:
            payload = {
                "status": "failed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "ctest -N discovered 0 tests despite "
                "KIM_API_BUILD_EXAMPLES=ON; the option did not propagate "
                "to the configure (round-2 precedent)",
            }
            self._hmbs_emit_upstream(payload)
            raise ConanInvalidConfiguration(
                "kim-api: upstream suite undiscoverable (ctest -N = 0)"
            )
        self._sign_upstream_test_binaries()
        # OHOS runtime closure for build-tree test executables (rnv/1.7.11
        # precedent: build-tree test binaries die at startup when the
        # just-built shared lib is not on the loader path; here every
        # should-pass case failed in 0.03-0.06s while the 6 WILL_FAIL
        # cases counted as Passed -- the classic whole-suite loader
        # failure signature. E019 same family). Collect deterministically:
        # dirs that actually contain libkim-api.so* in the build tree,
        # plus the flang runtime lib and the SDK llvm lib / clang search
        # lib dirs. Prepend to LD_LIBRARY_PATH so ctest children (and
        # their sh -c grandchildren) inherit it; log the final value.
        if str(self.settings.os) == "OHOS":
            _ld_dirs = []
            try:
                for _hit in sorted(glob.glob(os.path.join(
                        self.build_folder, "**", "libkim-api.so*"),
                        recursive=True)):
                    _d = os.path.dirname(_hit)
                    if os.path.isdir(_d) and _d not in _ld_dirs:
                        _ld_dirs.append(_d)
            except Exception as _e:
                self.output.info(f"kim-api: libkim-api glob failed: {_e}")
            for _cand in (self.build_folder,
                          os.path.join(self.build_folder, "lib")):
                try:
                    if os.path.isdir(_cand) and _cand not in _ld_dirs:
                        _ld_dirs.append(_cand)
                except Exception:
                    continue
            try:
                _flang_lib = os.path.join(
                    self.dependencies.build["flang-ohos"].package_folder,
                    "lib")
                if os.path.isdir(_flang_lib) and _flang_lib not in _ld_dirs:
                    _ld_dirs.append(_flang_lib)
            except Exception as _e:
                self.output.info(f"kim-api: flang lib lookup failed: {_e}")
            try:
                _sdk_llvm = self._ohos_sdk_llvm()
                if _sdk_llvm is not None:
                    _sdk_lib = os.path.join(_sdk_llvm, "lib")
                    if (os.path.isdir(_sdk_lib)
                            and _sdk_lib not in _ld_dirs):
                        _ld_dirs.append(_sdk_lib)
                else:
                    _q = self._query_clang_sdk(None)
                    for _d in _q.get("lib_dirs", []):
                        if os.path.isdir(_d) and _d not in _ld_dirs:
                            _ld_dirs.append(_d)
            except Exception as _e:
                self.output.info(f"kim-api: sdk lib lookup failed: {_e}")
            _old_ld = os.environ.get("LD_LIBRARY_PATH", "")
            if _old_ld:
                for _d in _old_ld.split(os.pathsep):
                    if _d and _d not in _ld_dirs:
                        _ld_dirs.append(_d)
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(_ld_dirs)
            self.output.info(
                f"kim-api: ctest LD_LIBRARY_PATH={os.environ['LD_LIBRARY_PATH']}")
        # Source 2 (executed/passed/failed): per-test result lines.
        proc = subprocess.run(
            [ctest, "--output-on-failure"],
            cwd=self.build_folder,
            capture_output=True,
            text=True,
            timeout=1500,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        for line in out.splitlines():
            s = line.rstrip()
            if ("Test #" in s or "tests passed" in s or "tests failed" in s
                    or "No tests were found" in s):
                self.output.info(f"kim-api: ctest | {s}"[:2000])
        passed_names = []
        failed_names = []
        skipped_names = []
        for line in out.splitlines():
            mt = re.search(r"Test\s+#\d+:\s+(\S+)", line)
            if not mt:
                continue
            name = mt.group(1)
            tail = line[mt.end():]
            if re.search(r"\bPassed\b", tail):
                passed_names.append(name)
            elif re.search(r"\bSkipped\b", tail):
                skipped_names.append(name)
            elif re.search(r"\b(Failed|Timeout)\b", tail):
                failed_names.append(name)
        passed = len(passed_names)
        failed = len(failed_names)
        skipped = len(skipped_names)
        executed = passed + failed
        # Witness 1: summary line must agree; mismatch invalidates the run.
        witness_ok = True
        ms = re.search(
            r"(\d+)% tests passed,\s*(\d+) tests failed out of (\d+)", out
        )
        if ms:
            # Compare failed/out-of exactly (percentage rounds, so the
            # percent field itself is not used for counts).
            if int(ms.group(2)) != failed or int(ms.group(3)) != discovered:
                witness_ok = False
                self.output.warning(
                    "kim-api: summary witness disagrees "
                    f"(summary failed={ms.group(2)} total={ms.group(3)} vs "
                    f"parsed failed={failed} discovered={discovered})"
                )
        else:
            self.output.warning("kim-api: no ctest summary line found")
        # Witness 2: LastTest.log presence (never parsed for counts).
        # On failure, also dump the failing sections' tails so the next
        # round has a precise failure domain (loader error vs model
        # error) instead of bare per-test lines. Bounded: first 3
        # failed tests x 30 lines.
        lastlogs = sorted(glob.glob(os.path.join(
            self.build_folder, "**", "LastTest.log"), recursive=True))
        self.output.info(f"kim-api: LastTest.log files: {lastlogs}")
        if failed > 0 and lastlogs:
            try:
                with open(lastlogs[0], "r", encoding="utf-8",
                          errors="replace") as _f:
                    _log_text = _f.read()
                _sections = re.split(
                    r"(?=\d+/\d+ Testing: \S+)", _log_text)
                _dumped = 0
                for _sec in _sections:
                    _msec = re.search(r"\d+/\d+ Testing: (\S+)", _sec)
                    if not _msec:
                        continue
                    _tname = _msec.group(1)
                    if _tname not in failed_names:
                        continue
                    self.output.error(
                        f"kim-api: --- LastTest section {_tname} (tail) ---")
                    for _ln in _sec.strip().splitlines()[-30:]:
                        self.output.error(f"kim-api: [{_tname}] {_ln.rstrip()}"[:2000])
                    _dumped += 1
                    if _dumped >= 3:
                        break
                if _dumped == 0:
                    for _ln in _log_text.strip().splitlines()[-30:]:
                        self.output.error(f"kim-api: [LastTest-tail] {_ln.rstrip()}"[:2000])
            except OSError as _e:
                self.output.warning(f"kim-api: cannot read LastTest.log: {_e}")
        status = "passed"
        gaps = []
        reason = (
            f"kim-api 2.4.1 ctest suite with KIM_API_BUILD_EXAMPLES=ON: "
            f"{passed}/{discovered} passed "
            f"(6 WILL_FAIL-expected-fail cases in "
            f"examples/simulators/CMakeLists.txt count as Passed by ctest)"
        )
        if failed > 0 or not witness_ok:
            status = "failed"
        if skipped > 0 or executed < discovered:
            status = "failed"
            gaps.append({
                "count": (discovered - executed) + skipped,
                "category": "environment",
                "detail": "upstream cases registered by ctest -N but not "
                "executed or skipped on the OHOS true machine "
                f"(executed={executed} skipped={skipped}); see ctest log",
                "evidence": "ctest --output-on-failure per-test lines in "
                "conan create output",
            })
        payload = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if status == "failed":
            payload["reason"] = reason
            if gaps:
                payload["gaps"] = gaps
        else:
            payload["reason"] = reason
        # Self-check the gate identities before emitting.
        assert passed + failed == executed
        assert executed + skipped <= discovered
        assert executed <= discovered
        self._hmbs_emit_upstream(payload)
        if failed > 0 or not witness_ok:
            raise ConanException(
                f"kim-api: upstream ctest failed "
                f"(passed={passed} failed={failed} skipped={skipped} "
                f"discovered={discovered})"
            )

    def package(self):
        copy(
            self,
            "LICENSE.LGPL",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        cmake = CMake(self)
        cmake.install()
        # Bundle the static Fortran runtime so static-library consumers can
        # close the Fortran symbol references (lapack/3.12.1 precedent).
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        for runtime in ("libFortranRuntime.a", "libFortranDecimal.a"):
            src = os.path.join(flang_pkg, "lib", runtime)
            if os.path.isfile(src):
                copy(
                    self,
                    runtime,
                    src=os.path.dirname(src),
                    dst=os.path.join(self.package_folder, "lib"),
                )
        # Carry the real upstream result into the package so cache-hit
        # test_package rounds can re-emit it without re-running the build
        # (zydis precedent).
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copyfile(
                    src, os.path.join(dst_dir, "hmbs_upstream.json"))
            else:
                self.output.warning(
                    "kim-api: hmbs_upstream.json missing in package()")
        except Exception as e:
            self.output.warning(
                f"kim-api: package upstream copy failed: {e}")

    def package_info(self):
        self.cpp_info.libs = ["kim-api"]
        if not self.options.shared:
            # Static archive consumers link Fortran objects directly and
            # need the bundled Fortran runtime closure.
            self.cpp_info.libs += ["FortranRuntime", "FortranDecimal"]
            self.cpp_info.system_libs = ["m"]
        # Public headers install to include/kim-api/.
        self.cpp_info.includedirs = ["include", os.path.join("include", "kim-api")]
        self.cpp_info.set_property("cmake_file_name", "KIM-API")
        self.cpp_info.set_property("cmake_target_name", "KIM-API::kim-api")
        self.cpp_info.set_property("pkg_config_name", "libkim-api")
