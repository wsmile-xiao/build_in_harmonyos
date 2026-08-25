import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class LibghthashConan(ConanFile):
    name = "libghthash"
    version = "0.6.2"
    package_type = "library"
    description = "Generic, extensible hash table for C for storing arbitrary data"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/SimonKagstrom/libghthash"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libghthash supports Linux and OHOS only")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS validation requires armv8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        src_sub = os.path.join(self.source_folder, "src")
        # ght_hash_table.h is generated from ght_hash_table.h.in by
        # substituting @INT32_T@ (configure picks int, which is 4 bytes
        # on all supported targets including aarch64).
        header_in = os.path.join(src_sub, "ght_hash_table.h.in")
        replace_in_file(self, header_in, "@INT32_T@", "int")
        shutil.copyfile(header_in, os.path.join(src_sub, "ght_hash_table.h"))

        cc = shutil.which(os.environ.get("CC", "cc")) or "clang"
        ar = shutil.which(os.environ.get("AR", "ar")) or "llvm-ar"
        cflags = f'-Wall -fPIC -O2 -I"{src_sub}"'
        if str(self.settings.build_type).lower() == "debug":
            cflags += " -g"
        else:
            cflags += " -DNDEBUG"

        objs = []
        for src in ("hash_table.c", "hash_functions.c"):
            obj = os.path.join(self.build_folder, src.replace(".c", ".o"))
            self.run(
                f'"{cc}" {cflags} -c "{os.path.join(src_sub, src)}" -o "{obj}"'
            )
            objs.append(obj)

        if self.options.shared:
            lib = os.path.join(self.build_folder, "libghthash.so")
            self.run(f'"{cc}" -shared {" ".join(objs)} -o "{lib}"')
        else:
            lib = os.path.join(self.build_folder, "libghthash.a")
            self.run(f'"{ar}" rcs "{lib}" {" ".join(objs)}')

    def package(self):
        copy(self, "ght_hash_table.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"))
        copy(self, "*.a", self.build_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "*.so", self.build_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["ghthash"]
        self.cpp_info.includedirs = ["include"]
