from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
import os


class LibpgQueryConan(ConanFile):
    name = "libpg_query"
    version = "18.0.0"
    description = "C library for accessing the PostgreSQL parser outside of the server environment"
    license = "PostgreSQL"
    homepage = "https://github.com/pganalyze/libpg_query"
    url = "https://github.com/pganalyze/libpg_query"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    # Upstream Makefile only has a static-library target (libpg_query.a); there is
    # no shared-library target, so no "shared" option is declared (avoids claiming
    # a shared artifact the recipe cannot produce).
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # make build only produces static library (libpg_query.a), skips examples/tests
        # CC from conan profile tools.build:compiler_executables
        compiler_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_execs.get("c", "")
        cc_flag = f"CC={cc}" if cc else ""
        self.run(f"make build {cc_flag}")

    def package(self):
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libpg_query.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["pg_query"]
        self.cpp_info.includedirs = ["include"]
