#!/usr/bin/env python3
"""Conan recipe — jrtplib 3.11.2 (CMake).

JRTPLIB is a fully featured C++ library for the Real-time Transport
Protocol (RTP). Upstream uses CMake (minimum 2.8); the library targets
are jrtplib-static/jrtplib-shared with output name 'jrtp' on non-MSVC,
and public headers are installed under include/jrtplib3. Thread support
comes from the companion JThread library (archives/j/jthread).
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class JrtplibConan(ConanFile):
    name = "jrtplib"
    version = "3.11.2"
    description = "Fully featured C++ library for the Real-time Transport Protocol (RTP)"
    license = "MIT"
    homepage = "https://research.edm.uhasselt.be/jori/jrtplib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # rtppollthread.h includes <jthread/jthread.h>, so consumers need
        # the JThread headers and library transitively.
        self.requires("jthread/1.3.3", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_compiler(self, name):
        candidates = [
            shutil.which(name),
            "/data/service/hnp/bin/%s" % name,
            os.path.expanduser("~/usr/local/bin/%s" % name),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise RuntimeError("%s compiler not found" % name)

    def _ensure_writable_tmp(self):
        # HMBS 真机 /tmp 只读；统一改用注入的 TMPDIR/TMP/TEMP，
        # 缺失或不可写时回退到 build_folder 下的 tmp 目录。
        # 仅替换临时文件根目录，不删除任何测试。
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val and os.path.isdir(val) and os.access(val, os.W_OK):
                tmpdir = val
                break
        else:
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        return tmpdir

    def _run_capture(self, cmd, cwd, timeout=300):
        self._ensure_writable_tmp()
        env = dict(os.environ)
        for key in ("TMPDIR", "TMP", "TEMP"):
            env[key] = os.environ.get(key, env.get(key, cwd))
        if isinstance(cmd, str):
            cmd = [cmd]
        proc = subprocess.run(cmd, shell=False, cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=timeout,
                              env=env)
        return proc.returncode, proc.stdout or ""

    def generate(self):
        cc = self._find_compiler("clang")
        cxx = self._find_compiler("clang++")
        self.output.info("Using C compiler: %s" % cc)
        self.output.info("Using CXX compiler: %s" % cxx)
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_C_COMPILER"] = cc
        tc.variables["CMAKE_CXX_COMPILER"] = cxx
        # Upstream declares cmake_minimum_required(VERSION 2.8); recent CMake
        # needs a compatibility floor (same approach as jthread 1.3.3).
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Thread support via the JThread package (found through the
        # CMAKE_PREFIX_PATH that Conan sets up for requirements).
        tc.variables["JTHREAD_ENABLED"] = True
        # Build the programs in tests/ so the automatable subset can run below.
        tc.variables["JRTPLIB_COMPILE_TESTS"] = True
        tc.variables["JRTPLIB_COMPILE_EXAMPLES"] = True
        # Upstream adds -Wall -Wextra -Werror for GNU-like compilers (clang
        # counts as one); the 2020-era code does not survive -Werror on
        # clang 15, so keep warnings on but non-fatal.
        tc.variables["JRTPLIB_WARNINGSASERRORS"] = False
        # Only honored when CMAKE_CROSSCOMPILING; aarch64 is little-endian.
        tc.variables["JRTPLIB_USE_BIGENDIAN"] = False
        # No libsrtp in the dependency closure; keep secure-RTP variants off.
        tc.variables["SRTP_ENABLED"] = False
        tc.variables["SRTP2_ENABLED"] = False
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def _fix_tcptest_bind(self):
        # Defensive fallback for 0001-tcptest-qualify-bsd-sockets.patch:
        # if the patch context ever drifts, still qualify the BSD socket
        # calls in tests/tcptest.cpp so 'using namespace std' cannot hijack
        # bind into std::bind (libc++ __bind). Idempotent plain-text edit.
        path = os.path.join(self.source_folder, "tests", "tcptest.cpp")
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        fixed = text
        fixed = fixed.replace("= socket(AF_INET", "= ::socket(AF_INET")
        fixed = fixed.replace("(bind(listener", "(::bind(listener")
        fixed = fixed.replace("\n\tlisten(listener", "\n\t::listen(listener")
        fixed = fixed.replace("(connect(client", "(::connect(client")
        fixed = fixed.replace("= accept(listener", "= ::accept(listener")
        if fixed != text:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(fixed)
            self.output.info("Qualified BSD socket calls in tests/tcptest.cpp")

    def build(self):
        self._ensure_writable_tmp()
        apply_conandata_patches(self)
        self._fix_tcptest_bind()
        cc = self._find_compiler("clang")
        cxx = self._find_compiler("clang++")
        cmake = CMake(self)
        cmake.configure(variables={
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            "CMAKE_C_COMPILER": cc,
            "CMAKE_CXX_COMPILER": cxx,
        })
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # tests/ 共 14 个手动程序（无 ctest harness）。其中 4 个可无人值守自动
        # 断言：timetest/timeinittest 练习 RTPTime，testexttrans 通过假 transmitter
        # 注入约 100 万包，testrawpacket 在 127.0.0.1 上跑回环 RTP 会话。每个用例
        # 校验内容标记，空输出或静默跳过不得判通过。discovered 记上游全部用例数
        # （14），executed 记实际无人值守执行的子集（4），差值作为 skipped 并在
        # reason 中逐项说明，供 HMBS 判定「部分执行放行」（详见 README/prompts）。
        cases = (
            ("timetest", "Microseconds:"),
            ("timeinittest", "0"),
            ("testexttrans", "Writing packet 1048000"),
            ("testrawpacket", "Valid RTP packet"),
        )
        all_upstream_programs = 14
        tests_dir = os.path.join(self.build_folder, "tests")
        executed = len(cases)
        passed = 0
        for program, marker in cases:
            binary = os.path.join(tests_dir, program)
            if not os.path.isfile(binary):
                raise RuntimeError("upstream test binary missing: %s" % binary)
            self.output.info("Running upstream test: %s" % binary)
            rc, out = self._run_capture(binary, tests_dir)
            self.output.info("%s output tail:\n%s" % (program, out[-2000:]))
            if rc != 0:
                raise RuntimeError("upstream test %s failed (rc=%d)" % (program, rc))
            if not out.strip():
                raise RuntimeError("upstream test %s printed nothing" % program)
            if marker not in out:
                raise RuntimeError("upstream test %s lacks marker %r" % (program, marker))
            self.output.info("[PASS] upstream %s" % program)
            passed += 1
        skipped = all_upstream_programs - executed
        skipped_reason = "；".join(
            [
                "testmultiplex(需 manual stdin 本端/对端端口与 IP)",
                "testexistingsockets(需预置 socket 与对端配合)",
                "testautoportbase(需手动输入端口、对端地址与包数)",
                "srtptest(需 libsrtp 与对端安全会话，本配方关闭 SRTP)",
                "rtcpdump(被动等待外部 RTCP 流)",
                "readlogfile(需外部 RTP 日志文件参数)",
                "abortdesctest(需双端 socket 与手动 abort 时序)",
                "abortdescipv6(需双端 socket 与 IPv6 环境)",
                "tcptest(需 manual 本端/对端 TCP 端口与 IP)",
                "sigintrtest(需人工发送 SIGINT 的交互式中断测试)",
            ]
        )
        marker_doc = {
            "status": "passed",
            "framework": "jrtplib-tests",
            "command": "timetest + timeinittest + testexttrans + testrawpacket"
                       " (tests/, JRTPLIB_COMPILE_TESTS=ON)",
            "discovered": all_upstream_programs,
            "executed": executed,
            "passed": passed,
            "failed": 0,
            "skipped": skipped,
            "reason": ("tests/ 共 %d 个手动程序且无 ctest harness；仅 4 项"
                       "（timetest/timeinittest/testexttrans/testrawpacket）可无人值守自动断言，"
                       "其余 %d 项需人工 stdin 输入、远程对端、libsrtp 安全会话、外部 RTP 日志"
                       "或人工 SIGINT，无法在无人值守真机自动化执行：%s。"
                       % (all_upstream_programs, skipped, skipped_reason)),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker_doc))
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8", newline="\n") as fh:
            json.dump(marker_doc, fh)
        if passed != executed:
            raise RuntimeError("upstream tests failed: %s" % marker_doc)

    def package(self):
        copy(self, "LICENSE.MIT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        # Upstream output name is 'jrtp' on non-MSVC (libjrtp.a / libjrtp.so).
        self.cpp_info.libs = ["jrtp"]
        self.cpp_info.set_property("cmake_file_name", "jrtplib")
        self.cpp_info.set_property("cmake_target_name", "jrtplib::jrtplib")
        if str(self.settings.os) == "OHOS":
            self.cpp_info.system_libs = ["pthread"]
