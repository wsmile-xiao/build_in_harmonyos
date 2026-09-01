#!/usr/bin/env python3
"""Conan recipe for sqlite-vec — A vector search SQLite extension.

Build system: Makefile (manual compilation).
Uses direct clang commands for precise NEON SIMD control on OHOS arm64.
"""
import os
from datetime import datetime

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class SqliteVecConan(ConanFile):
    name = "sqlite-vec"
    version = "0.1.9"
    description = "A vector search SQLite extension that runs anywhere"
    license = "Apache-2.0"
    homepage = "https://github.com/asg017/sqlite-vec"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sqlite3/3.49.1")

    def validate(self):
        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)

        # Create vendor/ dir with SQLite headers from conan dependency
        vendor_dir = os.path.join(self.build_folder, "vendor")
        os.makedirs(vendor_dir, exist_ok=True)
        dep = self.dependencies["sqlite3"]
        pf = getattr(dep, "package_folder", None) or ""
        for inc in dep.cpp_info.includedirs:
            inc_abs = os.path.join(pf, inc) if pf else inc
            for header in ("sqlite3.h", "sqlite3ext.h"):
                src = os.path.join(inc_abs, header)
                if os.path.exists(src):
                    copy(self, header, inc_abs, vendor_dir)

        # Generate sqlite-vec.h from template (pure Python, no envsubst dependency)
        template_vars = {
            "VERSION": "0.1.9",
            "DATE": datetime.utcnow().strftime("%FT%TZ%z"),
            "SOURCE": "unknown",
            "VERSION_MAJOR": "0",
            "VERSION_MINOR": "1",
            "VERSION_PATCH": "9",
        }
        with open(os.path.join(self.build_folder, "sqlite-vec.h.tmpl")) as f:
            template = f.read()
        result = template
        # Sort by key length descending to avoid partial matches
        # (e.g. ${VERSION} must not match inside ${VERSION_MAJOR})
        for k in sorted(template_vars, key=len, reverse=True):
            result = result.replace("${" + k + "}", template_vars[k])
        with open(os.path.join(self.build_folder, "sqlite-vec.h"), "w") as f:
            f.write(result)

        cflags = self._get_cflags()

        if not self.options.shared:
            # Static library: libsqlite_vec0.a
            self.run(f"clang -Ivendor/ {cflags} -DSQLITE_CORE -DSQLITE_VEC_STATIC "
                     f"-DSQLITE_VEC_ENABLE_NEON -c sqlite-vec.c -o vec.o")
            self.run("llvm-ar rcs libsqlite_vec0.a vec.o")
        else:
            # Loadable extension: vec0.so
            self.run(f"clang -fPIC -shared -Ivendor/ {cflags} "
                     f"-DSQLITE_VEC_ENABLE_NEON -lm sqlite-vec.c -o vec0.so")

    def _get_cflags(self):
        flags = ["-fPIC", "-O2"]
        if self.settings.build_type == "Debug":
            flags = ["-fPIC", "-g"]
        return " ".join(flags)

    def package(self):
        if not self.options.shared:
            copy(self, "libsqlite_vec0.a", src=".",
                 dst=os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "vec0.so", src=".",
                 dst=os.path.join(self.package_folder, "lib"))
        copy(self, "sqlite-vec.h", src=".",
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        if not self.options.shared:
            self.cpp_info.libs = ["sqlite_vec0"]
        else:
            self.cpp_info.libs = ["vec0"]
        self.cpp_info.includedirs = ["include"]
        # Declare transitive dependency so consumers get sqlite3 headers
        self.cpp_info.requires = ["sqlite3::sqlite3"]
