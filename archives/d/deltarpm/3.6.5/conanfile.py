#!/usr/bin/env python3
"""Conan recipe — deltarpm 3.6.5 (Makefile)

deltarpm is a suite of CLI tools to create and apply delta RPMs / delta ISOs:
makedeltarpm, applydeltarpm, combinedeltarpm, makedeltaiso, applydeltaiso, fragiso.
Plain Makefile project (no configure script).

Notes:
- rpmdumpheader is intentionally NOT built: it links -lrpm -lrpmio, and
  rpm/6.0.2 is not published in the artifact repo (R36 forbids depending on
  unpublished packages). All other tools parse RPM headers with the bundled
  rpmhead.c and need no librpm.
- Only lzma comes from Conan, pinned to lzma/5.6.2 — a package name that
  exists ONLY in ohpcd (conancenter carries liblzma only as xz), so
  dependency resolution is deterministic no matter the remote order, and
  its published binary ships complete headers (lzma.h + lzma/*.h) with a
  static liblzma.a. Plain bzip2/1.0.8 and zstd/1.5.6 exist in both
  conancenter and ohpcd; with both remotes enabled the resolver picks
  conancenter's CMake recipes, which cannot configure on OHOS (CMake
  knows no HarmonyOS platform). There is no published ohpcd-only
  bzip2/zstd version to pin to, so both are built in-tree from official,
  sha256-verified tarballs — the same pattern upstream itself uses for
  its bundled rsyncable zlib. (Why not xz/5.8.3.1: its published binary
  demonstrably lacks lzma.h under include/, failing the compile with
  `fatal error: 'lzma.h' file not found`; the 5.8.3.1 recipe dir no
  longer exists in-tree. deltarpm only uses the stable streaming APIs
  lzma_code/lzma_auto_decoder/lzma_easy_encoder/lzma_alone_encoder —
  never the index API — so CVE-2026-34743, fixed in 5.8.3, is not
  reachable from these code paths.)
- zlib uses the upstream-bundled rsyncable copy (zlib-1.2.2.f-rsyncable)
  built in-tree, exactly as upstream does.
- Upstream has no test suite (no check/test target, no tests/ directory), so
  build() emits a no_tests HMBS evidence marker instead of running make check.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class DeltarpmConan(ConanFile):
    name = "deltarpm"
    version = "3.6.5"
    description = "Tools to create and apply deltarpms (delta RPMs) and delta ISOs."
    license = "BSD-3-Clause"
    homepage = "https://github.com/rpm-software-management/deltarpm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Binaries shipped (upstream `all` minus rpmdumpheader, which needs librpm).
    _tools = [
        "makedeltarpm",
        "applydeltarpm",
        "combinedeltarpm",
        "makedeltaiso",
        "applydeltaiso",
        "fragiso",
    ]

    # bzip2 1.0.8 library translation units (the CLI tool bzip2.c and the
    # test helpers spewG/mk251/dlltest are intentionally excluded).
    _bz2_lib_srcs = [
        "blocksort.c",
        "huffman.c",
        "crctable.c",
        "randtable.c",
        "compress.c",
        "decompress.c",
        "bzlib.c",
    ]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Sole Conan dep. The `lzma` package name exists only in ohpcd
        # (conancenter carries liblzma only as `xz`), so resolution cannot
        # drift to a foreign recipe — same determinism goal as the earlier
        # xz/5.8.3.1 version pin, but at the name level, and with proven
        # complete headers (xz/5.8.3.1's published binary lacks lzma.h).
        # bzip2/zstd are vendored (see source()/build()).
        self.requires("lzma/5.6.2")  # ohpcd liblzma: headers + static lib

    def layout(self):
        basic_layout(self)
        # Upstream builds in-source (top Makefile + bundled zlib sub-make).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        for _name, sub in (self.conan_data.get("vendored", {}) or {}).items():
            dest = os.path.join(self.source_folder, sub["destination"])
            marker = os.path.join(dest, ".hmbs-vendored-ok")
            if os.path.isfile(marker):
                continue
            os.makedirs(dest, exist_ok=True)
            get(self, url=sub["url"], sha256=sub.get("sha256", ""),
                destination=dest, strip_root=True)
            with open(marker, "w") as _f:
                _f.write("ok")

    def generate(self):
        # Declare the build environment at the Conan-standard phase:
        # aggregate build env and pin a writable TMPDIR (the preflight
        # worker's /tmp is read-only). Sub-makes inherit it.
        VirtualBuildEnv(self).generate()
        tmpdir = None
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v and _v not in ("0", "1") and os.path.isdir(_v):
                tmpdir = _v
                break
        if tmpdir is None:
            tmpdir = os.path.join(self.build_folder, "tmp")
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except Exception:
                pass
        env = Environment()
        for _k in ("TMPDIR", "TMP", "TEMP"):
            env.define(_k, tmpdir)
        env.vars(self).save_script("deltarpm_tmpdir")

    def _config_shell(self):
        # CONFIG_SHELL/SHELL may point to /data/service/hnp/bin/bash which does
        # not exist on some workers. Prefer existing executable, fallback to
        # PATH lookup, then /bin/sh.
        for cand in (os.environ.get("CONFIG_SHELL"), os.environ.get("SHELL")):
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        for bare in ("bash", "sh"):
            found = shutil.which(bare)
            if found:
                return found
        self.output.warning("no usable shell found via PATH, using /bin/sh")
        return "/bin/sh"

    def _resolve_tool(self, conf_key, bare_names):
        # conf still preferred; only when an absolute path is missing or not
        # executable do we warn and fall back to bare names resolved via the
        # conanbuild PATH. bare_names[0] is the preferred fallback.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cand = compilers.get(conf_key)
        if cand:
            if os.path.sep in cand:
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand, compilers
                self.output.warning(
                    "conf compiler %s=%s missing or not executable, falling back to PATH" % (conf_key, cand))
            else:
                # bare name: resolved via shell PATH either way
                return cand, compilers
        for bare in bare_names:
            found = shutil.which(bare)
            if found:
                return found, compilers
        # Last resort: environment or bare name (resolved via conanbuild PATH)
        env_fallback = os.environ.get("CC" if conf_key == "c" else "CXX" if conf_key == "cpp" else conf_key.upper())
        if env_fallback:
            return env_fallback, compilers
        return bare_names[0] if bare_names else cand, compilers

    def _dep_flags(self):
        incs, libdirs = [], []
        for dep in self.dependencies.values():
            for d in dep.cpp_info.includedirs:
                if d not in incs:
                    incs.append(d)
            for d in dep.cpp_info.libdirs:
                if d not in libdirs:
                    libdirs.append(d)
        return incs, libdirs

    def _build_vendored_bz2(self, cc, ar):
        """Compile bzip2 1.0.8 library units directly (no configure/CMake)."""
        bzdir = os.path.join(self.source_folder, "vendored", "bzip2-1.0.8")
        lib = os.path.join(bzdir, "libbz2.a")
        if os.path.isfile(lib):
            self.output.info("vendored libbz2.a already built, reusing")
            return bzdir, lib
        if not os.path.isfile(os.path.join(bzdir, "bzlib.h")):
            raise Exception("vendored bzip2 sources missing bzlib.h in %s" % bzdir)
        objs = []
        for src in self._bz2_lib_srcs:
            obj = src[:-2] + ".o"
            self.run("%s -fPIC -O2 -Wall -c %s -o %s" % (cc, src, obj), cwd=bzdir)
            objs.append(obj)
        self.run("%s rcs libbz2.a %s" % (ar, " ".join(objs)), cwd=bzdir)
        return bzdir, lib

    def _build_vendored_zstd(self, cc, ar):
        """Compile zstd 1.5.6 library units directly (no cmake).

        zstd's build is glob-friendly: lib/common, lib/compress and
        lib/decompress hold the full single-threaded codec (the optional
        assembly file, if any, is simply not globbed and the C fallback
        is used).
        """
        zsdir = os.path.join(self.source_folder, "vendored", "zstd-1.5.6")
        libdir = os.path.join(zsdir, "lib")
        lib = os.path.join(zsdir, "libzstd.a")
        if os.path.isfile(lib):
            self.output.info("vendored libzstd.a already built, reusing")
            return libdir, lib
        if not os.path.isfile(os.path.join(libdir, "zstd.h")):
            raise Exception("vendored zstd sources missing lib/zstd.h in %s" % zsdir)
        objdir = os.path.join(zsdir, "obj")
        try:
            os.makedirs(objdir, exist_ok=True)
        except Exception:
            pass
        self.run(
            "%s -fPIC -O2 -I\"%s\" -I\"%s\" -c \"%s\"/*.c \"%s\"/*.c \"%s\"/*.c"
            % (cc, libdir, os.path.join(libdir, "common"),
               os.path.join(libdir, "common"), os.path.join(libdir, "compress"),
               os.path.join(libdir, "decompress")),
            cwd=objdir)
        self.run("%s rcs \"%s\" *.o" % (ar, lib), cwd=objdir)
        return libdir, lib

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler/linker come from Conan conf, never from shell env.
        # An absolute conf path is used only after os.path.isfile confirms
        # it exists, otherwise fall back to bare names via conanbuild PATH.
        cc, compilers = self._resolve_tool("c", ["clang", "cc"])
        cxx, _ = self._resolve_tool("cpp", ["clang++", "c++"])
        ar, _ = self._resolve_tool("ar", ["llvm-ar", "ar"])
        ranlib, _ = self._resolve_tool("ranlib", ["llvm-ranlib", "ranlib"])
        # Export for the bundled-zlib sub-make (upstream hardcodes
        # `cd $(zlibdir); make CFLAGS=... libz.a` without forwarding CC).
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        os.environ["AR"] = ar
        os.environ["RANLIB"] = ranlib
        # readonly_tmp: fall back to a writable TMPDIR when the worker's
        # /tmp is read-only. Only the temp root is replaced; no test is cut.
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v and _v not in ("0", "1") and os.path.isdir(_v):
                break
        else:
            _v = None
        if not _v:
            _v = os.path.join(self.build_folder, "tmp")
            try:
                os.makedirs(_v, exist_ok=True)
            except Exception:
                pass
            for _k in ("TMPDIR", "TMP", "TEMP"):
                os.environ[_k] = _v

        # Vendored bzip2/zstd: deterministic, no remote resolution involved.
        bzdir, bzlib = self._build_vendored_bz2(cc, ar)
        zstdinc, zstlib = self._build_vendored_zstd(cc, ar)

        incs, libdirs = self._dep_flags()
        bundled_zlib = os.path.join(self.source_folder, "zlib-1.2.2.f-rsyncable")
        cppflags = " ".join(
            [
                "-fPIC",
                "-DDELTARPM_64BIT",
                "-DBSDIFF_NO_SUF",
                # RPMDUMPHEADER must reach the compiler as a quoted C string literal.
                # It crosses two shell layers: (L1) this fragment is interpolated
                # into make ... CPPFLAGS="<frag>" ... run by sh, where \\ -> \
                # and \" -> " inside the outer double quotes; (L2) make runs
                # 'clang <CPPFLAGS> ...' via sh, where \" -> literal ".
                # Hence 3 backslashes + quote per side at runtime (chr-built so
                # the source stays free of escape-layering). Fewer backslashes
                # either close the outer quotes early or let L2 strip the quotes,
                # both yielding '#define RPMDUMPHEADER /usr/local/bin/...' and
                # the observed 20-error applydeltarpm.c failure.
                "-DRPMDUMPHEADER=" + chr(92) * 3 + chr(34) + "/usr/local/bin/rpmdumpheader" + chr(92) * 3 + chr(34),
                "-I" + bundled_zlib,
                "-I" + bzdir,
                "-I" + zstdinc,
            ]
            + ["-I" + d for d in incs]
        )
        cflags = "-fPIC -O2 -Wall -g -DWITH_ZSTD=1"
        ldflags = " ".join(["-L" + d for d in libdirs])
        ldlibs = "\"%s\" \"%s\" -llzma \"%s\"" % (
            bzlib, os.path.join(bundled_zlib, "libz.a"), zstlib)
        # NOTE: no `make check` — upstream has no test suite (see notes.md audit).
        # Build only the librpm-free tools; rpmdumpheader needs rpm (R36: unpublished).
        self.run(
            "make -j1 CC=%s SHELL=%s CFLAGS=\"%s\" CPPFLAGS=\"%s\" LDFLAGS=\"%s\" LDLIBS=\"%s\" %s"
            % (cc, self._config_shell(), cflags, cppflags, ldflags, ldlibs, " ".join(self._tools)),
            cwd=self.source_folder,
        )
        # Upstream test audit: no check/test target, no tests/ dir -> no_tests evidence.
        try:
            upstream = {
                "status": "no_tests",
                "framework": "make",
                "command": "make (upstream has no check/test target)",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "deltarpm-3.6.5 audited: top Makefile has no check/test target; "
                "tarball has no tests/ dir and no TEST/TEST_F/def test_ cases "
                "(only bundled-zlib contrib samples); make check would be a no-op",
            }
            msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
            print(msg, flush=True)
            self.output.info(msg)
        except Exception:
            pass

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for tool in self._tools:
            copy(self, tool, src=self.source_folder, dst=bindir)
        copy(self, "drpmsync", src=self.source_folder, dst=bindir)
        copy(self, "*.8", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man8"))
        licdir = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE.BSD", src=self.source_folder, dst=licdir)
        # Attribute the vendored codecs (both use file name LICENSE upstream).
        try:
            copy(self, "LICENSE", src=os.path.join(self.source_folder, "vendored", "bzip2-1.0.8"),
                 dst=os.path.join(licdir, "bzip2"))
        except Exception:
            pass
        try:
            copy(self, "LICENSE", src=os.path.join(self.source_folder, "vendored", "zstd-1.5.6"),
                 dst=os.path.join(licdir, "zstd"))
        except Exception:
            pass
        # Best effort: keep cli tools executable (HMDFS may ignore chmod).
        for tool in self._tools + ["drpmsync"]:
            try:
                fp = os.path.join(bindir, tool)
                if os.path.isfile(fp):
                    os.chmod(fp, 0o755)
            except Exception:
                pass

    def package_info(self):
        # Tool package: no libraries or headers for downstream linking.
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
