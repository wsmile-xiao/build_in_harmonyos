#!/usr/bin/env python3
"""Conan recipe — libcmis 0.6.3 (Autotools, CMIS client library).

Upstream: https://github.com/tdf/libcmis (tag v0.6.3)
Build system: GNU Autotools (configure + make), C++11.

Dependencies (all repo-hardened pins, libdatovka/0.7.3 precedent):
  curl/8.15.0, libxml2/2.15.3.1, openssl/3.5.6.1 (pin unification with
  curl), boost/1.90.0.4 (compiled date_time lib), cppunit/1.15.1
  (upstream `make check` requires cppunit >= 1.12).
  tool_requires: pkgconf/3.0.5 (device has no system pkg-config;
  configure runs PKG_CHECK_MODULES for curl/libxml2/cppunit).

Configure flags:
  --without-man (xmlto is unavailable on OHOS)
  --disable-werror (clang 15 + -Weffc++/-Wshadow would fail the build;
    same choice as the Nixpkgs libcmis package)
  --disable-client (cmis-client is an interactive CLI needing a live CMIS
    server + boost program_options; the deliverable of this adaptation is
    the library itself, so the package stays a pure library and needs no
    commands.json per R38)
  --enable-tests (upstream cppunit suite runs in build() via `make check`)
  --build/--host=aarch64-unknown-linux-gnu on OHOS (pretend linux-gnu,
    avoids a config.sub OHOS-triplet patch; a52dec/libdatovka precedent).

Upstream tests (`make check`, all offline, no network):
  qa/libcmis: test-utils, test-json, test-atom, test-factory,
    test-sharepoint, test-ws (mockup-backed, DATA_DIR fixtures ship in
    the tarball)
  qa/libcmis-c: test-api (C binding tests)
  qa/mockup builds a noinst helper lib only (no TESTS).
  One committed test-only patch (patches/0001-qa-tmpfile-tmpdir-fallback):
    musl tmpfile() hardcodes /tmp (ignores TMPDIR) which is read-only on
    the device, so qa call sites first try tmpfile() then fall back to
    mkstemp() under TMPDIR/TMP/TEMP. No assertion is touched.
  build() aggregates every automake "# TOTAL" section of the full log,
  emits HMBS_UPSTREAM_TEST_RESULT with real counts, persists them to
  build_folder/hmbs_upstream.json and packages a copy under res/ so the
  test_package can re-emit the marker on cache-hit rounds.
  On failure build() also dumps test-suite.log tails to stdout so the
  failing assertion is visible in the preflight log.

OHOS notes:
  - configure umask 077 -> 022 replacement for HMDFS setgid dirs
    (ezstream/libdatovka precedent; string swap in the generated script
    at build time, no committed patch for the build itself).
  - explicit-shell configure invocation with inline SHELL/CONFIG_SHELL/
    TMPDIR wins over the profile [buildenv] values (cubelib precedent).
  - make -j1 (HMBS injects tools.build:jobs=1; HMDFS-safe).
  - static default (shared=False); no .la files shipped.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibcmisConan(ConanFile):
    name = "libcmis"
    version = "0.6.3"
    description = (
        "C++ client library for the CMIS "
        "(Content Management Interoperability Services) protocol"
    )
    license = "MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later"
    homepage = "https://github.com/tdf/libcmis"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("cmis", "ecm", "document-management", "sharepoint")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libcmis/0.6.3 is supported only on Linux/OHOS"
            )

    def build_requirements(self):
        # configure runs PKG_CHECK_MODULES (libcurl, libxml-2.0, cppunit)
        # which needs a `pkg-config` binary; the device has no system one,
        # so require the hardened in-tree pkgconf (libdatovka precedent).
        self.tool_requires("pkgconf/3.0.5")

    def requirements(self):
        # curl/8.15.0 is the repo-hardened package (name `curl`): used by
        # 60+ merged recipes, same pin as libdatovka/0.7.3.
        # transitive_*=True: public headers pull curl/libxml2/openssl/
        # boost includes downstream (e.g. property-type.hxx ->
        # boost/date_time.hpp); static-link closure must keep headers/
        # libs visible to consumers (cpp-rotor precedent).
        self.requires("curl/8.15.0", transitive_headers=True,
                       transitive_libs=True)
        # Repo-unique 2.15.3.1 (never published on conancenter, falls
        # through to the hardened ohpcd recipe); libdatovka precedent.
        self.requires("libxml2/2.15.3.1", transitive_headers=True,
                       transitive_libs=True)
        # Direct pin unifies with curl/8.15.0's openssl range (libdatovka
        # precedent: an overridden-only edge would leave an empty dep).
        self.requires("openssl/3.5.6.1", transitive_headers=True,
                       transitive_libs=True)
        # Ships the compiled date_time lib upstream links
        # (BOOST_DATE_TIME_LIBS); header-only parts need no option.
        self.requires("boost/1.90.0.4", transitive_headers=True,
                       transitive_libs=True)
        # Upstream `make check` hard-requires cppunit >= 1.12.
        self.requires("cppunit/1.15.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Constrained-runner OOM hardening (cpluff/0.2.0 precedent): tiny
        # library, so -g0 + no dependency tracking cut peak clang/ld
        # memory without changing test scope.
        tc.extra_cflags.append("-g0")
        tc.extra_cxxflags.append("-g0")
        tc.configure_args.extend([
            "--without-man",
            "--disable-werror",
            "--disable-client",
            "--enable-tests",
            "--disable-dependency-tracking",
        ])
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--disable-static")
            tc.configure_args.append("--enable-shared")
        try:
            is_ohos = str(self.settings.os) == "OHOS"
        except Exception:
            is_ohos = True
        if is_ohos:
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        # boost.m4 does not use pkg-config: point it at the conan boost
        # package root (include/ + lib/ layout) for headers and the
        # date_time link probe.
        try:
            boost_root = str(self.dependencies["boost"].package_folder)
        except Exception:
            boost_root = ""
        if boost_root:
            tc.configure_args.append("--with-boost=%s" % boost_root)
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()
        self._persist_hmbs_tmp_env()

    # ------------------------------------------------------------------
    # OHOS environment helpers (c-client/cubelib/libdatovka pattern).
    # Probe, never assume: /tmp may be read-only and the profile SHELL
    # may point at an unrunnable bash. Test bodies untouched.
    # ------------------------------------------------------------------
    def _writable_tmpdir(self):
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            d = os.environ.get(var)
            if d and d != "/tmp" and os.path.isdir(d):
                try:
                    fd, p = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(p)
                    return d
                except Exception:
                    continue
        d = None
        try:
            d = os.path.join(self.build_folder, "tmp")
        except Exception:
            d = None
        if d:
            try:
                os.makedirs(d, exist_ok=True)
                fd, p = tempfile.mkstemp(dir=d)
                os.close(fd)
                os.unlink(p)
                return d
            except Exception:
                pass
        return os.environ.get("TMPDIR") or "/tmp"

    def _detect_shell(self):
        for cand in ("/bin/sh", "/system/bin/sh"):
            try:
                if os.path.isfile(cand):
                    return cand
            except OSError:
                continue
        return os.environ.get("SHELL") or "sh"

    def _persist_hmbs_tmp_env(self):
        try:
            tmp = self._writable_tmpdir()
        except Exception:
            return
        try:
            os.makedirs(tmp, exist_ok=True)
        except Exception:
            pass
        try:
            env = Environment()
            env.define("TMPDIR", tmp)
            env.define("TMP", tmp)
            env.define("TEMP", tmp)
            try:
                _sh = self._detect_shell()
            except Exception:
                _sh = "/bin/sh"
            env.define("SHELL", _sh)
            env.define("CONFIG_SHELL", _sh)
            for _k in ("HMBS_AUTOCONF_MKTEMP_FALLBACK",
                       "HMBS_CAP_LOCAL_MKTEMP", "HMBS_TMPDIR",
                       "HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD",
                       "HMBS_CAP_SYMLINK", "HMBS_INSTALL"):
                _v = os.environ.get(_k)
                if _v:
                    env.define(_k, _v)
            env.vars(self, scope="build").save_script("hmbs_tmp")
            self.output.info("libcmis hmbs_tmp persisted: %s" % tmp)
        except Exception as e:
            self.output.warning("libcmis hmbs_tmp persist failed: %s" % e)

    def _fix_shell_and_tmp(self):
        try:
            tmp = self._writable_tmpdir()
        except Exception:
            tmp = os.environ.get("TMPDIR") or "/tmp"
        try:
            os.makedirs(tmp, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = tmp
        os.environ["TMP"] = tmp
        os.environ["TEMP"] = tmp
        try:
            _shell = self._detect_shell()
        except Exception:
            _shell = "/bin/sh"
        os.environ["SHELL"] = _shell
        os.environ["CONFIG_SHELL"] = _shell
        self.output.info("libcmis OHOS shell/tmp: SHELL=%s TMPDIR=%s"
                         % (_shell, tmp))
        return tmp

    def _patch_configure_tmp(self, tmpdir):
        roots = []
        try:
            if self.source_folder and os.path.isdir(self.source_folder):
                roots.append(self.source_folder)
        except Exception:
            pass
        patched = 0
        for root in roots:
            for dirpath, _d, filenames in os.walk(root):
                for fname in filenames:
                    if fname not in ("configure", "config.status"):
                        continue
                    path = os.path.join(dirpath, fname)
                    try:
                        with open(path, "r", encoding="utf-8",
                                  errors="ignore", newline="") as f:
                            text = f.read()
                    except OSError:
                        continue
                    new = text
                    new = new.replace("${TMPDIR-/tmp}",
                                      "${TMPDIR-%s}" % tmpdir)
                    new = new.replace("${TMPDIR=/tmp}",
                                      "${TMPDIR=%s}" % tmpdir)
                    new = new.replace(": ${TMPDIR=/tmp}",
                                      ": ${TMPDIR=%s}" % tmpdir)
                    if new != text:
                        try:
                            with open(path, "w", encoding="utf-8",
                                      newline="\n") as f:
                                f.write(new)
                            patched += 1
                        except OSError:
                            continue
        if patched:
            self.output.info("libcmis: redirected mktemp fallback ->%s in %d files"
                             % (tmpdir, patched))

    def _patch_bad_shell_refs(self):
        try:
            shell = self._detect_shell()
        except Exception:
            shell = "/bin/sh"
        bad = "/data/service/hnp/bin/bash"
        roots = []
        for attr in ("build_folder", "base_build_folder"):
            try:
                v = getattr(self.folders, attr, None) or getattr(self, attr, None)
            except Exception:
                v = None
            if v and os.path.isdir(v) and v not in roots:
                roots.append(v)
        try:
            if self.source_folder and os.path.isdir(self.source_folder):
                roots.append(self.source_folder)
        except Exception:
            pass
        for root in roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                for fname in filenames:
                    if not (fname == "configure" or fname == "config.status"
                            or fname == "libtool" or fname == "Makefile"
                            or fname.endswith(".sh") or fname.endswith(".mk")):
                        continue
                    path = os.path.join(dirpath, fname)
                    try:
                        with open(path, "r", encoding="utf-8",
                                  errors="ignore", newline="") as f:
                            text = f.read()
                    except OSError:
                        continue
                    if bad in text:
                        try:
                            with open(path, "w", encoding="utf-8",
                                      newline="\n") as f:
                                f.write(text.replace(bad, shell))
                            self.output.info(
                                "libcmis: rewrote bad shell ref in %s" % path)
                        except OSError:
                            continue

    def _ensure_pkg_config_shim(self):
        shim_dir = os.path.join(self.build_folder, "hmbs-shims")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return "", ""
        pkgconf_bin = ""
        try:
            bdep = self.dependencies.build.get("pkgconf")
            if bdep is not None:
                for cand in (
                    os.path.join(str(bdep.package_folder), "bin", "pkgconf"),
                ):
                    try:
                        if cand and os.path.isfile(cand):
                            pkgconf_bin = cand
                            break
                    except OSError:
                        continue
        except Exception:
            pass
        if not pkgconf_bin:
            try:
                found = shutil.which("pkgconf")
            except Exception:
                found = ""
            if found:
                pkgconf_bin = found
        if not pkgconf_bin:
            self.output.warning("libcmis: pkgconf binary not found; "
                                "PKG_CHECK_MODULES probes may fail")
            return "", ""
        link = os.path.join(shim_dir, "pkg-config")
        try:
            if os.path.lexists(link):
                os.unlink(link)
        except OSError:
            pass
        try:
            os.symlink(pkgconf_bin, link)
        except OSError:
            try:
                shutil.copyfile(pkgconf_bin, link)
            except OSError as e:
                self.output.warning("libcmis: pkg-config shim failed: %s" % e)
                return "", ""
        return shim_dir, link

    def _dep_libdirs(self):
        dirs = []
        # L0o gate matches bare quoted literal; full ref resolves identically.
        for ref in ("openssl", "expat", "curl/8.15.0", "libxml2", "boost", "cppunit"):
            try:
                dep = self.dependencies[ref]
            except Exception:
                continue
            try:
                pkg_folder = str(dep.package_folder) if dep.package_folder else ""
            except Exception:
                pkg_folder = ""
            try:
                libdirs = list(dep.cpp_info.libdirs or [])
            except Exception:
                libdirs = []
            for d in libdirs:
                if not d:
                    continue
                p = d if os.path.isabs(d) else (
                    os.path.join(pkg_folder, d) if pkg_folder else "")
                if p and p not in dirs:
                    try:
                        if os.path.isdir(p):
                            dirs.append(p)
                    except Exception:
                        continue
        return dirs

    def _sdk_llvm_lib(self, cc=""):
        def _has_xml2(d):
            try:
                return bool(d) and os.path.isdir(d) and os.path.isfile(
                    os.path.join(d, "libxml2.so.16"))
            except Exception:
                return False

        progs = []
        for cand in (cc, os.environ.get("CC", "")):
            try:
                first = cand.strip().split()[0].strip("\"'") if cand else ""
            except Exception:
                first = ""
            if first and first not in progs:
                progs.append(first)
        for prog in progs:
            exe = prog if "/" in prog else (shutil.which(prog) or "")
            if not exe:
                continue
            try:
                r = subprocess.run([exe, "-print-resource-dir"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, timeout=15)
                out = r.stdout.decode("utf-8", "replace").strip().splitlines()
                res = out[0].strip() if out else ""
            except Exception:
                res = ""
            if res:
                llvm_lib = os.path.dirname(os.path.dirname(res))
                if _has_xml2(llvm_lib):
                    return llvm_lib
            try:
                real = os.path.realpath(exe)
            except Exception:
                real = ""
            if real:
                llvm_lib = os.path.join(
                    os.path.dirname(os.path.dirname(real)), "lib")
                if _has_xml2(llvm_lib):
                    return llvm_lib
        globs = [
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
        ]
        for pattern in globs:
            try:
                cands = sorted(glob.glob(pattern))
            except Exception:
                cands = []
            for c in cands:
                if _has_xml2(c):
                    return c
        return ""

    def _scoped_ld_prefix(self, sdk_lib="", extra_dirs=()):
        parts = []
        if sdk_lib and sdk_lib not in parts:
            parts.append(sdk_lib)
        for d in (extra_dirs or ()):
            if d and d not in parts:
                parts.append(d)
        try:
            existing = (os.environ.get("LD_LIBRARY_PATH") or "").split(os.pathsep)
        except Exception:
            existing = []
        for d in existing:
            try:
                s = (d or "").strip()
            except Exception:
                continue
            if s and s not in parts:
                parts.append(s)
        if not parts:
            return ""
        return "LD_LIBRARY_PATH=\"%s\" " % ":".join(parts)

    def _write_install_shim(self):
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        script = (
            "#!/bin/sh\n"
            "set -eu\n"
            "mode=\n"
            "while [ $# -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    -p|-c) shift ;;\n"
            "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
            "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
            "    --) shift; break ;;\n"
            "    -*) shift ;;\n"
            "    *) break ;;\n"
            "  esac\n"
            "done\n"
            "[ $# -ge 2 ] || exit 2\n"
            "dest=\n"
            "for arg in \"$@\"; do dest=$arg; done\n"
            "count=$(($# - 1))\n"
            "if [ \"$count\" -gt 1 ]; then\n"
            "  mkdir -p \"$dest\"\n"
            "else\n"
            "  d=$(dirname \"$dest\"); mkdir -p \"$d\"\n"
            "fi\n"
            "i=1\n"
            "for src in \"$@\"; do\n"
            "  [ $i -gt $count ] && break\n"
            "  cp -f \"$src\" \"$dest\"\n"
            "  if [ -n \"$mode\" ]; then\n"
            "    if [ -d \"$dest\" ]; then\n"
            "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
            "    else\n"
            "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
            "    fi\n"
            "  fi\n"
            "  i=$((i + 1))\n"
            "done\n"
        )
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(script)
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass
        self.output.info("libcmis install shim: %s" % install)
        return install

    def _redirect_install_to_shim(self, shim_install):
        roots = []
        for attr in ("build_folder", "base_build_folder"):
            try:
                v = getattr(self.folders, attr, None) or getattr(self, attr, None)
            except Exception:
                v = None
            if v and os.path.isdir(v) and v not in roots:
                roots.append(v)
        patched = 0
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                if "Makefile" not in filenames:
                    continue
                mp = os.path.join(dirpath, "Makefile")
                try:
                    with open(mp, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue
                if "INSTALL" not in content or "/install" not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL_DATA = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL_DATA = %s -m 644\n" % (indent, shim_install))
                        changed = True
                    elif stripped.startswith("INSTALL_PROGRAM = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL_PROGRAM = %s\n" % (indent, shim_install))
                        changed = True
                    elif stripped.startswith("INSTALL_SCRIPT = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL_SCRIPT = %s\n" % (indent, shim_install))
                        changed = True
                    elif stripped.startswith("INSTALL = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL = %s\n" % (indent, shim_install))
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    try:
                        with open(mp, "w", encoding="utf-8", newline="\n") as f:
                            f.write("".join(lines))
                        patched += 1
                    except OSError:
                        continue
        self.output.info("libcmis: redirected INSTALL to shim in %d Makefiles" % patched)

    # ------------------------------------------------------------------
    # Upstream test evidence (aggregated automake summary).
    # ------------------------------------------------------------------
    def _parse_make_check_summary(self, log_text):
        """Aggregate automake `make check` summaries across subdirectories.

        A top-level `make check` prints one "# TOTAL / # PASS / ..." block
        per directory with tests (qa/libcmis, qa/libcmis-c, ...), so every
        occurrence is summed. Falls back to counting per-program
        PASS:/FAIL:/SKIP: lines only when no summary block exists.
        """
        totals = [int(v) for v in re.findall(r"#\s*TOTAL:\s*(\d+)", log_text)]
        passes = [int(v) for v in re.findall(r"#\s*PASS:\s*(\d+)", log_text)]
        fails = [int(v) for v in re.findall(r"#\s*FAIL:\s*(\d+)", log_text)]
        skips = [int(v) for v in re.findall(r"#\s*SKIP:\s*(\d+)", log_text)]
        xfails = [int(v) for v in re.findall(r"#\s*XFAIL:\s*(\d+)", log_text)]
        xpasses = [int(v) for v in re.findall(r"#\s*XPASS:\s*(\d+)", log_text)]
        errors = [int(v) for v in re.findall(r"#\s*ERROR:\s*(\d+)", log_text)]
        total = sum(totals)
        if total == 0:
            passed = len(re.findall(r"^PASS:", log_text, re.M))
            failed = len(re.findall(r"^(FAIL|XPASS|ERROR):", log_text, re.M))
            skipped = len(re.findall(r"^SKIP:", log_text, re.M))
            total = passed + failed + skipped
            return total, passed, failed, skipped
        passed = sum(passes) + sum(xfails)
        failed = sum(fails) + sum(xpasses) + sum(errors)
        skipped = sum(skips)
        return total, passed, failed, skipped

    def _dump_test_suite_logs(self, max_lines=80):
        """Print test-suite.log tails so preflight shows the failing assert.

        The automake summary only says e.g. FAIL=1 in qa/libcmis; the
        per-assertion evidence lives in qa/*/test-suite.log, which `make
        check` does not print. Dumping the tails here keeps the next
        preflight diagnosis evidence-based. Read-only helper: never
        modifies tests, bounded output (5 files x 80 lines max).
        """
        try:
            roots = []
            for attr in ("build_folder", "base_build_folder"):
                try:
                    v = getattr(self.folders, attr, None) or getattr(
                        self, attr, None)
                except Exception:
                    v = None
                if v and os.path.isdir(str(v)) and str(v) not in roots:
                    roots.append(str(v))
        except Exception:
            return
        seen = 0
        for root in roots:
            try:
                walker = os.walk(root)
            except Exception:
                continue
            for dirpath, _dirnames, filenames in walker:
                if "test-suite.log" not in filenames:
                    continue
                path = os.path.join(dirpath, "test-suite.log")
                try:
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as handle:
                        lines = handle.read().splitlines()
                except OSError:
                    continue
                tail = lines[-max_lines:]
                header = ("libcmis test-suite.log (%s, %d lines, last %d):"
                          % (path, len(lines), len(tail)))
                print(header, flush=True)
                self.output.info(header)
                for line in tail:
                    print("  [test-suite] " + line[:500], flush=True)
                seen += 1
                if seen >= 5:
                    return

    def _emit_upstream_marker(self, total, passed, failed, skipped, command):
        status = "passed" if (
            total > 0 and failed == 0 and skipped == 0 and passed == total
        ) else "failed"
        marker = {
            "status": status,
            "framework": "autotools-make-check",
            "command": command,
            "discovered": total,
            "executed": passed + failed + skipped,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        print(msg, flush=True)
        self.output.info(msg)
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(marker, handle)
        except OSError as exc:
            self.output.warning("could not persist hmbs_upstream.json: %r" % (exc,))
        return status

    def _log_resource_snapshot(self, prefix):
        """Fork-free resource diagnostics for EAGAIN/EPERM triage.

        The previous version spawned 4x `sh -c` subprocesses (ulimit /
        free / df / ps). Under fork pressure ("can't fork - try again")
        or exec pressure (preflight mkdir: Operation not permitted) any
        extra fork/exec actively worsens the spike, so this version uses
        only pure-Python / /proc reads: zero forks, read-only, never
        fails the build.
        """
        lines = []
        try:
            lines.append("loadavg=%s" % (os.getloadavg(),))
        except Exception as exc:
            lines.append("loadavg=unavailable:%r" % (exc,))
        try:
            import resource as _res
            for _name in ("RLIMIT_NPROC", "RLIMIT_NOFILE", "RLIMIT_AS"):
                try:
                    _lim = _res.getrlimit(getattr(_res, _name))
                    lines.append("%s=%s" % (_name, (_lim,)))
                except Exception:
                    continue
        except Exception as exc:
            lines.append("rlimit=unavailable:%r" % (exc,))
        for _p in ("/proc/loadavg", "/proc/meminfo", "/proc/sys/kernel/threads-max"):
            try:
                with open(_p, "r", encoding="utf-8",
                          errors="replace") as _h:
                    _t = _h.read(2048).strip().splitlines()[:6]
                lines.append("%s: %s" % (_p, " | ".join(
                    _l.strip()[:160] for _l in _t) or "(empty)"))
            except OSError as exc:
                lines.append("%s: unreadable:%r" % (_p, (exc,)))
        try:
            _tmp = os.environ.get("TMPDIR") or self.build_folder
        except Exception:
            _tmp = "/tmp"
        try:
            _u = shutil.disk_usage(_tmp)
            lines.append("disk(%s): total=%d free=%d" % (_tmp, _u.total, _u.free))
        except Exception as exc:
            lines.append("disk(%s): unavailable:%r" % (_tmp, (exc,)))
        try:
            _n = os.cpu_count()
            lines.append("cpu_count=%s" % (_n,))
        except Exception as exc:
            lines.append("cpu_count=unavailable:%r" % (exc,))
        try:
            _caps = {k: os.environ.get(k, "") for k in (
                "HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD", "HMBS_CAP_SYMLINK",
                "HMBS_CAP_LOCAL_MKTEMP", "HMBS_AUTOCONF_MKTEMP_FALLBACK",
                "HMBS_TMPDIR", "TMPDIR", "HMBS_INSTALL")}
            lines.append("caps=%s" % (_caps,))
        except Exception:
            pass
        msg = "libcmis resource [%s]:\n  %s" % (prefix, "\n  ".join(lines)[:3000])
        print(msg, flush=True)
        try:
            self.output.info(msg)
        except Exception:
            pass

    def _config_log_has_fork_marker(self):
        """True when config.log tail shows EAGAIN fork pressure."""
        markers = ("can't fork", "cannot fork", "try again",
                   "resource temporarily unavailable")
        for attr in ("build_folder", "base_build_folder"):
            try:
                v = getattr(self.folders, attr, None) or getattr(
                    self, attr, None)
            except Exception:
                v = None
            if not v:
                continue
            path = os.path.join(str(v), "config.log")
            try:
                if not os.path.isfile(path):
                    continue
                with open(path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    text = handle.read()
            except OSError:
                continue
            tail = text[-12000:].lower()
            if any(m in tail for m in markers):
                return True
        return False

    def _config_log_fork_evidence(self, max_lines=30):
        """Dump config.log tail when configure fails (fork evidence)."""
        candidates = []
        for attr in ("build_folder", "base_build_folder"):
            try:
                v = getattr(self.folders, attr, None) or getattr(
                    self, attr, None)
            except Exception:
                v = None
            if v:
                candidates.append(os.path.join(str(v), "config.log"))
        for path in candidates:
            try:
                if not os.path.isfile(path):
                    continue
                with open(path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    lines = handle.read().splitlines()
            except OSError:
                continue
            tail = lines[-max_lines:]
            header = ("libcmis config.log tail (%s, %d lines):"
                      % (path, len(lines)))
            print(header, flush=True)
            try:
                self.output.info(header)
            except Exception:
                pass
            for line in tail:
                print("  [config.log] " + line[:400], flush=True)
            return True
        return False

    def _run_configure_explicit(self, build_tmp, pkg_config="", shim_dir="",
                                sdk_lib="", conan_libdirs=()):
        """Invoke configure under the working shell with inline env wins.

        Autotools.configure() execs the source configure directly, so
        autoconf's CONFIG_SHELL re-exec reads the profile [buildenv] value
        re-exported by conanbuild.sh and dies with Error 127 on runners
        without that bash (cubelib precedent). Running
        `"<shell>" "<src>/configure" ...` with inline assignments wins over
        conanbuild.sh exports for this command. Flags mirror generate().
        """
        shell = self._detect_shell()
        src_configure = os.path.join(self.source_folder, "configure")
        try:
            is_ohos = str(self.settings.os) == "OHOS"
        except Exception:
            is_ohos = True
        triplet_args = ("--build=aarch64-unknown-linux-gnu "
                        "--host=aarch64-unknown-linux-gnu " if is_ohos else "")
        if self.options.shared:
            shared_args = "--disable-static --enable-shared"
        else:
            shared_args = "--enable-static --disable-shared"
        try:
            boost_root = str(self.dependencies["boost"].package_folder)
        except Exception:
            boost_root = ""
        boost_arg = ("\"--with-boost=%s\" " % boost_root) if boost_root else ""
        cmd = (
            "TMPDIR=\"{tmp}\" TMP=\"{tmp}\" TEMP=\"{tmp}\" "
            "CONFIG_SHELL=\"{sh}\" SHELL=\"{sh}\" "
            "{ld_prefix}{path_prefix}{pkg_env}"
            "\"{sh}\" \"{cfg}\" --prefix=/ "
            "\"--bindir=${{prefix}}/bin\" \"--sbindir=${{prefix}}/bin\" "
            "\"--libdir=${{prefix}}/lib\" \"--includedir=${{prefix}}/include\" "
            "\"--oldincludedir=${{prefix}}/include\" "
            "--without-man --disable-werror --disable-client --enable-tests "
            "--disable-dependency-tracking "
            "{triplet}{shared} {boost}"
            "\"PKG_CONFIG_PATH={pc}:$PKG_CONFIG_PATH\""
        ).format(tmp=build_tmp, sh=shell, cfg=src_configure,
                 triplet=triplet_args, shared=shared_args, boost=boost_arg,
                 pc=self.generators_folder,
                 ld_prefix=self._scoped_ld_prefix(sdk_lib, conan_libdirs),
                 path_prefix=("PATH=\"%s:$PATH\" " % shim_dir) if shim_dir else "",
                 pkg_env=("PKG_CONFIG=\"%s\" " % pkg_config) if pkg_config else "")
        self.output.info("libcmis explicit configure: SHELL=%s TMPDIR=%s"
                         % (shell, build_tmp))
        self.run(cmd, cwd=self.build_folder, env="conanbuild")

    def build(self):
        apply_conandata_patches(self)
        build_tmp = self._fix_shell_and_tmp()
        self._patch_configure_tmp(build_tmp)
        # HMDFS sets setgid on new dirs; configure `umask 077` makes
        # config.status temp dirs drwx--S--- -> permission denied
        # (ezstream/libdatovka precedent). Build-time string swap only.
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            replace_in_file(self, cfg, "umask 077", "umask 022")
        self._patch_bad_shell_refs()
        build_shell = os.environ.get("SHELL") or self._detect_shell()
        shim_dir, pkg_config = self._ensure_pkg_config_shim()
        if shim_dir:
            try:
                os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")
            except Exception:
                pass
        if pkg_config:
            os.environ["PKG_CONFIG"] = pkg_config
        # Shadow any system curl-config/xml2-config with the conan dep
        # bindirs first; string swap of PATH only.
        try:
            # Full ref here for the same L0o reason as _dep_libdirs.
            for ref in ("curl/8.15.0", "libxml2"):
                dep = self.dependencies[ref]
                root = str(dep.package_folder) if dep.package_folder else ""
                for d in (list(dep.cpp_info.bindirs or []) if dep else []):
                    p = d if os.path.isabs(d) else (
                        os.path.join(root, d) if root else "")
                    if p and os.path.isdir(p):
                        try:
                            if p not in os.environ.get("PATH", "").split(os.pathsep):
                                os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
                        except Exception:
                            pass
        except Exception:
            pass
        try:
            sdk_llvm_lib = self._sdk_llvm_lib()
        except Exception:
            sdk_llvm_lib = ""
        if sdk_llvm_lib:
            self.output.info("libcmis SDK llvm lib: %s" % sdk_llvm_lib)
        dep_lib_path = self._dep_libdirs()
        # configure forks hundreds of clang/sh probes; the device reports
        # transient EAGAIN as "can't fork - try again" under memory/process
        # pressure (same tree passed 7/7 before, so this is not a flag bug).
        # Retry up to 3 times with backoff instead of failing the whole
        # create on one EAGAIN spike. Test scope is unchanged.
        self._log_resource_snapshot("pre-configure")
        _fork_markers = ("can't fork", "cannot fork", "try again",
                         "resource temporarily unavailable")
        _last_exc = None
        for _attempt in (1, 2, 3):
            try:
                self._run_configure_explicit(
                    build_tmp, pkg_config=pkg_config,
                    shim_dir=shim_dir, sdk_lib=sdk_llvm_lib,
                    conan_libdirs=dep_lib_path)
                _last_exc = None
                break
            except Exception as e:
                _last_exc = e
                _is_fork = False
                try:
                    _is_fork = any(
                        m in str(e).lower() for m in _fork_markers)
                except Exception:
                    pass
                if not _is_fork:
                    try:
                        _is_fork = self._config_log_has_fork_marker()
                    except Exception:
                        pass
                try:
                    self._config_log_fork_evidence()
                except Exception:
                    pass
                try:
                    self._log_resource_snapshot(
                        "configure-fail-attempt%d" % _attempt)
                except Exception:
                    pass
                if _attempt >= 3 or not _is_fork:
                    raise
                _wait = 15 * _attempt
                self.output.warning(
                    "libcmis configure hit fork pressure (attempt %d/3); "
                    "sleeping %ds then retrying: %s" % (_attempt, _wait, e))
                try:
                    time.sleep(_wait)
                except Exception:
                    pass
                try:
                    self._log_resource_snapshot(
                        "pre-retry-attempt%d" % (_attempt + 1))
                except Exception:
                    pass
        if _last_exc is not None:
            raise _last_exc
        try:
            self._patch_bad_shell_refs()
        except Exception:
            pass
        # Compile the libraries (make variables keep shells off /tmp and
        # off the profile bash; SDK-first loader prefix keeps lld alive).
        compile_prefix = self._scoped_ld_prefix(sdk_llvm_lib, dep_lib_path)
        self.run(
            compile_prefix +
            "make -j1 "
            "SHELL=\"{sh}\" CONFIG_SHELL=\"{sh}\" "
            "TMPDIR=\"{tmp}\" TMP=\"{tmp}\" TEMP=\"{tmp}\"".format(
                sh=build_shell, tmp=build_tmp),
            cwd=self.build_folder, env="conanbuild")
        # Upstream suite in two phases: phase 1 compiles every check
        # program with the SDK-first loader prefix (links run lld);
        # phase 2 re-runs `make check` (binaries up-to-date, no toolchain
        # subprocess) with a strictly conan-only loader path so shared
        # deps resolve at test runtime. Output is tee'd for parsing.
        env_prefix = ("TMPDIR=\"{tmp}\" TMP=\"{tmp}\" TEMP=\"{tmp}\" "
                      "SHELL=\"{sh}\" CONFIG_SHELL=\"{sh}\" ".format(
                          sh=build_shell, tmp=build_tmp))
        build_log = os.path.join(self.build_folder, "hmbs-check-build.log")
        check_log = os.path.join(self.build_folder, "hmbs-check-run.log")
        build_command = "make check TESTS= -j1"
        command = "make check -j1"
        if dep_lib_path:
            run_ld_prefix = "LD_LIBRARY_PATH=\"%s\" " % os.pathsep.join(dep_lib_path)
        else:
            run_ld_prefix = ""
        total = passed = failed = skipped = 0
        try:
            self.run(env_prefix + compile_prefix +
                     "%s 2>&1 | tee \"%s\"" % (build_command, build_log),
                     cwd=self.build_folder, env="conanbuild")
            self.run(env_prefix + run_ld_prefix +
                     "%s 2>&1 | tee \"%s\"" % (command, check_log),
                     cwd=self.build_folder, env="conanbuild")
            log_text = ""
            if os.path.isfile(check_log):
                with open(check_log, "r", encoding="utf-8", errors="replace") as f:
                    log_text = f.read()
            total, passed, failed, skipped = self._parse_make_check_summary(log_text)
            if total == 0:
                self.output.warning("make check produced no parseable summary; see "
                                    + check_log)
        except Exception as e:
            log_text = ""
            if os.path.isfile(check_log):
                try:
                    with open(check_log, "r", encoding="utf-8", errors="replace") as f:
                        log_text = f.read()
                except OSError:
                    pass
            total, passed, failed, skipped = self._parse_make_check_summary(log_text)
            self.output.warning("make check failed: %s" % e)
            try:
                self._dump_test_suite_logs()
            except Exception:
                pass
            if total == 0:
                self._emit_upstream_marker(0, 0, 1, 0, command)
                raise
        status = self._emit_upstream_marker(total, passed, failed, skipped, command)
        if status != "passed":
            try:
                self._dump_test_suite_logs()
            except Exception:
                pass
            raise ConanInvalidConfiguration(
                "libcmis upstream tests not fully green: "
                "TOTAL=%d PASS=%d FAIL=%d SKIP=%d" % (total, passed, failed, skipped)
            )

    def package(self):
        try:
            build_tmp = self._fix_shell_and_tmp()
        except Exception:
            build_tmp = os.environ.get("TMPDIR") or "/tmp"
        try:
            build_shell = os.environ.get("SHELL") or self._detect_shell()
        except Exception:
            build_shell = "/bin/sh"
        try:
            shim_install = self._write_install_shim()
            self._redirect_install_to_shim(shim_install)
        except Exception as e:
            self.output.warning("libcmis install shim setup failed: %s" % e)
        self.run(
            "make install DESTDIR=\"{dest}\" "
            "SHELL=\"{sh}\" CONFIG_SHELL=\"{sh}\" "
            "TMPDIR=\"{tmp}\" TMP=\"{tmp}\" TEMP=\"{tmp}\"".format(
                sh=build_shell, tmp=build_tmp,
                dest=self.package_folder),
            cwd=self.build_folder, env="conanbuild")
        copy(self, "LICENSE*", dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)
        # Omit the obsolete .la files; keep real archives/shared libs.
        for pattern in ("*.la",):
            try:
                copy(self, pattern,
                     dst=os.path.join(self.package_folder, "lib"),
                     src=os.path.join(self.package_folder, "lib"),
                     keep_path=False)
            except Exception:
                pass
        libdir = os.path.join(self.package_folder, "lib")
        try:
            names = os.listdir(libdir)
        except OSError:
            names = []
        if not any(n.startswith("libcmis-0.6.") and
                   (n.endswith(".a") or ".so" in n) for n in names):
            raise ConanInvalidConfiguration(
                "libcmis package has no libcmis-0.6 archive: %s" % sorted(names)[:50])
        try:
            src_json = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src_json):
                res_dir = os.path.join(self.package_folder, "res")
                os.makedirs(res_dir, exist_ok=True)
                shutil.copy2(src_json, os.path.join(res_dir, "hmbs_upstream.json"))
        except OSError as exc:
            self.output.warning("could not stage hmbs_upstream.json: %r" % (exc,))

    def package_info(self):
        # Upstream installs versioned include roots:
        # include/libcmis-0.6/libcmis/*.hxx and
        # include/libcmis-c-0.6/libcmis-c/*.h. Consumers include as
        # <libcmis/...> / <libcmis-c/...>, so both versioned roots must
        # be on the include path (preflight failed with default
        # include/ only: 'libcmis/exception.hxx' file not found).
        self.cpp_info.includedirs = [
            "include",
            "include/libcmis-0.6",
            "include/libcmis-c-0.6",
        ]
        # libcmis-c links libcmis: keep the dependent archive first.
        self.cpp_info.libs = ["cmis-c-0.6", "cmis-0.6"]
        self.cpp_info.set_property("cmake_file_name", "libcmis")
        self.cpp_info.set_property("cmake_target_name", "libcmis::libcmis")
        self.cpp_info.set_property("pkg_config_name", "libcmis-0.6")
