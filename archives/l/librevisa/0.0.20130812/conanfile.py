#!/usr/bin/env python3
"""Conan recipe for librevisa 0.0.20130812 (direct compile, no autotools).

librevisa is Simon Richter's free software implementation of the VISA
(Virtual Instrument Software Architecture) instrument control standard
(upstream: https://git.sr.ht/~sjr/librevisa, GPL-3.0-or-later).

The 0.0.20130812 snapshot corresponds to upstream commit 3e3e027
("Bump version number", 2013-08-12). The sourcehut archive ships only
git-tracked files: configure.ac + Makefile.am, NO generated `configure`.
Previous rounds tried to bootstrap with `autoreconf -fi` on the worker,
but the preflight pool has no autoconf suite at all: a bare `autoreconf`
fails with "inaccessible or not found" (Error 127), an absolute-path
probe of /data/service/hnp/bin, /storage/.../usr/local/bin,
/usr/local/bin and /usr/bin found nothing, and `which` found nothing
either. Adding Conan autoconf/2.72 is not an option either: it pulls
m4/1.4.19 from source, whose configure re-exec dies on the
profile-pinned missing /data/service/hnp/bin/bash (Error 127) outside
this recipe's environment.

So this recipe does not run autotools at all. It compiles the exact
source selection that configure would produce on OHOS (verified against
the 3e3e027 tarball):
  - WITH_USB=no, WITH_VXI=no, WITH_AVAHI=no (libusb-1.0, vxiclient/vxi.h
    and avahi-client are all absent on OHOS), i.e. the 33 portable-core
    .cpp files from src/Makefile.am, no USB/VXI/AVAHI sources;
  - no HAVE_CONFIG_H (all sources guard config.h with #ifdef, and the
    only AC_DEFINE is WITH_AVAHI which is off);
  - platform headers resolve to the pthread branch (#ifdef WIN32 is
    false on OHOS);
  - profile CFLAGS/CXXFLAGS/LDFLAGS are honoured by expanding them in
    the compile/link commands under the conanbuild environment
    (carries --target/--sysroot), so cross flags are not lost.
Only the C++ compiler, archiver and /bin/sh are required, all of which
HMBS guarantees, instead of the missing autoconf suite.

Upstream tests: the same 22 programs listed in tests/Makefile.am
check_PROGRAMS (= TESTS), each linked with tests/dummy.cpp (in-memory
DUMMY resource, no hardware) plus the built lib. Each test binary uses
exit-code semantics (0 = pass), so results come from one deterministic
source (process return codes), no log string counting.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


# Portable-core sources from src/Makefile.am with WITH_USB=no,
# WITH_VXI=no, WITH_AVAHI=no (the OHOS selection: no libusb, no
# vxiclient/vxi.h, no avahi-client). Order follows Makefile.am.
_LIB_SOURCES = [
    "base_vprintf.cpp",
    "event_queue.cpp",
    "findlist.cpp",
    "messagepump.cpp",
    "object.cpp",
    "object_cache.cpp",
    "resource.cpp",
    "resource_manager.cpp",
    "session.cpp",
    "thread_pthread.cpp",
    "viBufWrite.cpp",
    "viClose.cpp",
    "viDisableEvent.cpp",
    "viEnableEvent.cpp",
    "viFindNext.cpp",
    "viFindRsrc.cpp",
    "viFlush.cpp",
    "viGetAttribute.cpp",
    "viLock.cpp",
    "viOpen.cpp",
    "viOpenDefaultRM.cpp",
    "viParseRsrc.cpp",
    "viPrintf.cpp",
    "viRead.cpp",
    "viReadSTB.cpp",
    "viSetAttribute.cpp",
    "viSetBuf.cpp",
    "viSPrintf.cpp",
    "viUnlock.cpp",
    "viVPrintf.cpp",
    "viVSPrintf.cpp",
    "viWaitOnEvent.cpp",
    "viWrite.cpp",
]

# tests/Makefile.am check_PROGRAMS (= TESTS), in upstream order.
_UPSTREAM_TESTS = [
    "find",
    "lock_attr_exclusive",
    "lock_attr_global",
    "lock_attr_shared",
    "lock_invalid_mode",
    "lock_recursive_exclusive",
    "lock_recursive_shared",
    "open",
    "open_multi",
    "print",
    "read",
    "rule_3_2_3",
    "rule_3_3_2",
    "rule_3_6_38",
    "rule_3_7_3",
    "rule_4_2_1",
    "rule_4_2_2",
    "rule_4_3_11",
    "wait_immediate_noevents",
    "wait_nenabled",
    "wait_timeout",
    "write",
]


def _resolve_shell():
    """Return a usable POSIX shell (existence-first, then PATH).

    True-machine profiles pin CONFIG_SHELL/SHELL to
    /data/service/hnp/bin/bash, which is absent on some runners
    (Error 127). Only env exports are overridden; no flags touched.
    """
    for cand in (
        os.environ.get("CONFIG_SHELL"),
        os.environ.get("SHELL"),
        "/bin/sh",
        "/system/bin/sh",
    ):
        if cand and os.path.isfile(cand):
            return cand
    for name in ("bash", "sh"):
        found = shutil.which(name)
        if found:
            return found
    return "/bin/sh"


def _pinned_executable(conanfile, key):
    """Read tools.build:compiler_executables[key] if present, else None."""
    try:
        exes = conanfile.conf.get("tools.build:compiler_executables")
    except Exception:
        return None
    if isinstance(exes, dict):
        return exes.get(key)
    return None


def _resolve_cxx(conanfile):
    """C++ compiler: pinned path when it exists, else PATH fallback.

    Mirrors the aggregated compiler-fallback pattern: existence wins,
    never trust a pinned absolute path blindly.
    """
    pinned = _pinned_executable(conanfile, "cpp")
    if pinned and os.path.isfile(pinned):
        return pinned
    for name in ("c++", "clang++", "g++"):
        found = shutil.which(name)
        if found:
            return found
    if pinned:
        return pinned
    return "c++"


def _resolve_ar(conanfile, cxx):
    """Archiver: prefer a sibling of the compiler, else PATH fallback."""
    cxx_dir = os.path.dirname(cxx) if cxx else ""
    if cxx_dir:
        for name in ("llvm-ar", "ar"):
            cand = os.path.join(cxx_dir, name)
            if os.path.isfile(cand):
                return cand
    for name in ("ar", "llvm-ar"):
        found = shutil.which(name)
        if found:
            return found
    return "ar"


class LibrevisaConan(ConanFile):
    name = "librevisa"
    version = "0.0.20130812"
    description = "Free software implementation of the VISA instrument control standard"
    license = "GPL-3.0-or-later"
    homepage = "https://git.sr.ht/~sjr/librevisa"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "librevisa is only supported on Linux/OHOS, not "
                + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _fs_env(self):
        """HMDFS workarounds: explicit PWD plus writable TMPDIR, and a
        sanitized SHELL/CONFIG_SHELL (profile-pinned bash may be absent).
        No autotools PATH handling: this recipe needs no autotools."""
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, ".tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("PWD", self.build_folder)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        shell = _resolve_shell()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        return env

    def _compile_flags(self):
        if str(self.settings.build_type) == "Debug":
            opt = "-O0 -g"
        else:
            opt = "-O2"
        pic = ""
        if self.options.get_safe("fPIC", False) or self.options.shared:
            pic = " -fPIC"
        return opt + pic

    def build(self):
        src = self.source_folder
        inc = os.path.join(src, "include")
        srcdir = os.path.join(src, "src")
        testdir = os.path.join(src, "tests")
        objdir = os.path.join(self.build_folder, "manual-obj")
        testbindir = os.path.join(self.build_folder, "manual-tests")
        os.makedirs(objdir, exist_ok=True)
        os.makedirs(testbindir, exist_ok=True)

        cxx = _resolve_cxx(self)
        ar = _resolve_ar(self, cxx)
        flags = self._compile_flags()

        # 1. Compile the 33 portable-core objects. $CXXFLAGS/$LDFLAGS are
        # expanded by the shell from the conanbuild environment so profile
        # cross flags (--target/--sysroot) are honoured.
        objects = []
        with self._fs_env().vars(self).apply():
            for name in _LIB_SOURCES:
                cpf = os.path.join(srcdir, name)
                if not os.path.isfile(cpf):
                    raise ConanException("upstream source missing: " + cpf)
                obj = os.path.join(objdir, name + ".o")
                self.run(
                    '"%s" $CXXFLAGS %s -I"%s" -pthread -c "%s" -o "%s"'
                    % (cxx, flags, inc, cpf, obj),
                    env="conanbuild",
                )
                if not os.path.isfile(obj) or os.path.getsize(obj) == 0:
                    raise ConanException("empty object file: " + obj)
                objects.append(obj)
            # tests/dummy.cpp (needs -I src like libdummy_a_CPPFLAGS).
            dummy_obj = os.path.join(testbindir, "dummy.o")
            self.run(
                '"%s" $CXXFLAGS %s -I"%s" -I"%s" -pthread -c "%s" -o "%s"'
                % (
                    cxx,
                    flags,
                    inc,
                    srcdir,
                    os.path.join(testdir, "dummy.cpp"),
                    dummy_obj,
                ),
                env="conanbuild",
            )
            if not os.path.isfile(dummy_obj) or os.path.getsize(dummy_obj) == 0:
                raise ConanException("empty object file: " + dummy_obj)

            # 2. Library artefact.
            if self.options.shared:
                lib = os.path.join(self.build_folder, "libvisa.so")
                self.run(
                    '"%s" $CXXFLAGS $LDFLAGS -shared -fPIC -o "%s" %s -pthread'
                    % (cxx, lib, " ".join('"%s"' % o for o in objects)),
                    env="conanbuild",
                )
            else:
                lib = os.path.join(self.build_folder, "libvisa.a")
                self.run(
                    '"%s" rcs "%s" %s'
                    % (ar, lib, " ".join('"%s"' % o for o in objects)),
                    env="conanbuild",
                )
            if not os.path.isfile(lib) or os.path.getsize(lib) == 0:
                raise ConanException("empty library artefact: " + lib)

            # 3. Link + run the 22 upstream tests. Every test is attempted
            # even after failures so the counts stay honest; results come
            # from process return codes (0 = pass), a single deterministic
            # source, no stdout string counting.
            passed = []
            failed = []
            for name in _UPSTREAM_TESTS:
                test_src = os.path.join(testdir, name + ".c")
                if not os.path.isfile(test_src):
                    failed.append(name + " (missing source)")
                    continue
                test_bin = os.path.join(testbindir, name)
                try:
                    self.run(
                        '"%s" $CXXFLAGS $LDFLAGS -I"%s" "%s" "%s" "%s"'
                        ' -pthread -o "%s"'
                        % (cxx, inc, test_src, dummy_obj, lib, test_bin),
                        env="conanbuild",
                    )
                except Exception as exc:
                    failed.append(name + " (link failed: %s)" % exc)
                    continue
                if not os.path.isfile(test_bin) or os.path.getsize(test_bin) == 0:
                    failed.append(name + " (empty binary)")
                    continue
                try:
                    self.run('"%s"' % test_bin, env="conanbuild")
                    passed.append(name)
                except Exception:
                    failed.append(name + " (exit != 0)")
        self._emit_upstream_test_result(passed, failed)

    def _emit_upstream_test_result(self, passed, failed):
        """Emit the HMBS upstream-test marker from process return codes."""
        discovered = len(_UPSTREAM_TESTS)
        executed = len(passed) + len(failed)
        result = {
            "status": "passed" if not failed else "failed",
            "framework": "manual",
            "command": "direct CXX compile, link and run of 22 tests programs",
            "discovered": discovered,
            "executed": executed,
            "passed": len(passed),
            "failed": len(failed),
            "skipped": 0,
        }
        # Self-check the counting identities before emitting.
        assert discovered == 22
        assert result["passed"] + result["failed"] == result["executed"]
        assert result["executed"] <= result["discovered"]
        assert all(
            isinstance(result[k], int) and result[k] >= 0
            for k in ("discovered", "executed", "passed", "failed", "skipped")
        )
        if failed:
            self.output.info("failing upstream tests: " + ", ".join(failed))
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
        if result["status"] != "passed":
            raise ConanException(
                "upstream tests did not pass: " + json.dumps(result)
            )

    def package(self):
        src = self.source_folder
        if self.options.shared:
            lib = os.path.join(self.build_folder, "libvisa.so")
        else:
            lib = os.path.join(self.build_folder, "libvisa.a")
        copy(self, os.path.basename(lib), src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "visa.h", src=os.path.join(src, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "visatype.h", src=os.path.join(src, "include"),
             dst=os.path.join(self.package_folder, "include"))
        # librevisa.pc: same fields as librevisa.pc.in with the OHOS
        # selection (no optional deps, so Requires.private is empty).
        pc = (
            "prefix=%s\n"
            "exec_prefix=${prefix}\n"
            "libdir=${prefix}/lib\n"
            "includedir=${prefix}/include\n"
            "\n"
            "Name: librevisa\n"
            "Description: Open-source VISA library for GPIB/USBTMC/LXI\n"
            "URL: http://www.librevisa.org\n"
            "Requires:\n"
            "Requires.private:\n"
            "Version: 0.0.20130812\n"
            "Libs: -L${libdir} -lvisa\n"
            "Libs.private:\n"
            "Cflags: -I${includedir}\n"
        ) % self.package_folder.replace("\\", "/")
        pc_path = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pc_path, exist_ok=True)
        with open(os.path.join(pc_path, "librevisa.pc"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(pc)
        # NOTE: the 3e3e027 sourcehut archive ships no COPYING/LICENSE text
        # file (verified from the tarball listing), so there is no license
        # file to package; the license metadata stays GPL-3.0-or-later.

    def package_info(self):
        self.cpp_info.libs = ["visa"]
        self.cpp_info.set_property("cmake_file_name", "librevisa")
        self.cpp_info.set_property("cmake_target_name", "librevisa::librevisa")
        self.cpp_info.set_property("pkg_config_name", "librevisa")
        # vi* API uses pthreads internally (configure AC_CHECK_LIB pthread).
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
