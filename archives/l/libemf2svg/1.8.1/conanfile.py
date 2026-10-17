#!/usr/bin/env python3
"""Conan recipe — libemf2svg 1.8.1 (direct compile, no CMake).

Microsoft EMF to SVG conversion library. Library-only build (LONLY
equivalent): the demo converter needs glibc argp, which is absent on
OHOS, while the library itself only needs libpng, freetype, fontconfig
and libxml2. libuemf is used vendored (USE_SYSTEM_LIBUEMF=OFF equivalent)
so no extra system dependency is required.

Build route: direct compiler invocation, no CMake configure step.
Rationale: three consecutive preflight rounds all died at the same
fingerprint — CMakeLists.txt project() with "The C/CXX compiler
identification is unknown" for /data/service/hnp/bin/clang — across
three different CMake tunings (E092 Linux system-name mapping, Ninja
generator, verified-writable TMPDIR). critnib/1.1 documents the same
device behaviour: both the CMakeToolchain default and the Linux-override
variant fail compiler-ID with that exact clang even with writable TMPDIR
applied, because stock CMake 4.4.3 ships no HarmonyOS platform module.
Rather than a fourth CMake flag combination, this recipe bypasses the
try_compile probe entirely (ddate/clamav-libunrar precedent): the library
is 17 plain C files in src/lib plus 4 vendored libuemf files, compiled
straight with the validated profile compiler. A compiler smoke test runs
first so a genuinely broken toolchain shows its real stderr instead of
CMake's "identification is unknown" summary.
"""

import glob as _glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


# Vendored libuemf translation units (USE_SYSTEM_LIBUEMF=OFF equivalent).
_UEMF_SOURCES = ("uemf_utf.c", "uemf_endian.c", "uemf.c", "upmf.c")


