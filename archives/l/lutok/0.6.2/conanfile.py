#!/usr/bin/env python3
"""Conan recipe for lutok 0.6.2 — lightweight C++ API for Lua (RAII wrapper
over the Lua C API; base building block of the FreeBSD/ATF test stack).

OHOS adaptation notes:
  * Source is the official release tarball, a `make dist` artifact that ships
    a pre-generated `configure`; no autoreconf/automake bootstrap is needed.
  * config.guess (2018-08-29) cannot identify HarmonyOS, so explicit
    --build/--host triplets are passed to configure.
  * Lua discovery (m4/lua.m4) probes the pkg-config names lua-5.4, lua5.4 and
    lua.  PkgConfigDeps generates lua-5.4.pc for lua/5.4.8 (the recipe declares
    pkg_config_name=lua-5.4), so the first probe succeeds.
  * The upstream code mandates C++20 while the shared OHOS profile pins
    compiler.cppstd=17, so -std=c++20 is appended after the profile flag.
  * atf/0.23 ships pkg-config files and libtool archives built with prefix=/
    (includedir=//include, dependency_libs=//lib/libatf-c.la, compiled-in
    ATF_SHELL=/data/service/hnp/bin/bash), so the recipe writes its own
    atf-c++.pc/atf-sh.pc pointing at the real package folder, links against
    copies of the static archives (bypassing the broken .la files) and sets
    ATF_LIBEXECDIR/ATF_PKGDATADIR/ATF_SHELL when running examples_test.
  * The published lua package ships the C headers only; lutok's public
    c_gate.hpp includes <lua.hpp>.  The recipe generates the standard four-line
    Lua C++ wrapper in a private build prefix for the build and installs it
    next to lutok's headers so consumers can compile <lutok/c_gate.hpp>.
  * Toybox `mktemp -d` under umask 077 on HMDFS creates directories that
    cannot be written into, which aborts the config.status machinery; a mktemp
    shim implemented with mkdir is placed first in PATH for configure.
  * Upstream tests sit behind --enable-atf and are normally driven by kyua,
    which is not available on OHOS.  The recipe enumerates each ATF test
    program's cases with `-l` and runs them one by one (`prog <case>`,
    exit code 0 = pass): 6 atf-c++ programs (97 cases) plus the atf-sh
    examples_test (4 cases).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

_ATF_PROGRAMS = ("c_gate_test", "debug_test", "exceptions_test",
                 "operations_test", "stack_cleaner_test", "state_test")
_ATF_EXPECTED = {"c_gate_test": 2, "debug_test": 2, "exceptions_test": 4,
                 "operations_test": 19, "stack_cleaner_test": 4,
                 "state_test": 66}
_EXAMPLES_PROGRAMS = ("examples_test",)
_EXAMPLES_EXPECTED = {"examples_test": 4}

_LUA_HPP = ('extern "C" {\n'
            '#include "lua.h"\n'
            '#include "lualib.h"\n'
            '#include "lauxlib.h"\n'
            '}\n')

_RUNNER = """#!/bin/sh
# run_atf_suites.sh <logfile> <program> [program...]
# Enumerate each ATF test program's cases with -l (TP format) and run every
# case individually (exit code 0 = pass); print per-suite counts and a
# machine-readable SUMMARY line.  The caller validates the accounting.
log="$1"; shift
: > "$log"
total=0; passed=0; failed=0; fail_list=""
for prog in "$@"; do
    case_list=$("$prog" -l 2>>"$log" | sed -n 's/^ident: //p')
    n=0
    for tc in $case_list; do
        n=$((n + 1))
        if "$prog" "$tc" >>"$log" 2>&1; then
            passed=$((passed + 1))
            echo "PASS $prog $tc" >> "$log"
        else
            failed=$((failed + 1))
            fail_list="$fail_list ${prog}:${tc}"
            echo "FAIL $prog $tc" >> "$log"
        fi
        total=$((total + 1))
    done
    echo "SUITE $(basename "$prog") cases=$n" >> "$log"
done
echo "SUMMARY total=$total passed=$passed failed=$failed fails=$fail_list" >> "$log"
echo "SUMMARY total=$total passed=$passed failed=$failed fails=$fail_list"
exit 0
"""

_MKTEMP_SHIM = """#!/bin/sh
# mkdir-based `mktemp -d`: toybox mktemp under umask 077 creates directories
# on HMDFS that cannot be written into, aborting config.status.
mode=""
for a in "$@"; do
  case "$a" in
    -d) mode="-d" ;;
  esac
