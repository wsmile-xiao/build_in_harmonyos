#!/usr/bin/env python3
"""Conan recipe for libcombine 0.2.20 — CMake build system.

libcombine is a C++ library for working with the COMBINE archive
(OMEX) format. Upstream: https://github.com/sbmlteam/libCombine

Build notes:
- CMake project (C++11). Produces shared libCombine (+ static
  libCombine-static) with SOVERSION 0.
- Upstream hard-requires libSBML (its XML layer). libSBML is not yet
  published in the ohpcd registry, so this recipe vendors libSBML
  5.20.5 sources and builds a private static helper (single-PR
  constraint, R36). The vendored headers/static lib are shipped inside
  this package; split into a standalone libsbml recipe as follow-up.
- zipper (fbergmann/zipper @ c56a27f, incl. zero-size-file fix for
  upstream issue #59) and minizip (sebastiandev/minizip @ e3a8cb7)
  are vendored the same way FreeBSD biology/libcombine does, into
  submodules/zipper and submodules/zipper/minizip.
- Registry dependencies (published): zlib/1.3.1.1.1.1 (static, R26),
  libxml2/2.15.3.1 (shared) as the XML backend.
- BUILD_TEST=ON runs the upstream Catch suite via ctest
  (1 ctest entry, 10 Catch SCENARIO/TEST_CASE).
- OHOS toolchain: Conan CMakeToolchain with the generic_system block
  fixed to CMAKE_SYSTEM_NAME=OHOS / processor=aarch64 (yaml-cpp 0.9.0,
  nanoarrow 0.9.0 validated pattern). CMake 4.x ships
  Platform/OHOS.cmake (which just includes Platform/Linux); Conan's
  default "HarmonyOS" has no platform module (ML-0035) and faking
  "Linux" breaks the OHOS compiler check. No hard dependency on the
  NDK ohos.toolchain.cmake file (absent on the preflight worker).
"""

import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
    rmdir,
)

try:
    from conan.tools.cmake import CMakeToolchain
except ImportError:  # pragma: no cover - very old conan
    CMakeToolchain = None


