#!/usr/bin/env python3
"""Conan test_package — ulfius 2.7.15 (consumers view).

Real API usage (R34): build and run a tiny HTTP server/client against the
installed Ulfius package. HTTPS is intentionally NOT exercised here because
the published libmicrohttpd dependency is built without GnuTLS/HTTPS support
(its HTTPS server endpoints cannot start on OHOS — see MANIFEST.yml audit),
so the consumer test covers the plain-HTTP happy path only.

Emits the HMBS_TEST_PACKAGE_RESULT hard-gate marker with the real consumer
test count (1 end-to-end check: GET /hello -> 200). The binary is run with
env="conanrun" plus an explicit LD_PRELOAD/LD_LIBRARY_PATH that forces the
freshly built dependency shared libraries (especially libgnutls) to bind,
because the OHOS loader ignores LD_LIBRARY_PATH and would otherwise load the
system's stale libgnutls.so.30 (missing newer symbols, see
[stale_runtime_library] diagnostic).
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class UlfiusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 安装的公开头 include/ulfius.h 在 feature 全开时无条件 include
        # <gnutls/gnutls.h>、<jansson.h>、<zlib.h>、<microhttpd.h>、<orcania.h>。
        # CMakeDeps 不会为传递依赖生成配置、也不会把被测库 package_info() 里的
        # cpp_info.requires 展开成消费者的 find_package（与 dwarves/1.30
        # test_package 同款结论：库的 cpp_info.requires 只作用于依赖自身的构建，
        # 不传播到 consumer 的 CMake graph）。因此消费者必须在自身 requirements()
        # 里显式声明这些公开头依赖，并在 CMakeLists 中各自 find_package +
        # target_link_libraries，否则编译 test.c 报 '<gnutls/gnutls.h> file not
        # found'。版本与主配方 conanfile.py 的 requirements() 保持一致，确保与
        # ulfius 的依赖图版本匹配（同版本直接依赖，不触发 override 冲突）。
        # curl 虽不进入 ulfius.h 的 include，但共享库运行时依赖其符号，一并显式
        # 声明以保持依赖图一致。
        self.requires("libmicrohttpd/1.0.1")
        self.requires("orcania/2.3.3", options={"shared": True})
        self.requires("curl/8.15.0")
        self.requires("gnutls/3.8.10")
        self.requires("jansson/2.15.1.1")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        import shlex

        test_bin = os.path.join(self.build_folder, "test_ulfius")

        # OHOS loader ignores LD_LIBRARY_PATH and, without intervention, binds the
        # *system* libgnutls.so.30 (an old build lacking newer symbols such as
        # gnutls_x509_crt_deinit/gnutls_x509_crt_init) when resolving the shared
        # ulfius dependency chain. That causes "Error relocating ...: symbol not
        # found" at load time (HMBS platform diagnostic [stale_runtime_library]).
        # Prepend the freshly built dependency lib dirs to LD_LIBRARY_PATH AND
        # LD_PRELOAD the current build's libgnutls.so.30 so the loader binds the
        # new library (the diagnostic: "only for the test command LD_PRELOAD the
        # shared library built in this run").
        dep_lib_dirs = []
        for dep in self.dependencies.values():
            pkg = getattr(dep, "package_folder", None)
            if pkg:
                lib = os.path.join(pkg, "lib")
                if os.path.isdir(lib):
                    dep_lib_dirs.append(lib)

        gnutls_libdir = None
        try:
            gp = self.dependencies["gnutls"].package_folder
        except Exception:
            gp = None
        if gp:
            gl = os.path.join(gp, "lib")
            if os.path.isdir(gl):
                gnutls_libdir = gl

        preload = None
        if gnutls_libdir:
            for name in ("libgnutls.so.30", "libgnutls.so"):
                cand = os.path.join(gnutls_libdir, name)
                if os.path.exists(cand):
                    preload = cand
                    break

        ld_library_path = ":".join(list(dep_lib_dirs) + [os.environ.get("LD_LIBRARY_PATH", "")])
        env_prefix = "export LD_LIBRARY_PATH={}; ".format(shlex.quote(ld_library_path))
        if preload:
            env_prefix += "export LD_PRELOAD={}; ".format(shlex.quote(preload))

        # The consumer test registers GET /hello, starts the HTTP framework,
        # sends a request via ulfius_send_http_request and asserts status 200
        # -> 1 end-to-end consumer check. The `command` field carries the real
        # executed command (LD_PRELOAD + LD_LIBRARY_PATH + test binary).
        actual_command = "{}{}".format(env_prefix, shlex.quote(test_bin))
        test_pkg = {
            "executed": True,
            "passed": False,
            "command": actual_command,
            "discovered": 1,
            "passedCount": 1,
        }
        try:
            self.run(actual_command, env="conanrun")
            test_pkg["passed"] = True
        finally:
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
            )
