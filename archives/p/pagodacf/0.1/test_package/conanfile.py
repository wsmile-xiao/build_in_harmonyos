#!/usr/bin/env python3
"""Conan test_package — pagodacf 0.1

Builds t_pagodacf.ml against the installed pagodacf (Cf) library and runs
it. The test program calls real Cf APIs (Cf_rbtree.Map/Set, Cf_seq,
Cf_deque) and asserts on computed results, so a broken library build
cannot pass.

This recipe's ocaml/4.14.1 toolchain ships the OCaml compiler but not the
findlib front-end (`ocamlfind`), so we call `ocamlc` directly. The Cf
library installs to `<package>/lib/cf` (cf.cma + .cmi/.mli + META), and
its only dependency is the OCaml `unix` standard library; we resolve both
by path: `-I <cf_libdir>` for cf.cma and `-I +unix` for unix.cma.
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class PagodacfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # The ocaml/4.14.1 recipe installs its compiler binaries
        # (ocamlc/ocamlopt/ocamlmklib/ocamldep/ocamllex/ocamlyacc/ocamlrun)
        # into `<package>/bin/` but does NOT inject that directory into PATH
        # via its own package_info() (no env_info.PATH, no cpp_info.bindirs).
        # The main pagodacf recipe builds an `pagodacf_ocaml_env` script for
        # the build stage, but that script is not exported into the
        # test_package's context — so bare `ocamlc` here resolves via PATH
        # alone and fails with `ocamlc: inaccessible or not found` (真机日志
        # `/system/bin/sh: ocamlc: inaccessible or not found`, 退出码 127).
        # We replicate the same environment injection here: prepend ocaml/bin
        # to PATH so ocamlc and its child processes (ocamlrun) are found.
        ocaml_pkg = self.dependencies["ocaml"].package_folder
        ocaml_bin = os.path.join(ocaml_pkg, "bin")
        ocaml_lib = os.path.join(ocaml_pkg, "lib", "ocaml")
        env = Environment()
        env.prepend_path("PATH", ocaml_bin)
        # ocamlc locates stdlib.cmi via (1) OCAMLLIB env, (2) CAMLLIB env,
        # (3) standard_library_default compiled into the binary. The ocaml
        # recipe does not set OCAMLLIB; without it, when the compiled-in
        # prefix does not match the Conan cache layout, `ocamlc -c` aborts
        # with `Unbound module Stdlib` during type-checking. Set it ourselves.
        env.define("OCAMLLIB", ocaml_lib)
        # The bytecode loader finds dllcf.so / dllunix.so via
        # CAML_LD_LIBRARY_PATH. `dllcf.so` relocates `unix_error`
        # (cf_tai64n_p.c:190); `unix_error` lives in OCaml's `unix`
        # library C stub `dllunix.so`. Linking `unix.cma` before
        # `cf.cma` (see test()) makes the runtime `dlopen` `dllunix.so`
        # first, so `unix_error` is resolvable when `dllcf.so` is
        # relocated (RTLD_NOW). Without `dllunix.so` reachable via
        # CAML_LD_LIBRARY_PATH, `ocamlc` aborts at link time with
        # `I/O error: dllunix.so: No such file or directory`.
        #
        # OCaml 4.14's configure sets STUBLIBDIR = libdir/stublibs; the
        # ocaml Conan package installs its tree under <pkg>/lib/ocaml/
        # (its package_info.cpp_info.includedirs = ["lib/ocaml/caml"]),
        # so the canonical stub location is
        # `<ocaml_pkg>/lib/ocaml/stublibs/dllunix.so`. We also add the
        # adjacent `<ocaml_pkg>/lib/ocaml/stubs` and `<ocaml_pkg>/bin`
        # defensively (older layouts), plus `cf_libdir` (dllcf.so).
        cf = self.dependencies["pagodacf"]
        cf_libdir = cf.cpp_info.libdir  # .../lib/cf
        ocaml_stubs = os.path.join(ocaml_lib, "stublibs")
        env.append_path("CAML_LD_LIBRARY_PATH", ocaml_stubs)
        env.append_path("CAML_LD_LIBRARY_PATH", ocaml_bin)
        env.append_path("CAML_LD_LIBRARY_PATH", cf_libdir)
        # R22 fix: force-load dllunix.so before ocamlrun starts relocating
        # dllcf.so. R20/R21 linked `unix.cma` before `cf.cma`, but the OCaml
        # bytecode loader only `dlopen`s a .cma's stub dll when one of that
        # library's primitives is actually referenced in the bytecode — and
        # our t_pagodacf.ml does not call `Unix.` at all, so `dllunix.so` is
        # never loaded, and `dllcf.so`'s RTLD_NOW relocation of `unix_error`
        # (cf_tai64n_p.c:190) fails with `Error relocating dllcf.so:
        # unix_error: symbol not found`.
        #
        # LD_PRELOAD forces the dynamic loader to dlopen `dllunix.so` *before*
        # `main` runs, registering all of its symbols (`unix_error`, etc.)
        # into the global symbol table. When `ocamlrun` later `dlopen`s
        # `dllcf.so` (RTLD_NOW), `unix_error` is already globally resolvable.
        #
        # HMBS platform diagnostic `[stale_runtime_library]` explicitly
        # recommends LD_PRELOAD when the OHOS loader ignores LD_LIBRARY_PATH
        # for runtime symbol resolution.
        dllunix = os.path.join(ocaml_stubs, "dllunix.so")
        env.define("LD_PRELOAD", dllunix)
        env.vars(self).save_script("pagodacf_test_ocaml_env")

    def test(self):
        src = os.path.join(self.source_folder, "t_pagodacf.ml")
        out = os.path.join(self.build_folder, "t_pagodacf")
        # Resolve the installed Cf library directory from the dep's cpp_info.
        cf = self.dependencies["pagodacf"]
        cf_libdir = cf.cpp_info.libdir  # .../lib/cf
        # The upstream TAP test binaries (t.cf bytecode + t-opt.cf native) and
        # the upstream test source (t/t_cf.ml) are staged by the main recipe's
        # package() under lib/cf/tests/.  test_package runs them to produce
        # HMBS_UPSTREAM_TEST_RESULT.  This is necessary because `conan create`
        # skips build() on a cached package (R26 regression: discovered=0
        # executed=0), while test_package always runs.
        cf_pkg = self.dependencies["pagodacf"].package_folder
        tests_dir = os.path.join(cf_pkg, "lib", "cf", "tests")
        t_cf = os.path.join(tests_dir, "t.cf")
        t_opt_cf = os.path.join(tests_dir, "t-opt.cf")

        # ── Upstream official test suite (Layer 1) ──
        # Run the upstream TAP suite in BOTH modes (bytecode t.cf via explicit
        # `ocamlrun` to bypass the broken #! shebang — R19; native t-opt.cf
        # directly since native binaries have no shebang).  Both modes print
        # `1..13` then `ok N` / `not ok N` per the 13 upstream test functions
        # (T1..T13), giving 26 assertion executions across the two modes.
        # `ignore_errors=True` lets us inspect the exit code and emit the
        # evidence marker even on a test failure, then we raise ourselves.
        up_bc_log = os.path.join(self.build_folder, "hmbs_upstream_test_bc.log")
        up_nat_log = os.path.join(self.build_folder, "hmbs_upstream_test_nat.log")
        up_log = os.path.join(self.build_folder, "hmbs_upstream_test.log")
        upstream_rc = self.run(
            f'ocamlrun "{t_cf}" > "{up_bc_log}" 2>&1 ; '
            f'"{t_opt_cf}" > "{up_nat_log}" 2>&1',
            env=["conanrun", "pagodacf_test_ocaml_env"],
            ignore_errors=True,
        )
        # Merge per-mode logs so the TAP parser sees both runs in order.
        try:
            with open(up_log, "wb") as fout:
                for part in (up_bc_log, up_nat_log):
                    try:
                        with open(part, "rb") as fh:
                            fout.write(fh.read())
                    except OSError:
                        pass
        except OSError:
            pass
        # Tally TAP results across both modes.
        up_discovered = up_executed = up_passed = up_failed = up_skipped = 0
        tap_re = re.compile(r"^(ok|not ok)\s+(\d+)")
        header_re = re.compile(r"^1\.\.(\d+)\s*$")
        try:
            with open(up_log, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    hm = header_re.match(line)
                    if hm:
                        up_discovered += int(hm.group(1))
                        continue
                    m = tap_re.match(line)
                    if m:
                        up_executed += 1
                        if m.group(1) == "ok":
                            up_passed += 1
                        else:
                            up_failed += 1
        except OSError:
            up_passed = 0
            up_failed = 0 if upstream_rc == 0 else 1
            up_executed = up_passed + up_failed
            up_discovered = up_executed
        up_status = "passed" if (
            upstream_rc == 0 and up_failed == 0 and up_executed > 0
        ) else "failed"
        print(
            '\nHMBS_UPSTREAM_TEST_RESULT='
            '{"status":"%s","framework":"TAP-make-test",'
            '"command":"make -j1 t.cf t-opt.cf + ocamlrun t.cf / ./t-opt.cf '
            '(bytecode + native)","discovered":%d,"executed":%d,'
            '"passed":%d,"failed":%d,"skipped":%d}'
            % (up_status, up_discovered, up_executed,
               up_passed, up_failed, up_skipped)
        )
        if upstream_rc != 0 or up_failed > 0:
            raise ConanException(
                f"pagodacf upstream TAP suite failed: "
                f"discovered={up_discovered}, executed={up_executed}, "
                f"passed={up_passed}, failed={up_failed}"
            )

        # ── Layer 2: test_package (consumer perspective) ──
        # Link bytecode against cf.cma, mirroring upstream's `t.cf` target.
        self.run(
            f'ocamlc -I "{cf_libdir}" -I +unix -o "{out}" unix.cma cf.cma "{src}"',
            env=["conanrun", "pagodacf_test_ocaml_env"],
        )
        tp_log = os.path.join(self.build_folder, "hmbs_test_package.log")
        rc = self.run(
            f'ocamlrun "{out}" > "{tp_log}" 2>&1',
            env=["conanrun", "pagodacf_test_ocaml_env"],
            ignore_errors=True,
        )
        discovered = executed = passed = failed = skipped = 0
        try:
            with open(tp_log, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    hm = header_re.match(line)
                    if hm:
                        discovered += int(hm.group(1))
                        continue
                    m = tap_re.match(line)
                    if m:
                        executed += 1
                        if m.group(1) == "ok":
                            passed += 1
                        else:
                            failed += 1
        except OSError:
            passed = 0
            failed = 0 if rc == 0 else 1
            executed = passed + failed
            discovered = executed
        passed_count = passed
        tp_ok = (rc == 0 and failed == 0 and executed > 0)
        result = {
            "executed": True,
            "passed": tp_ok,
            "command": (
                "ocamlc -I {lib} -I +unix -o t_pagodacf unix.cma cf.cma "
                "t_pagodacf.ml && ocamlrun t_pagodacf"
            ).format(lib=cf_libdir),
            "discovered": discovered,
            "passedCount": passed_count,
        }
        print("\nHMBS_TEST_PACKAGE_RESULT=" + json.dumps(result))
        if not tp_ok:
            raise ConanException(
                f"pagodacf test_package failed: rc={rc}, "
                f"discovered={discovered}, executed={executed}, "
                f"passed={passed}, failed={failed}"
            )
