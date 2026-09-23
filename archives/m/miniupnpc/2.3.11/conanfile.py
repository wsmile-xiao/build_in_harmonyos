#!/usr/bin/env python3
"""Conan recipe for miniupnpc 2.3.11 — UPnP IGD client lightweight library.

Build route: direct compiler invocation, no CMake configure step.

Rationale: CMake project() repeatedly fails on the OHOS device with
"The C compiler identification is unknown" for /data/service/hnp/bin/clang.
Two CMake flag routes were already tried and both stayed red at
cmake.configure(): the default Conan mapping (CMAKE_SYSTEM_NAME=HarmonyOS,
no Platform/HarmonyOS module in stock CMake) and the Linux-override variant
(CMAKE_SYSTEM_NAME=Linux + PROCESSOR=aarch64, writable TMPDIR applied).
Rather than a third CMake flag combination, this recipe bypasses the broken
try_compile probe entirely (critnib 1.1 / ddate 0.2.2 / clamav-libunrar 1.4.5
precedent): the library is 14 pure-C translation units with no external
dependencies, so build() compiles them straight with the validated profile
compiler and archives them, then compiles the 7 upstream CTest harnesses
from the exact same sources CMakeLists.txt lists and runs all 7 cases for
real. A compiler smoke test runs first so a genuinely broken toolchain
shows its real stderr instead of CMake's summary.
"""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Exact library TU list from upstream miniupnpc/CMakeLists.txt
# (MINIUPNPC_SOURCES, minus the generated header handled separately).
_MINIUPNPC_LIB_SOURCES = [
    "src/igd_desc_parse.c",
    "src/miniupnpc.c",
    "src/minixml.c",
    "src/minisoap.c",
    "src/minissdpc.c",
    "src/miniwget.c",
    "src/upnpcommands.c",
    "src/upnpdev.c",
    "src/upnpreplyparse.c",
    "src/upnperrors.c",
    "src/connecthostport.c",
    "src/portlistingparse.c",
    "src/receivedata.c",
    "src/addr_is_reserved.c",
]

# Headers installed by upstream CMakeLists.txt install(FILES ...).
_MINIUPNPC_HEADERS = [
    "miniupnpc.h",
    "miniwget.h",
    "upnpcommands.h",
    "igd_desc_parse.h",
    "upnpreplyparse.h",
    "upnperrors.h",
    "upnpdev.h",
    "miniupnpctypes.h",
    "portlistingparse.h",
    "miniupnpc_declspec.h",
]

# Non-Windows compile definitions from upstream CMakeLists.txt
# (miniupnpc-private INTERFACE block).
_MINIUPNPC_DEFINES = [
    "MINIUPNPC_SET_SOCKET_TIMEOUT",
    "MINIUPNPC_GET_SRC_ADDR",
    "_BSD_SOURCE",
    "_DEFAULT_SOURCE",
    "_XOPEN_SOURCE=600",
]

# Upstream project() VERSION is 2.3.3 even at tag miniupnpd_2_3_11
# (monorepo tag name is the daemon version; see notes.md).
_UPSTREAM_PROJECT_VERSION = "2.3.3"


