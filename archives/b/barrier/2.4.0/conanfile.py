#!/usr/bin/env python3
"""Conan recipe for barrier 2.4.0 on HarmonyOS PC (OHOS armv8).

barrier — open-source KVM (keyboard/video/mouse) shared input, forked from
Symless Synergy 1.9.  CMake build; GUI requires Qt5.

OHOS-specific adaptations (see notes.md, P1-P9):
  P1: cmake_minimum_required(VERSION 3.4) collides with CMake 4 (removed
      <3.5 support).  Fixed by forcing -DCMAKE_POLICY_VERSION_MINIMUM=3.5
      (no source patch needed).
  P3: the OHOS conan toolchain sets CMAKE_SYSTEM_NAME=HarmonyOS, but CMake
      has no HarmonyOS platform module so `UNIX` is empty and every
      `if (UNIX)` branch in the upstream CMake is skipped -> the X11/curl/
      pthread detection and the XWindows platform glob all fail.  We force
      CMAKE_SYSTEM_NAME=Linux so the upstream Linux branches trigger.
  P4: upstream calls pkg_check_modules(AVAHI_COMPAT REQUIRED avahi-compat-libdns_sd),
      but the conan avahi package exposes a CMake target and no .pc; the
      conan-generated CMakeDeps target is used (patched in 0001).
  P8: upstream detects the X11 headers through module-mode
      check_include_files("X11/extensions/XTest.h" ...), which does not
      search the conan package include dirs by default.  We inject the deps'
      include dirs into CMAKE_REQUIRED_INCLUDES/CMAKE_INCLUDE_PATH.
  P2: the tarball ships EMPTY ext/gtest, ext/gmock and ext/gulrak-filesystem
      git submodules, but cmake/gtest.cmake unconditionally includes
      ../ext/gtest/src/gtest-all.cc, and io/filesystem.h includes
      <ghc/fs_fwd.hpp>.  We vendor those sources from conandata and unpack
      them under ext/ in source().
  P7: qt5-qtbase/5.15.2 was built against zlib/1.3.1 while libcurl/8.5.0
      needed zlib/1.3.1.1.  We keep zlib/1.3.1 (so the prebuilt qt5 binary is
      reusable) and build libcurl STATIC+fPIC so it links the non-PIC zlib
      without a relocation error.
"""
import os
import re
import json
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class BarrierConan(ConanFile):
    name = "barrier"
    version = "2.4.0"
    description = "Open-source KVM (keyboard/mouse) shared-input software"
    license = "GPL-2.0"
    homepage = "https://github.com/debauchee/barrier"
    url = "https://github.com/debauchee/barrier"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "gui": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "gui": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"barrier supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # CLI core (barriers/barrierc) is the primary deliverable.  The Qt5
        # GUI is documented as a separate known limitation (see notes.md):
        #   - qt5-qtbase/5.15.2 (OHOS binary on ohpcd) was built -no-widgets,
        #     so it exposes no Qt5::Widgets that the GUI links against.
        #   - qt5-qtbase/5.15.2.2 exposes Qt5::Widgets but its published binary
        #     does not match our dependency graph's expat/dbus resolution, and
        #     building Qt from source requires the cmake/4.4.2 tool_requires,
        #     whose recipe source() cannot build for OHOS (KeyError: 'OHOS').
        # P7: static+fPIC so libcurl links the non-PIC zlib without
        # R_AARCH64_ADR_PREL_PG_HI21 relocation errors.
        self.requires("libcurl/8.5.0", options={"shared": False, "fPIC": True})
        self.requires("openssl/1.1.1w")
        self.requires("libxtst/6.1.0")
        self.requires("libx11/6.4.0")          # X11 族与 libxtst/libxext/libxi 对齐 6.4.Z
        self.requires("libxi/6.1.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload URLs end in the tag (e.g. /v2.4.0) with no archive extension,
        # so conan's get() cannot infer the format -> pass filename explicitly.
        # NOTE: pull url/sha256 explicitly instead of **-expanding the dict,
        # because conandata may carry an empty `destination` (conan-verify
        # restores a backup copy) which get() would choke on ('': no such file).
        bar = self.conan_data["sources"]["barrier"]
        get(self, url=bar["url"], sha256=bar["sha256"],
            filename="barrier-2.4.0.tar.gz", strip_root=True)
        # P2: vendor the git-submodule sources that the tarball leaves empty.
        # NOTE: destination is passed here (not in conandata) to avoid a
        # duplicate-kwarg clash with the **-expansion above, and to a path that
        # makes sense after strip_root (filesystem-master/* -> ext/gulrak-...).
        gul = self.conan_data["sources"]["gulrak"]
        get(self, url=gul["url"], sha256=gul["sha256"],
            filename="gulrak-filesystem.tar.gz",
            destination="ext/gulrak-filesystem", strip_root=True)
        gts = self.conan_data["sources"]["googletest"]
        get(self, url=gts["url"], sha256=gts["sha256"],
            filename="googletest.tar.gz",
            destination="ext", strip_root=True)
        # googletest ships googletest/ and googlemock/; copy to ext/gtest and
        # ext/gmock as the upstream cmake/gtest.cmake expect.
        self._stage_googletest()

    def _stage_googletest(self):
        src = self.source_folder
        # source() unpacks googletest into ext/googletest + ext/googlemock
        # (strip_root=True leaves the inner dirs directly under ext/)
        # Googletest now lives under ext/{googletest,googlemock}; merge it
        # into the ALREADY-EXISTING ext/gtest / ext/gmock dirs that the
        # barrier tarball ships empty (empty git-submodule placeholders).
        # NOTE: copy(*, src, dst) copies the glob contents into dst; dst
        # must already exist, so do not gate on `not os.path.isdir(t)`.
        for submod, target in (("googletest", "ext/gtest"), ("googlemock", "ext/gmock")):
            s = os.path.join(src, "ext", submod)
            t = os.path.join(src, target)
            if os.path.isdir(s):
                os.makedirs(t, exist_ok=True)
                copy(self, "*", src=s, dst=t)
                import shutil
                shutil.rmtree(s)

    def generate(self):
        deps = CMakeDeps(self)
        # P5: qt5-qtbase ships per-module cmake configs (Qt5Core/Qt5Network/…)
        # but no aggregate Qt5Config; find_package(Qt5 COMPONENTS …) in the
        # GUI needs one, so CMakeDeps regenerates a clean Qt5 package.
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # P1: CMake 4 removed <3.5 support; the project asks for 3.4.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # P3: force the upstream Linux CMake branches.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # barrier option knobs.
        tc.variables["BARRIER_BUILD_GUI"] = "ON" if self.options.gui else "OFF"
        tc.variables["BARRIER_BUILD_INSTALLER"] = "OFF"
        tc.variables["BARRIER_BUILD_TESTS"] = "ON"
        tc.variables["BARRIER_USE_EXTERNAL_GTEST"] = "OFF"
        tc.variables["BARRIER_REVISION"] = "00000000"
        tc.variables["BARRIER_VERSION_STAGE"] = "release"
        # P8: let the module-mode check_include_files() see the conan include
        # dirs for X11/xtst/avahi.  CMakeDeps exposes includedirs per dep.
        inc = []
        for dep in self.dependencies.values():
            for inc_dir in dep.cpp_info.includedirs:
                abs_inc = os.path.join(dep.package_folder, inc_dir)
                inc.append(abs_inc)
        # dns_sd.h is shipped inside <avahi>/include/avahi-compat-libdns_sd/;
        # pkg-config would expose that via -I, so add the subdir explicitly so
        # upstream's check_include_files("dns_sd.h") succeeds.  Only when the
        # dep is present (GUI=OFF drops avahi; conan's dependencies.get() raises
        # KeyError for a missing ref rather than returning None).
        if "avahi-compat-libdns_sd" in self.dependencies:
            av = self.dependencies["avahi-compat-libdns_sd"]
            sub = os.path.join(av.package_folder, "include", "avahi-compat-libdns_sd")
            if os.path.isdir(sub):
                inc.append(sub)
        tc.variables["CMAKE_REQUIRED_INCLUDES"] = ";".join(inc)
        tc.variables["CMAKE_INCLUDE_PATH"] = ";".join(inc)
        # P8 (libs): barrier checks libraries via module-mode
        # check_library_exists("Xtst;Xext;X11" ...) which searches
        # CMAKE_LIBRARY_PATH; expose the conan lib dirs too.
        libs = []
        for dep in self.dependencies.values():
            for lib_dir in dep.cpp_info.libdirs:
                abs_lib = os.path.join(dep.package_folder, lib_dir)
                libs.append(abs_lib)
        tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(libs)
        # barrier links bare library names (Xtst/X11/ssl/crypto etc.) and
        # runs module-mode check_include_files / check_library_exists.
        # CMAKE_REQUIRED_INCLUDES + CMAKE_LIBRARY_PATH (set above) let those
        # probes find the conan headers/libs; do NOT pre-set HAVE_* so CMake
        # probes naturally (pre-setting would enable includes for headers we
        # don't actually have, e.g. Xinerama.h without libxinerama).
        link_flags = " ".join(f"-L{p}" for p in libs)
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = link_flags
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = link_flags
        tc.variables["CMAKE_MODULE_LINKER_FLAGS"] = link_flags
        # barrier's non-Apple/Linux branches add openssl/ssl/crypto etc. to
        # `libs` (link) but never add the dependency include dirs to the
        # actual target compile, so headers like <openssl/ossl_typ.h> are not
        # found.  Add the conan include dirs as -I to the compiler flags.
        inc_flags = " ".join(f"-I{p}" for p in inc)
        # _INIT forms are applied at project() init (after the toolchain
        # file) and are the mechanism for adding flags via a toolchain file.
        tc.variables["CMAKE_C_FLAGS_INIT"] = inc_flags
        tc.variables["CMAKE_CXX_FLAGS_INIT"] = inc_flags
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # ── 上游官方 GTest 单测（层1）──
        # barrier 的 unittests/integtests 目标未通过 add_test 注册（上游如此），
        # 故 ctest 发现不了它们。直接在 build() 里运行 unittests 可执行文件，
        # 并输出 HMBS_UPSTREAM_TEST_RESULT 标记（hmbs preflight 门禁据此收集）。
        # 仅当本机可执行 OHOS 目标二进制时才运行（交叉编译时 can_run 为 False）。
        if can_run(self):
            try:
                unittest_bin = os.path.join(self.build_folder, "bin", "unittests")
                if not os.path.isfile(unittest_bin):
                    self.output.warning("  unittests 未找到，跳过上游单测")
                else:
                    # 测试二进制动态链接 conan host 依赖库（libXtst/libX11/libXext/
                    # libXi/libc++_shared...），须把它们加入运行时搜索路径，否则
                    # 加载失败。参照 osm2pgsql 的做法重建 conanrun 运行时环境。
                    run_env = os.environ.copy()
                    lib_dirs = []
                    for dep in self.dependencies.host.values():
                        libdir = os.path.join(dep.package_folder, "lib")
                        if os.path.isdir(libdir):
                            lib_dirs.append(libdir)
                    run_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                        lib_dirs
                        + ([run_env["LD_LIBRARY_PATH"]] if run_env.get("LD_LIBRARY_PATH") else [])
                    )
                    proc = subprocess.run(
                        [unittest_bin], cwd=self.build_folder,
                        env=run_env, capture_output=True, text=True, timeout=1800)
                    rc = proc.returncode
                    raw = (proc.stdout or "") + (proc.stderr or "")
                    print(raw, end="", flush=True)

                    # 解析 gtest 汇总；若无解析证据用 0（诚实状态，绝不伪造通过）
                    total = passed = failed = 0
                    m = re.search(r"\[  PASSED  \]\s*(\d+)\s+tests", raw)
                    if m:
                        passed = int(m.group(1))
                    mf = re.search(r"\[  FAILED  \]\s*(\d+)\s+tests", raw)
                    if mf:
                        failed = int(mf.group(1))
                    m2 = re.search(r"\[==========\]\s*(\d+)\s+tests\s+from", raw)
                    if m2:
                        total = int(m2.group(1))
                    status = "passed" if (total > 0 and failed == 0 and rc == 0) else "failed"
                    marker = {
                        "status": status,
                        "framework": "gtest",
                        "command": os.path.basename(unittest_bin),
                        "discovered": total,
                        "executed": passed + failed,
                        "passed": passed,
                        "failed": failed,
                        "skipped": 0,
                    }
                    # flush=True 直达 stdout：Conan build 阶段可能不落日志，必须绕过缓冲
                    print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(marker)}", flush=True)
                    if rc != 0:
                        raise ConanException(f"上游 unittests 套件失败 (exit {rc})")
            except ConanException:
                raise
            except Exception as exc:
                raise ConanException(f"unittests 运行失败: {exc}")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # barrier is an application; expose the CLI binaries to consumers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
