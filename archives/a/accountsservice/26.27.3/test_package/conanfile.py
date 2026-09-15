#!/usr/bin/env python3
"""Conan test_package — accountsservice 26.27.3 L1 test.

Compiles and runs a C program that calls the real libaccountsservice API
(act_user_manager_get_default / act_user_manager_get_type /
act_user_manager_no_service / act_user_manager_get_user_by_id /
act_user_is_loaded / act_user_get_password_hint / act_user_get_uid),
verifying headers, linking and runtime behaviour without requiring a
running accounts-daemon or D-Bus system bus. The no-daemon assertions also
cover the client-visible defaults that the OHOS libc fallback stubs
(shadow-password / utmpx accounting) must stay coherent with (R40).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class AccountsserviceTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # test source also uses glib-2.0 (g_print/g_free)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(self.cpp.build.bindirs[0], "test_accountsservice" + suffix)
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
