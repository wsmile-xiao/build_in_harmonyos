#!/usr/bin/env python3
"""Conan recipe — libgeocoding 9.0.34 (Google libphonenumber offline geocoder, C++).

libgeocoding 是 google/libphonenumber 的离线号码地理编码库：源码位于上游
``cpp/src/phonenumbers/geocoding/``，与 libphonenumber 同处一份 ``cpp/`` CMake
配置，由 ``BUILD_GEOCODER=ON`` 一次配置同时产出（Debian 亦为同一源包的
``libgeocoding8`` / ``libphonenumber8`` 两个二进制）。

因此本配方**直接以上游真实 CMake 构建入口**构建该源码树并执行上游 install 规则；
``libgeocoding.a`` 引用 ``libphonenumber`` 的号码解析/元数据符号（离线 geocoder
必须解析号码），两者按上游语义一同归档并一同导出。

上游测试（``libphonenumber_test`` + ``tools/cpp`` 的
``generate_geocoding_data_test`` + 示例 ``geocoding_test_program``）在 build()
内真实执行，结果以 ``HMBS_UPSTREAM_TEST_RESULT`` 打印并随包持久化到 ``res/``
（缓存命中时由 test_package 重放，证据不丢失）。
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibgeocodingConan(ConanFile):
    name = "libgeocoding"
    version = "9.0.34"
    description = ("Google's offline phone number geocoder (C++), built from the "
                   "libphonenumber source tree")
    license = "Apache-2.0"
    homepage = "https://github.com/google/libphonenumber"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
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
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libgeocoding is only supported on Linux/OHOS, not %s" % self.settings.os
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "libgeocoding/9.0.34 以静态归档提供（上游 geocoding + 同源 phonenumber "
                "归档，离线 geocoder 交叉引用），shared 构型未适配"
            )
        self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def validate(self):
        check_min_cppstd(self, "17")

    def requirements(self):
        # 上游 cpp/CMakeLists.txt:430 LIBRARY_DEPS =
        #   ${ICU_LIB} ${PROTOBUF_LIB} absl::node_hash_set absl::strings absl::synchronization
        # 这三个即 geocoding 目标的直接链接依赖。
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)
        self.requires("protobuf/33.6", transitive_headers=True, transitive_libs=True)
        self.requires("icu4c/78", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # 上游 gtest 测试二进制（libphonenumber_test / generate_geocoding_data_test）
        # 仅在本包构建期运行，不向下游传播。
        self.test_requires("googletest/1.12.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ helpers

    def _cpp_dir(self):
        return os.path.join(self.source_folder, "cpp")

    def _writable_tmpdir(self):
        """Prefer the HMBS-provided writable TMPDIR (E002: /tmp may be read-only)."""
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val and os.path.isdir(val):
                return val
        fallback = os.path.join(self.build_folder, "test-tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _run_env(self):
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        env = dict(os.environ)
        for key in ("TMPDIR", "TMP", "TEMP", "TEST_TMPDIR"):
            env[key] = tmpdir
        return env

    def _protobuf_utf8_archives(self):
        """protobuf>=30 随包安装 utf8_range/utf8_validity，但未经 cpp_info 导出。

        libprotobuf.a 引用 utf8_range_IsValid/ValidPrefix，静态链接必须显式补上；
        扫真实包目录取绝对路径，取不到时返回规范名（保持响亮失败而非静默改变链接口径）。
        """
        found = []
        try:
            pkg = self.dependencies["protobuf"].package_folder
        except Exception:
            pkg = None
        if pkg:
            libdir = os.path.join(pkg, "lib")
            try:
                files = sorted(os.listdir(libdir))
            except OSError:
                files = []
            for fn in files:
                low = fn.lower()
                if low.startswith("libutf8") and low.endswith(".a"):
                    found.append(os.path.join(libdir, fn))
        if not found:
            self.output.info("utf8_range archives not found in protobuf package lib/; "
                             "falling back to canonical names")
            return ["-lutf8_validity", "-lutf8_range"]
        order = {"utf8_validity": 0, "utf8_range": 1}
        found.sort(key=lambda p: order.get(
            os.path.basename(p)[3:-2], 99))
        return found

    def _conan_link_closure(self):
        """静态链接闭包，交给上游 CMake（见 patches/0001）。

        上游只发现 icuuc/icui18n/protobuf 与三个 Abseil 目标，而静态归档不携带自身
        依赖：libprotobuf.a 需要 Abseil log/status 族、utf8_range/utf8_validity 与
        zlib，libicuuc.a 需要 libicudata.a。这里按真实依赖图（cpp_info）补齐，并把
        它们包在 --start-group/--end-group 内，避免静态库内部环依赖的解析顺序问题。
        googletest 只看不取：上游测试二进制用自身 run_tests.cc 提供 main()。
        """
        items = ["-Wl,--start-group"]
        seen_libdirs, seen_libs = set(), set()
        for dep in self.dependencies.values():
            if dep.ref.name == "googletest":
                continue
            info = dep.cpp_info
            libs = list(getattr(info, "libs", None) or [])
            components = getattr(info, "components", None)
            if components:
                for comp in components.values():
                    libs += [l for l in (getattr(comp, "libs", None) or [])
                             if not l.endswith("_main")]
            for libdir in (getattr(info, "libdirs", None) or []):
                if libdir not in seen_libdirs:
                    seen_libdirs.add(libdir)
                    items.append("-L" + libdir)
            for lib in libs:
                if lib not in seen_libs:
                    seen_libs.add(lib)
                    items.append("-l" + lib)
        items += self._protobuf_utf8_archives()
        items.append("-Wl,--end-group")
        self.output.info("conan static link closure: %s" % " ".join(items))
        return items

    def generate(self):
        # 必须用 Ninja：Makefile 生成器会在这些自定义命令上置 .DELETE_ON_ERROR，
        # 而上游在 REGENERATE_METADATA=OFF 时把「生成元数据」写成了空 `echo`
        # 自定义命令（不产出声明的 OUTPUT），规则一旦执行就删掉随包发布的
        # cpp/src/phonenumbers/test_metadata.cc → phonenumber_testing 编译失败。
        # Ninja 不删未更新的目标，实测该生成器下全量构建/测试/install 均通过。
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["BUILD_GEOCODER"] = True
        tc.variables["BUILD_TESTING"] = True
        tc.variables["BUILD_STATIC_LIB"] = True
        tc.variables["BUILD_SHARED_LIBS"] = False
        # 无 Java/Maven 工具链：使用源码树内预生成的 metadata 文件。
        tc.variables["REGENERATE_METADATA"] = False
        # 砍掉整条 Boost 依赖链，改用 C++11 std::mutex。
        tc.variables["USE_BOOST"] = False
        tc.variables["USE_STDMUTEX"] = True
        # 正则引擎由 ICU 承担（geocoder 亦强制 icui18n）。
        tc.variables["USE_ICU_REGEXP"] = True
        tc.variables["USE_ALTERNATE_FORMATS"] = True
        tc.variables["LIBPHONENUMBER_CONAN_LIBS"] = ";".join(self._conan_link_closure())
        # Conan 只把依赖包目录放进 CMAKE_LIBRARY_PATH/CMAKE_INCLUDE_PATH，不含
        # CMAKE_PREFIX_PATH：upstream 的 find_package(absl) 会落空并转入
        # FetchContent 从 GitHub 拉 abseil（CI 无外网 → 必然失败）。显式指向
        # 依赖包内 abseil 自带的 CMake 配置目录，使 find_package 直接命中。
        tc.variables["absl_DIR"] = os.path.join(
            self.dependencies["abseil-cpp"].package_folder, "lib", "cmake", "absl")
        # protoc 由 protobuf 依赖包提供（不在系统 PATH 上）。
        tc.variables["CMAKE_PROGRAM_PATH"] = os.path.join(
            self.dependencies["protobuf"].package_folder, "bin")
        tc.generate()
        VirtualBuildEnv(self).generate()   # protoc（protobuf 包 bin/）上 PATH
        VirtualRunEnv(self).generate()

    # ------------------------------------------------------------ upstream tests

    def _gtest_binaries(self):
        return [
            ("libphonenumber_test",
             os.path.join(self.build_folder, "libphonenumber_test")),
            ("generate_geocoding_data_test",
             os.path.join(self.build_folder, "tools", "generate_geocoding_data_test")),
        ]

    def _emit_upstream_result(self, result):
        """双通道打印 + 落盘，缓存命中时仍可由 test_package 重放。"""
        try:
            with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                      "w", encoding="utf-8") as f:
                json.dump(result, f)
        except OSError:
            pass
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result)
        print(msg, flush=True)
        self.output.info(msg)

    def _parse_gtest(self, output):
        """从 gtest 输出解析 通过/失败/跳过/执行 与逐条用例名。
        用例结果标记不一定在行首：上游 RegExpAdapterTest.TestFindAndConsume
        会先打印 "previous input: Present input: " 再接 "[       OK ] ..."，
        故用 search（要求带耗时括号，避免把失败汇总清单算成第二条）。
        """
        cases = []
        status_of = {"OK": "PASSED", "FAILED": "FAILED", "SKIPPED": "SKIPPED"}
        for line in output.splitlines():
            m = re.search(r"\[\s*(OK|FAILED|SKIPPED)\s*\]\s+(\S+)\s+\(", line)
            if m:
                cases.append({"name": m.group(2),
                              "status": status_of[m.group(1)]})
        passed = failed = skipped = ran = 0
        m = re.search(r"\[\s*PASSED\s*\]\s*(\d+)\s+tests?\.", output)
        if m:
            passed = int(m.group(1))
        m = re.search(r"\[\s*FAILED\s*\]\s*(\d+)\s+tests?", output)
        if m:
            failed = int(m.group(1))
        m = re.search(r"\[\s*SKIPPED\s*\]\s*(\d+)\s+tests?", output)
        if m:
            skipped = int(m.group(1))
        m = re.search(r"(\d+)\s+tests?\s+from\s+\d+\s+test suites?\s+ran", output)
        if m:
            ran = int(m.group(1))
        else:
            ran = passed + failed + skipped
        return {"ran": ran, "passed": passed, "failed": failed,
                "skipped": skipped, "cases": cases}

    def _run_upstream_tests(self):
        env = self._run_env()
        suites, all_cases = [], []
        total = {"discovered": 0, "executed": 0, "passed": 0,
                 "failed": 0, "skipped": 0}
        for name, binary in self._gtest_binaries():
            if not os.path.isfile(binary):
                raise ConanException("upstream test binary missing: %s" % binary)
            os.chmod(binary, 0o755)
            out = self._exec([binary], cwd=os.path.dirname(binary), env=env)
            stats = self._parse_gtest(out["stdout"])
            if stats["ran"] == 0:
                raise ConanException(
                    "%s exit %d but no gtest case ran (silent skip)" % (name, out["returncode"]))
            all_cases += [dict(case, suite=name) for case in stats["cases"]]
            suites.append({"name": name, "command": "./" + name,
                           "exit_code": out["returncode"],
                           "ran": stats["ran"], "passed": stats["passed"],
                           "failed": stats["failed"], "skipped": stats["skipped"]})
            for key in ("discovered", "executed", "passed", "failed", "skipped"):
                total[key] += stats["ran"] if key in ("discovered", "executed") else stats[key]
            try:
                with open(os.path.join(self.build_folder, "upstream-%s.log" % name),
                          "w", encoding="utf-8") as f:
                    f.write(out["stdout"])
            except OSError:
                pass
            self.output.info("upstream %s: ran=%d passed=%d failed=%d skipped=%d"
                             % (name, stats["ran"], stats["passed"],
                                stats["failed"], stats["skipped"]))

        # 上游示例程序（cpp/test/phonenumbers/geocoding/geocoding_test_program.cc）：
        # 上游用它校验两个库联编正确，必须一并执行。
        sample_bin = os.path.join(self.build_folder, "geocoding_test_program")
        if not os.path.isfile(sample_bin):
            raise ConanException("upstream sample binary missing: %s" % sample_bin)
        os.chmod(sample_bin, 0o755)
        sample_out = self._exec([sample_bin], cwd=self.build_folder, env=env)
        sample_desc = (sample_out["stdout"].strip().splitlines() or [""])[-1]
        if sample_out["returncode"] != 0 or sample_desc != "Mountain View, CA":
            raise ConanException(
                "upstream sample geocoding_test_program failed (exit %d, output=%r)"
                % (sample_out["returncode"], sample_desc))
        self.output.info("upstream sample geocoding_test_program -> %r" % sample_desc)

        status = "passed" if total["failed"] == 0 and total["passed"] > 0 else "failed"
        result = {
            "status": status,
            "framework": "gtest",
            "command": "./libphonenumber_test + ./tools/generate_geocoding_data_test",
            "discovered": total["discovered"],
            "executed": total["executed"],
            "passed": total["passed"],
            "failed": total["failed"],
            "skipped": total["skipped"],
            "suites": suites,
            "sample": {"name": "geocoding_test_program",
                       "exit_code": sample_out["returncode"],
                       "output": sample_desc},
        }
        self._emit_upstream_result(result)
        try:
            with open(os.path.join(self.build_folder, "upstream_test_cases.txt"),
                      "w", encoding="utf-8") as f:
                for case in all_cases:
                    f.write("%s\t%s\t%s\n" % (case.get("suite"), case["name"],
                                              case["status"]))
        except OSError:
            pass
        if status != "passed":
            raise ConanException("libgeocoding upstream tests failed: %s" % result)

    def _exec(self, cmd, cwd, env):
        proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True,
                              timeout=1800, env=env)
        return {"returncode": proc.returncode, "stdout": proc.stdout or ""}

    # ------------------------------------------------------------------- build

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=self._cpp_dir())
        cmake.build()
        if not can_run(self):
            raise ConanException(
                "libgeocoding upstream tests require can_run (native OHOS aarch64); "
                "cross-compiled binaries cannot execute here")
        self._run_upstream_tests()
        cmake.install()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 上游原始测试输出随包携带：conan create 命中缓存时 build() 被跳过，
        # test_package 仍能重放真实的上游测试证据（不伪造 pass）。
        res_dir = os.path.join(self.package_folder, "res")
        for name in ("upstream_test_result.json", "upstream_test_cases.txt"):
            src = os.path.join(self.build_folder, name)
            if os.path.isfile(src):
                copy(self, name, src=self.build_folder, dst=res_dir)
            else:
                self.output.warning("%s missing in build folder; upstream evidence "
                                    "incomplete" % name)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libgeocoding")
        self.cpp_info.set_property("cmake_target_name", "libgeocoding::libgeocoding")
        # libgeocoding 引用 libphonenumber 的解析/元数据符号，两个归档必须同时链接。
        self.cpp_info.libs = ["geocoding", "phonenumber"]
        # protobuf/33.6 的 cpp_info 未导出 utf8_range/utf8_validity（静态闭包缺口），
        # 在此补齐，否则下游链接 libprotobuf.a 时报 utf8_range_IsValid 未定义。
        try:
            protobuf_libdir = os.path.join(
                self.dependencies["protobuf"].package_folder, "lib")
            if os.path.isdir(protobuf_libdir):
                self.cpp_info.libdirs.append(protobuf_libdir)
                self.cpp_info.libs.extend(["utf8_validity", "utf8_range"])
        except Exception:
            pass
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.extend(["pthread", "dl", "m"])
