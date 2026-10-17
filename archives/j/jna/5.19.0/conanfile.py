#!/usr/bin/env python3
"""Conan recipe for JNA 5.19.0 native component (libjnidispatch.so).

JNA (Java Native Access) is a Java library that provides Java programs
access to native shared libraries. This recipe builds the native C
component (libjnidispatch.so) which is the JNI bridge library.

Build process:
1. Install bishengjdk (for JNI headers and javac)
2. Modify Version.java (TEMPLATE -> 5.19.0)
3. Compile Java source and generate JNI headers (javac -h)
4. Build native component with make (using conan-managed libffi)
5. Package libjnidispatch.so
"""
import os
import subprocess
import urllib.request
import tarfile
import tempfile

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class JnaConan(ConanFile):
    name = "jna"
    version = "5.19.0"
    description = "Java Native Access — native JNI bridge library (libjnidispatch.so)"
    license = "Apache-2.0 / LGPL-2.1+"
    homepage = "https://github.com/java-native-access/jna"
    url = "https://github.com/java-native-access/jna"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libffi/3.5.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _install_jdk(self):
        """Install bishengjdk if not already available (pure Python, no shell)."""
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "javac")):
            return java_home

        # Check common installation path
        bishengjdk_path = os.path.join(os.path.expanduser("~"), "bishengjdk17")
        if os.path.isfile(os.path.join(bishengjdk_path, "bin", "javac")):
            return bishengjdk_path

        # Install bishengjdk via direct download (no shell, pure Python)
        self.output.info("Installing bishengjdk 17.0.13 (pure Python download)...")
        url = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
               "releases/download/pkgs/bishengjdk-17.0.13-ohos-aarch64.tar.gz")
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
        source_dir = self.source_folder

        # 1. Install JDK
        java_home = self._install_jdk()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, "bin") + ":" + os.environ.get("PATH", "")

        # 2. Modify Version.java
        version_file = os.path.join(source_dir, "src", "com", "sun", "jna", "Version.java")
        with open(version_file, "r") as f:
            content = f.read()
        content = content.replace('String VERSION = "TEMPLATE"', 'String VERSION = "5.19.0"')
        content = content.replace('String VERSION_NATIVE = "TEMPLATE"', 'String VERSION_NATIVE = "5.19.0"')
        with open(version_file, "w") as f:
            f.write(content)

        # 3. Compile Java source and generate JNI headers
        build_dir = os.path.join(source_dir, "build")
        native_build_dir = os.path.join(build_dir, "native")
        classes_dir = os.path.join(build_dir, "classes")
        os.makedirs(native_build_dir, exist_ok=True)
        os.makedirs(classes_dir, exist_ok=True)

        java_files = []
        for root, _, files in os.walk(os.path.join(source_dir, "src")):
            for f in files:
                if f.endswith(".java"):
                    java_files.append(os.path.join(root, f))

        self.output.info(f"Compiling {len(java_files)} Java source files...")
        subprocess.run(
            [
                os.path.join(java_home, "bin", "javac"),
                "-h", native_build_dir,
                "-d", classes_dir,
                "-sourcepath", os.path.join(source_dir, "src"),
            ] + java_files,
            check=True,
            cwd=source_dir,
        )

        # 4. Build native component
        native_dir = os.path.join(source_dir, "native")

        # Get libffi paths from conan
        libffi_info = self.dependencies["libffi"]
        libffi_root = libffi_info.package_folder
        libffi_include = os.path.join(libffi_root, "include")
        libffi_lib = os.path.join(libffi_root, "lib")

        # Get compiler from settings (R33: no bare env vars)
        cc = self.conf_info.get("tools.build:compiler_executables", {}).get("c", "clang")

        env = os.environ.copy()
        env["JAVA_HOME"] = java_home
        env["CC"] = cc

        self.output.info("Building native component (libjnidispatch.so)...")
        # Override LDFLAGS to set correct SONAME (not build path)
        subprocess.run(
            [
                "make",
                "OS=linux",
                "DYNAMIC_LIBFFI=true",
                f"CC={cc}",
                f"CFLAGS_EXTRA=-I{libffi_include} -DNO_JAWT",
                f"LIBS=-L{libffi_lib} -lffi",
                "LDFLAGS=-o $@ -shared -Wl,-soname,libjnidispatch.so",
            ],
            check=True,
            cwd=native_dir,
            env=env,
        )

    def package(self):
        # Copy libjnidispatch.so to lib/
        source_dir = self.source_folder
        native_build_dir = os.path.join(source_dir, "build", "native")
        copy(self, "libjnidispatch.so", native_build_dir,
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["jnidispatch"]
        self.cpp_info.includedirs = []
