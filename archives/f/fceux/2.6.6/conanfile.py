#!/usr/bin/env python3
"""Conan recipe for fceux 2.6.6 — NES/Famicom emulator (Qt5/SDL2, CMake).

FCEUX 2.6.6 (2023-08-26) is a maintenance release of the NES/Famicom/Dendy
emulator. The Qt/SDL port builds with CMake and requires Qt5 Widgets +
OpenGL (REQUIRED), SDL2 (REQUIRED), system zlib (REQUIRED) and system
minizip (REQUIRED). libarchive / x264 / x265 / ffmpeg (libav) / X11 /
xkbcommon are optional: upstream only enables them when pkg-config finds
them, otherwise the corresponding feature is silently disabled.

OHOS/aarch64 adaptation notes (see notes.md):
- Hard requirements come from the registry: qt5-qtbase/5.15.2.2 (Qt5 Widgets
  + OpenGL frontend; 5.15.2 has no OHOS binary in the registry — preflight
  reports "No compatible configuration found" — and every Qt consumer
  (flameshot, quazip, neovim-qt, ...) pins 5.15.2.2, quazip precedent),
  sdl2/2.30.10 (augustus-game precedent), zlib/1.3.1.1 (unique
  OHOS rebuild of 1.3.1 source with -fPIC static; conancenter has no 1.3.1.1
  so the graph auto-resolves to ohpcd without an RREV hash — gtk4/wv
  precedent — and override unifies qt5-qtbase's transitive zlib/1.3.1).
- minizip is VENDORED (no external requires): minizip/1.3.1 defaults to the
  CCI CMake recipe under the default remote order (fails with
  "System is unknown to cmake" on HarmonyOS); the locally computed RREV
  0e5742df... does not exist in any remote ("Unable to find ... in remotes",
  2026-09-10 preflight). There is no repo precedent with a verified ohpcd
  RREV for minizip, and minizip has no unique-version alias (only 1.3.1).
  So the recipe downloads the same zlib-1.3.1 tarball the ohpcd minizip
  package uses, compiles contrib/minizip (ioapi/mztools/unzip/zip) to a
  static libminizip.a, and exposes it via a generated minizip.pc on
  PKG_CONFIG_PATH for upstream pkg_check_modules(MINIZIP REQUIRED minizip).
  Same sources, same version, statically linked — no runtime .so to sign.
- Transitive bzip2/1.0.8 and expat are override-pinned to the
  cataract/1.0.0-verified ohpcd RREVs: the default resolution hits
  conancenter revisions (bzip2's CMake recipe cannot configure under
  CMAKE_SYSTEM_NAME=HarmonyOS; CCI expat drags in CCI cmake/4.4.3 whose
  conandata has no OHOS sources entry).
- Lua uses the upstream-bundled copy (src/lua, LUA_USE_LINUX) statically
  linked, so no external lua requirement (same as upstream when the system
  cannot provide lua5.1).
- PkgConfigDeps generates .pc files for the Conan closure so upstream
  pkg_check_modules(sdl2/...) resolves to registry packages;
  pkgconf/3.0.5 is a build requirement (gulkan/ekg2 precedent).
- CMakeDeps maps qt5-qtbase to the Qt5 config file name; the OHOS SDK
  toolchain restricts CMAKE_FIND_ROOT_PATH_MODE_PACKAGE to ONLY, so it is
  reopened to BOTH and the generators folder is passed as Qt5_DIR /
  CMAKE_PREFIX_PATH / CMAKE_FIND_ROOT_PATH (flameshot precedent).
- Upstream ships no test suite (no enable_testing/add_test anywhere; only
  NewPPUtests.txt documentation and the pipelines build smoke check), so
  there is no ctest/make check entry to run; the no_tests audit lives in
  test_package/MANIFEST.yml and the marker is re-emitted by test_package.
"""

