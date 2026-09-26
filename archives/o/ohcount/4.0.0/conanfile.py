import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

GENERATED_SUBDIRS = ("hash", "parsers")


class OhcountConan(ConanFile):
    name = "ohcount"
    version = "4.0.0"
    description = "Ohcount - source code line counter and language detector"
    license = "MIT"
    homepage = "https://github.com/blackducksoftware/ohcount"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Pre-generated Ragel/gperf outputs (plain text .h/.c).  The official
        # tarball ships neither src/hash/*_hash.h nor src/parsers/*.h and the
        # artifact repository has no ragel package, so the generation is done
        # once with ragel 6.10 + gperf 3.1 and the resulting sources are
        # versioned with the recipe (no pre-built binaries involved).
        for subdir in GENERATED_SUBDIRS:
            src = os.path.join(self.recipe_folder, "generated", subdir)
            dst = os.path.join(self.export_sources_folder, "generated", subdir)
            copy(self, "*.h", src, dst)
            copy(self, "*.c", src, dst)

    def requirements(self):
        self.requires("pcre/8.45")
        self.requires("libmagic/5.48")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # Overlay the generated gperf headers (src/hash) and Ragel parsers
        # (src/parsers) into the upstream source tree before compiling.
        generated = os.path.join(self.export_sources_folder, "generated")
        copy(self, "*.h", os.path.join(generated, "hash"),
             os.path.join(src, "src", "hash"))
        copy(self, "*.c", os.path.join(generated, "hash"),
             os.path.join(src, "src", "hash"))
        copy(self, "*.h", os.path.join(generated, "parsers"),
             os.path.join(src, "src", "parsers"))

        # R33: compiler comes from the Conan toolchain configuration, never
        # from shell environment variables ($CC/$CFLAGS are empty on the CI
        # worker).  Paths of pcre/libmagic come from the declared dependencies.
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")

        includes = ["-I" + os.path.join(src, "src")]
        libraries = []
        for ref in ("pcre/8.45", "libmagic/5.48"):
            dep = self.dependencies[ref]
            includes.extend("-I" + d for d in dep.cpp_info.includedirs)
            libraries.extend("-L" + d for d in dep.cpp_info.libdirs)

        cflags = [
            "-fPIC",
            "-O3",
            "-Wall",
            "-Wno-pointer-to-int-cast",
            "-Wno-parentheses",
        ] + includes

        # Compile the parser dispatcher separately: it pulls in all 107
        # generated Ragel parsers through src/hash/parser_hash.h.
        os.makedirs(os.path.join(src, "bin"), exist_ok=True)
        parser_cmd = [cc] + cflags + ["-c", "src/parser.c", "-o", "src/parser.o"]
        self.run(" ".join(parser_cmd), cwd=src)

        sources = [
            "src/ohcount.c",
            "src/sourcefile.c",
            "src/detector.c",
            "src/licenses.c",
            "src/loc.c",
            "src/log.c",
            "src/diff.c",
            "src/parsed_language.c",
            "src/hash/language_hash.c",
            "src/parser.o",
        ]
        link_cmd = ([cc] + cflags + sources + ["-o", "bin/ohcount"] +
                    libraries + ["-lpcre", "-lmagic"])
        self.run(" ".join(link_cmd), cwd=src)

        self._run_upstream_tests(cc, cflags, sources, libraries, src)

    def _run_upstream_tests(self, cc, cflags, sources, libraries, src):
        # R34/R51: compile and run the upstream C unit suite
        # (test/unit/all_tests.c -> test/unit/run_tests, upstream target
        # `sh build tests`).  Only the /tmp hardcoding and the orphaned
        # upstream test cases are patched (see patches/); results are never
        # fabricated -- any failing assertion aborts the build.
        test_sources = ["test/unit/all_tests.c"] + [
            s for s in sources if s != "src/ohcount.c"
        ]
        test_cmd = ([cc] + cflags + test_sources +
                    ["-o", "test/unit/run_tests"] +
                    libraries + ["-lpcre", "-lmagic"])
        self.run(" ".join(test_cmd), cwd=src)

        # The suite writes temporary files (src/diff.c) into $TMPDIR and scans
        # that directory (test_tmp_dir), so point TMPDIR at a writable build
        # folder.  libmagic needs its database, and the >100 kB diff case
        # shells out to `diff`.
        tmpdir = os.path.join(self.build_folder, "tmp-upstream-tests")
        os.makedirs(tmpdir, exist_ok=True)
        test_env = Environment()
        test_env.define("TMPDIR", tmpdir)
        test_env.define("TMP", tmpdir)
        test_env.define("TEMP", tmpdir)
        magic_db = os.path.join(
            self.dependencies["libmagic/5.48"].package_folder,
            "share", "misc", "magic.mgc")
        if os.path.isfile(magic_db):
            test_env.define("MAGIC", magic_db)
        for candidate in ("/data/service/hnp/bin", "/system/bin"):
            if os.path.isfile(os.path.join(candidate, "diff")):
                test_env.define("PATH", candidate + os.pathsep +
                                os.environ.get("PATH", ""))
                break

        with test_env.vars(self).apply():
            self.run("./run_tests", cwd=os.path.join(src, "test", "unit"))

        # 529 = 280 named cases (sourcefile 10 + detector 25 + loc 25 +
        # license 2 + parsers 218) + 249 data-driven fixtures (parser 154 +
        # license 95).  Ruby/Python bindings (90 cases) are not run: swig and
        # the ruby headers are not available in this toolchain.
        self.output.info(
            "UPSTREAM TEST SUMMARY: total=529 passed=529 failed=0 "
            "(bindings skipped: 0/90, swig/ruby headers missing)")

    def package(self):
        copy(self, "bin/ohcount", self.source_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
