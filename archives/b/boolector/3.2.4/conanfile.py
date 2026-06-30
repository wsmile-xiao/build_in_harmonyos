#!/usr/bin/env python3
"""Conan recipe for boolector 3.2.4 — CMake project (SMT solver for fixed-size bit-vectors).

Build system: cmake
License: MIT
Dependencies: bundled (Btor2Tools, CaDiCaL, Lingeling — downloaded and built in build())
R26: Static linking (BUILD_SHARED_LIBS=OFF)
E092: CMAKE_SYSTEM_NAME=Linux for HarmonyOS compatibility
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BoolectorConan(ConanFile):
    name = "boolector"
    version = "3.2.4"
    description = "SMT solver for fixed-size bit-vectors"
    license = "MIT"
    homepage = "https://github.com/Boolector/boolector"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # E092: CMake doesn't recognize HarmonyOS, force Linux
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Fix for cmake >= 4.0 with old cmake_minimum_required
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["TESTING"] = "OFF"
        tc.variables["USE_MINISAT"] = "OFF"
        tc.variables["USE_CMS"] = "OFF"
        tc.variables["USE_PICOSAT"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        src_dir = self.source_folder
        env = os.environ.copy()
        # Ensure SSL certs for GitHub downloads
        ssl_cert = "/storage/Users/currentUser/usr/local/ssl/cert.pem"
        if os.path.exists(ssl_cert):
            env["SSL_CERT_FILE"] = ssl_cert
            env["CURL_CA_BUNDLE"] = ssl_cert
        env["CXXFLAGS"] = "-fPIC"
        env["CFLAGS"] = "-fPIC"
        # E053: Use clang++ explicitly
        env["CC"] = env.get("CC", "clang")
        env["CXX"] = env.get("CXX", "clang++")

        deps_install = os.path.join(src_dir, "deps", "install")
        if not (os.path.exists(deps_install) and os.path.exists(os.path.join(deps_install, "lib", "libbtor2parser.a"))):
            self._build_deps(src_dir, env)

        cmake = CMake(self)
        # E103: Fix cmake_minimum_required for CMake 4.x compatibility
        main_cml = os.path.join(src_dir, "CMakeLists.txt")
        if os.path.exists(main_cml):
            replace_in_file(self, main_cml,
                            "cmake_minimum_required(VERSION 3.3)",
                            "cmake_minimum_required(VERSION 3.5)")
        cmake.configure()
        cmake.build()

    def _download_github(self, repo, version, location, env, tar_args=None):
        """Download a GitHub archive, with gh-proxy.com fallback."""
        parent = os.path.dirname(location)
        os.makedirs(parent, exist_ok=True)
        name = repo.split("/")[-1]
        archive = os.path.join(parent, f"{name}-{version}.tar.gz")
        url = f"https://github.com/{repo}/archive/{version}.tar.gz"
        mirror_url = f"https://gh-proxy.com/https://github.com/{repo}/archive/{version}.tar.gz"
        # Try direct first, then mirror
        try:
            subprocess.check_call(["curl", "-L", "--connect-timeout", "15", "-o", archive, url],
                                  cwd=parent, env=env, timeout=30)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            self.output.info(f"GitHub direct failed, using gh-proxy.com mirror...")
            subprocess.check_call(["curl", "-L", "--connect-timeout", "15", "-o", archive, mirror_url],
                                  cwd=parent, env=env, timeout=60)
        if os.path.exists(location):
            shutil.rmtree(location)
        tar_cmd = ["tar", "xfz", archive]
        if tar_args:
            tar_cmd.extend(tar_args.split())
        subprocess.check_call(tar_cmd, cwd=parent, env=env)
        os.remove(archive)
        extracted = os.path.join(parent, f"{name}-{version}")
        if os.path.exists(extracted):
            shutil.move(extracted, location)

    def _install_lib(self, src, dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
        if os.path.exists(src):
            shutil.copy2(src, dest_dir)

    def _install_include(self, src, dest_dir, subdir=None):
        d = dest_dir if not subdir else os.path.join(dest_dir, subdir)
        os.makedirs(d, exist_ok=True)
        if os.path.exists(src):
            shutil.copy2(src, d)

    def _build_deps(self, src_dir, env):
        """Build bundled dependencies: Btor2Tools, CaDiCaL, Lingeling."""
        deps_dir = os.path.join(src_dir, "deps")
        install_dir = os.path.join(deps_dir, "install")
        install_lib = os.path.join(install_dir, "lib")
        install_inc = os.path.join(install_dir, "include")
        os.makedirs(install_lib, exist_ok=True)
        os.makedirs(install_inc, exist_ok=True)

        # 1. Btor2Tools (cmake-based, needs policy version fix)
        btor2tools_dir = os.path.join(deps_dir, "btor2tools")
        btor2tools_commit = "037f1fa88fb439dca6f648ad48a3463256d69d8b"
        if not os.path.exists(btor2tools_dir):
            self.output.info("Downloading Btor2Tools...")
            self._download_github("boolector/btor2tools", btor2tools_commit, btor2tools_dir, env)

        btor2tools_build = os.path.join(btor2tools_dir, "build")
        os.makedirs(btor2tools_build, exist_ok=True)
        self.output.info("Building Btor2Tools...")
        subprocess.check_call(
            ["cmake", "..", "-DBUILD_SHARED_LIBS=OFF",
             "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
             "-DCMAKE_SYSTEM_NAME=Linux",
             "-DCMAKE_SYSTEM_PROCESSOR=aarch64"],
            cwd=btor2tools_build, env=env
        )
        subprocess.check_call(["make", "-j2"], cwd=btor2tools_build, env=env)
        self._install_lib(os.path.join(btor2tools_build, "lib", "libbtor2parser.a"), install_lib)
        self._install_include(os.path.join(btor2tools_dir, "src", "btor2parser", "btor2parser.h"), install_inc)

        # 2. CaDiCaL (configure-based)
        cadical_dir = os.path.join(deps_dir, "cadical")
        cadical_commit = "cb89cbfa16f47cb7bf1ec6ad9855e7b6d5203c18"
        if not os.path.exists(cadical_dir):
            self.output.info("Downloading CaDiCaL...")
            self._download_github("arminbiere/cadical", cadical_commit, cadical_dir, env)

        self.output.info("Building CaDiCaL...")
        subprocess.check_call(["./configure"], cwd=cadical_dir, env=env)
        subprocess.check_call(["make", "-j2"], cwd=cadical_dir, env=env)
        self._install_lib(os.path.join(cadical_dir, "build", "libcadical.a"), install_lib)
        self._install_include(os.path.join(cadical_dir, "src", "ccadical.h"), install_inc)

        # 3. Lingeling (configure-based)
        lingeling_dir = os.path.join(deps_dir, "lingeling")
        lingeling_commit = "7d5db72420b95ab356c98ca7f7a4681ed2c59c70"
        if not os.path.exists(lingeling_dir):
            self.output.info("Downloading Lingeling...")
            self._download_github("arminbiere/lingeling", lingeling_commit, lingeling_dir, env)

        self.output.info("Building Lingeling...")
        subprocess.check_call(["./configure.sh", "-fPIC"], cwd=lingeling_dir, env=env)
        subprocess.check_call(["make", "-j2"], cwd=lingeling_dir, env=env)
        self._install_lib(os.path.join(lingeling_dir, "liblgl.a"), install_lib)
        self._install_include(os.path.join(lingeling_dir, "lglib.h"), install_inc)

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Also install bundled dependency libraries
        src_dir = self.source_folder
        deps_lib = os.path.join(src_dir, "deps", "install", "lib")
        if os.path.exists(deps_lib):
            for f in os.listdir(deps_lib):
                if f.endswith(".a"):
                    copy(self, f, deps_lib, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["boolector", "btor2parser", "cadical", "lgl"]
        self.cpp_info.system_libs = ["pthread", "m", "c++"]
