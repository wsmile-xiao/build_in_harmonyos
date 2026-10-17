#!/usr/bin/env python3
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class PamWrapperTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("linux-pam/1.7.2")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        dep = self.dependencies["pam-wrapper"]
        libdir = dep.cpp_info.libdirs[0] if dep.cpp_info.libdirs else "lib"
        if not os.path.isabs(libdir):
            libdir = os.path.join(dep.package_folder, libdir)

        linux_pam = self.dependencies["linux-pam"]
        linux_pam_include = linux_pam.cpp_info.includedirs[0]

        tc = CMakeToolchain(self)
        tc.variables["LINUX_PAM_INCLUDE_DIR"] = linux_pam_include
        tc.variables["PAM_WRAPPER_TEST_LIBRARY"] = os.path.join(
            libdir, "libpam_wrapper.so"
        ).replace("\\", "/")
        tc.generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["pam-wrapper"]
        libdir = dep.cpp_info.libdirs[0] if dep.cpp_info.libdirs else "lib"
        if not os.path.isabs(libdir):
            libdir = os.path.join(dep.package_folder, libdir)

        exe = os.path.join(self.cpp.build.bindirs[0], "test_pam_wrapper")
        runtime_dir = os.path.join(self.build_folder, "runtime")
        service_dir = os.path.join(self.build_folder, "services")
        os.makedirs(runtime_dir, exist_ok=True)
        os.makedirs(service_dir, exist_ok=True)

        matrix_module = os.path.join(libdir, "pam_wrapper", "pam_matrix.so").replace("\\", "/")
        passdb_path = os.path.join(service_dir, "passdb").replace("\\", "/")
        service_path = os.path.join(service_dir, "matrix")
        with open(os.path.join(service_dir, "passdb"), "w", encoding="utf-8") as passdb:
            passdb.write("trinity:secret:matrix\n")
        with open(service_path, "w", encoding="utf-8") as service:
            service.write("auth required {} passdb={}\n".format(matrix_module, passdb_path))

        library_paths = [libdir]
        for dependency in self.dependencies.values():
            for dependency_libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(dependency_libdir):
                    dependency_libdir = os.path.join(dependency.package_folder, dependency_libdir)
                if dependency_libdir not in library_paths:
                    library_paths.append(dependency_libdir)

        env = {
            "LD_PRELOAD": os.path.join(libdir, "libpam_wrapper.so"),
            "LD_LIBRARY_PATH": os.pathsep.join(library_paths),
            "PAM_WRAPPER": "1",
            "TMPDIR": runtime_dir,
            "PAM_WRAPPER_RUNTIME_DIR": runtime_dir,
            "PAM_WRAPPER_SERVICE_DIR": service_dir,
        }
        prefix = " ".join("{}={}".format(k, shlex.quote(v)) for k, v in env.items())
        self.run("{} {}".format(prefix, shlex.quote(exe)), env="conanrun")
