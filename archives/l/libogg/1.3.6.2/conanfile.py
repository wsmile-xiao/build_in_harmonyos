#!/usr/bin/env python3
"""Conan recipe for libogg 1.3.6.2 (upstream 1.3.6 + adaptation fix 2).

Build route (non-Windows): direct compiler invocation, no CMake
configure step.

Rationale: two CMake-based rounds both fail compiler identification on
the HMBS true machine with "/data/service/hnp/bin/clang" ("The
CMAKE_C_COMPILER ... is not able to compile a simple test program" at
CMakeLists.txt project()): first the plain CMakeToolchain route, then
the Ninja-generator + writable-TMPDIR hardening (E346/E002 style, same
error at cmake.configure()). Rather than a third CMake flag
combination, this recipe bypasses CMake try_compile probes entirely on
OHOS/Linux/macOS (validated precedent: critnib/1.1, same signature):
the library is two translation units (src/bitwise.c, src/framing.c),
compiled straight with the validated profile compiler, archived and,
for shared, linked with the upstream SONAME scheme (SOVERSION parsed
from configure.ac, never hard-coded). The two upstream self-test
programs are compiled from the same unmodified sources with the same
-D_V_SELFTEST define and include layout as upstream add_test() targets
(E249: executed directly, both results required), plus a stub negative
control proving the runner can detect failure. A compiler smoke test
runs first so a genuinely broken toolchain surfaces its real stderr
instead of CMake's summary. Windows keeps the legacy CMake route
unchanged (MSVC-style compilers need CMake flag handling).
"""