done
if [ "$mode" != "-d" ]; then
  exec %s "$@"
fi
dir=""
for a in "$@"; do
  case "$a" in
    -d) ;;
    *)  dir="$a" ;;
  esac
done
[ -n "$dir" ] || dir="./tmp.XXXXXX"
base=$(dirname "$dir")
pat=$(basename "$dir")
out=""
i=0
while [ -z "$out" ] && [ $i -lt 100 ]; do
  cand="$base/$(echo "$pat" | sed "s/XXXXXX/$$-$i/")"
  if mkdir -p "$cand" 2>/dev/null; then out="$cand"; fi
  i=$((i + 1))
done
if [ -n "$out" ]; then
  echo "$out"
  exit 0
fi
exit 1
"""


class LutokConan(ConanFile):
    name = "lutok"
    version = "0.6.2"
    description = "Lightweight C++ API for Lua (RAII wrapper over the Lua C API)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/jmmv/lutok"
    url = "https://github.com/jmmv/lutok"
    topics = ("lua", "cpp", "raii", "bindings")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The public headers expose the Lua C API (c_gate.hpp includes
        # <lua.hpp>), and static builds link liblua into consumers, so lua must
        # not be treated as a private implementation detail of the shared
        # library (otherwise the graph skips it for consumers and CMakeDeps
        # generates no lua config for them).
        self.requires("lua/5.4.8", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.test_requires("atf/0.23")

    def layout(self):
        basic_layout(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _atf_package_folder(self):
        return self.dependencies["atf"].package_folder.replace("\\", "/")

    def _lua_shim_dir(self):
        shim = os.path.join(self.build_folder, "lua-shim")
        os.makedirs(shim, exist_ok=True)
        save(self, os.path.join(shim, "lua.hpp"), _LUA_HPP)
        return shim.replace("\\", "/")

    def _atf_pkgconfig_dir(self):
        atf_folder = self._atf_package_folder()
        link_dir = os.path.join(self.build_folder, "atf-libs")
        os.makedirs(link_dir, exist_ok=True)
        for lib in ("libatf-c++.a", "libatf-c.a"):
            shutil.copy2(os.path.join(atf_folder, "lib", lib),
                         os.path.join(link_dir, lib))
        pcdir = os.path.join(self.build_folder, "atf-pkgconfig")
        os.makedirs(pcdir, exist_ok=True)
        save(self, os.path.join(pcdir, "atf-c++.pc"),
             "prefix=%s\n"
             "includedir=${prefix}/include\n"
             "libdir=%s\n\n"
             "Name: atf-c++\n"
             "Description: Automated Testing Framework (C++ binding)\n"
             "Version: %s\n"
             "Cflags: -I${includedir}\n"
             "Libs: -L${libdir} -latf-c++ -latf-c\n"
             % (atf_folder, link_dir.replace("\\", "/"), self.dependencies["atf"].ref.version))
        save(self, os.path.join(pcdir, "atf-sh.pc"),
             "exec_prefix=%s\n"
             "interpreter=${exec_prefix}/bin/atf-sh\n\n"
             "Name: atf-sh\n"
             "Description: Automated Testing Framework (POSIX shell binding)\n"
             "Version: %s\n"
             % (atf_folder, self.dependencies["atf"].ref.version))
        return pcdir.replace("\\", "/")

    def _mktemp_shim_dir(self):
        real = None
        for candidate in (shutil.which("mktemp"), "/bin/mktemp", "/usr/bin/mktemp"):
            if candidate and os.path.isfile(candidate):
                real = candidate
                break
        if real is None:
            raise ConanException("mktemp not found; cannot install the HMDFS shim")
        wrapper_dir = os.path.join(self.build_folder, "mktemp-wrapper")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, "mktemp")
        save(self, wrapper, _MKTEMP_SHIM % real)
        os.chmod(wrapper, 0o755)
        return wrapper_dir.replace("\\", "/")

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self, prefix=self.package_folder)
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--enable-atf",
            "--with-doxygen=no",
        ])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.extra_cxxflags.append("-std=c++20")
        tc.extra_cxxflags.append("-I%s" % self._lua_shim_dir())
        env = tc.environment()
        env.prepend_path("PKG_CONFIG_PATH", self._atf_pkgconfig_dir())
        env.prepend_path("PATH", self._mktemp_shim_dir())
        tc.generate(env=env)

    def _run_atf_suites(self, label, programs, expected):
        runner = os.path.join(self.build_folder, "run_atf_suites.sh")
        save(self, runner, _RUNNER)
        log = os.path.join(self.build_folder, "%s-upstream-tests.log" % label)
        quoted = " ".join('"%s"' % os.path.join(self.build_folder, p).replace("\\", "/")
                          for p in programs)
        prefix = ""
        if label == "examples":
            atf_folder = self._atf_package_folder()
            shell = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
            prefix = (
                'export PKG_CONFIG_PATH="%s:$PKG_CONFIG_PATH"; ' %
                os.path.join(self.package_folder, "lib", "pkgconfig").replace("\\", "/") +
                'export LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH"; ' %
                os.path.join(self.package_folder, "lib").replace("\\", "/") +
                'export ATF_LIBEXECDIR="%s/libexec"; ' % atf_folder +
                'export ATF_PKGDATADIR="%s/share/atf"; ' % atf_folder +
                'export ATF_SHELL="%s"; ' % shell
            )
        command = '%ssh "%s" "%s" %s' % (prefix, runner.replace("\\", "/"),
                                         log.replace("\\", "/"), quoted)
        self.output.info("Running upstream %s tests: %s" % (label, command))
        self.run(command, env="conanbuild", cwd=self.build_folder)
        self._check_accounting(label, log, expected)

    def _check_accounting(self, label, log, expected):
        contents = open(log, encoding="utf-8", errors="replace").read()
        suites = {}
        summary = None
        for line in contents.splitlines():
            if line.startswith("SUITE "):
                fields = line.split()
                suites[fields[1]] = int(fields[2].split("=", 1)[1])
            elif line.startswith("SUMMARY "):
                summary = line
        if summary is None:
            raise ConanException("ATF runner produced no SUMMARY for %s (log: %s)" % (label, log))
        fields = dict(part.split("=", 1) for part in summary.split()[1:])
        total = int(fields.get("total", 0))
        passed = int(fields.get("passed", 0))
        failed = int(fields.get("failed", 0))
        expected_total = sum(expected.values())
        if total != expected_total or passed != total or failed != 0:
            raise ConanException(
                "ATF %s accounting mismatch: total=%d passed=%d failed=%d expected=%d (log: %s)"
                % (label, total, passed, failed, expected_total, log))
        for program, count in expected.items():
            actual = suites.get(program)
            if actual != count:
                raise ConanException("ATF %s suite %s ran %s cases, expected %d (log: %s)"
                                     % (label, program, actual, count, log))
        self.output.info("Upstream %s tests passed: %d/%d (log: %s)"
                         % (label, passed, total, log))

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        run_tests = (can_run(self) and
                     not self.conf.get("tools.build:skip_test", default=False))
        if run_tests:
            self._run_atf_suites("atf-cxx", _ATF_PROGRAMS, _ATF_EXPECTED)
        # Install directly into the configure-time prefix (the package folder);
        # examples_test compiles the upstream examples against that installed
        # copy, so the install must happen before the example suite runs.
        autotools.make(target="install", args=["-j1"])
        if run_tests:
            self._run_atf_suites("examples", _EXAMPLES_PROGRAMS, _EXAMPLES_EXPECTED)
        else:
            self.output.info("Skipping upstream tests (cannot run or tools.build:skip_test set)")

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for entry in os.listdir(lib_dir):
                if entry.endswith(".la"):
                    os.remove(os.path.join(lib_dir, entry))
        include_dir = os.path.join(self.package_folder, "include")
        os.makedirs(include_dir, exist_ok=True)
        save(self, os.path.join(include_dir, "lua.hpp"), _LUA_HPP)

    def package_info(self):
        # CMakeDeps resolves transitive dependencies through components, so
        # lutok is modelled as a single component that requires lua::lua.
        component = self.cpp_info.components["lutok"]
        component.libs = ["lutok"]
        component.set_property("cmake_target_name", "lutok::lutok")
        component.set_property("pkg_config_name", "lutok")
        component.requires = ["lua::lua"]