class LibcombineConan(ConanFile):
    name = "libcombine"
    version = "0.2.20"
    description = "C++ library for working with the COMBINE archive (OMEX) format"
    license = "BSD-2-Clause"
    homepage = "https://sbml.org/software/libcombine/"
    url = "https://github.com/sbmlteam/libCombine"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libcombine supports Linux and OHOS targets, got {}".format(
                    self.settings.os)
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def requirements(self):
        # ohpcd-only pins: zlib/1.3.1 and libxml2/2.15.3 also exist in
        # conancenter, and the preflight remote order resolves them to the
        # upstream recipes whose tool_require cmake/4.x has no OHOS key in
        # conan_data sources (KeyError: 'OHOS' in cmake build()). The
        # .1-suffixed versions exist only in ohpcd (no conan cmake
        # tool_require, bare cmake + ohos toolchain), same fix as
        # audtty/0.1.12 (expat/2.8.2.1, zlib/1.3.1.1.1.1) and
        # ayatana-indicator-keyboard/26.6.2 (libxml2/2.15.3.1).
        # libSBML/zipper/minizip are vendored (see class docstring) so they
        # must NOT appear here (R36/PF4).
        self.requires("zlib/1.3.1.1.1.1")
        self.requires("libxml2/2.15.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["libcombine"], strip_root=True)
        get(self, **self.conan_data["sources"]["zipper"],
            destination=os.path.join(self.source_folder, "submodules", "zipper"),
            strip_root=True)
        get(self, **self.conan_data["sources"]["minizip"],
            destination=os.path.join(self.source_folder, "submodules", "zipper", "minizip"),
            strip_root=True)
        get(self, **self.conan_data["sources"]["libsbml"],
            destination=os.path.join(self.source_folder, "libsbml-src"),
            strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream floors cmake_minimum_required at 2.6; allow modern CMake.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # No language bindings / examples on OHOS.
        tc.variables["WITH_SWIG"] = False
        tc.variables["WITH_EXAMPLES"] = False
        tc.variables["WITH_CHECK"] = False
        # Upstream Catch suite (ctest entry test_Combine_run).
        tc.variables["BUILD_TEST"] = True
        tc.variables["LIBCOMBINE_SKIP_SHARED_LIBRARY"] = not bool(self.options.shared)
        if self.settings.os == "OHOS":
            # CMake ships Platform/OHOS.cmake (includes Platform/Linux)
            # but Conan defaults CMAKE_SYSTEM_NAME to "HarmonyOS", which
            # CMake has no platform file for (ML-0035). Fix the block
            # values (yaml-cpp 0.9.0 / nanoarrow 0.9.0 validated); the
            # os guard keeps native Linux detection intact.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # Preflight worker drift (nanoarrow 0.9.0 evidence): the CI
        # profile's /data/service/hnp/bin/clang may not exist/run on the
        # preflight worker. Discover a runnable pair and pin it so CMake
        # never uses a dead absolute path ("compiler identification is
        # unknown").
        _disc_c, _disc_cpp = self._discover_compilers()
        if _disc_c and _disc_cpp:
            tc.variables["CMAKE_C_COMPILER"] = _disc_c
            tc.variables["CMAKE_CXX_COMPILER"] = _disc_cpp
            self.output.info("Pinning discovered compilers: %s / %s" % (_disc_c, _disc_cpp))
        tc.generate()
        # HMBS readonly_tmp: /tmp is read-only on the true machine and the
        # compiler probe spills temp files there. Persist the writable
        # TMPDIR chain via a buildenv script so cmake/ctest inherit it.
        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, "tmp")
        )
        try:
            os.makedirs(tmpdir, exist_ok=True)
            probe = os.path.join(tmpdir, ".hmbs_write_probe")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(probe)
        except OSError:
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        # OHOS SDK lld needs its llvm/lib (libxml2.so.16) on
        # LD_LIBRARY_PATH or the compiler probe cannot start the linker.
        for _llvm_lib in self._all_sdk_llvm_lib_dirs():
            try:
                env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
            except Exception:
                pass
        env.vars(self).save_script("libcombine_tmpdir")

    def _dep_lib(self, ref, names):
        dep = self.dependencies[ref]
        libdir = os.path.join(dep.package_folder, "lib")
        for name in names:
            for suffix in (".so", ".a", ".dylib"):
                cand = os.path.join(libdir, name + suffix)
                if os.path.isfile(cand) and not os.path.islink(cand):
                    return cand
                if os.path.islink(cand) or os.path.lexists(cand):
                    return cand
        return os.path.join(libdir, names[0] + ".so")

    def _dep_include(self, ref, extra=None):
        dep = self.dependencies[ref]
        # Prefer `extra` candidates (e.g. include/libxml2) over the generic
        # include root: callers like FindLIBXML need the directory that
        # directly contains `libxml/parser.h`. The old order returned
        # package/include first, which breaks `#include <libxml/parser.h>`
        # when headers live in include/libxml2/libxml/.
        candidates = []
        if extra:
            candidates.extend(
                os.path.join(dep.package_folder, e) for e in extra)
        candidates.append(os.path.join(dep.package_folder, "include"))
        for cand in candidates:
            probe = os.path.join(cand, "libxml", "parser.h")
            if os.path.isfile(probe):
                return cand
        found = [c for c in candidates if os.path.isdir(c)]
        return found[0] if found else candidates[0]

    def _cmake_exe(self):
        # HMBS injects HMBS_CMAKE (+ PATH prepend); validate before use and
        # fall back to PATH lookup instead of propagating a hardcoded name.
        import shutil
        for cand in (os.environ.get("HMBS_CMAKE", ""), shutil.which("cmake")):
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        return "cmake"

    def _ensure_writable_tmp(self):
        # True-machine /tmp is read-only (preflight readonly_tmp): reuse the
        # HMBS-injected writable dir chain for cmake/mktemp temp files.
        # (The buildenv script in generate() covers child processes; this
        # covers the current process before self.run.)
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key, "")
            if val:
                try:
                    os.makedirs(val, exist_ok=True)
                except OSError:
                    pass
                if os.path.isdir(val):
                    for k in ("TMPDIR", "TMP", "TEMP"):
                        os.environ[k] = val
                    return val
        fallback = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        for k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[k] = fallback
        return fallback

    def _runs_ok(self, path):
        import subprocess as _sp
        try:
            if not path or not os.path.isfile(path) or not os.access(path, os.X_OK):
                return False
            r = _sp.run([path, "--version"], capture_output=True, text=True,
                        timeout=30, env=os.environ.copy())
            return r.returncode == 0
        except Exception:
            return False

    def _discover_compilers(self):
        # Accept a compiler candidate only after it executes. Order:
        # profile paths, PATH names, well-known absolute locations.
        import shutil as _sh
        try:
            cmap = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            cmap = {}
        pc = cmap.get("c", "") if isinstance(cmap, dict) else ""
        pcpp = cmap.get("cpp", "") if isinstance(cmap, dict) else ""
        if pc and pcpp and self._runs_ok(pc) and self._runs_ok(pcpp):
            return pc, pcpp
        if pc or pcpp:
            self.output.warning("Profile compiler not runnable: c=%s cpp=%s" % (pc, pcpp))
        for nc, ncpp in (("clang", "clang++"), ("cc", "c++")):
            wc = _sh.which(nc) or ""
            wcpp = _sh.which(ncpp) or ""
            if wc and wcpp and self._runs_ok(wc) and self._runs_ok(wcpp):
                self.output.info("Using PATH compilers: %s / %s" % (wc, wcpp))
                return wc, wcpp
        for d in ("/storage/Users/currentUser/usr/local/bin",
                  "/data/service/hnp/bin", "/opt/hnp/bin",
                  "/usr/local/bin", "/usr/bin"):
            for nc, ncpp in (("clang", "clang++"), ("cc", "c++")):
                c = os.path.join(d, nc)
                cpp = os.path.join(d, ncpp)
                if self._runs_ok(c) and self._runs_ok(cpp):
                    self.output.info("Using absolute compilers: %s / %s" % (c, cpp))
                    return c, cpp
        self.output.warning("No runnable compiler pair found; keeping toolchain defaults")
        return "", ""

    def _all_sdk_llvm_lib_dirs(self):
        import glob as _glob
        found = []
        for pat in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
                    "/data/service/hnp/*/ohos/native/llvm/lib",
                    "/data/service/hnp/*/native/llvm/lib"):
            try:
                for g in sorted(_glob.glob(pat)):
                    if os.path.isdir(g) and g not in found:
                        found.append(g)
            except Exception:
                continue
        return found

    def _sanitize_link_env_for_configure(self, pkg_dirs):
        # Remove conan package dirs from the process link env before cmake
        # TryCompile runs. CMake forwards $CFLAGS/$LDFLAGS into the compiler
        # check, and the dynamic loader resolves SDK lld via
        # $LD_LIBRARY_PATH at exec time -- either channel breaks lld when it
        # points at the conan libxml2. Keep SDK llvm/lib entries, drop conan
        # lib/include entries, and log the result for diagnosis.
        import re as _re
        pkg_dirs = [str(p) for p in pkg_dirs if p]
        for key in ("CFLAGS", "CPPFLAGS", "CXXFLAGS"):
            val = os.environ.get(key, "")
            if not val:
                continue
            tokens = val.split()
            kept = [t for t in tokens
                    if not any(pd in t for pd in pkg_dirs)]
            if len(kept) != len(tokens):
                os.environ[key] = " ".join(kept).strip()
        val = os.environ.get("LDFLAGS", "")
        if val:
            tokens = val.split()
            kept = [t for t in tokens
                    if not any(pd in t for pd in pkg_dirs)]
            if len(kept) != len(tokens):
                os.environ["LDFLAGS"] = " ".join(kept).strip()
        lp = os.environ.get("LD_LIBRARY_PATH", "")
        if lp:
            parts = [p for p in lp.split(os.pathsep)
                     if p and not any(pd in p for pd in pkg_dirs)]
            # Always keep SDK llvm/lib (lld's own libxml2) if known.
            for d in self._all_sdk_llvm_lib_dirs():
                if d not in parts:
                    parts.append(d)
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(parts)
        else:
            sdks = self._all_sdk_llvm_lib_dirs()
            if sdks:
                os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(sdks)
        self.output.info("LINK_ENV_CLEAN CFLAGS=%s LDFLAGS=%s LD_LIBRARY_PATH=%s" % (
            os.environ.get("CFLAGS", ""), os.environ.get("LDFLAGS", ""),
            os.environ.get("LD_LIBRARY_PATH", "")))

    def _env_with_conan_run_libs(self):
        # Narrow scope: conan shared libdirs are needed only to RUN already
        # built test binaries (ctest), never to START the linker during
        # configure/build. Callers pass this env explicitly to the test
        # subprocess instead of polluting os.environ globally.
        env = os.environ.copy()
        try:
            dirs = []
            for ref in ("libxml2", "zlib"):
                try:
                    libdir = os.path.join(
                        self.dependencies[ref].package_folder, "lib")
                    if os.path.isdir(libdir):
                        dirs.append(libdir)
                except Exception:
                    continue
            if dirs:
                prev = env.get("LD_LIBRARY_PATH", "")
                ordered = [d for d in dirs if d not in prev.split(os.pathsep)] \
                    + ([prev] if prev else [])
                env["LD_LIBRARY_PATH"] = os.pathsep.join(
                    [p for p in ordered if p])
        except Exception:
            pass
        return env

    def _dump_cmake_logs(self, bdir):
        # The preflight summary truncates cmake stderr ("..."), so persist
        # the real failure evidence (CMakeError.log/CMakeOutput.log tails)
        # in the conan output for the next round. Search recursively: with
        # cmake_layout the try_compile logs may sit one level below/above
        # the passed dir, and CMake 4.x keeps the same filenames.
        import glob as _glob
        seen = set()
        patterns = [
            os.path.join(bdir, "CMakeFiles", "CMakeError.log"),
            os.path.join(bdir, "CMakeFiles", "CMakeOutput.log"),
            os.path.join(bdir, "**", "CMakeError.log"),
            os.path.join(bdir, "**", "CMakeOutput.log"),
        ]
        for pat in patterns:
            try:
                files = _glob.glob(pat, recursive=True)
            except Exception:
                continue
            for p in files:
                if p in seen or not os.path.isfile(p):
                    continue
                seen.add(p)
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        txt = f.read()
                    self.output.info("%s tail:\n%s" % (p, txt[-5000:]))
                except OSError as e:
                    self.output.warning("cannot read %s: %s" % (p, e))
        if not seen:
            self.output.info("CMake logs absent under build dir %s" % bdir)
            try:
                entries = sorted(os.listdir(bdir))[:30]
                self.output.info("build dir entries: %s" % entries)
            except OSError as e:
                self.output.warning("cannot list %s: %s" % (bdir, e))

    def _precheck_libxml(self, xml_inc, xml_lib, z_inc, z_lib):
        # Directly compile FindLIBXML's probe program with the discovered C
        # compiler. Diagnostic only: cmake remains the gate, this never
        # masks a real failure, it only records include-vs-link evidence in
        # conan output (CMakeError.log was absent in the last round).
        import subprocess as _sp
        import tempfile as _tf
        code = ('#include <libxml/xmlversion.h>\n#include <libxml/parser.h>\n'
                '#include <stdio.h>\nint main(void){\n'
                'LIBXML_TEST_VERSION\nxmlKeepBlanksDefault(0);\n'
                'xmlDocPtr doc = xmlParseFile("none");\nxmlCleanupParser();\nreturn 0;\n}\n')
        cc = ""
        try:
            _c, _cpp = self._discover_compilers()
            cc = _c
        except Exception:
            cc = ""
        if not cc:
            self.output.warning("libxml precheck skipped: no C compiler discovered")
            return
        tmpd = os.environ.get("TMPDIR") or os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmpd, exist_ok=True)
            fd, src = _tf.mkstemp(suffix=".c", dir=tmpd)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(code)
            exe = src + ".out"
            cmd = [cc, "-I" + xml_inc, "-I" + z_inc, src, xml_lib, z_lib, "-lm", "-o", exe]
            self.output.info("LIBXML_PRECHECK_CMD=%s" % " ".join(cmd))
            # Run with conan dirs stripped from LD_LIBRARY_PATH so SDK lld
            # starts against the system libxml2 (same hygiene as configure).
            _env = os.environ.copy()
            try:
                _lp = _env.get("LD_LIBRARY_PATH", "")
                if _lp:
                    _env["LD_LIBRARY_PATH"] = os.pathsep.join(
                        [p for p in _lp.split(os.pathsep)
                         if "conan-home" not in p and "/p/libxm" not in p
                         and "/p/zlib" not in p])
            except Exception:
                pass
            r = _sp.run(cmd, capture_output=True, text=True, timeout=120,
                        env=_env)
            tail = ((r.stdout or "") + (r.stderr or ""))[-2000:]
            self.output.info("LIBXML_PRECHECK rc=%s out=%s" % (r.returncode, tail))
            try:
                if os.path.isfile(src):
                    os.remove(src)
                if os.path.isfile(exe):
                    os.remove(exe)
            except OSError:
                pass
        except Exception as e:
            self.output.warning("libxml precheck error: %s" % e)

    def _build_vendored_sbml(self):
        self._ensure_writable_tmp()
        cmake_exe = self._cmake_exe()
        src = os.path.join(self.source_folder, "libsbml-src")
        build_dir = os.path.join(self.build_folder, "sbml-build")
        prefix = os.path.join(self.build_folder, "sbml-prefix")
        mkdir(self, build_dir)
        mkdir(self, prefix)
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        xml_lib = self._dep_lib("libxml2", ["libxml2"])
        xml_inc = self._dep_include("libxml2", ["include/libxml2"])
        z_lib = self._dep_lib("zlib", ["libz"])
        z_inc = self._dep_include("zlib")
        # Evidence for the next round: FindLIBXML.cmake needs xml_inc to
        # directly contain libxml/parser.h and xml_lib to exist. Log both
        # plus the probe result so a future failure is distinguishable from
        # the fixed wrong-root cause.
        self.output.info("LIBXML_LIBRARY=%s exists=%s" % (xml_lib, os.path.exists(xml_lib)))
        self.output.info("LIBXML_INCLUDE_DIR=%s probe=%s" % (
            xml_inc, os.path.isfile(os.path.join(xml_inc, "libxml", "parser.h"))))
        # Link-env hygiene (fixes lld startup failure on the true machine):
        # NEVER export conan libxml2/zlib libdirs via global CFLAGS/LDFLAGS/
        # LD_LIBRARY_PATH. The OHOS SDK lld links against the system
        # libxml2.so.16; prepending the conan libxml2 libdir on
        # LD_LIBRARY_PATH makes lld load the conan libxml2.so.16 instead and
        # die with "xmlDocGetRootElement: symbol not found", which then fails
        # every CMake compiler check (TryCompile) and the precheck alike.
        # FindLIBXML only needs the absolute LIBXML_LIBRARY/LIBXML_INCLUDE_DIR
        # cache variables passed below (plus EXTRA_LIBS absolute paths for the
        # main build), so no global link-line hardening is required. Strip any
        # leaked conan dirs here so cmake TryCompile sees a clean linker.
        try:
            _xml_pkg = self.dependencies["libxml2"].package_folder
            _z_pkg = self.dependencies["zlib"].package_folder
            self._sanitize_link_env_for_configure([_xml_pkg, _z_pkg])
        except Exception as _e:
            self.output.warning("link env sanitize skipped: %s" % _e)
        # Independent verification (not the same command as last round):
        # compile FindLIBXML's own test program with the discovered C
        # compiler before cmake runs, so include-vs-link causes are
        # distinguishable even when CMakeError.log is absent/truncated.
        self._precheck_libxml(xml_inc, xml_lib, z_inc, z_lib)

        def q(value):
            return '"{}"'.format(str(value).replace('"', '\"'))

        parts = [
            q(cmake_exe),
            "-S", q(src),
            "-B", q(build_dir),
            "-DCMAKE_TOOLCHAIN_FILE=" + q(toolchain),
            "-DCMAKE_BUILD_TYPE=" + q(self.settings.build_type),
            "-DCMAKE_INSTALL_PREFIX=" + q(prefix),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DWITH_LIBXML=ON",
            "-DLIBXML_LIBRARY=" + q(xml_lib),
            "-DLIBXML_INCLUDE_DIR=" + q(xml_inc),
            "-DWITH_EXPAT=OFF",
            "-DWITH_XERCES=OFF",
            "-DWITH_ZLIB=ON",
            "-DZLIB_LIBRARY=" + q(z_lib),
            "-DZLIB_INCLUDE_DIR=" + q(z_inc),
            "-DWITH_BZIP2=OFF",
            "-DWITH_SWIG=OFF",
            "-DWITH_STABLE_PACKAGES=OFF",
            "-DWITH_EXAMPLES=OFF",
            "-DWITH_CHECK=OFF",
            "-DWITH_DOXYGEN=OFF",
        ]
        try:
            self.run(" ".join(parts))
        except Exception:
            self._dump_cmake_logs(build_dir)
            raise
        self.run("{} --build {} --config {} --parallel 1".format(
            q(cmake_exe), q(build_dir), q(self.settings.build_type)))
        self.run("{} --install {}".format(q(cmake_exe), q(build_dir)))

    def _extra_libs(self):
        # Full paths: plain "xml2"/"z" would not resolve without -L flags,
        # and R33 forbids inventing shell link lines. "m" is a real system
        # lib on OHOS/Linux toolchains.
        xml_lib = self._dep_lib("libxml2", ["libxml2"])
        z_lib = self._dep_lib("zlib", ["libz"])
        sbml_lib = os.path.join(self.build_folder, "sbml-prefix", "lib", "libsbml-static.a")
        return ";".join([sbml_lib, xml_lib, z_lib, "m"])

    def _emit_upstream_marker(self, marker):
        # Dual-channel evidence (libogg/1.3.6.2 + osi/0.108.12 pattern):
        # self.output.info (conan log) + print (stdout) + persist to
        # build_folder/upstream_test_result.json for package() to ship.
        # HMBS preflight only collects the marker from the test_package
        # stage stdout, so the main build marker alone is invisible when
        # the package is cache-hit; test_package re-emits from res/.
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            with open(os.path.join(
                    self.build_folder,
                    "upstream_test_result.json"), "w",
                      encoding="utf-8", newline="\n") as fh:
                json.dump(marker, fh)
        except Exception as e:
            self.output.warning("persist upstream marker failed: %s" % e)

    def _run_upstream_tests(self, main_build_dir):
        # Run the upstream Catch suite via ctest and emit the HMBS machine
        # evidence marker. Numbers come from the real ctest/Catch output.
        # Upstream layout: 1 ctest entry test_Combine_run driving the
        # Combine-test Catch binary (10 SCENARIO/TEST_CASE in
        # src/test/*.cpp). Plain `ctest --output-on-failure` hides the
        # Catch stdout on success ("Passed" only), so the Catch summary
        # "All tests passed (N assertions in M test cases)" is unparsable
        # and the marker degrades to executed=1/discovered=10 (skipped=9),
        # which gates reject. Use verbose ctest so passing output is shown,
        # and fall back to running the Combine-test binary directly when
        # the summary is still absent.
        discovered = 10  # src/test/*.cpp: 10 Catch SCENARIO/TEST_CASE
        command = "ctest -V --output-on-failure"
        if not can_run(self):
            up = {"status": "skipped", "framework": "ctest",
                  "command": command, "discovered": discovered,
                  "executed": 0, "passed": 0, "failed": 0,
                  "skipped": discovered, "reason": "cross-building"}
            self._emit_upstream_marker(up)
            return
        try:
            proc = subprocess.run(
                command, shell=True, cwd=main_build_dir,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=600,
                env=self._env_with_conan_run_libs())
            out = proc.stdout or ""
            self.output.info(out[-3000:] if len(out) > 3000 else out)
            import re
            passed = 0
            failed = 0
            # Prefer the Catch summary inside the ctest output, which counts
            # real test cases: "All tests passed (N assertions in M test
            # cases)". M is the executed/passed Catch case count.
            mc = re.search(r"All tests passed\s*\((\d+)\s+assertions?\s+in\s+(\d+)\s+test cases?\)", out)
            if mc and proc.returncode == 0:
                passed = int(mc.group(2))
                failed = 0
            else:
                # Verbose ctest should carry the Catch summary; when it
                # still does not (old Catch wording, truncation), run the
                # Combine-test binary directly so the case count is real
                # instead of degrading to the 1-entry ctest count.
                direct_out = ""
                try:
                    import glob as _glob
                    _cands = []
                    for _pat in ("Combine-test", "combine-test",
                                 "**/Combine-test", "**/combine-test",
                                 "**/Combine-test.exe"):
                        try:
                            _cands.extend(
                                _glob.glob(os.path.join(main_build_dir, _pat),
                                           recursive=True))
                        except Exception:
                            continue
                    _bin = ""
                    for _c in sorted(set(_cands)):
                        if os.path.isfile(_c) and os.access(_c, os.X_OK):
                            _bin = _c
                            break
                    if _bin:
                        _env = self._env_with_conan_run_libs()
                        _env["srcdir"] = os.path.join(self.source_folder,
                                                      "src", "test")
                        _r = subprocess.run(
                            [_bin], cwd=main_build_dir,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=600, env=_env)
                        direct_out = _r.stdout or ""
                        self.output.info(
                            "direct Combine-test rc=%s tail=%s" % (
                                _r.returncode,
                                direct_out[-2000:] if len(direct_out) > 2000
                                else direct_out))
                        _mc = re.search(
                            r"All tests passed\s*\((\d+)\s+assertions?\s+in\s+(\d+)\s+test cases?\)",
                            direct_out)
                        if _mc and _r.returncode == 0:
                            out = out + "\n" + direct_out
                            passed = int(_mc.group(2))
                            failed = 0
                            mc = _mc
                except Exception as _e:
                    self.output.warning("direct Combine-test run skipped: %s" % _e)
            if passed == 0 and failed == 0 and not (mc and proc.returncode == 0):
                m = re.search(r"(\d+)\s+tests?\s+passed", out)
                if m:
                    passed = int(m.group(1))
                m2 = re.search(r"(\d+)\s+tests?\s+failed", out)
                if m2:
                    failed = int(m2.group(1))
                if passed == 0 and failed == 0:
                    # ctest summary form: "100% tests passed, 0 tests failed out of 1"
                    m3 = re.search(r"tests passed,\s*(\d+)\s*tests? failed\s*out of\s*(\d+)",
                                  out)
                    if m3:
                        failed = int(m3.group(1))
                        total = int(m3.group(2))
                        passed = total - failed
                    elif proc.returncode != 0 or "No tests were found" in out or "Failed" in out:
                        pass  # handled by the falsification guard below
                    else:
                        # ctest entry passed but neither verbose ctest nor
                        # the direct binary yielded a Catch summary: do NOT
                        # shrink discovered to fake a pass. Leave counts at
                        # zero so the falsification guard below reports
                        # failed with the log tail for diagnosis.
                        pass
            executed = passed + failed
            # Falsification guard: upstream test binaries write real archives;
            # a zero-test "pass" must not be reported as passed.
            if executed == 0 or proc.returncode != 0 and failed == 0:
                failed = max(failed, discovered - passed) if discovered else 1
                executed = passed + failed
            skipped = max(0, discovered - executed)
            status = "passed" if (failed == 0 and executed > 0 and proc.returncode == 0) else "failed"
            up = {"status": status, "framework": "ctest",
                  "command": command, "discovered": discovered,
                  "executed": executed, "passed": passed,
                  "failed": failed, "skipped": skipped}
            self._emit_upstream_marker(up)
            if status != "passed":
                raise RuntimeError("upstream ctest failed: {}".format(out[-1500:]))
        except subprocess.TimeoutExpired as e:
            up = {"status": "failed", "framework": "ctest",
                  "command": command, "discovered": discovered,
                  "executed": 0, "passed": 0, "failed": discovered,
                  "skipped": 0, "reason": "timeout: {}".format(e)[:300]}
            self._emit_upstream_marker(up)
            raise
        except Exception as e:
            # Guarantee evidence on any unexpected harness error: never
            # leave preflight without a marker (would be incomplete).
            up = {"status": "failed", "framework": "ctest",
                  "command": command, "discovered": discovered,
                  "executed": 0, "passed": 0, "failed": discovered,
                  "skipped": 0, "reason": "harness error: {}".format(e)[:300]}
            try:
                self._emit_upstream_marker(up)
            except Exception:
                pass
            raise

    def build(self):
        apply_conandata_patches(self)
        self._ensure_writable_tmp()
        self._build_vendored_sbml()
        cmake_exe = self._cmake_exe()
        main_build_dir = os.path.join(self.build_folder, "build-ohos-main")
        mkdir(self, main_build_dir)
        sbml_prefix = os.path.join(self.build_folder, "sbml-prefix")
        sbml_inc = os.path.join(sbml_prefix, "include")
        sbml_lib = os.path.join(sbml_prefix, "lib", "libsbml-static.a")
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        zlib_pkg = self.dependencies["zlib"].package_folder
        xml2_pkg = self.dependencies["libxml2"].package_folder
        # Keep the main configure under the same clean-linker hygiene: the
        # vendored step already sanitized, re-apply in case the toolchain or
        # buildenv re-exported conan paths between the two configures.
        try:
            self._sanitize_link_env_for_configure([xml2_pkg, zlib_pkg])
        except Exception:
            pass

        def q(value):
            return '"{}"'.format(str(value).replace('"', '\"'))

        parts = [
            q(cmake_exe),
            "-S", q(self.source_folder),
            "-B", q(main_build_dir),
            "-DCMAKE_TOOLCHAIN_FILE=" + q(toolchain),
            "-DCMAKE_BUILD_TYPE=" + q(self.settings.build_type),
            "-DCMAKE_INSTALL_PREFIX=" + q(os.path.join(self.build_folder, "install-prefix")),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DBUILD_SHARED_LIBS=" + ("ON" if self.options.shared else "OFF"),
            "-DWITH_SWIG=OFF",
            "-DWITH_EXAMPLES=OFF",
            "-DWITH_CHECK=OFF",
            "-DBUILD_TEST=ON",
            "-DLIBCOMBINE_SKIP_SHARED_LIBRARY=" + ("ON" if not self.options.shared else "OFF"),
            "-DLIBSBML_INCLUDE_DIR=" + q(sbml_inc),
            "-DLIBSBML_LIBRARY=" + q(sbml_lib),
            "-DEXTRA_LIBS=" + q(self._extra_libs()),
            "-DCMAKE_PREFIX_PATH=" + q("{};{}".format(zlib_pkg, xml2_pkg)),
        ]
        try:
            self.run(" ".join(parts))
        except Exception:
            self._dump_cmake_logs(main_build_dir)
            raise
        self.run("{} --build {} --config {}".format(
            q(cmake_exe), q(main_build_dir), q(self.settings.build_type)))
        self._run_upstream_tests(main_build_dir)

    def package(self):
        cmake_exe = self._cmake_exe()
        main_build_dir = os.path.join(self.build_folder, "build-ohos-main")
        self.run('{} --install "{}" --prefix "{}"'.format(
            cmake_exe, main_build_dir, self.package_folder))
        copy(self, "LICENSE.md",
             src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # test_package links libCombine-static.a the way upstream's own
        # Combine-test binary does. Upstream install rules center on the
        # shared target, so ensure the static archive ships even if
        # `cmake --install` leaves it in the build tree.
        try:
            import glob as _glob
            _want = os.path.join(self.package_folder, "lib",
                                 "libCombine-static.a")
            if not os.path.isfile(_want):
                _cands = sorted(_glob.glob(
                    os.path.join(main_build_dir, "**",
                                 "libCombine-static.a"),
                    recursive=True))
                if _cands:
                    copy(self, "libCombine-static.a",
                         src=os.path.dirname(_cands[0]),
                         dst=os.path.join(self.package_folder, "lib"))
                    self.output.info(
                        "shipped built libCombine-static.a from %s"
                        % _cands[0])
                else:
                    self.output.warning(
                        "libCombine-static.a not found under %s"
                        % main_build_dir)
        except Exception as _e:
            self.output.warning("static-archive ensure skipped: %s" % _e)
        # Ship the vendored libSBML headers + static helper: omex public
        # headers include <sbml/...>, so consumers need them.
        sbml_prefix = os.path.join(self.build_folder, "sbml-prefix")
        copy(self, "*.h",
             src=os.path.join(sbml_prefix, "include", "sbml"),
             dst=os.path.join(self.package_folder, "include", "sbml"))
        copy(self, "libsbml-static.a",
             src=os.path.join(sbml_prefix, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        try:
            copy(self, "upstream_test_result.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"))
        except Exception as e:
            self.output.warning("ship upstream marker skipped: %s" % e)
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # Same device signing as libxml2/2.15.3: cmake-built .so files need
        # a fresh .codesign section to execute on HarmonyOS. Guarded: skip
        # silently when the signing tools are absent (e.g. CI containers).
        import glob as _glob
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            return
        libdir = os.path.join(self.package_folder, "lib")
        sos = _glob.glob(os.path.join(libdir, "**", "*.so*"), recursive=True)
        for so in sos:
            if os.path.islink(so):
                continue
            self.run('{} --remove-section .codesign "{}" 2>/dev/null || true'.format(objcopy, so))
            self.run('{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, so, so))

    def package_info(self):
        self.cpp_info.libs = ["Combine", "sbml-static"]
        self.cpp_info.set_property("cmake_file_name", "Combine")
        self.cpp_info.set_property("cmake_target_name", "Combine::Combine")
        self.cpp_info.set_property("pkg_config_name", "libCombine")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
