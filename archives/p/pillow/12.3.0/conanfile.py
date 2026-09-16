#!/usr/bin/env python3
"""Conan recipe for Pillow 12.3.0 as a Python extension package."""
import os
import sys
import sysconfig

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PillowConan(ConanFile):
    name = "pillow"
    version = "12.3.0"
    description = "Python Imaging Library fork with native image codecs"
    license = "MIT-CMU"
    homepage = "https://python-pillow.github.io"
    url = "https://github.com/python-pillow/Pillow"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {
        "shared": False,
        "libjpeg-turbo/*:shared": True,
    }

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("libjpeg-turbo/3.0.4")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _site_packages(self, root):
        return os.path.join(root, "lib", "python3.12", "site-packages")

    def _dependency_environment(self):
        env = Environment()
        include_dirs = []
        library_dirs = []
        for dep_name in ("zlib", "libjpeg-turbo"):
            dep = self.dependencies[dep_name]
            include_dirs.extend(
                os.path.join(dep.package_folder, path or "include")
                for path in (dep.cpp_info.includedirs or ["include"])
            )
            library_dirs.extend(
                os.path.join(dep.package_folder, path or "lib")
                for path in (dep.cpp_info.libdirs or ["lib"])
            )
        python_libdir = sysconfig.get_config_var("LIBDIR")
        python_library = sysconfig.get_config_var("LDLIBRARY") or "libpython3.12.so"
        python_name = python_library.removeprefix("lib").split(".so", 1)[0]
        include_flags = " ".join(f"-I{path}" for path in include_dirs)
        library_flags = " ".join(f"-L{path}" for path in library_dirs)
        # The OHOS HNP toolchain lives outside the worker PATH, so the build is
        # pointed at its clang/llvm binaries explicitly.
        env.define("CC", "/data/service/hnp/bin/clang")
        env.define("CXX", "/data/service/hnp/bin/clang++")
        env.define("AR", "/data/service/hnp/bin/llvm-ar")
        env.define("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
        env.define("CFLAGS", include_flags)
        env.define("CPPFLAGS", include_flags)
        env.define("LDFLAGS", f"{library_flags} -L{python_libdir} -l{python_name}")
        return env

    def generate(self):
        self._dependency_environment().vars(self).save_script("pillow-deps")
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        package_dir = os.path.join(self.build_folder, "site-packages")
        os.makedirs(package_dir, exist_ok=True)
        build_tools = os.path.join(self.build_folder, "build-tools")
        os.makedirs(build_tools, exist_ok=True)
        self.run(
            f'"{sys.executable}" -m pip install --disable-pip-version-check '
            f'--no-input --no-deps --target "{build_tools}" "setuptools>=77"',
            cwd=self.source_folder,
            env=["conanbuild", "pillow-deps"],
        )
        build_env = Environment()
        build_env.define("PYTHONPATH", build_tools)
        build_env.vars(self).save_script("pillow-python-tools")
        self.run(
            f'PYTHONPATH="{build_tools}" "{sys.executable}" setup.py bdist_wheel '
            f'--dist-dir "{package_dir}"',
            cwd=self.source_folder,
            env=["conanbuild", "pillow-deps", "pillow-python-tools"],
        )
        wheels = [name for name in os.listdir(package_dir) if name.endswith(".whl")]
        if not wheels:
            raise ConanException("Pillow setup.py did not produce a wheel")
        self.run(
            f'"{sys.executable}" -m pip install --no-deps --no-index '
            f'--target "{package_dir}" "{os.path.join(package_dir, wheels[0])}"',
            cwd=self.source_folder,
            env=["conanbuild", "pillow-deps"],
        )
        for root, _dirs, files in os.walk(package_dir):
            for filename in files:
                if filename.endswith(".so"):
                    os.chmod(os.path.join(root, filename), 0o755)
        if self.settings.os == "OHOS":
            self._sign_extensions(package_dir)

    def _sign_extensions(self, site_dir):
        """Signs every compiled extension in place.

        OHOS refuses to load shared objects that carry no valid signature, so
        each Pillow extension has to be signed with the SDK signing tool.  The
        signature is created while the extension still lives in the build
        folder: signing the copy that Conan already moved into the package
        cache produces a tool-successful signature that the OHOS Python loader
        rejects from dlopen (same constraint as aggdraw/1.4.1).
        """
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool) or not os.path.isfile(objcopy):
            raise ConanInvalidConfiguration(
                "OHOS binary signing tools are required for the Pillow extensions"
            )
        signed = 0
        for root, _dirs, files in os.walk(site_dir):
            for filename in files:
                if not filename.endswith(".so"):
                    continue
                extension = os.path.join(root, filename)
                # Drop any pre-existing .codesign section so re-signing stays
                # idempotent; unsigned extensions have none, and objcopy then
                # reports nothing to remove, which is expected.
                self.run(
                    f'"{objcopy}" --remove-section .codesign "{extension}" '
                    f'2>/dev/null || true'
                )
                self.run(
                    f'"{sign_tool}" sign -inFile "{extension}" '
                    f'-outFile "{extension}" -selfSign 1'
                )
                os.chmod(extension, 0o755)
                signed += 1
        if not signed:
            raise ConanException("the Pillow build produced no native extension to sign")
        self.output.info(f"signed {signed} Pillow native extension(s)")

    def package(self):
        package_dir = os.path.join(self.build_folder, "site-packages")
        if not os.path.isdir(os.path.join(package_dir, "PIL")):
            raise ConanException("Pillow installation did not produce a PIL package")
        package_site = self._site_packages(self.package_folder)
        copy(self, "*", src=package_dir, dst=package_site)
        for root, _dirs, files in os.walk(package_site):
            for filename in files:
                if filename.endswith(".so"):
                    os.chmod(os.path.join(root, filename), 0o755)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("python_package", "PIL")
        self.runenv_info.define_path("PILLOW_SITE_PACKAGES", self._site_packages(self.package_folder))