import glob
import os
import shutil
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMakeDeps, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class FceuxConan(ConanFile):
    name = "fceux"
    version = "2.6.6"
    description = "NES/Famicom/Dendy emulator, Qt/SDL cross-platform port"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/TASEmulators/fceux"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports = "gles_immediate.h", "gles_immediate.cpp"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qt5-qtbase/5.15.2.2: 5.15.2 has no OHOS binary in the registry
        # ("No compatible configuration found"); every Qt consumer pins
        # 5.15.2.2 (flameshot/quazip/neovim-qt, 20+ references). This package
        # does not depend on qt5-qtsvg, so plain requires keeps full
        # CMakeDeps metadata (quazip precedent).
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("sdl2/2.30.10")
        # NOTE: no external minizip requires — vendored from zlib-1.3.1
        # contrib/minizip (see _build_vendored_minizip). Rationale in module
        # docstring: default remote order hits the CCI CMake recipe (fails on
        # HarmonyOS) and the locally computed RREV does not exist in remotes.
        # zlib version-suffix dedup: 1.3.1.1 is unique to this repo (same
        # upstream 1.3.1 sources + -fPIC static rebuild; conancenter has no
        # 1.3.1.1 so it auto-resolves to ohpcd — gtk4/4.22.4, wv/1.2.9
        # precedent). override unifies qt5-qtbase's transitive zlib/1.3.1.
        self.requires("zlib/1.3.1.1", override=True)
        # bzip2 RREV override: transitive bzip2/1.0.8 defaults to the
        # conancenter CMake recipe, which cannot configure under
        # CMAKE_SYSTEM_NAME=HarmonyOS. Force the cataract/1.0.0-verified
        # OHOS revision (Makefile recipe). fceux itself does not link bz2.
        self.requires(
            "bzip2/1.0.8#3b49a968338a1932917a5049fce54a4e",
            override=True,
        )
        # expat RREV override: dbus (via qt5-qtbase/5.15.2.2) declares
        # expat/2.8.2, default remote order hits conancenter; CCI expat's
        # tool_requires("cmake") pulls CCI cmake/4.4.3 whose conandata has
        # no OHOS sources entry (KeyError: 'OHOS'). Force the
        # cataract/1.0.0-verified ohpcd revision (no requirements /
        # tool_requires), cutting off both CCI expat and CCI cmake builds.
        self.requires(
            "expat/2.8.2.1#332af6a48367eceadb1f9cf0c32f340d",
            override=True,
        )

    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.5")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "fceux only supports Linux and OHOS, got %s" % self.settings.os
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "fceux on OHOS only supports armv8, got %s" % self.settings.arch
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=5, retry_wait=10)
        # Vendored minizip sources: same zlib-1.3.1 tarball the ohpcd
        # minizip/1.3.1 package builds from (contrib/minizip/).
        get(self, **self.conan_data["minizip_sources"],
            destination=os.path.join(self.source_folder, "minizip-src"),
            strip_root=True, retry=5, retry_wait=10)

    def _sdk_llvm_libdir(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or shutil.which("clang")
        if not cc:
            self.output.info("C compiler not found, skip OHOS SDK link guard")
            return ""
        sdk_lib = os.path.normpath(os.path.join(
            os.path.dirname(os.path.realpath(cc)), os.pardir, "lib"
        ))
        if not os.path.isfile(os.path.join(sdk_lib, "libxml2.so.16")):
            self.output.info("no libxml2.so.16 under llvm/lib, skip link guard")
            return ""
        return sdk_lib

    def _vendored_minizip_prefix(self):
        return os.path.join(self.build_folder, "vendored-minizip", "install")

    def _build_environment(self):
        environment = Environment()
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        # hmbs injects a task-private writable TMPDIR (host /tmp is
        # read-only); propagate it so the compiler driver / archiver temp
        # files never fall back to /tmp ([readonly_tmp] diagnosis).
        for _tmpvar in ("TMPDIR", "TMP", "TEMP"):
            _tmpval = os.environ.get(_tmpvar)
            if _tmpval:
                environment.define(_tmpvar, _tmpval)
        # Vendored zlib.pc + minizip.pc live here; keep Conan generators too.
        environment.prepend_path(
            "PKG_CONFIG_PATH",
            os.path.join(self._vendored_zlib_prefix(), "lib", "pkgconfig"),
        )
        environment.prepend_path(
            "PKG_CONFIG_PATH",
            os.path.join(self._vendored_minizip_prefix(), "lib", "pkgconfig"),
        )
        environment.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        return environment

    @staticmethod
    def _tool_next_to(compiler, tool):
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        candidate = os.path.join(bindir, tool) if bindir else ""
        return candidate if candidate and os.path.isfile(candidate) else ""

    def _resolve_tool(self, configured, fallback):
        # Prefer an existing configured absolute path; otherwise PATH lookup
        # (hmbs/profile prepend SDK + /usr/local/bin); otherwise the sibling
        # tool next to the configured compiler (SDK llvm/bin layout).
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback)
        if found:
            return found
        if configured:
            sibling = self._tool_next_to(configured, fallback)
            if sibling:
                return sibling
        return fallback

    def _exec_tool(self, tool):
        if self._is_script(tool):
            return ["sh", tool]
        return [tool]

    @staticmethod
    def _is_script(path):
        if not path or not os.path.isfile(path):
            return False
        try:
            with open(path, "rb") as handle:
                return handle.read(2) == b"#!"
        except OSError:
            return False

    def _vendored_zlib_prefix(self):
        return os.path.join(self.build_folder, "vendored-zlib", "install")

    def _build_vendored_zlib(self):
        """Compile zlib-1.3.1 core to static libz.a + headers + zlib.pc.

        Third route for the FindZLIB failure (rounds 1-2 tried forwarding
        the Conan zlib package and both missed: override=True adds no
        direct edge so self.dependencies["zlib"] raises, and PkgConfigDeps
        emits no zlib.pc for the override-only node). Instead build libz
        from the already-vendored zlib-1.3.1 sources (same tarball as the
        ohpcd minizip package, same version) and satisfy upstream
        find_package(ZLIB) from that prefix — no Conan graph lookup.
        """
        zsrc = os.path.join(self.source_folder, "minizip-src")
        if not os.path.isfile(os.path.join(zsrc, "zlib.h")):
            raise ConanInvalidConfiguration(
                "vendored zlib sources missing: %s" % zsrc
            )
        prefix = self._vendored_zlib_prefix()
        libdir = os.path.join(prefix, "lib")
        incdir = os.path.join(prefix, "include")
        pcdir = os.path.join(libdir, "pkgconfig")
        for d in (libdir, incdir, pcdir):
            os.makedirs(d, exist_ok=True)
        for h in ("zlib.h", "zconf.h"):
            src_h = os.path.join(zsrc, h)
            if os.path.isfile(src_h):
                shutil.copy2(src_h, os.path.join(incdir, h))
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = self._resolve_tool(compilers.get("c"), "clang")
        objdir = os.path.join(self.build_folder, "vendored-zlib", "obj")
        os.makedirs(objdir, exist_ok=True)
        cc_cmd = " ".join(shlex.quote(p) for p in self._exec_tool(cc))
        cflags = "-fPIC -O2 -I%s" % zsrc
        objs = []
        for srcfile in ("adler32.c", "compress.c", "crc32.c", "deflate.c",
                        "gzclose.c", "gzlib.c", "gzread.c", "gzwrite.c",
                        "inflate.c", "infback.c", "inftrees.c", "inffast.c",
                        "trees.c", "uncompr.c", "zutil.c"):
            obj = os.path.join(objdir, srcfile.replace(".c", ".o"))
            self.run("%s %s -c %s -o %s" % (
                cc_cmd, cflags,
                shlex.quote(os.path.join(zsrc, srcfile)),
                shlex.quote(obj),
            ))
            objs.append(shlex.quote(obj))
        static_lib = os.path.join(libdir, "libz.a")
        ar = self._resolve_tool(compilers.get("ar"), "llvm-ar")
        if ar == "llvm-ar" and not shutil.which("llvm-ar"):
            ar = self._resolve_tool(compilers.get("ar"), "ar")
        ar_cmd = " ".join(shlex.quote(p) for p in self._exec_tool(ar))
        self.run("%s rcs %s %s" % (ar_cmd, shlex.quote(static_lib), " ".join(objs)))
        ranlib = self._resolve_tool(compilers.get("ranlib"), "llvm-ranlib")
        ranlib_cmd = " ".join(shlex.quote(p) for p in self._exec_tool(ranlib))
        try:
            self.run("%s %s" % (ranlib_cmd, shlex.quote(static_lib)))
        except Exception:
            pass
        self.output.info("vendored libz.a: %s" % static_lib)
        pc = """prefix=%s
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include

Name: zlib
Description: Vendored zlib 1.3.1 (static, for fceux upstream find_package)
Version: 1.3.1
Libs: -L${libdir} -lz
Cflags: -I${includedir}
""" % prefix
        with open(os.path.join(pcdir, "zlib.pc"), "w", encoding="utf-8", newline="\n") as f:
            f.write(pc)
        self.output.info("vendored zlib.pc: %s" % os.path.join(pcdir, "zlib.pc"))

    def _build_vendored_minizip(self):
        """Compile zlib-1.3.1 contrib/minizip to static lib + minizip.pc."""
        zlib_root = os.path.join(self.source_folder, "minizip-src")
        mz_src = os.path.join(zlib_root, "contrib", "minizip")
        if not os.path.isfile(os.path.join(mz_src, "unzip.c")):
            raise ConanInvalidConfiguration(
                "vendored minizip sources missing: %s" % mz_src
            )
        prefix = self._vendored_minizip_prefix()
        libdir = os.path.join(prefix, "lib")
        incdir = os.path.join(prefix, "include", "minizip")
        pcdir = os.path.join(libdir, "pkgconfig")
        for d in (libdir, incdir, pcdir):
            os.makedirs(d, exist_ok=True)
        # Headers: same 5 public headers the ohpcd minizip package ships.
        # Install BOTH layouts: include/minizip/*.h (namespaced, ohpcd style)
        # AND include/*.h (flat, Debian style). Upstream fceux uses the flat
        # spelling `#include <unzip.h>` (AboutWindow.cpp:26), which the
        # namespaced dir alone cannot satisfy with `-I<pp>/include`.
        for h in ("crypt.h", "ioapi.h", "mztools.h", "unzip.h", "zip.h"):
            src_h = os.path.join(mz_src, h)
            if os.path.isfile(src_h):
                shutil.copy2(src_h, os.path.join(incdir, h))
                shutil.copy2(src_h, os.path.join(prefix, "include", h))

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        # NOTE: must run inside _build_environment() (see build()): the OHOS
        # SDK clang needs LD_LIBRARY_PATH to llvm/lib (libxml2.so.16) and the
        # task-private TMPDIR; outside that env it fails with
        # "/bin/sh: .../clang: inaccessible or not found".
        cc = self._resolve_tool(compilers.get("c"), "clang")
        # Vendored zlib headers (same 1.3.1 sources, built by
        # _build_vendored_zlib just before this step).
        zlib_inc = os.path.join(self._vendored_zlib_prefix(), "include")

        objdir = os.path.join(self.build_folder, "vendored-minizip", "obj")
        os.makedirs(objdir, exist_ok=True)
        cc_cmd = " ".join(shlex.quote(p) for p in self._exec_tool(cc))
        cflags = "-fPIC -O2 -I%s -I%s" % (zlib_inc, mz_src)
        objs = []
        for srcfile in ("ioapi.c", "mztools.c", "unzip.c", "zip.c"):
            obj = os.path.join(objdir, srcfile.replace(".c", ".o"))
            self.run("%s %s -c %s -o %s" % (
                cc_cmd, cflags,
                shlex.quote(os.path.join(mz_src, srcfile)),
                shlex.quote(obj),
            ))
            objs.append(shlex.quote(obj))
        static_lib = os.path.join(libdir, "libminizip.a")
        # Resolve archiver via PATH / compiler sibling (zimg precedent);
        # never hardcode SDK absolute paths (layout varies per worker).
        ar = self._resolve_tool(compilers.get("ar"), "llvm-ar")
        if ar == "llvm-ar" and not shutil.which("llvm-ar"):
            ar = self._resolve_tool(compilers.get("ar"), "ar")
        ar_cmd = " ".join(shlex.quote(p) for p in self._exec_tool(ar))
        ar_bin = ar
        try:
            self.run("%s rcs %s %s" % (ar_cmd, shlex.quote(static_lib), " ".join(objs)))
            ar_ok = True
        except Exception:
            ar_ok = False
        if not ar_ok:
            raise ConanInvalidConfiguration("no working ar found for vendored minizip")
        # Ranlib (best effort; llvm-ar archives work without it too).
        ranlib = self._resolve_tool(compilers.get("ranlib"), "llvm-ranlib")
        ranlib_cmd = " ".join(shlex.quote(p) for p in self._exec_tool(ranlib))
        try:
            self.run("%s %s" % (ranlib_cmd, shlex.quote(static_lib)))
        except Exception:
            pass
        self.output.info("vendored minizip static lib via %s: %s" % (ar_bin, static_lib))

        pc = """prefix=%s
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include

Name: minizip
Description: Zip library from zlib (vendored 1.3.1, static)
Version: 1.3.1
Requires: zlib
Libs: -L${libdir} -lminizip
Cflags: -I${includedir} -I${includedir}/minizip
""" % prefix
        with open(os.path.join(pcdir, "minizip.pc"), "w", encoding="utf-8", newline="\n") as f:
            f.write(pc)
        self.output.info("vendored minizip.pc: %s" % os.path.join(pcdir, "minizip.pc"))

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()
        PkgConfigDeps(self).generate()
        # NOTE: conan CMakeToolchain is intentionally NOT generated here.
        # Under os=OHOS it maps CMAKE_SYSTEM_NAME to a value stock cmake does
        # not recognise ("System is unknown to cmake" + broken compiler
        # check, ML-0035); build() uses the self-discovered SDK
        # ohos.toolchain.cmake + bare cmake instead
        # (expat/2.8.2.1, zstd/1.5.7.1 precedent).

    def _ohos_toolchain(self):
        # Self-discover OHOS NDK ohos.toolchain.cmake (no profile
        # user_toolchain dependency). Same approach as expat/2.8.2.1,
        # zstd/1.5.7.1, glfw, libjpeg-turbo — plus a geogram/1.10.1-style
        # task-local fallback: the preflight worker ships its SDK under
        # /storage/Users/currentUser/usr/local (HMBS_BUILD_TOOLS), not
        # /data/service/hnp, so the legacy glob alone hard-fails with
        # "Cannot find ohos.toolchain.cmake".
        ut = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain",
            default=[], check_type=list,
        )
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut)
        if ndk:
            candidates.append(
                os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")
            )
            # NDK may already point at <sdk>/ohos/native.
            candidates.append(
                os.path.join(ndk, "ohos", "native", "build", "cmake",
                             "ohos.toolchain.cmake")
            )
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/storage/Users/currentUser/usr/local/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake",
        ):
            globbed = sorted(glob.glob(pattern))
            if globbed:
                self.output.info("ohos.toolchain via glob %s: %s" % (pattern, globbed[-1]))
                return globbed[-1]
        # Fallback: generate a minimal task-local toolchain (geogram
        # precedent). Log every probe so the next preflight log shows what
        # the worker actually provides.
        return self._ohos_toolchain_fallback()

    def _ohos_sdk_compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        for key in ("c", "cpp"):
            cand = compilers.get(key)
            if cand and os.path.isfile(cand):
                self.output.info("OHOS compiler from profile conf [%s]: %s" % (key, cand))
                return cand
        for envkey in ("OHOS_SDK_ROOT", "OHOS_NDK_HOME", "HMBS_INSTALL"):
            base = os.environ.get(envkey, "")
            for rel in ("bin/clang", "ohos/native/llvm/bin/clang",
                        "native/llvm/bin/clang"):
                cand = os.path.join(base, rel) if base else ""
                if cand and os.path.isfile(cand):
                    self.output.info("OHOS compiler via $%s: %s" % (envkey, cand))
                    return cand
        for base in ("/storage/Users/currentUser/usr/local",
                     "/data/service/hnp"):
            for rel in ("bin/clang", "bin/clang++",
                        "ohos/native/llvm/bin/clang"):
                cand = os.path.join(base, rel)
                if os.path.isfile(cand):
                    self.output.info("OHOS compiler via base %s: %s" % (base, cand))
                    return cand
        found = shutil.which("clang")
        if found:
            self.output.info("OHOS compiler via PATH: %s" % found)
            return found
        return ""

    def _ohos_toolchain_fallback(self):
        cc = self._ohos_sdk_compiler()
        if not cc or not os.path.isfile(cc):
            self.output.warning(
                "ohos.toolchain.cmake not found and no clang discovered; "
                "checked user_toolchain/OHOS_NDK_HOME/legacy globs/PATH")
            raise ConanInvalidConfiguration(
                "Cannot find ohos.toolchain.cmake: set OHOS_NDK_HOME, or configure "
                "tools.cmake.cmaketoolchain:user_toolchain=[<sdk>/ohos/native/build/cmake/ohos.toolchain.cmake] in profile [conf]"
            )
        real_cc = os.path.realpath(cc)
        bindir = os.path.dirname(real_cc)
        cxx = os.path.join(bindir, "clang++")
        if not os.path.isfile(cxx):
            cxx = cc + "++" if cc.endswith("clang") else ""
        # Sysroot probes: harmonybrew Cellar (<sdk>/native/sysroot), classic
        # SDK (<sdk>/ohos/native/sysroot), preflight (<sdk>/sysroot), plus
        # `clang -print-sysroot`. Upstream OpenGL mapping needs the sysroot
        # GLESv2/EGL; omit only if truly absent (compiler built-in default).
        sysroot = ""
        try:
            import subprocess
            out = subprocess.run(
                [real_cc, "-print-sysroot"],
                capture_output=True, text=True, timeout=30,
            )
            cand = (out.stdout or "").strip()
            if cand and os.path.isdir(cand):
                sysroot = cand
                self.output.info("OHOS sysroot via -print-sysroot: %s" % sysroot)
        except Exception as e:
            self.output.info("clang -print-sysroot query failed: %s" % e)
        if not sysroot:
            seen = set()
            anchor = bindir
            for _ in range(6):
                for rel in ("native/sysroot", "ohos/native/sysroot", "sysroot"):
                    norm = os.path.normpath(os.path.join(anchor, rel))
                    if norm not in seen:
                        seen.add(norm)
                        if os.path.isdir(norm):
                            sysroot = norm
                            break
                if sysroot:
                    break
                parent = os.path.dirname(anchor)
                if parent == anchor:
                    break
                anchor = parent
            for cand in ("/storage/Users/currentUser/usr/local/sysroot",
                         "/data/service/hnp/sysroot"):
                if not sysroot and os.path.isdir(cand):
                    sysroot = cand
            if sysroot:
                self.output.info("OHOS sysroot via layout walk: %s" % sysroot)
        self.output.warning(
            "ohos.toolchain.cmake missing; using task-local fallback "
            "toolchain (cc=%s cxx=%s sysroot=%s)" % (real_cc, cxx, sysroot or "-"))
        path = os.path.join(self.build_folder, "fceux-ohos-toolchain.cmake")
        os.makedirs(self.build_folder, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("set(CMAKE_SYSTEM_NAME OHOS)\n")
            f.write("set(CMAKE_SYSTEM_PROCESSOR aarch64)\n")
            f.write('set(CMAKE_C_COMPILER "%s")\n' % real_cc.replace("\\", "/"))
            if cxx and os.path.isfile(cxx):
                f.write('set(CMAKE_CXX_COMPILER "%s")\n' % os.path.realpath(cxx).replace("\\", "/"))
            if sysroot:
                f.write('set(CMAKE_SYSROOT "%s")\n' % sysroot.replace("\\", "/"))
            f.write("set(CMAKE_C_COMPILER_TARGET aarch64-unknown-linux-ohos)\n")
            f.write("set(CMAKE_CXX_COMPILER_TARGET aarch64-unknown-linux-ohos)\n")
            f.write("set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)\n")
            # build() overrides PACKAGE mode to BOTH via -D so Conan Qt5
            # config packages remain findable; keep toolchain default ONLY.
        return path

    def _patch_upstream_opengl_for_ohos(self):
        # Upstream src/CMakeLists.txt does `find_package(OpenGL REQUIRED)`
        # (desktop GL/GLX). OHOS ships GLESv2+EGL only, so map the request on
        # OHOS and keep REQUIRED semantics (FATAL when GLESv2 is absent —
        # never a silent skip). Idempotent: only patches while the original
        # call is still present (source cache may persist across retries).
        # astromenace/1.3.2 precedent (GLESv2+EGL substitution), here without
        # touching upstream sources beyond this one call.
        path = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        try:
            with open(path, encoding="utf-8") as f:
                txt = f.read()
        except OSError as e:
            self.output.warning("OpenGL patch: cannot read %s: %s" % (path, e))
            return
        marker = "find_package(OpenGL REQUIRED)"
        if marker not in txt and "OHOS_GLESv2_LIB" not in txt:
            self.output.info("OpenGL patch: already applied or upstream changed, skip")
            return
        block = (
            'if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")\n'
            '  # OHOS has GLESv2+EGL, no desktop GL/GLX: satisfy the REQUIRED\n'
            '  # OpenGL dependency from the platform libraries (astromenace precedent).\n'
            '  message(STATUS "OHOS GL lookup: CMAKE_SYSROOT=${CMAKE_SYSROOT}")\n'
            '  find_library(OHOS_GLESv2_LIB NAMES GLESv2 GLESv3\n'
            '    PATHS ${CMAKE_SYSROOT}/usr/lib\n'
            '          ${CMAKE_SYSROOT}/usr/lib/aarch64-linux-ohos\n'
            '          ${CMAKE_SYSROOT}/lib\n'
            '    NO_DEFAULT_PATH)\n'
            '  if(NOT OHOS_GLESv2_LIB)\n'
            '    find_library(OHOS_GLESv2_LIB NAMES GLESv2 GLESv3)\n'
            '  endif()\n'
            '  find_library(OHOS_EGL_LIB NAMES EGL\n'
            '    PATHS ${CMAKE_SYSROOT}/usr/lib\n'
            '          ${CMAKE_SYSROOT}/usr/lib/aarch64-linux-ohos\n'
            '          ${CMAKE_SYSROOT}/lib\n'
            '    NO_DEFAULT_PATH)\n'
            '  if(NOT OHOS_EGL_LIB)\n'
            '    find_library(OHOS_EGL_LIB NAMES EGL)\n'
            '  endif()\n'
            '  message(STATUS "OHOS GL lookup result: GLESv2=${OHOS_GLESv2_LIB} EGL=${OHOS_EGL_LIB}")\n'
            '  if(NOT OHOS_GLESv2_LIB)\n'
            '    message(FATAL_ERROR "GLESv2 not found on OHOS (replaces desktop OpenGL)")\n'
            '  endif()\n'
            '  set(OPENGL_LIBRARIES ${OHOS_GLESv2_LIB} ${OHOS_EGL_LIB})\n'
            '  set(OPENGL_INCLUDE_DIR "")\n'
            '  set(OPENGL_FOUND TRUE)\n'
            '  find_path(OHOS_GLES_INCLUDE GLES2/gl2.h\n'
            '    PATHS ${CMAKE_SYSROOT}/usr/include\n'
            '    NO_DEFAULT_PATH)\n'
            '  if(NOT OHOS_GLES_INCLUDE)\n'
            '    find_path(OHOS_GLES_INCLUDE GLES2/gl2.h)\n'
            '  endif()\n'
            '  if(OHOS_GLES_INCLUDE)\n'
            '    include_directories(${OHOS_GLES_INCLUDE})\n'
            '  endif()\n'
            'else()\n'
            '  find_package(OpenGL REQUIRED)\n'
            'endif()'
        )
        if marker in txt:
            txt = txt.replace(marker, block)
        else:
            # Upgrade path: source cache already holds the round-2 narrow
            # find_library block (bare NAMES without sysroot PATHS) which
            # just failed with "GLESv2 not found". Replace the whole OHOS
            # conditional with the robust sysroot-aware version above.
            import re
            pattern = re.compile(
                r'if\(CMAKE_SYSTEM_NAME STREQUAL "OHOS"\)\s*\n'
                r'.*?\n'
                r'else\(\)\s*\n'
                r'\s*find_package\(OpenGL REQUIRED\)\s*\n'
                r'endif\(\)',
                re.DOTALL,
            )
            txt, n = pattern.subn(block, txt, count=1)
            if n == 0:
                self.output.warning("OpenGL patch: upgrade pattern not matched, skip")
                return
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
        self.output.info("OpenGL patch: mapped desktop OpenGL to GLESv2/EGL on OHOS")

    def _patch_upstream_githdr_tmpdir(self):
        # scripts/genGitHdr.sh hardcodes TMP_FILE="/tmp/$FILE"; host /tmp
        # is read-only on the worker ([readonly_tmp] diagnosis). Point only
        # the temp root at the task-private TMPDIR/TMP/TEMP, keep the
        # generate-or-diff logic untouched. Idempotent.
        path = os.path.join(self.source_folder, "scripts", "genGitHdr.sh")
        try:
            with open(path, encoding="utf-8") as f:
                txt = f.read()
        except OSError as e:
            self.output.warning("genGitHdr patch: cannot read %s: %s" % (path, e))
            return
        old = 'TMP_FILE="/tmp/$FILE";'
        new = 'TMP_FILE="${TMPDIR:-${TMP:-${TEMP:-/tmp}}}/$FILE";'
        if old in txt:
            txt = txt.replace(old, new)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(txt)
            self.output.info("genGitHdr patch: temp root now respects TMPDIR")
        elif "TMPDIR" in txt:
            self.output.info("genGitHdr patch: already applied, skip")
        else:
            self.output.warning("genGitHdr patch: pattern not matched, skip")

    def _patch_upstream_qt_targets_for_ohos(self):
        # Upstream src/CMakeLists.txt uses legacy variables
        # include_directories(${Qt5Widgets_INCLUDE_DIRS}) +
        # target_link_libraries(... ${Qt5Widgets_LIBRARIES} ...). CMakeDeps
        # only generates modern imported targets (Qt5::Widgets/Gui/Core) so
        # the legacy variables are empty -> 'QWidget' file not found at
        # mocs_compilation.cpp.o (quazip/flameshot use Qt5:: targets, fceux
        # is the only legacy-style Qt consumer). Append a guarded modern
        # link after the existing block: it propagates both INTERFACE
        # includes (fixes compile) and libs (fixes link). Idempotent.
        path = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        try:
            with open(path, encoding="utf-8") as f:
                txt = f.read()
        except OSError as e:
            self.output.warning("Qt targets patch: cannot read %s: %s" % (path, e))
            return
        if "OHOS_QT5_MODERN_TARGETS" in txt:
            self.output.info("Qt targets patch: already applied, skip")
            return
        anchor = "target_link_libraries( ${APP_NAME}"
        if anchor not in txt:
            self.output.warning("Qt targets patch: anchor not matched, skip")
            return
        shim = (
            "\n\n"
            "# OHOS_QT5_MODERN_TARGETS: CMakeDeps provides Qt5:: imported\n"
            "# targets but not legacy Qt5Widgets_* variables; link modern\n"
            "# targets so INTERFACE includes/libs reach the fceux target.\n"
            "if(TARGET Qt5::Widgets)\n"
            "  target_link_libraries(${APP_NAME} Qt5::Widgets Qt5::Gui Qt5::Core)\n"
            "endif()\n"
        )
        # Insert right after the closing paren of the target_link_libraries
        # block (first ')' following the anchor).
        start = txt.index(anchor)
        end = txt.index(")", start)
        txt = txt[: end + 1] + shim + txt[end + 1 :]
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
        self.output.info("Qt targets patch: appended Qt5::Widgets/Gui/Core link")

    def _conan_header_dir(self, dep_name, header_name, subdir=""):
        """Probe <pkg>/include/<subdir> then <pkg>/include for a header.

        augustus-game/4.0.0 precedent (same sdl2/2.30.10): SDL headers live
        under include/SDL2, so plain -I<pkg>/include cannot resolve
        `#include <SDL.h>`; PkgConfigDeps CFLAGS may not carry the suffixed
        dir either. Returns "" when unavailable (caller skips; REQUIRED-ness
        stays enforced by upstream pkg_check_modules, never silently passed).
        """
        try:
            pkg = self.dependencies[dep_name].package_folder
        except Exception as e:
            self.output.info("%s include probe: dep unavailable (%s)"
                             % (dep_name, e))
            return ""
        if not pkg:
            return ""
        candidates = []
        if subdir:
            candidates.append(os.path.join(pkg, "include", subdir))
        candidates.append(os.path.join(pkg, "include"))
        for cand in candidates:
            if os.path.isfile(os.path.join(cand, header_name)):
                self.output.info("%s header %s via %s"
                                 % (dep_name, header_name, cand))
                return cand
        self.output.info("%s header %s not found under %s"
                         % (dep_name, header_name, pkg))
        return ""

    def _patch_upstream_sdl_pkgconfig_includes(self):
        # Upstream consumes SDL2 *only* via add_definitions(${SDL2_CFLAGS}):
        # -I smuggled through add_definitions is fragile (it is meant for -D)
        # and never reaches AUTOMOC's moc invocation. The canonical consumer
        # is SDL2_INCLUDE_DIRS via include_directories() (this same file
        # already does that for X11). This covers the .pc-right case; the
        # recipe additionally injects the probed dir via CMAKE_CXX_FLAGS /
        # CMAKE_AUTOMOC_MOC_OPTIONS. Idempotent, no absolute paths baked in.
        path = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        try:
            with open(path, encoding="utf-8") as f:
                txt = f.read()
        except OSError as e:
            self.output.warning("SDL includes patch: cannot read %s: %s" % (path, e))
            return
        if ("OHOS_SDL2_PKGCONFIG_INCLUDES" in txt
                or "include_directories(${SDL2_INCLUDE_DIRS})" in txt):
            self.output.info("SDL includes patch: already applied, skip")
            return
        old = "add_definitions( ${SDL2_CFLAGS} -D__SDL__ )"
        if old not in txt:
            self.output.warning("SDL includes patch: pattern not matched, skip")
            return
        new = (old + "\n"
               "  # OHOS_SDL2_PKGCONFIG_INCLUDES: feed pkg-config include dirs\n"
               "  # to the target AND automoc (add_definitions -I above does not\n"
               "  # reach moc; the /SDL2-suffixed dir is needed for <SDL.h>).\n"
               "  include_directories(${SDL2_INCLUDE_DIRS})")
        txt = txt.replace(old, new)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
        self.output.info("SDL includes patch: added include_directories(SDL2_INCLUDE_DIRS)")

    def _patch_upstream_timestamp_for_ohos(self):
        # Upstream src/utils/timeStamp.cpp includes <x86intrin.h>
        # unconditionally on non-Windows and calls __rdtsc(). On OHOS/aarch64
        # the SDK clang (aarch64 target) cannot parse that x86-only header:
        # immintrin.h -> mmintrin.h errors "only meant to be used on x86 and
        # x64 architecture", 20 errors, build stops at timeStamp.cpp.o (this
        # round's log). Upstream issue #663 fix (commit 3960962) only guards
        # with __QT_DRIVER__ — but the Qt build defines __QT_DRIVER__, so
        # ARM+Qt still hits the x86 header; chimera-linux cports works around
        # it with __FCEU_X86_TSC_ENABLE (never defined = TSC always off).
        # Here guard by architecture instead: x86/x64 keeps the exact
        # upstream path, other arches (OHOS armv8) fall back to the monotonic
        # clock so tsc calibration still yields a valid frequency instead of
        # a dead zero. Idempotent via FCEU_HAS_X86_TSC marker.
        path = os.path.join(self.source_folder, "src", "utils", "timeStamp.cpp")
        try:
            with open(path, encoding="utf-8") as f:
                txt = f.read()
        except OSError as e:
            self.output.warning("timeStamp patch: cannot read %s: %s" % (path, e))
            return
        if "FCEU_HAS_X86_TSC" in txt:
            self.output.info("timeStamp patch: already applied, skip")
            return
        old = ("#if defined(WIN32)\n"
               "#include <intrin.h>\n"
               "#pragma intrinsic(__rdtsc)\n"
               "#else\n"
               "#include <x86intrin.h>\n"
               "#endif\n"
               "\n"
               "static uint64_t rdtsc()\n"
               "{\n"
               "\treturn __rdtsc();\n"
               "}")
        if old not in txt:
            # Tab/space variant (patched or reformatted upstream).
            old = (old.replace("\treturn", "        return")
                   if "\treturn" in old else old)
        if old not in txt:
            self.output.warning("timeStamp patch: pattern not matched, skip")
            return
        new = ("#if defined(__i386__) || defined(__x86_64__) "
               "|| defined(_M_IX86) || defined(_M_X64)\n"
               "#define FCEU_HAS_X86_TSC 1\n"
               "#endif\n"
               "\n"
               "#if defined(FCEU_HAS_X86_TSC)\n"
               "#if defined(WIN32)\n"
               "#include <intrin.h>\n"
               "#pragma intrinsic(__rdtsc)\n"
               "#else\n"
               "#include <x86intrin.h>\n"
               "#endif\n"
               "\n"
               "static uint64_t rdtsc()\n"
               "{\n"
               "\treturn __rdtsc();\n"
               "}\n"
               "#else\n"
               "// OHOS/aarch64 port (no x86 TSC): monotonic-clock fallback so\n"
               "// timeStampRecord::tscCalibrate() still measures a valid\n"
               "// frequency; <time.h> already comes via timeStamp.h on POSIX.\n"
               "static uint64_t rdtsc()\n"
               "{\n"
               "#if defined(__linux__) || defined(__APPLE__) || defined(__unix__)\n"
               "\tstruct timespec _ohos_ts;\n"
               "\tclock_gettime(CLOCK_MONOTONIC, &_ohos_ts);\n"
               "\treturn (uint64_t)_ohos_ts.tv_sec * 1000000000ULL "
               "+ (uint64_t)_ohos_ts.tv_nsec;\n"
               "#else\n"
               "\treturn 0;\n"
               "#endif\n"
               "}\n"
               "#endif")
        txt = txt.replace(old, new)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
        self.output.info("timeStamp patch: guarded x86 TSC by architecture")

    def _patch_upstream_gles_immediate_shim(self):
        # OHOS ships GLESv2+EGL only: ConsoleViewerGL.cpp compiles (Qt headers
        # declare the desktop entry points) but the link fails with
        # `undefined symbol: glLoadIdentity/glMatrixMode/glOrtho/glBegin/
        # glTexCoord2f/glVertex2f/glEnd` — the fixed-pipeline immediate mode
        # paintGL() path has no GLESv2 equivalent. The recipe ships
        # gles_immediate.cpp (same dir, exported) which implements exactly
        # that used subset on a GLSL textured-quad program; copy it into the
        # source tree and compile it on OHOS only (desktop keeps using real
        # libGL, so the shim must not be built there — duplicate symbols).
        # Idempotent via FCEUX_OHOS_GLES_IMMEDIATE marker.
        qt_dir = os.path.join(self.source_folder, "src", "drivers", "Qt")
        for fname in ("gles_immediate.cpp", "gles_immediate.h"):
            src = os.path.join(self.recipe_folder, fname)
            dst = os.path.join(qt_dir, fname)
            try:
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
            except OSError as e:
                self.output.warning("GLES shim copy %s failed: %s" % (fname, e))
                return
        path = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        try:
            with open(path, encoding="utf-8") as f:
                txt = f.read()
        except OSError as e:
            self.output.warning("GLES shim patch: cannot read %s: %s" % (path, e))
            return
        if "FCEUX_OHOS_GLES_IMMEDIATE" in txt:
            self.output.info("GLES shim patch: already applied, skip")
            return
        anchor = "set(SOURCES ${SRC_CORE} ${SRC_DRIVERS_COMMON} ${SRC_DRIVERS_SDL})"
        if anchor not in txt:
            self.output.warning("GLES shim patch: anchor not matched, skip")
            return
        shim = (
            "\n\n"
            "# FCEUX_OHOS_GLES_IMMEDIATE: OHOS has GLESv2+EGL, no desktop GL\n"
            "# immediate mode; compile the recipe-shipped shim (which provides\n"
            "# glMatrixMode/glLoadIdentity/glOrtho/glBegin/glTexCoord2f/\n"
            "# glVertex2f/glEnd via a GLSL textured quad) on OHOS only.\n"
            "if(CMAKE_SYSTEM_NAME STREQUAL \"OHOS\")\n"
            "  list(APPEND SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/drivers/Qt/gles_immediate.cpp)\n"
            "endif()\n"
        )
        txt = txt.replace(anchor, anchor + shim)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
        self.output.info("GLES shim patch: appended gles_immediate.cpp for OHOS")

    def _cmake_ar_ranlib(self, toolchain):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        # llvm-ar lives next to the SDK toolchain's llvm
        # (<sdk>/ohos/native/llvm/bin). Only trust that derivation for a
        # real SDK toolchain file; the task-local fallback lives in
        # build_folder, so resolve via compiler sibling / PATH instead.
        cmake_ar = ""
        if os.path.basename(toolchain) == "ohos.toolchain.cmake":
            sdk_ar = os.path.join(
                os.path.dirname(os.path.dirname(
                    os.path.dirname(toolchain))),
                "llvm", "bin", "llvm-ar",
            )
            if os.path.isfile(sdk_ar):
                cmake_ar = sdk_ar
        if not cmake_ar:
            cmake_ar = self._resolve_tool(compilers.get("ar"), "llvm-ar")
        # The SDK llvm/bin ships no llvm-ranlib: prefer a real binary from
        # PATH/conf, otherwise shim it over llvm-ar (zstd precedent).
        cand = self._resolve_tool(compilers.get("ranlib"), "llvm-ranlib")
        if os.path.isfile(cand) or shutil.which(cand):
            return cmake_ar, cand
        shim = os.path.join(self.build_folder, "llvm-ranlib-shim")
        with open(shim, "w", encoding="utf-8", newline="\n") as f:
            f.write('#!/bin/sh\nexec "%s" s "$@"\n' % cmake_ar)
        try:
            os.chmod(shim, 0o755)
        except OSError:
            pass
        return cmake_ar, shim

    def _zlib_cmake_defs(self):
        # Upstream src/CMakeLists.txt:164 does find_package(ZLIB) (Module
        # mode). The fallback toolchain sets FIND_ROOT_MODE_*=ONLY so the
        # module only searches CMAKE_SYSROOT, while the Conan zlib node is
        # override-only (no direct edge, no zlib.pc emitted) — rounds 1-2
        # forwarding the Conan package both missed. This round points the
        # module at the vendored libz prefix built above (same 1.3.1
        # sources, same version), bypassing the Conan graph entirely.
        prefix = self._vendored_zlib_prefix()
        inc = os.path.join(prefix, "include")
        lib = os.path.join(prefix, "lib", "libz.a")
        self.output.info("ZLIB hints (vendored): root=%s lib=%s" % (prefix, lib))
        return [
            '-DZLIB_ROOT="%s"' % prefix,
            '-DZLIB_INCLUDE_DIR="%s"' % inc,
            '-DZLIB_LIBRARY="%s"' % lib,
        ]

    def build(self):
        apply_conandata_patches(self)
        qt5 = self.dependencies["qt5-qtbase"].package_folder
        # Bare cmake + SDK ohos.toolchain (NOT conan_toolchain): conan's
        # CMakeToolchain degenerates to "System is unknown HarmonyOS" with a
        # broken compiler check on this worker (ML-0035; expat/zstd precedent).
        toolchain = self._ohos_toolchain()
        cmake_ar, cmake_ranlib = self._cmake_ar_ranlib(toolchain)
        with self._build_environment().vars(self).apply():
            # Vendored libs must compile inside the build env: SDK clang
            # needs LD_LIBRARY_PATH (libxml2.so.16) + task TMPDIR.
            # Order matters: minizip compiles against vendored zlib headers.
            self._build_vendored_zlib()
            self._build_vendored_minizip()
            # OHOS has no desktop GL/GLX: map REQUIRED OpenGL to GLESv2/EGL.
            self._patch_upstream_opengl_for_ohos()
            self._patch_upstream_gles_immediate_shim()
            self._patch_upstream_githdr_tmpdir()
            self._patch_upstream_qt_targets_for_ohos()
            self._patch_upstream_sdl_pkgconfig_includes()
            self._patch_upstream_timestamp_for_ohos()
            bdir = os.path.join(self.build_folder, "build-ohos")
            defs = [
                '-DCMAKE_TOOLCHAIN_FILE="%s"' % toolchain,
                "-DOHOS_ARCH=arm64-v8a",
                "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
                '-DCMAKE_AR="%s"' % cmake_ar,
                '-DCMAKE_RANLIB="%s"' % cmake_ranlib,
                "-DQT_DEFAULT_MAJOR_VERSION=5",
                "-DQT_VERSION_MAJOR=5",
                "-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH",
                "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
                '-DQt5_DIR="%s"' % self.generators_folder,
                '-DCMAKE_PREFIX_PATH="%s"' % self.generators_folder,
                '-DCMAKE_FIND_ROOT_PATH="%s"' % self.generators_folder,
                '-DCMAKE_AUTOMOC_EXECUTABLE="%s"'
                % os.path.join(qt5, "bin", "moc"),
                '-DCMAKE_AUTORCC_EXECUTABLE="%s"'
                % os.path.join(qt5, "bin", "rcc"),
                '-DCMAKE_AUTOUIC_EXECUTABLE="%s"'
                % os.path.join(qt5, "bin", "uic"),
            ]
            # Extra -I set (flameshot-style manual injection, stateless):
            # Qt module headers (legacy ${Qt5Widgets_INCLUDE_DIRS} is empty
            # under CMakeDeps) + SDL2 headers (<pkg>/include/SDL2 layout,
            # augustus-game _header_dir precedent for the same sdl2/2.30.10).
            # The same set goes to CMAKE_AUTOMOC_MOC_OPTIONS: AUTOMOC never
            # inherits CMAKE_CXX_FLAGS -I (and add_definitions() -I never
            # reaches moc either), so moc parses Qt/SDL includes with the
            # same roots the compiler uses; missing moc includes yield broken
            # qt_metacast bodies (this round's ConsoleViewerSDL symptom).
            extra_incs = []
            qt_inc_base = os.path.join(qt5, "include")
            if os.path.isdir(qt_inc_base):
                extra_incs.append(qt_inc_base)
                for _n in ("QtWidgets", "QtGui", "QtCore"):
                    _c = os.path.join(qt_inc_base, _n)
                    if os.path.isdir(_c):
                        extra_incs.append(_c)
            sdl_inc = self._conan_header_dir("sdl2", "SDL.h", "SDL2")
            if sdl_inc and sdl_inc not in extra_incs:
                extra_incs.append(sdl_inc)
            # Vendored minizip/zlib headers (flat `#include <unzip.h>` needs
            # the vendored include roots on the compiler AND moc paths;
            # upstream only forwards ${MINIZIP_CFLAGS} via add_definitions,
            # which never reaches moc — same root cause as the SDL case).
            for _vd in (os.path.join(self._vendored_minizip_prefix(), "include"),
                        os.path.join(self._vendored_minizip_prefix(),
                                     "include", "minizip"),
                        os.path.join(self._vendored_zlib_prefix(), "include")):
                if os.path.isdir(_vd) and _vd not in extra_incs:
                    extra_incs.append(_vd)
            if extra_incs:
                cxx_flags = " ".join("-I%s" % p for p in extra_incs)
                defs.append('-DCMAKE_CXX_FLAGS="%s"' % cxx_flags)
                moc_opts = ";".join("-I%s" % p for p in extra_incs)
                defs.append('-DCMAKE_AUTOMOC_MOC_OPTIONS="%s"' % moc_opts)
            qt_libdir = os.path.join(qt5, "lib")
            defs.append('-DCMAKE_EXE_LINKER_FLAGS="-L%s -lQt5Widgets -lQt5Gui -lQt5Core"'
                        % qt_libdir)
            self.output.info("Qt/SDL/minizip fallback: extra_incs=%s libdir=%s"
                             % (extra_incs, qt_libdir))
            defs.extend(self._zlib_cmake_defs())
            self.run('cmake -B "%s" -S "%s" %s'
                     % (bdir, self.source_folder, " ".join(defs)))
            self.run('cmake --build "%s" --parallel 1' % bdir)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        bdir = os.path.join(self.build_folder, "build-ohos")
        with self._build_environment().vars(self).apply():
            self.run('cmake --install "%s" --prefix "%s"'
                     % (bdir, self.package_folder))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
