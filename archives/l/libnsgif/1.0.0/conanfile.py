from conan import ConanFile
from conan.tools.files import get, copy
import os
import shlex


class LibnsgifConan(ConanFile):
    name = "libnsgif"
    version = "1.0.0"
    license = "MIT"
    homepage = "https://www.netsurf-browser.org/projects/libnsgif/"
    description = "NetSurf GIF decoding library"
    topics = ("gif", "decoder", "netsurf")

    settings = "os", "arch", "compiler", "build_type"
    package_type = "static-library"

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
        )

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        return compilers.get("c", "clang")

    def _archiver(self):
        cc = self._compiler()
        bindir = os.path.dirname(cc)
        if bindir:
            return os.path.join(bindir, "llvm-ar")
        return "llvm-ar"

    def build(self):
        q = shlex.quote

        cc = self._compiler()
        ar = self._archiver()

        src = self.source_folder
        build = self.build_folder

        os.makedirs(build, exist_ok=True)

        common = [
            "-std=c99",
            "-fPIC",
            "-DNSGIF_NAME=nsgif",
            '-DNSGIF_VERSION="1.0.0"',
            "-I" + os.path.join(src, "include"),
            "-I" + os.path.join(src, "src"),
        ]

        if str(self.settings.build_type) == "Debug":
            common += ["-O0", "-g"]
        else:
            common += ["-O2"]

        flags = " ".join(q(x) for x in common)
        gif_obj = os.path.join(build, "gif.o")
        lzw_obj = os.path.join(build, "lzw.o")
        library = os.path.join(build, "libnsgif.a")
        test_binary = os.path.join(build, "test_nsgif")

        self.run(
            f"{q(cc)} {flags} "
            f"-c {q(os.path.join(src, 'src', 'gif.c'))} "
            f"-o {q(gif_obj)}"
        )

        self.run(
            f"{q(cc)} {flags} "
            f"-c {q(os.path.join(src, 'src', 'lzw.c'))} "
            f"-o {q(lzw_obj)}"
        )

        self.run(
            f"{q(ar)} rcs {q(library)} {q(gif_obj)} {q(lzw_obj)}"
        )

        self.run(
            f"{q(cc)} {flags} "
            f"-I{q(os.path.join(src, 'test'))} "
            f"{q(os.path.join(src, 'test', 'nsgif.c'))} "
            f"{q(library)} -lm -o {q(test_binary)}"
        )

        runner = (
            f'OUT=$(sh test/runtest.sh {q(build)}); '
            f'printf "%s\\n" "$OUT"; '
            f'printf "%s\\n" "$OUT" | '
            f'grep -q "Tests:284 Pass:284 Fail:0 Error:0"'
        )

        self.run(runner, cwd=src)

    def package(self):
        copy(
            self,
            "nsgif.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )

        copy(
            self,
            "libnsgif.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["nsgif"]
        self.cpp_info.set_property("cmake_file_name", "libnsgif")
        self.cpp_info.set_property(
            "cmake_target_name",
            "libnsgif::nsgif",
        )
