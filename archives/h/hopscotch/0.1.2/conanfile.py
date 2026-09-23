#!/usr/bin/env python3
"""Conan recipe — hopscotch 0.1.2 (raw Makefile)."""

import hashlib
import os
import pathlib
import shlex
import shutil
import tarfile
import urllib.error
import urllib.request

from conan import ConanFile
from conan.tools.cmake import CMakeDeps, CMakeToolchain
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
)
from conan.tools.layout import basic_layout


class HopscotchConan(ConanFile):
    name = "hopscotch"
    version = "0.1.2"
    package_type = "library"
    license = "MIT"
    homepage = "https://github.com/silentbicycle/hopscotch"
    url = "https://github.com/silentbicycle/hopscotch"
    description = "A fast and compact hash table for C"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [False]}
    default_options = {"shared": False}
    exports_sources = (
        "test_package/CMakeLists.txt",
        "test_package/MANIFEST.yml",
        "test_package/conanfile.py",
        "test_package/test.c",
        "conandata.yml",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # The upstream build is a raw Makefile; its outputs are under the
        # source tree's build/ directory rather than Conan's build folder.
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"][self.version]
        raw_urls = source["url"]
        urls = raw_urls if isinstance(raw_urls, list) else [raw_urls]
        digest = source["sha256"]
        archive = pathlib.Path(self.source_folder).parent / "hopscotch.tar.gz"
        download_errors = []
        for candidate in urls:
            try:
                urllib.request.urlretrieve(str(candidate), archive)
                break
            except (OSError, ValueError, urllib.error.URLError) as exc:
                download_errors.append(f"{candidate}: {exc}")
                if archive.exists():
                    archive.unlink()
        else:
            raise RuntimeError(
                "unable to download hopscotch source from configured URLs: "
                + "; ".join(download_errors)
            )
        actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        if actual != digest:
            raise RuntimeError("hopscotch source SHA256 mismatch: %s" % actual)
        # Do not use Conan's extractor: the release contains a broken absolute link.
        with tarfile.open(archive, "r:gz") as tf:
            root = pathlib.Path(self.source_folder).resolve()
            for member in tf.getmembers():
                if member.issym() or member.islnk():
                    # The release link is absolute and broken; no link is needed to build.
                    continue
                destination = (root / member.name).resolve()
                if os.path.commonpath((str(root), str(destination))) != str(root):
                    raise RuntimeError("unsafe path in source archive: %s" % member.name)
                tf.extract(member, self.source_folder)
        root = pathlib.Path(self.source_folder) / "hopscotch-0.1.2"
        for item in root.iterdir():
            target = pathlib.Path(self.source_folder) / item.name
            if target.exists() or target.is_symlink():
                if target.is_dir() and not target.is_symlink():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            shutil.move(str(item), str(target))
        root.rmdir()
        archive.unlink()

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            # CMake 4.1 has no OHOS platform module; the native compiler is
            # Linux-compatible for this CMake consumer test.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.generate()

    def _conf(self, key, default):
        try:
            value = self.conf.get(key)
        except Exception:
            value = None
        return value or default

    def _tool(self, name, default):
        try:
            tools = self.conf.get("tools.build:compiler_executables") or {}
            if isinstance(tools, dict) and tools.get(name):
                return tools[name]
        except Exception:
            pass
        return self._conf("tools.build:compiler_executables.%s" % name, default)

    def build(self):
        apply_conandata_patches(self)
        cc = self._tool("c", "clang")
        ar = self._tool("ar", "llvm-ar")
        ranlib = self._tool("ranlib", "llvm-ranlib")
        cflags = self._conf("tools.build:cflags", "")
        command = "CC={} AR={} RANLIB={} ".format(
            shlex.quote(str(cc)), shlex.quote(str(ar)), shlex.quote(str(ranlib))
        )
        if cflags:
            command += "CFLAGS={} ".format(shlex.quote(str(cflags)))
        command += "make -j1"
        self.run(command, cwd=self.source_folder)

    def package(self):
        source_build = os.path.join(self.source_folder, "build")
        copy(self, "hopscotch.h", src=os.path.join(self.source_folder, "include"), dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "libhopscotch.a", src=source_build, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "hopscotch", src=source_build, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["hopscotch"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "hopscotch")
        self.cpp_info.set_property("cmake_target_name", "hopscotch::hopscotch")
        self.cpp_info.builddirs = []