import glob as _glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LiboggConan(ConanFile):
    name = "libogg"
    version = "1.3.6.2"
    description = "Ogg multimedia container library"
    license = "BSD-3-Clause"
    homepage = "https://xiph.org/ogg/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        if str(self.settings.os) == "Windows":
            cmake_layout(self)
        else:
            basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ------------------------------------------------------------------
    # Shared helpers (both routes)
    # ------------------------------------------------------------------
    def _ensure_writable_tmp(self):
        # E002: guarantee cmake/clang child processes see a writable temp
        # root even if the outer env was reset (conan buildenv isolation).
        # HMBS injects a task-private TMPDIR/TMP/TEMP; /tmp is read-only
        # (erofs) on HarmonyOS, so compiler temp files fail there. Only
        # the temp root is redirected; no test is skipped.
        cand = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP"))
        ok = bool(cand) and os.path.isdir(cand) and os.access(cand, os.W_OK)
        if not ok:
            cand = os.path.join(self.build_folder, "hmbs-tmp")
            try:
                os.makedirs(cand, exist_ok=True)
            except Exception:
                pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = cand
        self.output.info("Using writable TMPDIR=%s" % cand)
        return cand

    def _validated_cc(self):
        # m1ddc rule (adapted): conf absolute compiler path stays
        # preferred; only when it is missing/non-executable do we warn and
        # fall back, so build and test phases share one working compiler.
        # Absolute candidates need no PATH; bare names resolve at exec time.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = (compilers.get("c") or "").strip()
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        if cand:
            self.output.warning(
                "conf c compiler '%s' not usable, falling back to PATH lookup" % cand)
        for fallback in (shutil.which("clang"),
                         "/data/service/hnp/bin/clang",
                         shutil.which("cc"),
                         os.environ.get("CC")):
            if fallback and (os.path.isfile(fallback) or "/" not in fallback):
                self.output.info("Using C compiler: %s" % fallback)
                return fallback
        self.output.info("Using C compiler from PATH: clang")
        return "clang"

    def _validated_ar(self):
        for ar in (shutil.which("llvm-ar"),
                   "/data/service/hnp/bin/llvm-ar",
                   shutil.which("ar")):
            if ar and os.path.isfile(ar):
                self.output.info("Using archiver: %s" % ar)
                return ar
        self.output.info("Using archiver from PATH: ar")
        return "ar"

    def _exec(self, cmd, cwd):
        env = os.environ.copy()
        self.output.info("+ %s" % cmd)
        proc = subprocess.run(
            cmd, shell=True, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=1200, env=env,
        )
        return proc.returncode, (proc.stdout or "")

    def _run_cmd(self, cmd, cwd):
        rc, out = self._exec(cmd, cwd)
        if rc != 0:
            self.output.info(out[-8000:])
            raise ConanException(
                "command failed (rc=%s): %s\n%s" % (rc, cmd, out[-4000:]))
        return out

    def _smoke_test_cc(self, cc):
        # Compile+link+run a trivial TU first so a genuinely broken
        # toolchain shows its real stderr here (CMake only prints a
        # one-line identification failure and hides the cause).
        work = os.path.join(self.build_folder, "cc-smoke")
        os.makedirs(work, exist_ok=True)
        src = os.path.join(work, "smoke.c")
        with open(src, "w", encoding="utf-8") as f:
            f.write("int main(void){return 0;}\n")
        out = os.path.join(work, "smoke")
        self._run_cmd('"%s" "%s" -o "%s"' % (cc, src, out), cwd=work)
        self._run_cmd('"%s"' % out, cwd=work)
        self.output.info("C compiler smoke test passed: %s" % cc)

    def _sign_ohos_elf(self, path):
        tools = {}
        for name in ("llvm-readelf", "llvm-objcopy", "binary-sign-tool"):
            tools[name] = shutil.which(name) or os.path.join(
                "/data/service/hnp/bin", name)
            if not os.path.isfile(tools[name]):
                raise ConanException(f"Required OHOS tool is missing: {name}")
        temporary = path + ".libogg-signed"
        subprocess.run(
            [tools["binary-sign-tool"], "sign", "-inFile", path,
             "-outFile", temporary, "-selfSign", "1"], check=True, timeout=60
        )
        sections = subprocess.run(
            [tools["llvm-readelf"], "-SW", temporary], check=True,
            capture_output=True, text=True, timeout=30
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        # HMBS_CAP_CHMOD=0: HMDFS ignores chmod; failure must not fail build.
        try:
            os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        except OSError:
            pass
        os.replace(temporary, path)

    def _resolve_tool(self, name):
        # Absolute path only when it exists, else PATH lookup (m1ddc rule).
        candidate = shutil.which(name)
        if candidate and os.path.isfile(candidate):
            return candidate
        fixed = os.path.join("/data/service/hnp/bin", name)
        if os.path.isfile(fixed):
            return fixed
        return candidate or fixed

    def _hmbs_emit_upstream(self, data):
        # Dual-channel emit (stdout + conan log) so HMBS preflight captures
        # the marker regardless of log routing, plus persist to build folder
        # for package() to ship into res/ (cache-hit re-emit by test_package).
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as _f:
                json.dump(data, _f)
        except OSError as exc:
            self.output.warning("persist hmbs_upstream.json failed: %s" % exc)

    # ------------------------------------------------------------------
    # Direct-cc route (non-Windows)
    # ------------------------------------------------------------------
    def _upstream_versions(self):
        # Parsed from configure.ac at build time (LIB_CURRENT=8,
        # LIB_REVISION=6, LIB_AGE=8 for 1.3.6 -> SOVERSION 0, LIB 0.8.6);
        # never hard-coded so a version bump cannot silently desync.
        text = open(os.path.join(self.source_folder, "configure.ac"),
                    encoding="utf-8", errors="replace").read()

        def num(key):
            m = re.search(r"^%s=([0-9]+)" % key, text, re.M)
            if not m:
                raise ConanException("cannot parse %s from configure.ac" % key)
            return int(m.group(1))

        cur, rev, age = num("LIB_CURRENT"), num("LIB_REVISION"), num("LIB_AGE")
        m = re.search(r"AC_INIT\(\[libogg\],\[([0-9][0-9.]*)\]\)", text)
        project = m.group(1) if m else "1.3.6"
        sover = cur - age
        return {"project": project, "sover": str(sover),
                "libver": "%d.%d.%d" % (sover, age, rev)}

    def _gen_config_types_h(self, cc, gen_ogg_dir):
        # Upstream generates include/ogg/config_types.h via
        # CheckSizes+check_include_files probes. Reproduce the outcome with
        # a compile-only probe (no link, no try_compile framework): on all
        # supported targets the stdint types have the expected widths.
        os.makedirs(gen_ogg_dir, exist_ok=True)
        probe = (
            "#include <inttypes.h>\n"
            "#include <stdint.h>\n"
            "#include <sys/types.h>\n"
            "typedef int16_t _p16; typedef uint16_t _pu16;\n"
            "typedef int32_t _p32; typedef uint32_t _pu32;\n"
            "typedef int64_t _p64; typedef uint64_t _pu64;\n"
            "_Static_assert(sizeof(int16_t)==2,\"16\");\n"
            "_Static_assert(sizeof(uint16_t)==2,\"u16\");\n"
            "_Static_assert(sizeof(int32_t)==4,\"32\");\n"
            "_Static_assert(sizeof(uint32_t)==4,\"u32\");\n"
            "_Static_assert(sizeof(int64_t)==8,\"64\");\n"
            "_Static_assert(sizeof(uint64_t)==8,\"u64\");\n"
            "int ogg_type_probe;\n"
        )
        work = os.path.join(self.build_folder, "direct", "probe")
        os.makedirs(work, exist_ok=True)
        src = os.path.join(work, "probe.c")
        with open(src, "w", encoding="utf-8") as f:
            f.write(probe)
        rc, out = self._exec('"%s" -c "%s" -o "%s"' % (
            cc, src, os.path.join(work, "probe.o")), cwd=work)
        include_sys_types = 1
        if rc != 0:
            # Rare toolchain without <sys/types.h>: retry stdint-only.
            self.output.info("full type probe failed, retrying stdint-only")
            self.output.info(out[-4000:])
            src2 = os.path.join(work, "probe2.c")
            with open(src2, "w", encoding="utf-8") as f:
                f.write(probe.replace("#include <sys/types.h>\n", ""))
            rc, out = self._exec('"%s" -c "%s" -o "%s"' % (
                cc, src2, os.path.join(work, "probe2.o")), cwd=work)
            if rc != 0:
                self.output.info(out[-8000:])
                raise ConanException(
                    "C type probe failed; toolchain lacks stdint types:\n%s"
                    % out[-4000:])
            include_sys_types = 0
        text = (
            "#ifndef __CONFIG_TYPES_H__\n"
            "#define __CONFIG_TYPES_H__\n"
            "/* Generated by conan direct-cc recipe (upstream CheckSizes/\n"
            "   check_include_files outcome reproduced via compile probe) */\n"
            "#define INCLUDE_INTTYPES_H 1\n"
            "#define INCLUDE_STDINT_H 1\n"
            "#define INCLUDE_SYS_TYPES_H %d\n"
            "\n"
            "#if INCLUDE_INTTYPES_H\n"
            "#  include <inttypes.h>\n"
            "#endif\n"
            "#if INCLUDE_STDINT_H\n"
            "#  include <stdint.h>\n"
            "#endif\n"
            "#if INCLUDE_SYS_TYPES_H\n"
            "#  include <sys/types.h>\n"
            "#endif\n"
            "\n"
            "typedef int16_t ogg_int16_t;\n"
            "typedef uint16_t ogg_uint16_t;\n"
            "typedef int32_t ogg_int32_t;\n"
            "typedef uint32_t ogg_uint32_t;\n"
            "typedef int64_t ogg_int64_t;\n"
            "typedef uint64_t ogg_uint64_t;\n"
            "\n"
            "#endif\n" % include_sys_types
        )
        with open(os.path.join(gen_ogg_dir, "config_types.h"),
                  "w", encoding="utf-8") as f:
            f.write(text)
        self.output.info("Generated config_types.h (INCLUDE_SYS_TYPES_H=%d)"
                         % include_sys_types)

    def _compile_flags(self):
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-O0 -g"
        pic = ""
        if self.options.shared or self.options.get_safe("fPIC", True):
            pic = " -fPIC"
        return "%s -Wall%s" % (opt, pic)

    def _build_direct(self):
        cc = self._validated_cc()
        ar = self._validated_ar()
        self._smoke_test_cc(cc)
        vers = self._upstream_versions()
        self.output.info("Upstream library version: project=%s lib=%s so=%s"
                         % (vers["project"], vers["libver"], vers["sover"]))

        work = os.path.join(self.build_folder, "direct")
        objdir = os.path.join(work, "objs")
        tdir = os.path.join(work, "tests")
        gen_ogg_dir = os.path.join(work, "gen-include", "ogg")
        for d in (objdir, tdir, gen_ogg_dir):
            os.makedirs(d, exist_ok=True)
        self._gen_config_types_h(cc, gen_ogg_dir)

        src_dir = os.path.join(self.source_folder, "src")
        inc_dir = os.path.join(self.source_folder, "include")
        geninc = os.path.join(work, "gen-include")
        cflags = self._compile_flags()
        incs = '"-I%s" "-I%s" "-I%s"' % (src_dir, inc_dir, geninc)

        objs = []
        for tu in ("bitwise.c", "framing.c"):
            obj = os.path.join(objdir, tu.replace(".c", ".o"))
            self._run_cmd('"%s" %s -c "%s" %s -o "%s"' % (
                cc, cflags, os.path.join(src_dir, tu), incs, obj), cwd=objdir)
            objs.append('"%s"' % obj)

        static_lib = os.path.join(work, "libogg.a")
        self._run_cmd('"%s" rcs "%s" %s' % (ar, static_lib, " ".join(objs)),
                      cwd=objdir)

        shared_libs = []
        if self.options.shared:
            if str(self.settings.os) in ("Macos", "iOS", "watchOS", "tvOS"):
                soname = "libogg.%s.dylib" % vers["sover"]
                real = "libogg.%s.dylib" % vers["libver"]
                self._run_cmd(
                    '"%s" -dynamiclib -install_name "@rpath/%s" -o "%s" %s' % (
                        cc, soname, os.path.join(work, real), " ".join(objs)),
                    cwd=work)
            else:
                soname = "libogg.so.%s" % vers["sover"]
                real = "libogg.so.%s" % vers["libver"]
                self._run_cmd(
                    '"%s" -shared -Wl,-soname,%s -o "%s" %s' % (
                        cc, soname, os.path.join(work, real), " ".join(objs)),
                    cwd=work)
            real_path = os.path.join(work, real)
            if str(self.settings.os) == "OHOS":
                self._sign_ohos_elf(real_path)
            # SONAME symlink chain (symlink capability present on HMBS);
            # fall back to copies where symlink() is refused.
            if real.endswith(".dylib"):
                links = (soname, "libogg.dylib")
            else:
                links = (soname, "libogg.so")
            for link in links:
                if link == os.path.basename(real):
                    continue
                link_path = os.path.join(work, link)
                if os.path.lexists(link_path):
                    try:
                        os.remove(link_path)
                    except OSError:
                        pass
                try:
                    os.symlink(os.path.basename(real), link_path)
                except OSError:
                    shutil.copy2(real_path, link_path)
            shared_libs = sorted(_glob.glob(os.path.join(work, "libogg.so*"))
                                 + _glob.glob(os.path.join(work, "libogg.*.dylib")))
        self._run_upstream_direct(cc, src_dir, inc_dir, geninc, tdir)
        return {"static": static_lib, "shared": shared_libs, "vers": vers,
                "gen_ogg_dir": gen_ogg_dir}

    def _run_upstream_direct(self, cc, src_dir, inc_dir, geninc, tdir):
        """Compile the real upstream self-tests and run both cases.

        Same sources, define and include layout as upstream
        CMakeLists.txt under if(BUILD_TESTING): test_bitwise from
        src/bitwise.c + _V_SELFTEST, test_framing from src/framing.c +
        _V_SELFTEST (each TU self-contained, no lib link — exactly like
        upstream add_executable targets). Results come from real runs.
        """
        if not can_run(self):
            self._hmbs_emit_upstream({
                "status": "skipped",
                "framework": "official-selftest-programs",
                "command": "test_bitwise && test_framing",
                "discovered": 2, "executed": 0, "passed": 0,
                "failed": 0, "skipped": 2,
                "reason": "cross-building: test binaries cannot run on build host",
            })
            return
        cflags = self._compile_flags()
        incs = '"-I%s" "-I%s" "-I%s"' % (src_dir, inc_dir, geninc)
        commands, completed = [], 0
        outputs = {}
        try:
            for name, tu in (("test_bitwise", "bitwise.c"),
                             ("test_framing", "framing.c")):
                exe = os.path.join(tdir, name)
                self._run_cmd('"%s" %s -D_V_SELFTEST "%s" %s -o "%s"' % (
                    cc, cflags, os.path.join(src_dir, tu), incs, exe),
                    cwd=tdir)
                if str(self.settings.os) == "OHOS":
                    self._sign_ohos_elf(exe)
                if os.path.getsize(exe) < 4096:
                    raise ConanException(
                        "suspiciously small test binary: %s" % exe)
                commands.append('"%s"' % exe)
                rc, out = self._exec('"%s"' % exe, cwd=tdir)
                self.output.info("--- %s (rc=%s, %d bytes output) ---\n%s" % (
                    name, rc, len(out), out[-4000:]))
                outputs[name] = out
                if rc != 0:
                    raise ConanException(
                        "upstream self-test failed: %s\n%s" % (name, out[-4000:]))
                completed += 1
            # Falsifiability (negative control): a stub returning 1 must be
            # reported as failure by this same runner; if it ever looks
            # green, the harness cannot detect red and the pass is void.
            stub = os.path.join(tdir, "fail_stub.c")
            with open(stub, "w", encoding="utf-8") as f:
                f.write("int main(void){return 1;}\n")
            stub_exe = os.path.join(tdir, "fail_stub")
            self._run_cmd('"%s" -O0 "%s" -o "%s"' % (cc, stub, stub_exe),
                          cwd=tdir)
            rc, _ = self._exec('"%s"' % stub_exe, cwd=tdir)
            if rc == 0:
                raise ConanException(
                    "negative control failed: exit-1 stub reported as pass")
            self.output.info("negative control ok: exit-1 stub detected (rc=%s)" % rc)
        except Exception:
            self._hmbs_emit_upstream({
                "status": "failed",
                "framework": "official-selftest-programs",
                "command": " && ".join(commands),
                "discovered": 2,
                "executed": completed + 1,
                "passed": completed,
                "failed": 1,
                "skipped": 0,
            })
            raise
        self._hmbs_emit_upstream({
            "status": "passed",
            "framework": "official-selftest-programs",
            "command": " && ".join(commands),
            "discovered": 2,
            "executed": 2,
            "passed": 2,
            "failed": 0,
            "skipped": 0,
        })

    # ------------------------------------------------------------------
    # Route dispatch
    # ------------------------------------------------------------------
    def generate(self):
        self._ensure_writable_tmp()
        if str(self.settings.os) == "Windows":
            tc = CMakeToolchain(self)
            tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
            tc.variables["BUILD_TESTING"] = True
            tc.variables["INSTALL_DOCS"] = False
            tc.variables["INSTALL_PKG_CONFIG_MODULE"] = True
            tc.variables["INSTALL_CMAKE_PACKAGE_MODULE"] = True
            tc.generator = "Ninja"
            ninja = self._resolve_ninja()
            tc.variables["CMAKE_MAKE_PROGRAM"] = ninja
            tc.cache_variables["CMAKE_MAKE_PROGRAM"] = ninja
            tc.generate()

    def _resolve_ninja(self):
        # E346: prefer Ninja to avoid make SHELL=/bin/sh sandbox denial.
        # Absolute path first only when it exists, else PATH lookup.
        candidates = [
            os.environ.get("HMBS_NINJA"),
            self.conf.get("user.hmbs:ninja_path", check_type=str),
            "/data/service/hnp/bin/ninja",
            shutil.which("ninja"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return shutil.which("ninja") or "ninja"

    def build(self):
        self._ensure_writable_tmp()
        if str(self.settings.os) == "Windows":
            self._build_cmake()
        else:
            self._build_direct()

    def _direct_work(self):
        # Artifacts live at deterministic paths under build_folder/direct,
        # so package() never relies on in-memory state carried from build().
        work = os.path.join(self.build_folder, "direct")
        return {
            "work": work,
            "static": os.path.join(work, "libogg.a"),
            "shared": sorted(
                _glob.glob(os.path.join(work, "libogg.so*"))
                + _glob.glob(os.path.join(work, "libogg.*.dylib"))),
            "gen_ogg_dir": os.path.join(work, "gen-include", "ogg"),
        }

    def _build_cmake(self):
        # Legacy Windows route (MSVC-style compilers need CMake flag
        # handling); unchanged behaviour.
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            suffix = ".exe" if self.settings.os == "Windows" else ""
            commands = []
            completed = 0
            try:
                for name in ("test_bitwise", "test_framing"):
                    executable = os.path.join(self.build_folder, name + suffix)
                    if str(self.settings.os) == "OHOS":
                        self._sign_ohos_elf(executable)
                    commands.append('"%s"' % executable)
                    self.run('"%s"' % executable)
                    completed += 1
            except Exception:
                self._hmbs_emit_upstream({
                    "status": "failed",
                    "framework": "official-selftest-programs",
                    "command": " && ".join(commands),
                    "discovered": 2,
                    "executed": completed + 1,
                    "passed": completed,
                    "failed": 1,
                    "skipped": 0,
                })
                raise
            self._hmbs_emit_upstream({
                "status": "passed",
                "framework": "official-selftest-programs",
                "command": " && ".join(commands),
                "discovered": 2,
                "executed": 2,
                "passed": 2,
                "failed": 0,
                "skipped": 0,
            })

    def _ship_hmbs_upstream(self):
        try:
            _src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(_src):
                _dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(_dst_dir, exist_ok=True)
                copy(self, "hmbs_upstream.json", src=self.build_folder,
                     dst=_dst_dir, keep_path=False)
            else:
                self.output.warning(
                    "hmbs_upstream.json not found in build folder; "
                    "package will lack upstream evidence")
        except Exception as exc:
            self.output.warning("shipping hmbs_upstream.json failed: %s" % exc)

    def package(self):
        if str(self.settings.os) == "Windows":
            CMake(self).install()
            self._set_soname_and_resign(['libogg.so'])
            self._ship_hmbs_upstream()
            return
        built = self._direct_work()
        if not os.path.isfile(built["static"]):
            # Safety net for flows running package() without build()
            # (e.g. export-pkg style); normal `conan create` always has
            # the artifacts from build().
            self._ensure_writable_tmp()
            self._build_direct()
            built = self._direct_work()
        vers = self._upstream_versions()
        inc_dst = os.path.join(self.package_folder, "include", "ogg")
        lib_dst = os.path.join(self.package_folder, "lib")
        os.makedirs(inc_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)
        # Headers: upstream ogg.h + os_types.h plus generated config_types.h.
        copy(self, "ogg.h",
             src=os.path.join(self.source_folder, "include", "ogg"),
             dst=inc_dst)
        copy(self, "os_types.h",
             src=os.path.join(self.source_folder, "include", "ogg"),
             dst=inc_dst)
        copy(self, "config_types.h", src=built["gen_ogg_dir"], dst=inc_dst)
        # Libraries: static always; shared chain only for shared option.
        # SONAME was fixed at link time (-soname), so no patchelf rewrite
        # (and no re-sign dance) is needed afterwards.
        copy(self, "libogg.a",
             src=os.path.dirname(built["static"]), dst=lib_dst)
        if self.options.shared:
            for f in built["shared"]:
                if os.path.islink(f):
                    target = os.readlink(f)
                    dest = os.path.join(lib_dst, os.path.basename(f))
                    if os.path.lexists(dest):
                        try:
                            os.remove(dest)
                        except OSError:
                            pass
                    try:
                        os.symlink(target, dest)
                    except OSError:
                        shutil.copy2(os.path.join(os.path.dirname(f), target)
                                    if not os.path.isabs(target) else target,
                                    dest)
                elif os.path.isfile(f):
                    copy(self, os.path.basename(f),
                         src=os.path.dirname(f), dst=lib_dst)
        self._write_pc(vers)
        self._write_cmake_config(vers)
        # Carry upstream evidence into the package so test_package can
        # re-emit HMBS_UPSTREAM_TEST_RESULT on EVERY run, even when conan
        # skips build() on a cached binary ("Already installed!").
        self._ship_hmbs_upstream()
        self.output.info("packaged libogg %s (lib %s, so %s)" % (
            vers["project"], vers["libver"], vers["sover"]))

    def _write_pc(self, vers):
        # Relocatable pkg-config file (same fields as upstream ogg.pc.in;
        # downstream oggz consumes libogg via PkgConfigDeps 'ogg').
        content = (
            "prefix=${pcfiledir}/../..\n"
            "exec_prefix=${prefix}\n"
            "libdir=${prefix}/lib\n"
            "includedir=${prefix}/include\n"
            "\n"
            "Name: ogg\n"
            "Description: ogg is a library for manipulating ogg bitstreams\n"
            "Version: %s\n"
            "Requires:\n"
            "Conflicts:\n"
            "Libs: -L${libdir} -logg\n"
            "Cflags: -I${includedir}\n" % vers["project"]
        )
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        with open(os.path.join(pc_dir, "ogg.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(content)

    def _write_cmake_config(self, vers):
        # Same interface as upstream CMake install: Ogg::ogg target plus
        # OggConfig.cmake / OggConfigVersion.cmake (SameMajorVersion).
        cfg_dir = os.path.join(self.package_folder, "lib", "cmake", "Ogg")
        os.makedirs(cfg_dir, exist_ok=True)
        if self.options.shared:
            if str(self.settings.os) in ("Macos", "iOS", "watchOS", "tvOS"):
                lib_file = "libogg.%s.dylib" % vers["libver"]
                soname = "libogg.%s.dylib" % vers["sover"]
                kind, location = "SHARED", "IMPORTED_LOCATION"
            else:
                lib_file = "libogg.so.%s" % vers["libver"]
                soname = "libogg.so.%s" % vers["sover"]
                kind, location = "SHARED", "IMPORTED_LOCATION"
            target_props = (
                '  INTERFACE_INCLUDE_DIRECTORIES "${_IMPORT_PREFIX}/include"\n'
                '  %s "${_IMPORT_PREFIX}/lib/%s"\n'
                '  IMPORTED_SONAME "%s"\n' % (location, lib_file, soname)
            )
        else:
            kind = "STATIC"
            target_props = (
                '  INTERFACE_INCLUDE_DIRECTORIES "${_IMPORT_PREFIX}/include"\n'
                '  IMPORTED_LOCATION "${_IMPORT_PREFIX}/lib/libogg.a"\n'
            )
        targets = (
            "# Generated by conan direct-cc recipe; same interface as\n"
            "# upstream CMake install(EXPORT OggTargets).\n"
            "get_filename_component(_IMPORT_PREFIX "
            '"${CMAKE_CURRENT_LIST_FILE}" PATH)\n'
            "get_filename_component(_IMPORT_PREFIX "
            '"${_IMPORT_PREFIX}" PATH)\n'
            "get_filename_component(_IMPORT_PREFIX "
            '"${_IMPORT_PREFIX}" PATH)\n'
            "get_filename_component(_IMPORT_PREFIX "
            '"${_IMPORT_PREFIX}" PATH)\n'
            "add_library(Ogg::ogg %s IMPORTED)\n"
            "set_target_properties(Ogg::ogg PROPERTIES\n"
            "%s)\n"
            "set(Ogg_TARGET Ogg::ogg)\n" % (kind, target_props)
        )
        with open(os.path.join(cfg_dir, "OggTargets.cmake"),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write(targets)
        config = (
            "# Generated by conan direct-cc recipe; mirrors upstream\n"
            "# cmake/OggConfig.cmake.in.\n"
            'get_filename_component(_OGG_PREFIX '
            '"${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)\n'
            'set(Ogg_INCLUDE_DIR "${_OGG_PREFIX}/include")\n'
            'set(OGG_INCLUDE_DIR "${_OGG_PREFIX}/include")\n'
            'set(Ogg_INCLUDE_DIRS "${_OGG_PREFIX}/include")\n'
            'set(OGG_INCLUDE_DIRS "${_OGG_PREFIX}/include")\n'
            "include(${CMAKE_CURRENT_LIST_DIR}/OggTargets.cmake)\n"
            "set(Ogg_LIBRARY Ogg::ogg)\n"
            "set(OGG_LIBRARY Ogg::ogg)\n"
            "set(Ogg_LIBRARIES Ogg::ogg)\n"
            "set(OGG_LIBRARIES Ogg::ogg)\n"
            "check_required_components(Ogg)\n"
            "set(OGG_FOUND 1)\n"
        )
        with open(os.path.join(cfg_dir, "OggConfig.cmake"),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write(config)
        version = (
            "# SameMajorVersion package version file for Ogg %s.\n"
            'set(PACKAGE_VERSION "%s")\n'
            "if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)\n"
            "  set(PACKAGE_VERSION_COMPATIBLE FALSE)\n"
            "else()\n"
            '  if("%s" MATCHES "^([0-9]+)\\\\.")\n'
            '    set(CVF_VERSION_MAJOR "${CMAKE_MATCH_1}")\n'
            "  else()\n"
            '    set(CVF_VERSION_MAJOR "%s")\n'
            "  endif()\n"
            "  if(PACKAGE_FIND_VERSION_RANGE)\n"
            "    if(NOT PACKAGE_FIND_VERSION_RANGE_MIN VERSION_LESS "
            "CVF_VERSION_MAJOR)\n"
            "      set(PACKAGE_VERSION_COMPATIBLE TRUE)\n"
            "    else()\n"
            "      set(PACKAGE_VERSION_COMPATIBLE FALSE)\n"
            "    endif()\n"
            "  else()\n"
            "    if(PACKAGE_FIND_VERSION)\n"
            "      if(PACKAGE_FIND_VERSION VERSION_EQUAL PACKAGE_VERSION)\n"
            "        set(PACKAGE_VERSION_EXACT TRUE)\n"
            "      endif()\n"
            "      if(PACKAGE_FIND_VERSION VERSION_LESS CVF_VERSION_MAJOR)\n"
            "        set(PACKAGE_VERSION_COMPATIBLE FALSE)\n"
            "      else()\n"
            "        set(PACKAGE_VERSION_COMPATIBLE TRUE)\n"
            "      endif()\n"
            "    else()\n"
            "      set(PACKAGE_VERSION_COMPATIBLE TRUE)\n"
            "    endif()\n"
            "  endif()\n"
            "endif()\n" % (vers["project"], vers["project"],
                           vers["project"], vers["project"])
        )
        with open(os.path.join(cfg_dir, "OggConfigVersion.cmake"),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write(version)

    def _set_soname_and_resign(self, sonames):
        """给缺 SONAME 的 .so 补上 SONAME 并**重新签名**。

        为何需要：本包产物无 DT_SONAME。后果不在本包，而在**下游** ——
        CMake 默认按完整路径链接无 SONAME 的库，于是把构建机的 conan cache
        绝对路径写进下游的 DT_NEEDED，换机器即无法加载。
        制品仓已实测到三个因此损坏的包（fontconfig / poppler / tbb）。

        为何用 patchelf 而不改构建系统：本包的 .so 本来就是**无版本名**
        （libfoo.so，没有 libfoo.so.X 实体），SONAME 设成文件名本身即完全正确，
        与上游本意一致；换构建方式的收益一样而风险更高。
        （若包里存在版本化实体文件，则说明上游有 SOVERSION 意图，
          那种情况应改构建方式而非 patchelf —— 见 skill 的 references/soname-repair.md）

        为何必须重签：改动 ELF 会破坏链接器自签，鸿蒙 PC 的 XPM 会拒绝 dlopen
        （报 Permission denied / Operation not permitted）。
        顺序必须是 patchelf → 剥旧签名段 → 自签。
        （注：direct-cc 路线在链接期即设 SONAME，无需本流程；仅 Windows
        遗留 CMake 路线保留调用。）
        """
        patchelf = self._resolve_tool("patchelf")
        objcopy = self._resolve_tool("llvm-objcopy")
        signer = self._resolve_tool("binary-sign-tool")
        for name in sonames:
            f = os.path.join(self.package_folder, "lib", name)
            if not os.path.isfile(f) or os.path.islink(f):
                self.output.warning("补 SONAME：找不到 %s，跳过" % f)
                continue
            self.run('{pe} --set-soname "{n}" "{f}"'.format(pe=patchelf, n=name, f=f))
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=f))
            self.output.info("已设 SONAME=%s 并重签" % name)

    def package_info(self):
        self.cpp_info.libs = ["ogg"]
        self.cpp_info.set_property("cmake_file_name", "Ogg")
        self.cpp_info.set_property("cmake_target_name", "Ogg::ogg")
        self.cpp_info.set_property("pkg_config_name", "ogg")
