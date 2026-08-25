import os
import shutil
import stat

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.layout import basic_layout


class LibghthashTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # Copy the built library + header into the test build folder so we
        # can compile/link directly without CMakeDeps toolchain indirection
        # (the OHOS profile carries no [conf] compiler_executables, which
        # makes CMake's compiler identification fail).
        deps = self.dependencies[self.tested_reference_str]
        agg = deps.cpp_info.aggregated_components()
        inc = agg.includedirs[0]
        lib = agg.libdirs[0]
        gen = self.generators_folder
        os.makedirs(os.path.join(gen, "include"), exist_ok=True)
        os.makedirs(os.path.join(gen, "lib"), exist_ok=True)
        copy(self, "ght_hash_table.h", inc, os.path.join(gen, "include"))
        for pattern in ("*.a", "*.so"):
            copy(self, pattern, lib, os.path.join(gen, "lib"))

    def build(self):
        cc = shutil.which(os.environ.get("CC", "clang")) or "clang"
        src = os.path.join(self.source_folder, "test_ght.c")
        bin_path = os.path.join(self.build_folder, "test_ght")
        gen = self.generators_folder
        cflags = f'-I"{os.path.join(gen, "include")}" -L"{os.path.join(gen, "lib")}"'
        if str(self.settings.build_type).lower() == "debug":
            cflags += " -g"
        self.run(f'"{cc}" {cflags} "{src}" -lghthash -o "{bin_path}"')

    def test(self):
        binary = os.path.join(self.build_folder, "test_ght")
        if str(self.settings.os) == "OHOS":
            files_dir = os.path.join(self.build_folder, "files")
            os.makedirs(files_dir, exist_ok=True)
            signed_binary = os.path.join(files_dir, "test_ght")
            shutil.copy2(binary, signed_binary)
            signer = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(signer):
                self.run(
                    f'{signer} sign -inFile "{signed_binary}" '
                    f'-outFile "{signed_binary}.signed" -selfSign 1'
                )
                os.replace(signed_binary + ".signed", signed_binary)
                os.chmod(
                    signed_binary,
                    os.stat(signed_binary).st_mode
                    | stat.S_IXUSR
                    | stat.S_IXGRP
                    | stat.S_IXOTH,
                )
            self.run(
                f'patchelf --set-rpath "$ORIGIN" "{signed_binary}"',
                ignore_errors=True,
            )
            binary = signed_binary
        self.run(f'"{binary}"', env="conanrun")
