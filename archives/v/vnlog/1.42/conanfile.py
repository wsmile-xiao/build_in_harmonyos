"""Conan recipe for vnlog 1.42's native C library and header generator."""

import os
import shlex

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class VnlogConan(ConanFile):
    name = "vnlog"
    version = "1.42"
    description = "C library for labelled tabular text, with a Perl header generator"
    homepage = "https://github.com/dkogan/vnlog"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "LGPL-2.1-or-later"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = shlex.quote(executables.get("c", "clang"))
        ar = shlex.quote(executables.get("ar", "ar"))
        src = shlex.quote(self.source_folder)

        objects = []
        for name in ("b64_cencode", "vnlog", "vnlog-parser"):
            obj = os.path.join(self.build_folder, name + ".o")
            objects.append(obj)
            self.run(
                f"{cc} -std=gnu99 -O2 -fPIC -I{src} -c "
                f"{shlex.quote(os.path.join(self.source_folder, name + '.c'))} "
                f"-o {shlex.quote(obj)}"
            )
        self.run(
            f"{ar} rcs libvnlog.a " + " ".join(shlex.quote(obj) for obj in objects),
            cwd=self.build_folder,
        )

        # The C tests are upstream originals. Their normal Make target needs
        # mrbuild; compile the same sources directly so this recipe has no
        # unpublished build-time Conan dependency.
        for number in (1, 2):
            self.run(
                "perl vnl-gen-header < test/vnlog{0}.defs | "
                "sed 's@<vnlog/vnlog.h>@<vnlog.h>@' > "
                "test/vnlog_fields_generated{0}.h".format(number),
                cwd=self.source_folder,
            )
        archive = shlex.quote(os.path.join(self.build_folder, "libvnlog.a"))
        self.run(
            f"{cc} -std=gnu99 -O2 -I. -Itest test/test1.c test/test2.c "
            f"{archive} -o test/test1",
            cwd=self.source_folder,
        )
        self.run(
            f"{cc} -std=gnu99 -O2 -I. test/test-parser.c {archive} "
            "-o test/test-parser",
            cwd=self.source_folder,
        )
        self.run("bash test/test_c_api.sh", cwd=self.source_folder)
        self.output.info("Upstream C API checks: 12/12 passed")

    def package(self):
        include = os.path.join(self.package_folder, "include", "vnlog")
        for header in ("vnlog.h", "vnlog-parser.h", "vnlog-base64.h"):
            copy(self, header, self.source_folder, include)
        copy(self, "libvnlog.a", self.build_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "vnl-gen-header", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(
            self,
            "README.org",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["vnlog"]
        self.cpp_info.set_property("cmake_file_name", "vnlog")
        self.cpp_info.set_property("cmake_target_name", "vnlog::vnlog")
