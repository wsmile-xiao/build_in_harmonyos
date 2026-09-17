#!/usr/bin/env python3
"""Conan recipe — libmustach-core 1.2.10 (Makefile).

Mustache templating core in C (mustach.c + mustach-wrap.c, no external
dependencies). Only the core library is packaged (JSON backends and the CLI
tool disabled); upstream basic-tests (test1..test8) run in build() against
official cJSON 1.7.19 (MIT) fetched in source().
"""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibmustachCoreConan(ConanFile):
    name = "libmustach-core"
    version = "1.2.10"
    description = "Mustache templating core library in C (no dependencies)"
    license = "0BSD"
    homepage = "https://gitlab.com/jobol/mustach"
    url = "https://gitlab.com/jobol/mustach"
    topics = ("mustache", "template", "templating")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "vendor_cjson/test-custom-write-cjson.c"

    def export_sources(self):
        export_conandata_patches(self)
        # NOTE: only the authored test6 harness (test-custom-write-cjson.c) is
        # exported. The cJSON.c/.h it compiles against are unmodified upstream
        # third-party source and are fetched at source() time, NOT vendored.

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libmustach-core is only supported on Linux/OHOS, "
                "not %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)
        # Upstream builds in-source (raw Makefile without out-of-tree support).
        self.folders.build = "."

    def source(self):
        # readonly_tmp: conan get() may stage via /tmp (read-only on HMBS
        # preflight); prefer the HMBS-injected writable dir. Never use /tmp.
        def _pick_tmp():
            for _k in ("TMPDIR", "TMP", "TEMP"):
                _v = os.environ.get(_k)
                if _v and _v != "/tmp":
                    return _v
            return os.path.join(self.base_source_folder, "tmp")
        _tmp = _pick_tmp()
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        get(self, **self.conan_data["sources"], strip_root=True)
        # Fetch official cJSON 1.7.19 (MIT) used to build the mustach test
        # tool for upstream basic-tests. Unmodified third-party source, so it
        # is NOT part of the repo diff (PR-size guard); see review rules R39.
        self._fetch_cjson_toolchain()

    def _fetch_cjson_toolchain(self):
        """Fetch official cJSON 1.7.19 into source_folder/vendor_cjson/.

        cJSON.c/.h are byte-identical to the upstream v1.7.19 tag (MIT). The
        test6 harness test-custom-write-cjson.c is authored PR code, so it is
        exported via exports_sources and copied alongside here to keep the
        test runner reading one self-contained vendor dir.
        """
        vendor = os.path.join(self.source_folder, "vendor_cjson")
        os.makedirs(vendor, exist_ok=True)
        get(
            self,
            url="https://github.com/DaveGamble/cJSON/archive/refs/tags/v1.7.19.tar.gz",
            filename="cjson-1.7.19.tar.gz",
            sha256="7fa616e3046edfa7a28a32d5f9eacfd23f92900fe1f8ccd988c1662f30454562",
            strip_root=False,
        )
        # get() unzips into source_folder → cJSON-1.7.19/ (strip_root=False).
        _src_root = os.path.join(self.source_folder, "cJSON-1.7.19")
        for _f in ("cJSON.c", "cJSON.h"):
            _p = os.path.join(_src_root, _f)
            if os.path.isfile(_p):
                copy(self, _f, src=_src_root, dst=vendor, keep_path=False)
        # mustach-cjson.h includes <cjson/cJSON.h>: mirror the header with
        # plain shutil (conan copy with nested src/dst can silently no-op).
        os.makedirs(os.path.join(vendor, "cjson"), exist_ok=True)
        shutil.copyfile(os.path.join(vendor, "cJSON.h"),
                        os.path.join(vendor, "cjson", "cJSON.h"))
        # Authored test6 harness stays committed; exports_sources already
        # stages it into base_source_folder, so when dest exists do nothing.
        # Never use conan copy() src==dst (raises); use shutil with
        # realpath/SameFile guard for layout aliasing/symlinks.
        try:
            _dest_pre = os.path.join(vendor, "test-custom-write-cjson.c")
            if os.path.isfile(_dest_pre) and os.path.getsize(_dest_pre) > 0:
                _cand_list = []
            else:
                _cand_list = [
                    os.path.join(self.export_sources_folder or "", "vendor_cjson",
                                 "test-custom-write-cjson.c"),
                    os.path.join(self.recipe_folder or "", "vendor_cjson",
                                 "test-custom-write-cjson.c"),
                ]
        except OSError:
            _cand_list = []
        for _cand in _cand_list:
            if not os.path.isfile(_cand):
                continue
            _dest = os.path.join(vendor, os.path.basename(_cand))
            try:
                if os.path.realpath(_cand) == os.path.realpath(_dest):
                    break
                if os.path.realpath(os.path.dirname(os.path.abspath(_cand))) == os.path.realpath(os.path.abspath(vendor)):
                    break
            except Exception:
                pass
            try:
                shutil.copyfile(_cand, _dest)
            except shutil.SameFileError:
                pass
            except OSError:
                pass
            break
        # Drop the tarball + full extracted tree (tests/, docs/) so nothing
        # beyond the two needed sources lingers in the local cache.
        try:
            os.remove(os.path.join(self.source_folder, "cjson-1.7.19.tar.gz"))
        except OSError:
            pass
        try:
            shutil.rmtree(_src_root)
        except OSError:
            pass

    def generate(self):
        # Forward the writable TMPDIR into buildenv so compiler/make temp
        # files never fall back to read-only /tmp. Never forward bare /tmp.
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v and _v != "/tmp":
                try:
                    os.makedirs(_v, exist_ok=True)
                except Exception:
                    pass
                self.buildenv_info.define(_k, _v)
        # E266: OHOS SDK lld dynamically needs libxml2.so.16 from SDK
        # llvm/lib (no RUNPATH). CI workers miss it in the ambient
        # LD_LIBRARY_PATH, so every link step fails with
        # "Error loading shared library libxml2.so.16 ... xmlFreeDoc".
        # Prepend the discovered dir (glob, no pinned SDK version) so the
        # bundled lld finds its matching libxml2 (lziprecover/gupnp-av
        # precedent). True-machine env already has it; extra entry is safe.
        _sdk_lib = self._sdk_llvm_libdir()
        if _sdk_lib:
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", _sdk_lib)
            self.output.info("lld runtime: LD_LIBRARY_PATH+=%s" % _sdk_lib)

    @staticmethod
    def _sdk_llvm_libdir():
        """Return OHOS SDK llvm/lib dir holding lld's libxml2.so.16."""
        try:
            _dirs = sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"))
        except Exception:
            _dirs = []
        for _d in reversed(_dirs):
            try:
                if os.path.isdir(_d):
                    return _d
            except Exception:
                continue
        return None

    def _fix_ld_env(self, env):
        """Prepend SDK llvm/lib to LD_LIBRARY_PATH in the given env dict."""
        _sdk_lib = self._sdk_llvm_libdir()
        if _sdk_lib:
            _cur = env.get("LD_LIBRARY_PATH", "") or ""
            if not _cur.split(os.pathsep).count(_sdk_lib):
                env["LD_LIBRARY_PATH"] = _sdk_lib + (os.pathsep + _cur if _cur else "")
        return env

    def _conf_list(self, name):
        try:
            val = self.conf.get(name, default=[])
        except Exception:
            return []
        if isinstance(val, (list, tuple)):
            return [str(v) for v in val]
        if isinstance(val, str) and val:
            return [val]
        if val:
            return [str(val)]
        return []

    def _ohos_flags(self):
        # Conan OHOS profile carries no cflags by default, but HMBS/CI may
        # inject target/sysroot/hardening via tools.build conf. Forward
        # everything so bare `cc` invocations still target OHOS correctly.
        cflags = self._conf_list("tools.build:cflags")
        defines = self._conf_list("tools.build:defines")
        exelink = self._conf_list("tools.build:exelinkflags")
        sharedlink = self._conf_list("tools.build:sharedlinkflags")
        return cflags, defines, exelink, sharedlink

    def _resolve_tool(self, *candidates):
        # R33: prefer the conf value, but only when the file really exists
        # here. The profile pins absolute /data/service/hnp/bin/* paths that
        # are inaccessible inside the HMBS preflight sandbox
        # ("/bin/sh: /data/service/hnp/bin/clang: inaccessible or not found");
        # in that case fall back to PATH lookup (hmbs prepends the real tool
        # dirs to buildenv PATH, lzsa precedent uses bare "clang").
        for _c in candidates:
            if not _c:
                continue
            if os.path.isabs(_c):
                if os.path.isfile(_c):
                    return _c
                _w = shutil.which(os.path.basename(_c))
                if _w:
                    return _w
            else:
                _w = shutil.which(_c)
                if _w:
                    return _w
                if os.path.isfile(_c):
                    return _c
        for _c in candidates:
            if _c:
                return _c
        return "clang"

    def _toolchain(self):
        # conan 2.29/2.30 OHOS build rejects the ":c" sub-key form; read the
        # dict form and index it.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = self._resolve_tool(compilers.get("c"), "aarch64-linux-ohos-clang",
                                "clang")
        ar = self._resolve_tool(compilers.get("ar"), "llvm-ar", "ar")
        ranlib = self._resolve_tool(compilers.get("ranlib"), "llvm-ranlib", "ranlib")
        make = self._resolve_tool(
            self.conf.get("user.hmbs:make_path", check_type=str, default=None),
            os.environ.get("HMBS_MAKE"),
            "make",
        )
        return cc, ar, ranlib, make

    def _pick_tmp(self, fallback):
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v and _v != "/tmp":
                return _v
        return fallback

    def _run_noshell(self, args, cwd=None):
        # Shell-free exec: bypass /bin/sh -c so dash never creates
        # /tmp/sh*.tmp on read-only /tmp. List form directly execs.
        # Never fall back to bare /tmp.
        _tmp = self._pick_tmp(os.path.join(self.build_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        _env = dict(os.environ)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _env[_k] = _tmp
        # Raw subprocess bypasses conanbuild env, so re-apply the E266
        # lld runtime path here (CI worker lacks it ambiently).
        self._fix_ld_env(_env)
        self.output.info("noshell: %s" % " ".join(args))
        subprocess.run(args, check=True, cwd=cwd or self.source_folder,
                       env=_env)

    def _emit_upstream_marker(self, marker):
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        self.output.info(line)
        # Dual channel: harness scans stdout tail, conan may route
        # output.info elsewhere, so print the identical line (cld2 pattern).
        print(line, flush=True)

    def _vendor_dir(self):
        # cJSON.c/.h are fetched at source() into source_folder/vendor_cjson;
        # fall back to the export/recipe copies only for the authored harness
        # (never a real cJSON.c). source_folder is authoritative.
        for cand in (
            os.path.join(self.source_folder or "", "vendor_cjson"),
            os.path.join(self.export_sources_folder or "", "vendor_cjson"),
            os.path.join(self.recipe_folder or "", "vendor_cjson"),
        ):
            if cand and os.path.isfile(os.path.join(cand, "cJSON.c")):
                return cand
        return None

    def _run_upstream_basic_tests(self, cc):
        """Build the mustach tool against fetched cJSON and run basic-tests.

        Returns (discovered, executed, passed, failed, skipped, note).
        test1..test5/test7/test8 run the real `mustach` tool binary with the
        upstream fixture args; test6 runs the cJSON port of
        test-custom-write.c (same fixtures, same dotest.sh assertion).
        spec-tests are excluded (need git clone of mustache/spec + network).
        """
        src = self.source_folder
        vendor = self._vendor_dir()
        if not vendor:
            return (8, 0, 0, 8, 0, "vendor_cjson/cJSON.c missing - refusing false run")
        for _f in ("cJSON.c", "cJSON.h", "test-custom-write-cjson.c",
                   "cjson/cJSON.h"):
            _p = os.path.join(vendor, _f)
            try:
                if (not os.path.isfile(_p)) or os.path.getsize(_p) <= 0:
                    return (8, 0, 0, 8, 0, "vendored %s empty/missing" % _f)
            except OSError:
                return (8, 0, 0, 8, 0, "vendored %s unreadable" % _f)
        for _f in ("mustach.c", "mustach-wrap.c", "mustach-cjson.c",
                   "mustach-tool.c", "dotest.sh"):
            if not os.path.isfile(os.path.join(src, _f)):
                return (8, 0, 0, 8, 0, "upstream %s missing in source" % _f)
        # Writable work dir for tool binaries + outputs (never /tmp).
        _tmp = self._pick_tmp(os.path.join(self.build_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        work = os.path.join(self.build_folder, "upstream_test")
        try:
            os.makedirs(work, exist_ok=True)
        except Exception:
            pass
        _env = dict(os.environ)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _env[_k] = _tmp
        # E266: raw subprocess bypasses conanbuild env; re-apply SDK
        # llvm/lib so the link steps can start lld on CI workers.
        self._fix_ld_env(_env)
        cflags, defines, exelink, _sharedlink = self._ohos_flags()
        verdef = '-DVERSION="%s"' % self.version
        base = ["-fPIC", "-Wall", "-Wextra", verdef]
        base += ["-D%s" % d for d in defines]
        base += cflags
        inc_src = "-I%s" % src
        inc_vendor = "-I%s" % vendor
        # Compile objects (absolute paths, cwd=work).
        objs = {}
        jobs = [
            ("cjson", [cc] + base + [inc_vendor, "-c",
             os.path.join(vendor, "cJSON.c"), "-o", os.path.join(work, "cJSON.o")]),
            ("core", [cc] + base + [inc_src, inc_vendor, "-c",
             os.path.join(src, "mustach.c"), "-o", os.path.join(work, "mustach.o")]),
            ("wrap", [cc] + base + [inc_src, inc_vendor, "-c",
             os.path.join(src, "mustach-wrap.c"), "-o", os.path.join(work, "mustach-wrap.o")]),
            ("cjsonbe", [cc] + base + [inc_src, inc_vendor, "-c",
             os.path.join(src, "mustach-cjson.c"), "-o", os.path.join(work, "mustach-cjson.o")]),
            ("tool", [cc] + base + [inc_src, inc_vendor, "-DTOOL=MUSTACH_TOOL_CJSON", "-c",
             os.path.join(src, "mustach-tool.c"), "-o", os.path.join(work, "mustach-tool.o")]),
            ("custom", [cc] + base + [inc_src, inc_vendor, "-c",
             os.path.join(vendor, "test-custom-write-cjson.c"), "-o",
             os.path.join(work, "test-custom-write-cjson.o")]),
        ]
        for label, cmd in jobs:
            self.output.info("upstream-build %s: %s" % (label, " ".join(cmd)))
            try:
                subprocess.run(cmd, check=True, cwd=work, env=_env)
            except Exception as e:
                return (8, 0, 0, 8, 0, "compile %s failed: %s" % (label, str(e)[:200]))
        mustach_bin = os.path.join(work, "mustach")
        custom_bin = os.path.join(work, "test-custom-write-cjson")
        try:
            subprocess.run(
                [cc, os.path.join(work, "mustach.o"), os.path.join(work, "mustach-wrap.o"),
                 os.path.join(work, "mustach-cjson.o"), os.path.join(work, "cJSON.o"),
                 os.path.join(work, "mustach-tool.o"), "-o", mustach_bin] + exelink,
                check=True, cwd=work, env=_env)
            subprocess.run(
                [cc, os.path.join(work, "test-custom-write-cjson.o"),
                 os.path.join(work, "mustach.o"), os.path.join(work, "mustach-wrap.o"),
                 os.path.join(work, "mustach-cjson.o"), os.path.join(work, "cJSON.o"),
                 "-o", custom_bin] + exelink,
                check=True, cwd=work, env=_env)
        except Exception as e:
            return (8, 0, 0, 8, 0, "link tool failed: %s" % str(e)[:200])
        # Falsifiability probe: binaries must exist and be non-empty.
        for _b in (mustach_bin, custom_bin):
            try:
                if (not os.path.isfile(_b)) or os.path.getsize(_b) <= 0:
                    return (8, 0, 0, 8, 0, "tool binary empty: %s" % os.path.basename(_b))
            except OSError:
                return (8, 0, 0, 8, 0, "tool binary unreadable")
        self.output.info("upstream tools built: mustach=%s custom=%s"
                         % (mustach_bin, custom_bin))
        # Run the 8 cases with upstream fixtures + dotest.sh semantics
        # (run tool, diff -w resu.ref resu.last). Implemented in Python so
        # read-only /tmp and missing valgrind never matter (NOVALGRIND=1).
        cases = [
            ("test1", mustach_bin, ["json", "must"]),
            ("test2", mustach_bin, ["json", "must"]),
            ("test3", mustach_bin, ["json", "must"]),
            ("test4", mustach_bin, ["json", "must"]),
            ("test5", mustach_bin, ["json", "must"]),
            ("test6", custom_bin, ["json", "-U", "must", "-l", "must", "-x", "must"]),
            ("test7", mustach_bin, ["json", "base.mustache"]),
            ("test8", mustach_bin, ["json", "must"]),
        ]
        discovered = len(cases)
        passed = 0
        failures = []
        diff_bin = shutil.which("diff")
        for name, binary, args in cases:
            tdir = os.path.join(src, name)
            # Fixture guard: refuse empty-file false green (toybox-tar lesson).
            need = ["resu.ref"] + args
            ok = True
            for _a in need:
                if _a.startswith("-"):
                    continue
                _p = os.path.join(tdir, _a)
                try:
                    if (not os.path.isfile(_p)) or os.path.getsize(_p) <= 0:
                        failures.append("%s: fixture %s empty/missing" % (name, _a))
                        ok = False
                        break
                except OSError:
                    failures.append("%s: fixture %s unreadable" % (name, _a))
                    ok = False
                    break
            if not ok:
                continue
            out_path = os.path.join(work, name + ".resu.last")
            try:
                with open(out_path, "wb") as _of:
                    _pr = subprocess.run(
                        [binary] + args, cwd=tdir, stdout=_of,
                        stderr=subprocess.PIPE, env=_env, timeout=120, check=False)
                if _pr.returncode != 0:
                    failures.append("%s: tool rc=%d stderr=%s" % (
                        name, _pr.returncode, (_pr.stderr or b"")[:200].decode("utf-8", "replace")))
                    continue
                try:
                    if os.path.getsize(out_path) <= 0:
                        failures.append("%s: empty output - refusing false green" % name)
                        continue
                except OSError:
                    failures.append("%s: output unreadable" % name)
                    continue
                ref_path = os.path.join(tdir, "resu.ref")
                if diff_bin:
                    _dr = subprocess.run(
                        [diff_bin, "-w", ref_path, out_path],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        env=_env, timeout=60, check=False)
                    if _dr.returncode == 0:
                        passed += 1
                        self.output.info("upstream %s: result ok" % name)
                    else:
                        _tail = (_dr.stdout or b"")[:500].decode("utf-8", "replace")
                        failures.append("%s: diff differs: %s" % (name, _tail))
                else:
                    # Python fallback approximating `diff -w` (ignore all
                    # whitespace): compare whitespace-stripped byte streams.
                    try:
                        with open(ref_path, "rb") as _rf:
                            _ref = _rf.read()
                        with open(out_path, "rb") as _of2:
                            _got = _of2.read()
                        import re as _re
                        _norm = lambda b: _re.sub(rb"\s+", b"", b)
                        if _norm(_ref) == _norm(_got) and len(_norm(_ref)) > 0:
                            passed += 1
                            self.output.info("upstream %s: result ok (py-diff)" % name)
                        else:
                            failures.append("%s: py-diff differs (ref=%d got=%d)"
                                            % (name, len(_ref), len(_got)))
                    except Exception as _e:
                        failures.append("%s: py-diff error %s" % (name, str(_e)[:120]))
            except Exception as _e:
                failures.append("%s: exec error %s" % (name, str(_e)[:150]))
        failed = discovered - passed
        note = "; ".join(failures[:3])[:600] if failures else "make basic-tests 8/8 passed (cJSON tool)"
        return (discovered, discovered if passed or failed else 0, passed, failed, 0, note)

    def build(self):
        # Ensure writable tmp is exported before any tool runs. Never /tmp.
        _tmp = self._pick_tmp(os.path.join(self.build_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        cc, ar, ranlib, make = self._toolchain()
        self.output.info(
            "libmustach-core toolchain: CC=%s AR=%s RANLIB=%s MAKE=%s"
            % (cc, ar, ranlib, make)
        )
        # Core-only split build: no JSON backend, no CLI tool. EFLAGS already
        # carries -fPIC -Wall -Wextra upstream; pass CC/AR/RANLIB explicitly.
        # Upstream builds in-source, so run everything in source_folder.
        src = self.source_folder
        if self.options.shared:
            # R9: single job on OHOS.
            core_vars = ["cjson=no", "jsonc=no", "jansson=no",
                         "libs=split", "tool=none"]
            self._run_noshell(
                [make, "CC=%s" % cc, "AR=%s" % ar, "RANLIB=%s" % ranlib,
                 "-j1"] + core_vars,
                cwd=src,
            )
            self._run_noshell(
                [make, "install", "CC=%s" % cc, "AR=%s" % ar,
                 "RANLIB=%s" % ranlib, "-j1"] + core_vars
                + ["DESTDIR=%s" % self.package_folder, "PREFIX=/"],
                cwd=src,
            )
        else:
            cflags, defines, _exelink, _sharedlink = self._ohos_flags()
            # Quote VERSION as a C string literal (cutmp3 precedent:
            # -DVERSION=\"x\"); bare -DVERSION=1.2.10 is not a valid token
            # when mustach.c stringifies it.
            verdef = '-DVERSION="%s"' % self.version
            base_cflags = ["-c", "-fPIC", "-Wall", "-Wextra", verdef]
            base_cflags += ["-D%s" % d for d in defines]
            base_cflags += cflags
            self._run_noshell(
                [cc] + base_cflags + ["-o", "mustach.o", "mustach.c"],
                cwd=src,
            )
            self._run_noshell(
                [cc] + base_cflags + ["-o", "mustach-wrap.o", "mustach-wrap.c"],
                cwd=src,
            )
            self._run_noshell(
                [ar, "rcs", "libmustach-core.a",
                 "mustach.o", "mustach-wrap.o"],
                cwd=src,
            )
            self._run_noshell([ranlib, "libmustach-core.a"], cwd=src)

        # Upstream basic-tests (test1..test8) run for real in build() against
        # official cJSON 1.7.19 (MIT) fetched in source(): the `mustach` tool
        # is built with TOOL=MUSTACH_TOOL_CJSON and each fixture runs through
        # the upstream dotest.sh assertion (run tool, diff -w resu.ref).
        # test6 uses the cJSON port of test-custom-write.c (same fixtures,
        # same assertion). spec-tests are excluded: they git-clone
        # mustache/spec @ v1.4.1 (network) — documented in MANIFEST/PR.
        _disc, _exec, _pass, _fail, _skip, _note = self._run_upstream_basic_tests(cc)
        if _fail == 0 and _skip == 0 and _disc > 0 and _exec == _disc and _pass == _disc:
            _status = "passed"
        elif _fail > 0:
            _status = "failed"
        else:
            _status = "failed"
        _marker_obj = {
            "status": _status,
            "framework": "makefile",
            "command": "make basic-tests (cJSON tool, test6 via cJSON port)",
            "discovered": _disc,
            "executed": _exec,
            "passed": _pass,
            "failed": _fail,
            "skipped": _skip,
        }
        if _status != "passed":
            _marker_obj["reason"] = _note
        self._emit_upstream_marker(_marker_obj)
        # Persist for test_package re-emit (conan cache hit => build()
        # skipped, test() must still reproduce the marker every round).
        try:
            _resdir = os.path.join(self.build_folder, "upstream_res")
            os.makedirs(_resdir, exist_ok=True)
            with open(os.path.join(_resdir, "upstream_test_result.json"),
                      "w", encoding="utf-8", newline="\n") as _f:
                json.dump(_marker_obj, _f, ensure_ascii=False)
        except Exception:
            pass
        if _status != "passed":
            raise ConanException("upstream basic-tests failed: %s" % _note)

    def package(self):
        # Persist upstream marker into the package for cache-hit rounds.
        try:
            copy(
                self,
                "upstream_test_result.json",
                src=os.path.join(self.build_folder, "upstream_res"),
                dst=os.path.join(self.package_folder, "res"),
                keep_path=False,
            )
        except Exception:
            pass
        if self.options.shared:
            # make install already staged lib/include/pkgconfig/man under
            # DESTDIR=package_folder; only the license file is missing.
            copy(
                self,
                "LICENSE.txt",
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
                keep_path=False,
            )
        else:
            copy(
                self,
                "libmustach-core.a",
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "lib"),
                keep_path=False,
            )
            for header in ("mustach.h", "mustach-wrap.h"):
                copy(
                    self,
                    header,
                    src=self.source_folder,
                    dst=os.path.join(self.package_folder, "include", "mustach"),
                    keep_path=False,
                )
            copy(
                self,
                "LICENSE.txt",
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.libs = ["mustach-core"]
        # Headers live in include/mustach (upstream layout); also expose
        # include so `#include <mustach.h>` keeps working.
        self.cpp_info.includedirs = ["include", "include/mustach"]
        self.cpp_info.set_property("cmake_file_name", "libmustach-core")
        self.cpp_info.set_property(
            "cmake_target_name", "libmustach-core::libmustach-core"
        )
        self.cpp_info.set_property("pkg_config_name", "libmustach-core")
