#!/usr/bin/env python3
"""Conan test_package for libocas 0.97.

Runs two real consumer tests against the packaged library:
  1. test_ocas (C API): 6 checks covering LIBOCAS_INDEX and a real
     libqp_splx_solver simplex QP solve (exitflag, finite QP/QD,
     simplex feasibility, non-negativity, iteration budget).
  2. svmocas/linclassif CLI flow: trains a tiny SVM-light dataset with
     the packaged svmocas binary and classifies with linclassif,
     verifying non-empty model, non-empty predictions, line count and
     label agreement.

Build note: compiled directly with the resolved C compiler (no CMake).
CMake 4.x has no Platform/HarmonyOS module ("System is unknown to
cmake") and the CI-profile compiler path /data/service/hnp/bin/clang
no longer exists on preflight hosts (clang moved to ~/usr/local/bin),
so a CMakeToolchain-based test_package fails at project() before
compiling anything. Direct `cc` compile with the same fallback
resolution as the main recipe sidesteps both issues (lame precedent).

Emits HMBS_TEST_PACKAGE_RESULT (discovered/passedCount = 2, with gaps
when <100%) and HMBS_UPSTREAM_TEST_RESULT (no_tests with source-tree
audit).
"""
import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import save

CONSUMER_TEST_COUNT = 2


class LibocasTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_cc(self):
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default=None
            )
        except Exception:
            compilers = None
        configured = None
        if isinstance(compilers, dict):
            configured = compilers.get("c")
        if configured and os.path.exists(configured):
            return configured
        for name in ("clang", "cc", "gcc"):
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local",
                                "bin")
        for name in ("clang", "cc", "gcc"):
            cand = os.path.join(home_bin, name)
            if os.path.exists(cand):
                return cand
        if configured:
            return configured
        env_cc = os.environ.get("CC")
        if env_cc:
            return env_cc
        return "clang"

    def build(self):
        dep = self.dependencies["libocas"]
        inc = os.path.join(dep.package_folder, "include")
        lib = os.path.join(dep.package_folder, "lib")
        cc = self._resolve_cc()
        self.output.info("libocas test_package: resolved CC=%s" % cc)
        self.run("{} --version".format(shlex.quote(cc)),
                 ignore_errors=True)
        src = os.path.join(self.source_folder, "test_ocas.c")
        out = os.path.join(self.build_folder, "test_ocas")
        self.run(
            "{cc} {src} -o {out} -I{inc} -L{lib} -locas -lm".format(
                cc=shlex.quote(cc),
                src=shlex.quote(src),
                out=shlex.quote(out),
                inc=shlex.quote(inc),
                lib=shlex.quote(lib),
            )
        )

    def _emit(self, test_pkg, upstream):
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg))
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))

    def test(self):
        if not can_run(self):
            raise Exception("Cannot run the test binary on this host")
        audit_cmd = ("grep -nE '^[a-zA-Z0-9_.-]+:' Makefile | grep -iE 'check|test'")
        upstream = {
            "status": "no_tests",
            "framework": "none",
            "command": audit_cmd,
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "upstream libocas 0.97 ships no automated C tests: "
                      "Makefile defines only all/svmocas/msvmocas/linclassif/"
                      "libocas.so/clean targets, no check/test target; "
                      "only Matlab scripts (libocas_test.m) require Matlab",
        }
        # Re-emit persisted upstream evidence from the package when present
        # (dual-channel: build-time audit file carried via res/).
        try:
            dep0 = self.dependencies["libocas"]
            ev_path = os.path.join(dep0.package_folder, "res",
                                   "hmbs_upstream_evidence.json")
            if os.path.exists(ev_path):
                with open(ev_path, "r", encoding="utf-8") as f:
                    persisted = json.load(f)
                if isinstance(persisted, dict) and persisted.get("status") == "no_tests":
                    upstream = persisted
                    self.output.info("libocas test_package: re-emitting persisted upstream evidence")
        except Exception as e:
            self.output.warning("libocas test_package: upstream evidence read failed: %s" % e)
        passed_count = 0
        gaps = []
        # --- Test 1: C API consumer binary (6 checks inside test_ocas) ---
        try:
            self.run(os.path.join(self.build_folder, "test_ocas"),
                     env="conanrun")
            passed_count += 1
            self.output.info("libocas test_package: test_ocas PASSED (6 checks)")
        except Exception as exc:
            gaps.append({
                "count": 1,
                "category": "test_failure",
                "detail": "test_ocas C API consumer binary failed: %s" % str(exc),
                "evidence": "conan test_package log: test_ocas run raised; see stdout above",
            })
            test_pkg = {
                "executed": True,
                "passed": False,
                "command": "test_ocas + svmocas/linclassif CLI flow",
                "discovered": CONSUMER_TEST_COUNT,
                "passedCount": passed_count,
                "gaps": gaps,
            }
            self._emit(test_pkg, upstream)
            raise exc
        # --- Test 2: svmocas/linclassif CLI flow ---
        # NOTE (2026-09-23 CI #56621): upstream linclassif.c uses inverted
        # exit codes -- `int exitflag = 0;` at entry, `exitflag = 1;` only
        # on the success path before `return(exitflag);` (error paths
        # `goto clean_up` with exitflag still 0). So a successful classify
        # exits 1 and conan self.run raises "Error 1 while executing".
        # svmocas.c is normal (init 1, success 0). Gate linclassif on real
        # artifacts (non-empty preds, 4 lines, 4/4 label agreement), not on
        # its exit code; stale preds are removed first so the checks cannot
        # pass on leftovers. Run `-e` only as a non-gating diagnostic.
        try:
            dataset = os.path.join(self.build_folder, "tiny_train.light")
            model = os.path.join(self.build_folder, "tiny.model")
            preds = os.path.join(self.build_folder, "tiny.pred")
            save(
                self,
                dataset,
                "1 1:0.9 2:0.1\n1 1:0.8 2:0.2\n-1 1:-0.9 2:-0.1\n-1 1:-0.8 2:-0.2\n",
            )
            dep = self.dependencies["libocas"]
            bindir = os.path.join(dep.package_folder, "bin")
            self.run(
                '"{}" -c 1 -b 0 -v 0 "{}" "{}"'.format(
                    os.path.join(bindir, "svmocas"), dataset, model
                ),
                env="conanrun",
            )
            if os.path.getsize(model) == 0:
                raise Exception("svmocas produced an empty model file")
            # Gating run: generate predictions without -e. Upstream success
            # exit is 1 (see note above), so ignore the exit code here and
            # gate strictly on the prediction file below.
            try:
                os.remove(preds)
            except OSError:
                pass
            self.run(
                '"{}" -o "{}" "{}" "{}"'.format(
                    os.path.join(bindir, "linclassif"), preds, dataset, model
                ),
                env="conanrun",
                ignore_errors=True,
            )
            if not os.path.exists(preds):
                raise Exception("linclassif produced no predictions file (inverted exit 1 is success; missing file means real failure)")
            if os.path.getsize(preds) == 0:
                raise Exception("linclassif produced empty predictions")
            with open(preds, "r", encoding="utf-8", errors="replace") as f:
                pred_lines = [ln.strip() for ln in f if ln.strip() != ""]
            if len(pred_lines) != 4:
                raise Exception("linclassif predictions line count %d != 4" % len(pred_lines))
            expected = ["1", "1", "-1", "-1"]
            for i, (got, want) in enumerate(zip(pred_lines, expected)):
                tok = got.split()[0]
                # Upstream linclassif prints positive labels with an
                # explicit '+' sign ("+1", CI #56823 evidence). Normalize
                # before comparing so "+1" == "1".
                if tok.startswith("+"):
                    tok = tok[1:]
                if tok != want:
                    raise Exception("prediction mismatch line %d: got %r want %r (full=%r)" % (i + 1, tok, want, got))
            # Non-gating diagnostic: classification error printout.
            self.run(
                '"{}" -e -o "{}" "{}" "{}"'.format(
                    os.path.join(bindir, "linclassif"), preds + ".diag", dataset, model
                ),
                env="conanrun",
                ignore_errors=True,
            )
            passed_count += 1
            self.output.info("libocas test_package: CLI flow PASSED (model+preds 4/4 labels match)")
        except Exception as exc:
            gaps.append({
                "count": 1,
                "category": "test_failure",
                "detail": "svmocas/linclassif CLI flow failed: %s" % str(exc),
                "evidence": "conan test_package log: CLI flow raised after svmocas run; see stdout above",
            })
            test_pkg = {
                "executed": True,
                "passed": False,
                "command": "test_ocas + svmocas/linclassif CLI flow",
                "discovered": CONSUMER_TEST_COUNT,
                "passedCount": passed_count,
                "gaps": gaps,
            }
            self._emit(test_pkg, upstream)
            raise exc
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "test_ocas + svmocas/linclassif CLI flow",
            "discovered": CONSUMER_TEST_COUNT,
            "passedCount": passed_count,
        }
        self._emit(test_pkg, upstream)