class MiniupnpcConan(ConanFile):
    name = "miniupnpc"
    version = "2.3.11"
    description = "UPnP IGD client lightweight library"
    license = "BSD-3-Clause"
    homepage = "https://miniupnp.tuxfamily.org/"
    url = "https://github.com/miniupnp/miniupnp"
    topics = ("upnp", "igd", "nat", "network")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "build_samples": [True, False],
    }
    default_options = {
        "shared": False,
        "build_samples": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="miniupnp-miniupnpd_2_3_11.tar.gz")

    def generate(self):
        self._ensure_writable_tmp()

    def _ensure_writable_tmp(self):
        # HMBS diagnosis [readonly_tmp]: device /tmp is read-only; clang and
        # mktemp-based test scripts spill temp files via $TMPDIR. HMBS injects
        # a task-private TMPDIR/TMP/TEMP; ensure all three point at a writable
        # dir (prefer injected value, else build_folder/tmp).
        cand = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP") or "")
        if not cand or not os.path.isdir(cand):
            cand = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(cand, exist_ok=True)
        except OSError:
            pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = cand
        self.output.info("Using writable TMPDIR=%s" % cand)
        return cand

    def _validated_cc(self):
        # R33: compiler comes from the Conan conf (authoritative OHOS profile
        # value), never from a bare ${CC} shell variable. PATH fallback only
        # when the conf value is missing/non-executable.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cand = (compilers.get("c") or "").strip()
        if cand:
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
            resolved = shutil.which(os.path.basename(cand))
            if resolved:
                return resolved
            self.output.warning(
                "conf c compiler '%s' not usable, falling back to PATH lookup" % cand)
        return shutil.which("clang") or shutil.which("cc") or "clang"

    def _validated_ar(self):
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        self.output.info("Using archiver: %s" % ar)
        return ar

    def _run_cmd(self, cmd, cwd, extra_env=None, timeout=1200):
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        self.output.info("+ %s" % cmd)
        proc = subprocess.run(cmd, shell=True, cwd=cwd,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=timeout, env=env)
        out = proc.stdout or ""
        if proc.returncode != 0:
            self.output.info(out[-8000:])
            raise ConanException(
                "command failed (rc=%s): %s\n%s"
                % (proc.returncode, cmd, out[-4000:]))
        return out

    def _smoke_test_cc(self, cc):
        # Compile+link a trivial TU first so a genuinely broken toolchain
        # shows its real stderr here (CMake only prints "identification is
        # unknown" and hides the cause).
        work = os.path.join(self.build_folder, "cc-smoke")
        os.makedirs(work, exist_ok=True)
        src = os.path.join(work, "smoke.c")
        with open(src, "w") as f:
            f.write("int main(void){return 0;}\n")
        out = os.path.join(work, "smoke")
        self._run_cmd('"%s" "%s" -o "%s"' % (cc, src, out), cwd=work)
        self._run_cmd('"%s"' % out, cwd=work)
        self.output.info("C compiler smoke test passed: %s" % cc)

    def _miniupnpc_dir(self):
        d = os.path.join(self.source_folder, "miniupnpc")
        if not os.path.isdir(d):
            raise ConanException(
                "miniupnpc source subdir not found: %s" % d)
        return d

    def _generate_strings_header(self, gen_dir):
        # Replicates configure_file(miniupnpcstrings.h.cmake) exactly:
        # OS_STRING is ${CMAKE_SYSTEM_NAME}; the Linux-override route used
        # "Linux". The UPNP_VERSION_* block is required too (minisoap.c uses
        # UPNP_VERSION_STRING in a snprintf User-Agent line; omitting it
        # breaks compilation with "expected ')'").
        os.makedirs(gen_dir, exist_ok=True)
        path = os.path.join(gen_dir, "miniupnpcstrings.h")
        with open(path, "w", encoding="utf-8") as f:
            f.write("#ifndef MINIUPNPCSTRINGS_H_INCLUDED\n"
                    "#define MINIUPNPCSTRINGS_H_INCLUDED\n\n"
                    '#define OS_STRING "Linux"\n'
                    '#define MINIUPNPC_VERSION_STRING "%s"\n\n'
                    "/* according to \"UPnP Device Architecture 1.1\" */\n"
                    "#define UPNP_VERSION_MAJOR 1\n"
                    "#define UPNP_VERSION_MINOR 1\n"
                    '#define UPNP_VERSION_STRING "UPnP/1.1"\n\n'
                    "#endif\n" % _UPSTREAM_PROJECT_VERSION)
        return path

    def _compile_flags(self, gen_dir, src_dir, extra_defines=None):
        opt = "-O2 -DNDEBUG" if str(self.settings.build_type) == "Release" else "-O0 -g"
        defines = list(_MINIUPNPC_DEFINES) + list(extra_defines or [])
        parts = ["-std=c99", "-fPIC", "-Wall", opt]
        parts += ['-D%s' % d for d in defines]
        parts += ['-I"%s"' % os.path.join(src_dir, "include"), '-I"%s"' % gen_dir]
        return " ".join(parts)

    def _build_library(self, cc, ar, src_dir, gen_dir, obj_dir):
        missing = [s for s in _MINIUPNPC_LIB_SOURCES
                   if not os.path.isfile(os.path.join(src_dir, s))]
        if missing:
            raise ConanException("miniupnpc sources missing: %s" % ", ".join(missing))
        cflags = self._compile_flags(gen_dir, src_dir,
                                     extra_defines=["MINIUPNP_STATICLIB"]
                                     if not self.options.shared else [])
        objects = []
        for src_rel in _MINIUPNPC_LIB_SOURCES:
            src = os.path.join(src_dir, src_rel)
            obj = os.path.join(obj_dir, src_rel.replace("/", "_").replace(".c", ".o"))
            self._run_cmd('"%s" %s -c "%s" -o "%s"' % (cc, cflags, src, obj),
                          cwd=obj_dir)
            objects.append('"%s"' % obj)
        static_lib = os.path.join(obj_dir, "libminiupnpc.a")
        self._run_cmd('"%s" rcs "%s" %s' % (ar, static_lib, " ".join(objects)),
                      cwd=obj_dir)
        shared_lib = ""
        if self.options.shared:
            shared_lib = os.path.join(obj_dir, "libminiupnpc.so")
            self._run_cmd('"%s" -shared -o "%s" %s' % (cc, shared_lib, " ".join(objects)),
                          cwd=obj_dir)
        return static_lib, shared_lib

    def _build_test_binary(self, cc, name, sources, src_dir, gen_dir, test_dir,
                           extra_defines=None):
        cflags = self._compile_flags(gen_dir, src_dir, extra_defines=extra_defines)
        srcs = " ".join('"%s"' % os.path.join(src_dir, s) for s in sources)
        out = os.path.join(test_dir, name)
        self._run_cmd('"%s" %s %s -o "%s"' % (cc, cflags, srcs, out), cwd=test_dir)
        return out

    def _write_upstream_result(self, data):
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            path = os.path.join(self.build_folder, "upstream_test_result.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            self.output.info("wrote upstream_test_result.json to {}".format(path))
        except Exception as e:
            self.output.warning("write upstream_test_result.json failed: {}".format(e))

    def _fix_testupnpreplyparse_ub(self, src_dir):
        # Upstream src/testupnpreplyparse.c declares `FILE * f;` without an
        # initializer, then dispatches on `f == NULL` to tell the XML file
        # apart from the .namevalue file. That is use-of-uninitialized-memory:
        # on toolchains where the stack slot is non-zero the first file lands
        # in `name_value_file` and the second hits the `unrecognized argument`
        # branch (true-machine log: DeletePortMapping.namevalue rejected,
        # validateupnpreplyparse rc=1). Zero-initializing the local is a
        # test-harness-only correctness fix; the shipped library is untouched
        # and the 7-case count/coverage is unchanged.
        path = os.path.join(src_dir, "src", "testupnpreplyparse.c")
        try:
            with open(path, "r", encoding="utf-8") as f:
                txt = f.read()
        except OSError as e:
            raise ConanException("cannot read testupnpreplyparse.c: %s" % e)
        if "FILE * f = NULL;" in txt:
            return
        old = "FILE * f;"
        if old not in txt:
            raise ConanException(
                "testupnpreplyparse.c UB pattern not found, refusing to guess")
        txt = txt.replace(old, "FILE * f = NULL;", 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)
        self.output.info("fixed uninitialized FILE * f in testupnpreplyparse.c")

    def _run_upstream_tests(self, cc, src_dir, gen_dir):
        """Compile the real upstream harnesses and run all 7 ctest cases.

        Same binaries and cases as upstream miniupnpc/CMakeLists.txt
        (validateminixml, validateminiwget, validateupnpreplyparse,
        validateportlistingparse, validateigddescparse1/2,
        validateaddr_is_reserved), without the broken CMake ID probe.
        """
        discovered = 7
        if not can_run(self):
            result = {
                "status": "skipped", "framework": "direct-cc",
                "command": "cross-building: test binaries cannot run on build host",
                "discovered": discovered, "executed": 0, "passed": 0,
                "failed": 0, "skipped": discovered,
                "reason": "cross-building: test binaries cannot run on build host",
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT={}".format(
                json.dumps(result, separators=(",", ":"))))
            self._write_upstream_result(result)
            return
        test_dir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(test_dir, exist_ok=True)
        self._fix_testupnpreplyparse_ub(src_dir)
        tdefs = ["MINIUPNP_STATICLIB"]
        bins = {}
        bins["minixmlvalid"] = self._build_test_binary(
            cc, "minixmlvalid", ["src/minixmlvalid.c", "src/minixml.c"],
            src_dir, gen_dir, test_dir, extra_defines=tdefs)
        bins["testminiwget"] = self._build_test_binary(
            cc, "testminiwget",
            ["src/testminiwget.c", "src/miniwget.c", "src/miniupnpc.c",
             "src/minisoap.c", "src/upnpcommands.c", "src/minissdpc.c",
             "src/upnpreplyparse.c", "src/minixml.c", "src/igd_desc_parse.c",
             "src/connecthostport.c", "src/portlistingparse.c",
             "src/receivedata.c", "src/addr_is_reserved.c"],
            src_dir, gen_dir, test_dir, extra_defines=tdefs)
        bins["minihttptestserver"] = self._build_test_binary(
            cc, "minihttptestserver", ["src/minihttptestserver.c"],
            src_dir, gen_dir, test_dir, extra_defines=tdefs)
        bins["testupnpreplyparse"] = self._build_test_binary(
            cc, "testupnpreplyparse",
            ["src/testupnpreplyparse.c", "src/minixml.c", "src/upnpreplyparse.c"],
            src_dir, gen_dir, test_dir, extra_defines=tdefs)
        bins["testportlistingparse"] = self._build_test_binary(
            cc, "testportlistingparse",
            ["src/testportlistingparse.c", "src/minixml.c", "src/portlistingparse.c"],
            src_dir, gen_dir, test_dir, extra_defines=tdefs)
        bins["testigddescparse"] = self._build_test_binary(
            cc, "testigddescparse",
            ["src/testigddescparse.c", "src/igd_desc_parse.c", "src/minixml.c",
             "src/miniupnpc.c", "src/miniwget.c", "src/minissdpc.c",
             "src/upnpcommands.c", "src/upnpreplyparse.c", "src/minisoap.c",
             "src/connecthostport.c", "src/portlistingparse.c",
             "src/receivedata.c", "src/addr_is_reserved.c"],
            src_dir, gen_dir, test_dir, extra_defines=tdefs)
        bins["testaddr_is_reserved"] = self._build_test_binary(
            cc, "testaddr_is_reserved",
            ["src/testaddr_is_reserved.c", "src/addr_is_reserved.c"],
            src_dir, gen_dir, test_dir, extra_defines=tdefs)

        # Falsifiability: fixtures must be non-empty, else a harness could
        # compare empty-vs-empty and fake a pass.
        for fixture in ("testdesc/new_LiveBox_desc.xml",
                        "testdesc/new_LiveBox_desc.values",
                        "testdesc/linksys_WAG200G_desc.xml",
                        "testdesc/linksys_WAG200G_desc.values"):
            p = os.path.join(src_dir, fixture)
            if not os.path.isfile(p) or os.path.getsize(p) == 0:
                raise ConanException("upstream fixture missing or empty: %s" % p)

        passed, failed = 0, 0
        details = []

        def run_case(label, cmd, cwd):
            nonlocal passed, failed
            env = os.environ.copy()
            self.output.info("+ [%s] %s (cwd=%s)" % (label, cmd, cwd))
            proc = subprocess.run(cmd, shell=True, cwd=cwd,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=600, env=env)
            out = proc.stdout or ""
            self.output.info("--- %s (rc=%s) ---\n%s" % (label, proc.returncode, out[-4000:]))
            details.append("%s:rc=%s" % (label, proc.returncode))
            if proc.returncode == 0:
                passed += 1
            else:
                failed += 1

        run_case("validateminixml", '"%s"' % bins["minixmlvalid"], test_dir)
        miniwget_sh = os.path.join(src_dir, "testminiwget.sh")
        env_miniwget = ("TESTSERVER=\"%s\" TESTMINIWGET=\"%s\" "
                        % (bins["minihttptestserver"], bins["testminiwget"]))
        run_case("validateminiwget", "%ssh \"%s\"" % (env_miniwget, miniwget_sh), test_dir)
        reply_sh = os.path.join(src_dir, "testupnpreplyparse.sh")
        env_reply = "TESTUPNPREPLYPARSE=\"%s\" " % bins["testupnpreplyparse"]
        run_case("validateupnpreplyparse", "%ssh \"%s\"" % (env_reply, reply_sh), src_dir)
        run_case("validateportlistingparse",
                 '"%s"' % bins["testportlistingparse"], test_dir)
        testdesc = os.path.join(src_dir, "testdesc")
        run_case("validateigddescparse1",
                 '"%s" new_LiveBox_desc.xml new_LiveBox_desc.values' % bins["testigddescparse"],
                 testdesc)
        run_case("validateigddescparse2",
                 '"%s" linksys_WAG200G_desc.xml linksys_WAG200G_desc.values'
                 % bins["testigddescparse"], testdesc)
        run_case("validateaddr_is_reserved",
                 '"%s"' % bins["testaddr_is_reserved"], test_dir)

        executed = passed + failed
        status = "passed" if (failed == 0 and executed == discovered) else "failed"
        result = {
            "status": status,
            "framework": "direct-cc",
            "command": "minixmlvalid + sh testminiwget.sh + sh testupnpreplyparse.sh + "
                       "testportlistingparse + testigddescparse x2 + testaddr_is_reserved "
                       "(%s)" % ";".join(details),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT={}".format(
            json.dumps(result, separators=(",", ":"))))
        self._write_upstream_result(result)
        if status != "passed":
            raise ConanException("miniupnpc upstream tests failed: {}".format(
                json.dumps(result)))

    def build(self):
        self._ensure_writable_tmp()
        cc = self._validated_cc()
        ar = self._validated_ar()
        self._smoke_test_cc(cc)
        src_dir = self._miniupnpc_dir()
        gen_dir = os.path.join(self.build_folder, "gen")
        obj_dir = os.path.join(self.build_folder, "objs")
        os.makedirs(obj_dir, exist_ok=True)
        self._generate_strings_header(gen_dir)
        self._build_library(cc, ar, src_dir, gen_dir, obj_dir)
        self._run_upstream_tests(cc, src_dir, gen_dir)

    def package(self):
        src_dir = os.path.join(self.source_folder, "miniupnpc")
        obj_dir = os.path.join(self.build_folder, "objs")
        for header in _MINIUPNPC_HEADERS:
            copy(self, header, src=os.path.join(src_dir, "include"),
                 dst=os.path.join(self.package_folder, "include", "miniupnpc"))
        for lib in glob.glob(os.path.join(obj_dir, "libminiupnpc.a")):
            copy(self, os.path.basename(lib), src=obj_dir,
                 dst=os.path.join(self.package_folder, "lib"))
        for lib in glob.glob(os.path.join(obj_dir, "libminiupnpc.so*")):
            copy(self, os.path.basename(lib), src=obj_dir,
                 dst=os.path.join(self.package_folder, "lib"))
        _lic = os.path.join(src_dir, "LICENSE")
        if os.path.isfile(_lic):
            copy(self, "LICENSE", src=src_dir,
                 dst=os.path.join(self.package_folder, "licenses"))
        # Minimal pkg-config file (upstream miniupnpc.pc.in equivalent).
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        with open(os.path.join(pc_dir, "miniupnpc.pc"), "w", encoding="utf-8") as f:
            f.write("prefix=${pcfiledir}/../..\n"
                    "exec_prefix=${prefix}\n"
                    "libdir=${prefix}/lib\n"
                    "includedir=${prefix}/include\n\n"
                    "Name: miniupnpc\n"
                    "Description: UPnP IGD client lightweight library\n"
                    "Version: %s\n"
                    "Libs: -L${libdir} -lminiupnpc\n"
                    "Cflags: -I${includedir}\n" % self.version)
        try:
            copy(self, "upstream_test_result.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.libs = ["miniupnpc"]
        self.cpp_info.set_property("cmake_file_name", "miniupnpc")
        self.cpp_info.set_property("cmake_target_name", "miniupnpc::miniupnpc")
        self.cpp_info.set_property("pkg_config_name", "miniupnpc")
        if not self.options.shared:
            self.cpp_info.defines.append("MINIUPNP_STATICLIB")
