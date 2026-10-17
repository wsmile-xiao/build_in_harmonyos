#!/usr/bin/env python3
"""Conan recipe for THESIAS 3.1.1 — haplotype inference JNI library.

Upstream build is a plain Makefile producing:
  - libthesiaslib.so(.0): JNI shared library (Cephes numerics + THESIAS core)
  - thesias.jar: Swing GUI (GraficT main class)

Both require a JDK (jni.h for the JNI header, javac/jar for the GUI jar).
The device/worker has no system JDK, so build() bootstraps BiSheng JDK 17
from the cmd-pkgs release (pure Python, no shell) — same precedent as
archives/j/jna/5.19.0 (E084).

R33: the C compiler is taken from tools.build:compiler_executables (Conan
toolchain), never from bare shell env.
"""
import os
import subprocess
import tarfile
import tempfile
import urllib.request

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ThesiasConan(ConanFile):
    name = "thesias"
    version = "3.1.1"
    description = ("THESIAS haplotype inference JNI shared library "
                   "(libthesiaslib.so, Cephes numerical routines + THESIAS core)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/daissi/thesias"
    url = "https://github.com/daissi/thesias"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # no third-party dependencies: Cephes is bundled, JDK is self-bootstrapped

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _install_jdk(self):
        """Bootstrap BiSheng JDK 17 (jni.h / javac / jar), pure Python (E084 precedent)."""
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "javac")):
            return java_home

        bishengjdk_path = os.path.join(os.path.expanduser("~"), "bishengjdk17")
        if os.path.isfile(os.path.join(bishengjdk_path, "bin", "javac")):
            return bishengjdk_path

        url = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
               "releases/download/pkgs/bishengjdk-17.0.13-ohos-aarch64.tar.gz")
        self.output.info("Bootstrapping bishengjdk 17.0.13 (pure Python download)...")
        tmp = tempfile.mktemp(suffix=".tar.gz")
        urllib.request.urlretrieve(url, tmp)
        with tarfile.open(tmp, "r:gz") as tar:
            tar.extractall(os.path.expanduser("~"))
        os.unlink(tmp)

        if os.path.isfile(os.path.join(bishengjdk_path, "bin", "javac")):
            return bishengjdk_path
        raise Exception(f"JDK installation failed: javac not found at {bishengjdk_path}")

    def build(self):
        apply_conandata_patches(self)
        java_home = self._install_jdk()

        cc = (self.conf_info.get("tools.build:compiler_executables") or {}).get("c", "clang")
        src_dir = os.path.join(self.source_folder, "src")
        build_dir = self.build_folder

        # --- native: src/*.c -> libthesiaslib.so (upstream Makefile `libthesiaslib.so` rule) ---
        objects = []
        include_flags = [f"-I{os.path.join(java_home, 'include')}",
                         f"-I{os.path.join(java_home, 'include', 'linux')}"]
        for c_file in sorted(f for f in os.listdir(src_dir) if f.endswith(".c")):
            obj = os.path.join(build_dir, os.path.basename(c_file)[:-2] + ".o")
            subprocess.run([cc, "-O2", "-fPIC"] + include_flags +
                           ["-c", os.path.join(src_dir, c_file), "-o", obj],
                           check=True, cwd=build_dir)
            objects.append(obj)
        so_path = os.path.join(build_dir, "libthesiaslib.so")
        # SONAME must equal the packaged file name (libthesiaslib.so, no version
        # suffix) so consumers' DT_NEEDED resolves against the conan package file
        # (jna/libjnidispatch.so precedent, E084 family).
        subprocess.run([cc, "-shared", "-fPIC"] + objects + ["-o", so_path,
                       "-Wl,-soname,libthesiaslib.so"],
                       check=True, cwd=build_dir)

        # --- java GUI: thesias.jar (upstream Makefile `thesias.jar` rule) ---
        classes = os.path.join(build_dir, "class")
        os.makedirs(classes, exist_ok=True)
        java_dir = os.path.join(self.source_folder, "java")
        java_files = [os.path.join(java_dir, f) for f in sorted(os.listdir(java_dir))
                      if f.endswith(".java")]
        env = os.environ.copy()
        env["JAVA_HOME"] = java_home
        env["PATH"] = os.path.join(java_home, "bin") + os.pathsep + env.get("PATH", "")
        env["JAVA_TOOL_OPTIONS"] = "-Dfile.encoding=UTF8"
        subprocess.run([os.path.join(java_home, "bin", "javac"), "-d", classes] + java_files,
                       check=True, cwd=build_dir, env=env)
        jar_path = os.path.join(build_dir, "thesias.jar")
        subprocess.run([os.path.join(java_home, "bin", "jar"), "cfe", jar_path, "GraficT",
                        "-C", classes, ".",
                        "-C", os.path.join(self.source_folder, "misc"), "LogoThesias.png"],
                       check=True, cwd=build_dir, env=env)

    def package(self):
        copy(self, "libthesiaslib.so", self.build_folder,
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "thesiaslib.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "thesias.jar", self.build_folder,
             os.path.join(self.package_folder, "res"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["thesiaslib"]
