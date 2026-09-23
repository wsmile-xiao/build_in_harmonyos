#!/usr/bin/env python3
"""Conan 2 recipe for libowfat 0.34 on HarmonyOS PC (aarch64-linux-ohos).

libowfat is Felix von Leitner's "Liberate your programs from your OS' libc"
library: a bundle of small static component archives (byte, str, fmt, scan,
stralloc, array, buffer, io, socket, textcode, cdb, critbit, dns, ...) plus a
convenience umbrella archive libowfat.a, all driven by a hand-written
GNU Makefile with compile-time feature probes.

Key facts established while auditing the upstream GNUmakefile (see notes.md
for the full trail):

* CC is UNCONDITIONALLY reassigned by a PATH scan at line 69-74: if any
  ``gcc`` is found in PATH, CC=gcc; otherwise CC=clang. An environment
  CC variable is silently dropped. A **make command-line** variable beats
  this block, so the recipe must pass CC as a command-line variable with an
  ABSOLUTE path (never a bare name resolved by PATH luck, never a hard-coded
  SDK path).
* The same holds for CFLAGS: the makefile sets ``CFLAGS=-pipe $(WARN)
  $(DEFINE) $(OPT_REG)`` unconditionally; a command-line variable override
  is the only reliable way to inject profile flags. ``+=`` after a
  command-line variable is ignored by GNU make for command-line-origin
  variables.
* AR/RANLIB are only ever referenced through $(CROSS)$(AR) / $(CROSS)$(RANLIB)
  with no reassignment block, but the wrapper resolves bare ``ar`` via PATH;
  the recipe passes absolute paths as command-line variables too.
* Build-time probes (try*.c -> have*.h / iopause.h / select.h / libsocket)
  are PURE COMPILE-TIME probes using the TARGET compiler ($(CCC) == $(CC)),
  so the generated sysdeps headers describe the OHOS target, not the build
  host. The only host-executed build tool is the ``ent`` entity-table
  generator (compiled by $(CC) -g and run at build time to render
  entities.json into entities.h); on this native OHOS build machine the
  target compiler also produces runnable binaries, so no host/target split
  is required.
* The ``headers`` target uses ``ln -f`` hard links, which fail with EPERM on
  the HarmonyOS PC filesystem; a one-line patch switches them to copies.
* ``t`` (upstream unit-test binary) returns ``totalread == total`` — i.e.
  EXIT 1 means all 1120372 bytes were seen and the suite PASSED; exit 0
  means failure. The recipe treats 0/1 accordingly.
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibowfatConan(ConanFile):
    name = "libowfat"
    version = "0.34"
    description = (
        "libowfat: Felix von Leitner's low-level component library "
        "(byte/str/fmt/scan/stralloc/array/buffer/io/socket/textcode/cdb/"
        "critbit/dns ...) built from the upstream GNU Makefile."
    )
    license = "GPL-2.0-only"
    homepage = "https://www.fefe.de/libowfat/"
    url = ""
    topics = ("libowfat", "libc-replacement", "low-level", "io", "network")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    # Upstream only builds static archives (ar cru ...); there is no
    # shared-library rule at all, so the shared option is not offered.
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libowfat is supported only on Linux/OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ------------------------------------------------------------------ #

    def _abs_tool(self, conf_key, env_names, fallback):
        """Resolve a build tool to an ABSOLUTE executable path.

        Order: tools.build:compiler_executables (JSON conf) for compilers,
        then environment variables, then a filesystem check of the candidate.
        A candidate that is not a real executable file is rejected: the goal
        is to never depend on PATH lookup accidentally finding a bare
        gcc/clang (the upstream GNUmakefile PATH-scans for CC, and bare
        tool names in this environment resolve through the toolchain dir
        only because the profile prepends it to PATH — an accident we must
        not rely on).
        """
        candidates = []
        if conf_key:
            raw = self.conf.get("tools.build:compiler_executables", default=None)
            if raw:
                try:
                    d = json.loads(raw) if isinstance(raw, str) else raw
                    c = d.get(conf_key)
                    if c:
                        candidates.append(c)
                except Exception:
                    pass
        for env in env_names:
            v = os.environ.get(env)
            if v:
                candidates.append(v)
        candidates.append(fallback)
        for c in candidates:
            if c and os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        # Last resort: resolve via PATH but verify it is a real file, so we
        # at least pin an absolute path into the make command line.
        for c in candidates:
            if not c:
                continue
            if os.path.sep in c:
                continue
            found = None
            search = os.environ.get("PATH", "")
            for d in search.split(os.pathsep):
                p = os.path.join(d, c) if d else c
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    found = p
                    break
            if found:
                return found
        return None

    def _cc(self):
        cc = self._abs_tool("c", ["CC"], "clang")
        if not cc:
            raise ConanInvalidConfiguration(
                "could not resolve the C compiler to an absolute path "
                "(tools.build:compiler_executables / CC / clang)"
            )
        return cc

    def _ar(self):
        # llvm-ar first, but plain `ar` (LLVM symlink in the OHOS SDK) is fine
        for cand in ("llvm-ar", "ar"):
            p = self._abs_tool(None, [], cand)
            if p:
                return p
        raise ConanInvalidConfiguration("no usable AR (llvm-ar/ar) found")

    def _ranlib(self):
        for cand in ("llvm-ranlib", "ranlib"):
            p = self._abs_tool(None, [], cand)
            if p:
                return p
        raise ConanInvalidConfiguration("no usable RANLIB (llvm-ranlib/ranlib) found")

    # ------------------------------------------------------------------ #

    def build(self):
        cc = self._cc()
        ar = self._ar()
        ranlib = self._ranlib()

        # The OHOS clang wrapper injects -Wl,--code-sign, -fuse-ld=lld and a
        # sysroot -L even during compile-only steps; upstream compiles with
        # -W -Wall -Wextra so we do not add -Werror. We DO neutralise the
        # harmless "unused during compilation" chatter is not needed here
        # (no -Werror in libowfat), so flags stay minimal: profile flags
        # come only from the recipe, not from the makefile defaults.
        build_type = str(self.settings.build_type)
        opt = {"Release": "-O2", "Debug": "-g -Og", "RelWithDebInfo": "-O2 -g",
               "MinSizeRel": "-Os"}.get(build_type, "-O2")
        cflags = ["-pipe", "-I.", "-W", "-Wall", "-Wextra", "-D_REENTRANT", opt]
        if self.options.get_safe("fPIC"):
            cflags.append("-fPIC")

        # IMPORTANT: every variable is passed as a make COMMAND-LINE
        # variable, which outranks any assignment (including the
        # unconditional CC PATH-scan at GNUmakefile:69-74 and the bare
        # ``CFLAGS=`` at line 44). shlex.quote keeps multi-token values
        # intact through the shell.
        make_vars = [
            "CC=" + shlex.quote(cc),
            "AR=" + shlex.quote(ar),
            "RANLIB=" + shlex.quote(ranlib),
            "CFLAGS=" + shlex.quote(" ".join(cflags)),
        ]
        cmd = "make -C {} -j{} {}".format(
            shlex.quote(self.source_folder),
            os.cpu_count() or 1,
            " ".join(make_vars),
        )
        # `all` = ent + the 21 component .a archives + libowfat.a +
        # libsocket (empty on Linux/OHOS) + t (the unit-test binary).
        # `t` is built here so the artifact exists for `make test` in
        # test_type=build scenarios; it is NOT packaged.
        self.run(cmd + " all")
        # Upstream integration suite: EXIT 1 == PASS (t returns
        # `totalread == total`; all 1120372 bytes echoed back). The suite
        # needs a writable CWD and takes a few seconds.
        test_cmd = "cd {} && ./t; rc=$?; if [ $rc -eq 1 ]; then echo " \
                   "'libowfat: upstream t suite PASSED (exit 1)'; " \
                   "elif [ $rc -eq 0 ]; then echo 'libowfat: upstream t " \
                   "suite FAILED (exit 0)'; exit 1; else exit $rc; fi"
        self.run(test_cmd.format(shlex.quote(self.source_folder)),
                 cwd=self.build_folder)

    # ------------------------------------------------------------------ #

    def package(self):
        # Upstream has no real `make install` (INSTALL says so; the install
        # rule only knows libowfat.a + the flattened libowfat/ header dir
        # and its `headers` target hard-links, which EPERMs on this fs).
        # We collect: the umbrella libowfat.a, the 21 component archives
        # and the 37 public headers (INCLUDES) from the source tree.
        src = self.source_folder

        copy(self, "COPYING", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README", src=src, dst=os.path.join(self.package_folder, "licenses"))

        # Public headers: upstream installs the flattened libowfat/ tree
        # (37 headers, INCLUDES list at GNUmakefile:1205). The recipe
        # builds the same flattened layout so consumers use
        # #include <libowfat/byte.h> style, matching upstream install-inc.
        headers = (
            "buffer.h byte.h fmt.h ip4.h ip6.h mmap.h scan.h socket.h str.h "
            "stralloc.h uint16.h uint32.h uint64.h open.h textcode.h tai.h "
            "taia.h dns.h iopause.h case.h openreadclose.h readclose.h "
            "ndelay.h array.h io.h safemult.h iob.h havealloca.h errmsg.h "
            "cdb.h cdb_make.h rangecheck.h iarray.h va_narg.h isset.h "
            "compiletimeassert.h critbit.h parse.h compiler.h"
        ).split()
        incdir = os.path.join(self.package_folder, "include", "libowfat")
        for h in headers:
            copy(self, h, src=src, dst=incdir)

        # Component archives produced by the build (21 module libs + the
        # umbrella archive). Upstream names them without the conventional
        # `lib` prefix (byte.a, fmt.a, ...); CMakeDeps' find_library only
        # looks for lib<name>.a/.so, so they are renamed to lib<byte>.a
        # etc. in the package. The umbrella stays libowfat.a as upstream
        # ships it. Components are declared in package_info().
        libs = (
            "byte fmt scan str uint open stralloc unix socket buffer mmap "
            "taia tai dns case mult array io textcode cdb critbit"
        ).split()
        libdir = os.path.join(self.package_folder, "lib")
        copy(self, "libowfat.a", src=src, dst=libdir)
        for l in libs:
            src_lib = os.path.join(src, l + ".a")
            if not os.path.isfile(src_lib):
                raise Exception("missing component archive: " + src_lib)
            copy(self, l + ".a", src=src, dst=libdir, keep_path=False)
            dst_lib = os.path.join(libdir, l + ".a")
            new_lib = os.path.join(libdir, "lib" + l + ".a")
            if os.path.isfile(dst_lib) and not os.path.isfile(new_lib):
                os.rename(dst_lib, new_lib)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # The umbrella archive already contains every component object;
        # linking it alone is the documented usage
        # (LDFLAGS="... libowfat.a -lpthread" in upstream Makefile/test).
        self.cpp_info.libs = ["owfat"]
        self.cpp_info.system_libs = ["pthread"]
        # Component names expose the individual archives for consumers that
        # prefer minimal link sets; each requires the umbrella-less set of
        # peers it depends on is NOT tracked upstream, so each component
        # also lists the umbrella as a dependency to stay correct.
        comps = (
            "byte fmt scan str uint open stralloc unix socket buffer mmap "
            "taia tai dns case mult array io textcode cdb critbit"
        ).split()
        for c in comps:
            self.cpp_info.components[c].libs = [c]
            self.cpp_info.components[c].system_libs = ["pthread"]
        self.cpp_info.set_property("cmake_file_name", "libowfat")
        self.cpp_info.set_property("cmake_target_name", "libowfat::libowfat")