class Libemf2svgConan(ConanFile):
    name = "libemf2svg"
    version = "1.8.1"
    description = "Microsoft EMF to SVG conversion library"
    license = "GPL-2.0-only"
    homepage = "https://github.com/kakwa/libemf2svg"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def requirements(self):
        self.requires("libpng/1.6.58.2")
        self.requires("freetype/2.14.3")
        self.requires("fontconfig/2.18.1.1")
        self.requires("libxml2/2.15.3.1")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libemf2svg supports Linux and OHOS, not {}".format(
                    self.settings.os
                )
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_writable_tmp()

    def _ensure_writable_tmp(self):
        # HMBS diagnosis [readonly_tmp]: device /tmp is read-only; clang
        # spills temp files via $TMPDIR. HMBS injects a task-private
        # TMPDIR/TMP/TEMP; ensure all three point at a writable dir
        # (prefer injected value, else a build_folder subdir). Only the
        # temp root is replaced; no test is skipped or deleted.
        # (critnib/clamav-libunrar precedent.)
        import tempfile
        cand = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        ok = bool(cand) and os.path.isdir(cand) and os.access(cand, os.W_OK)
        if not ok:
            cand = os.path.join(self.build_folder, "tmp")
            try:
                os.makedirs(cand, exist_ok=True)
            except Exception:
                cand = tempfile.gettempdir()
        for k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[k] = cand
        self.output.info("Using writable TMPDIR=%s" % cand)

    def _validated_cc(self):
        # R33: compiler comes from the Conan conf (authoritative OHOS
        # profile value), never from a bare ${CC} shell variable. PATH
        # fallback only when the conf path is missing/non-executable.
        # (critnib precedent.)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = (compilers.get("c") or "").strip()
        if cand:
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
            self.output.warning(
                "conf c compiler '%s' not usable, falling back to PATH lookup"
                % cand
            )
        path_cc = shutil.which("clang") or shutil.which("cc") or "clang"
        self.output.info("Using C compiler from PATH: %s" % path_cc)
        return path_cc

    def _validated_ar(self):
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        self.output.info("Using archiver: %s" % ar)
        return ar

    def _run_cmd(self, cmd, cwd):
        env = os.environ.copy()
        self.output.info("+ %s" % cmd)
        proc = subprocess.run(
            cmd, shell=True, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=1200, env=env,
        )
        out = proc.stdout or ""
        if proc.returncode != 0:
            self.output.info(out[-8000:])
            raise ConanException(
                "command failed (rc=%s): %s\n%s"
                % (proc.returncode, cmd, out[-4000:])
            )
        return out

    def _smoke_test_cc(self, cc):
        # Compile+link+run a trivial TU first so a genuinely broken
        # toolchain shows its real stderr here (CMake only prints
        # "identification is unknown" and hides the cause).
        work = os.path.join(self.build_folder, "cc-smoke")
        os.makedirs(work, exist_ok=True)
        src = os.path.join(work, "smoke.c")
        with open(src, "w") as f:
            f.write("int main(void){return 0;}\n")
        out = os.path.join(work, "smoke")
        self._run_cmd('"%s" "%s" -o "%s"' % (cc, src, out), cwd=work)
        self._run_cmd('"%s"' % out, cwd=work)
        self.output.info("C compiler smoke test passed: %s" % cc)

    def _dep_flags(self):
        # Collect -I/-L/-l/-D from every dependency (direct + transitive:
        # libpng/freetype/fontconfig/libxml2 plus zlib/expat etc.).
        # Upstream include variables were PNG/FREETYPE/FONTCONFIG/LIBXML2;
        # here all dependency include/lib dirs are passed explicitly, so
        # no CMakeDeps file_name/target bridging is needed.
        incs, libdirs, libs, defines = [], [], [], []
        seen = set()

        def _abs(dep_folder, p):
            return p if os.path.isabs(p) else os.path.join(dep_folder, p)

        for _ref, _dep in self.dependencies.items():
            try:
                info = _dep.cpp_info.aggregated_components()
            except Exception:
                info = _dep.cpp_info
            pf = _dep.package_folder or ""
            for d in getattr(info, "includedirs", []) or []:
                q = _abs(pf, d)
                # Drop entries that do not exist on disk (preflight showed
                # a bare relative -I"include" from a dep without
                # package_folder): a bogus -I only adds noise, and every
                # real package folder exists at build() time.
                if q not in seen and os.path.isdir(q):
                    seen.add(q)
                    incs.append(q)
            for d in getattr(info, "libdirs", []) or []:
                q = _abs(pf, d)
                if q not in seen and os.path.isdir(q):
                    seen.add(q)
                    libdirs.append(q)
            for lib in list(getattr(info, "libs", []) or []) + list(
                getattr(info, "system_libs", []) or []
            ):
                if lib and lib not in libs:
                    libs.append(lib)
            for d in getattr(info, "defines", []) or []:
                if d and d not in defines:
                    defines.append(d)
        return incs, libdirs, libs, defines

    def _collect_sources(self):
        lib_src_dir = os.path.join(self.source_folder, "src", "lib")
        uemf_src_dir = os.path.join(
            self.source_folder, "vendor", "libuemf"
        )
        sources = sorted(_glob.glob(os.path.join(lib_src_dir, "*.c")))
        if not sources:
            raise ConanException(
                "no library sources found in %s (expected src/lib/*.c)"
                % lib_src_dir
            )
        for fname in _UEMF_SOURCES:
            p = os.path.join(uemf_src_dir, fname)
            if not os.path.isfile(p):
                raise ConanException(
                    "vendored libuemf source missing: %s" % p
                )
            sources.append(p)
        pub = os.path.join(self.source_folder, "inc", "emf2svg.h")
        if not os.path.isfile(pub):
            raise ConanException(
                "public header missing: %s" % pub
            )
        return sources, lib_src_dir, uemf_src_dir

    def build(self):
        self._ensure_writable_tmp()
        cc = self._validated_cc()
        ar = self._validated_ar()
        self._smoke_test_cc(cc)
        sources, lib_src_dir, uemf_src_dir = self._collect_sources()
        incs, libdirs, libs, defines = self._dep_flags()

        objdir = os.path.join(self.build_folder, "objs")
        os.makedirs(objdir, exist_ok=True)
        opt = (
            "-O2 -DNDEBUG"
            if str(self.settings.build_type) == "Release"
            else "-O0 -g"
        )
        cflags = (
            "-std=c11 -fPIC -Wall %s -DE2S_VERSION='\"%s\"'"
            % (opt, self.version)
        )
        # aarch64 is little-endian: WORDS_BIGENDIAN stays unset, same as
        # upstream TestBigEndian would conclude. No -pthread: the library
        # uses no threads. Upstream links libm explicitly on UNIX.
        # Upstream include_directories(./inc ...): the public header lives
        # in inc/, not next to the sources (preflight evidence:
        # emf2svg.c:8 fatal error: 'emf2svg.h' file not found).
        # (_collect_sources already raises if inc/emf2svg.h is absent.)
        inc_dir = os.path.join(self.source_folder, "inc")
        for inc in [inc_dir, lib_src_dir, uemf_src_dir] + incs:
            cflags += ' -I"%s"' % inc
        for d in defines:
            cflags += ' -D"%s"' % d

        objects = []
        for src in sources:
            obj = os.path.join(
                objdir,
                os.path.splitext(os.path.basename(src))[0] + ".o",
            )
            self._run_cmd(
                '"%s" %s -c "%s" -o "%s"' % (cc, cflags, src, obj),
                cwd=objdir,
            )
            objects.append('"%s"' % obj)

        linklibs = "".join(' -L"%s"' % d for d in libdirs)
        linklibs += "".join(" -l%s" % lib for lib in libs)
        linklibs += " -lm"

        static_lib = os.path.join(objdir, "libemf2svg.a")
        self._run_cmd(
            '"%s" rcs "%s" %s' % (ar, static_lib, " ".join(objects)),
            cwd=objdir,
        )
        if self.options.shared:
            # Upstream VERSION 1.8.1 / SOVERSION 1: real file plus
            # SONAME -soname link flag (libharu precedent:
            # -Wl,-soname, unversioned-SONAME friendly).
            real = os.path.join(objdir, "libemf2svg.so.1.8.1")
            self._run_cmd(
                '"%s" -shared -o "%s" %s%s -Wl,-soname,libemf2svg.so.1'
                % (cc, real, " ".join(objects), linklibs),
                cwd=objdir,
            )

    def package(self):
        self._ensure_writable_tmp()
        copy(
            self,
            "emf2svg.h",
            src=os.path.join(self.source_folder, "inc"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        objdir = os.path.join(self.build_folder, "objs")
        if self.options.shared:
            real = "libemf2svg.so.1.8.1"
            copy(
                self,
                real,
                src=objdir,
                dst=os.path.join(self.package_folder, "lib"),
                keep_path=False,
            )
            self._make_version_links()
            self._sign_shared_libs()
        else:
            copy(
                self,
                "libemf2svg.a",
                src=objdir,
                dst=os.path.join(self.package_folder, "lib"),
                keep_path=False,
            )
        if os.path.isfile(os.path.join(self.source_folder, "LICENSE")):
            copy(
                self,
                "LICENSE",
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
                keep_path=False,
            )
        else:
            # Unverified for the 1.8.1 tarball (no build ever reached
            # package()): warn instead of failing the whole preflight.
            self.output.warning(
                "LICENSE not found in source tree, skipping licenses copy"
            )

    def _make_version_links(self):
        # SONAME/SOVERSION link set for the versioned shared lib when the
        # filesystem supports symlinks (HMBS_CAP_SYMLINK=1 on device);
        # fall back to copies where it does not.
        libdir = os.path.join(self.package_folder, "lib")
        real = os.path.join(libdir, "libemf2svg.so.1.8.1")
        if not os.path.isfile(real):
            raise ConanException(
                "shared library not built: %s" % real
            )
        for link in ("libemf2svg.so.1", "libemf2svg.so"):
            link_path = os.path.join(libdir, link)
            try:
                if os.path.islink(link_path) or os.path.isfile(link_path):
                    os.unlink(link_path)
            except OSError:
                pass
            try:
                os.symlink("libemf2svg.so.1.8.1", link_path)
            except OSError:
                copy(
                    self,
                    "libemf2svg.so.1.8.1",
                    src=libdir,
                    dst=libdir,
                    keep_path=False,
                )

    def _sign_shared_libs(self):
        # HarmonyOS PC requires code signing for .so loaded via dlopen
        # (zstd/expat/clamav-libunrar precedent). Best-effort only: the
        # preflight worker may lack the signer (Error 127
        # inaccessible or not found even when the path exists but is
        # not executable), so any missing/unusable tool or signing
        # failure degrades to a warning and never fails package().
        import glob as _g

        libdir = os.path.join(self.package_folder, "lib")
        targets = _g.glob(os.path.join(libdir, "*.so*"))
        if not targets:
            return
        objcopy = os.environ.get(
            "LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy"
        )
        signer = os.environ.get(
            "BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool"
        )
        if not shutil.which("binary-sign-tool"):
            if not (
                os.path.isfile(signer) and os.access(signer, os.X_OK)
            ):
                self.output.warning(
                    "binary-sign-tool not usable, skipping code signing"
                )
                return
        else:
            signer = shutil.which("binary-sign-tool")
        if not os.path.isfile(objcopy) and not shutil.which("llvm-objcopy"):
            objcopy = "llvm-objcopy"
        for target in targets:
            if os.path.islink(target):
                continue
            try:
                self.run(
                    '{0} --remove-section .codesign "{1}" 2>/dev/null || true'.format(
                        objcopy, target
                    )
                )
                self.run(
                    '{0} sign -inFile "{1}" -outFile "{1}" -selfSign 1'.format(
                        signer, target
                    )
                )
            except Exception as e:
                self.output.warning(
                    "code signing skipped for %s: %s" % (target, e)
                )
                return

    def package_info(self):
        self.cpp_info.libs = ["emf2svg"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            # Upstream links libm explicitly on UNIX (link_libraries(m)).
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "libemf2svg")
        self.cpp_info.set_property(
            "cmake_target_name", "libemf2svg::libemf2svg"
        )
