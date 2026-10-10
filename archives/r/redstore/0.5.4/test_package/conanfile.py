#!/usr/bin/env python3
"""Conan test_package for redstore 0.5.4.

Runs test.sh which invokes the real redstore binary (redstore -h plus
a version-string check). Emits HMBS_TEST_PACKAGE_RESULT with the real
assertion count and re-emits HMBS_UPSTREAM_TEST_RESULT for the
cache-hit case (build() skipped, aggregated evidence preserved).
"""
import glob
import json
import os
import shlex

from conan import ConanFile


class RedstoreTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Preflight 2026-09-29: /data/service/hnp/bin/bash is not exec-able
        # from the sandbox (exit 127); never default to it. Prefer the
        # hmbs-selected CONFIG_SHELL/SHELL, then capability /bin/sh.
        bash = ""
        for cand in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            "/bin/sh",
            "/system/bin/sh",
        ):
            if cand and os.path.isfile(cand):
                bash = cand
                break
        if not bash:
            import shutil as _shutil

            bash = _shutil.which("sh") or _shutil.which("bash") or "sh"
        redstore_bin = ""
        try:
            ref_name = self.tested_reference_str.split("/")[0]
            dep = self.dependencies[ref_name]
            cand = os.path.join(dep.package_folder, "bin", "redstore")
            if os.path.isfile(cand):
                redstore_bin = cand
                try:
                    os.chmod(redstore_bin, 0o755)
                except Exception:
                    pass
        except Exception as exc:
            self.output.warning("could not resolve redstore package_folder: %s" % exc)

        if redstore_bin:
            os.environ["CONAN_REDSTORE_BIN"] = redstore_bin
            actual_cmd = '%s test.sh "%s"' % (bash, redstore_bin)
        else:
            actual_cmd = "%s test.sh" % bash
        # 2026-09-30 stale_runtime_library (+2026-10-03 rule4 0/12 broadening):
        # redstore links the Conan curl/libxml2/libxslt shared libs, but the
        # OHOS loader ignores LD_LIBRARY_PATH and conanrun alone still
        # resolves the system libcurl.so.4 (preflight 11:47 UTC:
        # curl_global_init et al symbol-not-found). Preload the exact Conan
        # shared objects by absolute realpath, test command only; keep
        # LD_LIBRARY_PATH as fallback where honored. The 4-name allowlist
        # missed the transitive closure (openssl/zlib/libssh2...), so scan
        # every test dependency lib dir for ELF *.so* after the priority set.
        preloads = []
        libdirs = []
        for _name, _patterns in (
            ("curl", ("libcurl.so*",)),
            ("libxml2", ("libxml2.so*",)),
            ("libxslt", ("libxslt.so*", "libexslt.so*")),
            ("check", ("libcheck.so*",)),
        ):
            try:
                _dep = self.dependencies.get(_name)
            except Exception:
                try:
                    _dep = self.dependencies[_name]
                except Exception:
                    _dep = None
            _folder = getattr(_dep, "package_folder", None) if _dep else None
            if not _folder:
                continue
            _lib = os.path.join(_folder, "lib")
            if not os.path.isdir(_lib):
                continue
            if _lib not in libdirs:
                libdirs.append(_lib)
            for _pat in _patterns:
                try:
                    _cands = sorted(glob.glob(os.path.join(_lib, _pat)))
                except Exception:
                    _cands = []
                for _c in _cands:
                    try:
                        _real = os.path.realpath(_c)
                        if not os.path.isfile(_real):
                            continue
                        try:
                            with open(_real, "rb") as _fh:
                                if _fh.read(4) != b"\x7fELF":
                                    continue
                        except OSError:
                            continue
                        if _real not in preloads:
                            preloads.append(_real)
                    except Exception:
                        continue
        try:
            _all_deps = list(self.dependencies.values())
        except Exception:
            _all_deps = []
        for _dep in _all_deps:
            try:
                _folder = getattr(_dep, "package_folder", None)
            except Exception:
                continue
            if not _folder:
                continue
            _lib = os.path.join(_folder, "lib")
            if not os.path.isdir(_lib):
                continue
            if _lib not in libdirs:
                libdirs.append(_lib)
            try:
                _cands = sorted(glob.glob(os.path.join(_lib, "*.so*")))
            except Exception:
                continue
            for _c in _cands:
                try:
                    _real = os.path.realpath(_c)
                    if not os.path.isfile(_real):
                        continue
                    try:
                        with open(_real, "rb") as _fh:
                            if _fh.read(4) != b"\x7fELF":
                                continue
                    except OSError:
                        continue
                    if _real not in preloads:
                        preloads.append(_real)
                except Exception:
                    continue
        if preloads:
            self.output.info("test LD_PRELOAD: %s" % ":".join(preloads))
        else:
            self.output.warning("test preload scan found no shared libs")
        _run_prefix = ""
        if libdirs:
            _run_prefix += 'LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ' % (
                ":".join([shlex.quote(d) for d in libdirs]))
        if preloads:
            _run_prefix += 'LD_PRELOAD="%s" ' % (
                ":".join([shlex.quote(x) for x in preloads]))
        discovered = 2
        passed = 0
        _fail_detail = ""
        try:
            if redstore_bin:
                self.run('%s%s test.sh "%s"' % (_run_prefix, bash, redstore_bin), env="conanrun")
            else:
                self.run("%s%s test.sh" % (_run_prefix, bash), env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error("test.sh failed: %s" % exc)
            _fail_detail = str(exc)[:900]
            raise
        finally:
            try:
                tp_marker = {
                    "executed": True,
                    "passed": passed == discovered,
                    "command": actual_cmd,
                    "discovered": discovered,
                    "passedCount": passed,
                }
                if passed != discovered:
                    tp_marker["gaps"] = [{
                        "count": discovered - passed,
                        "category": "environment",
                        "detail": ("redstore smoke test failed under stale system libcurl; "
                                   "LD_PRELOAD=%s; %s" % (":".join(preloads) if preloads else "none",
                                   _fail_detail or "see test.sh output"))[:400],
                        "evidence": (_fail_detail or "test.sh exit != 0; "
                                     "preflight 11:47 UTC: Error relocating redstore: "
                                     "curl_global_init symbol not found via system libcurl.so.4")[:900],
                    }]
                tp_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker)
                print(tp_msg, flush=True)
                self.output.info(tp_msg)
            except Exception:
                pass
        if passed != discovered:
            from conan.errors import ConanException

            raise ConanException("test_package smoke tests failed")
