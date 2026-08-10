import os

from conan import ConanFile


class LibgcabTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        libgcab_dep = self.dependencies["libgcab"]
        glib_dep = self.dependencies["glib"]
        zlib_dep = self.dependencies["zlib"]
        libffi_dep = self.dependencies["libffi"]
        pcre2_dep = self.dependencies["pcre2"]

        cflags = " ".join([
            f"-I{libgcab_dep.package_folder}/include/libgcab-1.0",
            f"-I{glib_dep.package_folder}/include/glib-2.0",
            f"-I{glib_dep.package_folder}/lib/glib-2.0/include",
            f"-I{zlib_dep.package_folder}/include",
            f"-I{libffi_dep.package_folder}/include",
            f"-I{pcre2_dep.package_folder}/include",
        ])
        libs = " ".join([
            f"-L{libgcab_dep.package_folder}/lib",
            f"-L{glib_dep.package_folder}/lib",
            f"-L{zlib_dep.package_folder}/lib",
            f"-L{libffi_dep.package_folder}/lib",
            f"-L{pcre2_dep.package_folder}/lib",
            "-lgcab-1.0",
            "-lgio-2.0", "-lgobject-2.0", "-lglib-2.0",
            "-lgmodule-2.0", "-lgthread-2.0",
            "-lz", "-lffi", "-lpcre2-8",
            "-lm", "-lpthread", "-lrt", "-ldl",
            "-l:ld-musl-aarch64.so.1", "-L/lib",
        ])

        src = os.path.join(self.source_folder, "src", "test_libgcab.c")
        out = os.path.join(self.build_folder, "test_libgcab")
        self.run(f"clang {cflags} {src} -o {out} {libs}", env="conanbuild")

    def test(self):
        self.run(os.path.join(self.build_folder, "test_libgcab"), env="conanrun")
