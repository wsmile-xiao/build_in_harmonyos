import os
from conan import ConanFile
from conan.tools.build import cross_building


class LibarchiveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Compile the test against the packaged libarchive (headers + lib).
        # Link note: zlib/bzip2/xz objects are statically absorbed into
        # libarchive.so; only zstd stays a dynamic NEEDED entry, so the link
        # line needs -L for all dep libdirs plus -lzstd to resolve it.
        incs = []
        libdirs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            libdirs += [str(d) for d in _d.cpp_info.libdirs]
        inc = " ".join(incs)
        lib_flags = " ".join("-L{}".format(d) for d in libdirs)
        link = "-larchive -lzstd"
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test_libarchive.c -o test_libarchive {inc} {lib_flags} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile + link only")
            return
        # R34: real tar.gz write/read round-trip through the packaged library.
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries — wrap in bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        all_libdirs = []
        for _ref, _d in self.dependencies.items():
            all_libdirs += [str(d) for d in _d.cpp_info.libdirs]
        ld_path = ":".join(dict.fromkeys(all_libdirs))
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH={ld_path}:$LD_LIBRARY_PATH; ./test_libarchive'",
            env="conanrun")
