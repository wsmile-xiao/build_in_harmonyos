import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class ZsyncConan(ConanFile):
    name = "zsync"
    version = "0.6.3"
    description = "Partial file download utility based on the rsync algorithm"
    license = "Artistic-2.0"
    homepage = "https://github.com/cph6/zsync"
    url = "https://github.com/cph6/zsync"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # c/check-zsyncmake, the only upstream test, is a perl script
        self.tool_requires("perl/5.42.2")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration("zsync supports Linux and OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "c")
        out = os.path.join(self.build_folder, "bin")
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(src, "config.h"), "w", encoding="ascii") as handle:
            handle.write("#include <sys/types.h>\n")
            handle.write("#define PACKAGE \"zsync\"\n#define VERSION \"0.6.3\"\n")
            handle.write("#define HAVE_INTTYPES_H 1\n#define HAVE_GETADDRINFO 1\n")
            handle.write("#define HAVE_MEMCPY 1\n#define HAVE_PWRITE 1\n#define HAVE_PREAD 1\n")
        configured_cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c")
        cc = os.environ.get("CC") or shutil.which("clang") or configured_cc or "cc"
        flags = "-I. -Ilibrcksum -Ilibzsync -Izlib -DHAVE_CONFIG_H"
        rcksum = "librcksum/hash.c librcksum/md4.c librcksum/range.c librcksum/rsum.c librcksum/state.c"
        zsynclib = "libzsync/sha1.c libzsync/zmap.c libzsync/zsync.c"
        zlib = "zlib/adler32.c zlib/compress.c zlib/crc32.c zlib/deflate.c zlib/inflate.c zlib/inftrees.c zlib/trees.c zlib/zutil.c"
        self.run(f"cd {src} && {cc} {flags} -o {out}/zsyncmake make.c makegz.c progress.c {rcksum} {zsynclib} {zlib} -lm")
        self.run(f"cd {src} && {cc} {flags} -o {out}/zsync client.c http.c url.c base64.c progress.c {rcksum} {zsynclib} {zlib} -lm")

        # Upstream test suite - four cases, taken from the TESTS variables of
        # c/Makefile.am (check-zsyncmake), c/librcksum/Makefile.am (md4test,
        # rsumtest) and c/libzsync/Makefile.am (sha1test). The source tarball
        # has no generated configure and the CI image has no autoreconf, so
        # automake's `make check` is unavailable; build and run the very same
        # test programs directly instead.
        if not can_run(self):
            self.output.info("skipping upstream tests: cannot run target binaries")
            return
        tests_dir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(tests_dir, exist_ok=True)
        subflags = "-I. -I.. -DHAVE_CONFIG_H"
        self.run(f"cd {src}/librcksum && {cc} {subflags} -o {tests_dir}/md4test md4test.c md4.c")
        self.run(f"cd {src}/librcksum && {cc} {subflags} -o {tests_dir}/rsumtest rsumtest.c rsum.c hash.c range.c state.c md4.c ../progress.c")
        self.run(f"cd {src}/libzsync && {cc} {subflags} -o {tests_dir}/sha1test sha1test.c sha1.c")
        self.run(f"{tests_dir}/md4test")
        self.run(f"{tests_dir}/rsumtest")
        self.run(f"{tests_dir}/sha1test")

        # check-zsyncmake is a perl script (see build_requirements); it reads
        # top_builddir for the zsyncmake binary and srcdir for INSTALL.
        shutil.copy(os.path.join(src, "INSTALL"), tests_dir)
        self.run(f"cd {tests_dir} && top_builddir={out} srcdir={tests_dir} sh -e {src}/check-zsyncmake",
                 env="conanbuild")

    def package(self):
        copy(self, "zsync", src=os.path.join(self.build_folder, "bin"), dst=os.path.join(self.package_folder, "bin"))
        copy(self, "zsyncmake", src=os.path.join(self.build_folder, "bin"), dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=os.path.join(self.source_folder, "c"), dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
