"""Kuroko 1.4.0 interpreter and embeddable C library for HarmonyOS PC."""

import os
import shlex

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class KurokoConan(ConanFile):
    name = "kuroko"
    version = "1.4.0"
    description = "Kuroko bytecode-compiled language and embeddable VM"
    homepage = "https://github.com/kuroko-lang/kuroko"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "MIT"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise RuntimeError("This recipe is verified for HarmonyOS PC AArch64 only")
        executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = shlex.quote(executables.get("c", "clang"))
        ar = shlex.quote(executables.get("ar", "llvm-ar"))
        self.run(f"make -j1 CC={cc} AR={ar} all", cwd=self.source_folder)
        # The release contains 148 .krk/.expect pairs. Do not replace them
        # with a smaller smoke test: upstream's own runner checks each diff.
        self.run("make -j1 test", cwd=self.source_folder)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        libdir = os.path.join(self.package_folder, "lib")
        copy(self, "kuroko", self.source_folder, bindir, keep_path=False)
        copy(self, "krk-*", self.source_folder, bindir, keep_path=False)
        for library in ("libkuroko.a", "libkuroko.so"):
            copy(self, library, self.source_folder, libdir, keep_path=False)
        copy(self, "*.h", os.path.join(self.source_folder, "src", "kuroko"),
             os.path.join(self.package_folder, "include", "kuroko"),
             keep_path=False)
        modules = os.path.join(self.source_folder, "modules")
        runtime = os.path.join(libdir, "kuroko")
        copy(self, "*.krk", modules, runtime, keep_path=True)
        copy(self, "*.so", modules, runtime, keep_path=True)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["kuroko"]
        self.cpp_info.system_libs = ["dl", "pthread"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        # Upstream's krk-* tools use $ORIGIN rather than $ORIGIN/../lib.
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
