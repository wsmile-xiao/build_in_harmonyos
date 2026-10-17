#!/usr/bin/env python3
"""Conan recipe for libatomic-queue 1.7.2 — header-only C++ lock-free queues.

The library ships as headers under include/atomic_queue/ (atomic_queue.h,
atomic_queue_mutex.h, barrier.h, defs.h, spinlock.h). No runtime library is
produced.

Upstream ships a Boost.Test suite (src/tests.cc, 12 BOOST_AUTO_TEST_CASE cases).
It is compiled and executed here, so `conan create` really runs the upstream
tests. The ohpcd boost package ships headers but no compiled
`unit_test_framework` component, so the upstream source (unmodified) is built
against Boost.Test's header-only entry point via a shim include directory:
<boost/test/unit_test.hpp> -> <boost/test/included/unit_test.hpp>.
test_package additionally exercises the public API from a consumer.
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LibAtomicQueueConan(ConanFile):
    name = "libatomic-queue"
    version = "1.7.2"
    description = "C++14 lock-free concurrent queue library (header-only)"
    license = "MIT"
    homepage = "https://github.com/max0x7ba/atomic_queue"
    url = "https://github.com/max0x7ba/atomic_queue"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # Boost headers only (Boost.Test header-only mode). Used to build and
        # run the upstream test suite during `conan create`; never propagated
        # to consumers.
        self.test_requires("boost/1.84.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _boost_include(self):
        for setname in ("test", "build", "host"):
            deps = getattr(self.dependencies, setname, None)
            if deps is None:
                continue
            try:
                dep = deps["boost"]
            except Exception:
                continue
            return os.path.join(dep.package_folder, "include")
        raise RuntimeError("boost test_requires not found in dependency sets")

    def build(self):
        apply_conandata_patches(self)
        boost_inc = self._boost_include()

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = str(executables.get("cpp") or "clang++")
        opt = "-O2" if self.settings.build_type == "Release" else "-g -O0"

        tests_bin = os.path.join(self.build_folder, "atomic_queue_tests")
        tests_src = os.path.join(self.source_folder, "src", "tests.cc")
        inc = os.path.join(self.source_folder, "include")
        # Boost.Test header-only mode for the unmodified upstream tests.cc:
        # pre-include the header-only entry point (which also provides main)
        # and set BOOST_TEST_MODULE on the command line, since tests.cc's own
        # #define happens after the pre-include.
        self.run(
            f'{cxx} -std=c++14 {opt} -pthread '
            f'-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE '
            f'-DBOOST_TEST_MODULE=atomic_queue '
            f'-include boost/test/included/unit_test.hpp '
            f'-I "{boost_inc}" -I "{inc}" '
            f'"{tests_src}" -o "{tests_bin}"'
        )
        # Run the upstream Boost.Test suite (12 cases); non-zero exit = failure.
        self.run(f'"{tests_bin}" --log_level=test_suite --report_level=detailed')

    def package(self):
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include", "atomic_queue"),
             dst=os.path.join(self.package_folder, "include", "atomic_queue"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "atomic_queue")
        self.cpp_info.set_property("cmake_target_name", "atomic_queue::atomic_queue")
