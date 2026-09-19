from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # hoel's public header hoel.h includes <jansson.h>, <yder.h> and
        # <orcania.h> (the json-based query language and the orcania
        # allocators are part of the public API surface), so consumers need
        # those headers too. jansson/2.14 on ohpcd is a shared package.
        self.requires("jansson/2.14")
        # The test drives the sqlite backend end to end.
        self.requires("sqlite3/3.53.4")
        self.requires("libyder/1.4.20")
        self.requires("orcania/2.3.3")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Actually execute the packaged library: open an in-memory sqlite
        # database through hoel, run a json INSERT/SELECT round trip and
        # verify the data round-trips — exercises h_connect_sqlite,
        # h_insert, h_select, h_close_db and the h_*_json_* machinery on
        # the real packaged archive.
        import os
        exe = os.path.join(self.build_folder, "bin", "test_hoel")
        if not os.path.isfile(exe):
            exe = os.path.join(self.build_folder, "test_hoel")
        tmpdir = os.environ.get("TMPDIR") or self.build_folder
        db_path = os.path.join(tmpdir, "conan_test_hoel.db")
        if os.path.exists(db_path):
            os.unlink(db_path)
        # hoel's h_connect_sqlite opens with SQLITE_OPEN_READWRITE (no
        # CREATE) — the upstream fixtures are pre-seeded files. Seed an
        # empty file the same way the upstream CI does (the schema is
        # applied by the test through h_execute_query_sqlite).
        open(db_path, "wb").close()
        # jansson/2.14 ships a shared library on ohpcd: prepend its lib
        # dir to the process LD_LIBRARY_PATH so the test executable
        # resolves libjansson.so at runtime (self.run inherits this env).
        jansson_lib = os.path.join(
            self.dependencies["jansson"].package_folder, "lib")
        if os.path.isdir(jansson_lib):
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = jansson_lib + (
                ":" + existing if existing else "")
        # self.run executes the built consumer against the packaged
        # archive; a non-zero exit propagates and fails the test.
        self.run('"{exe}" "{db}"'.format(exe=exe, db=db_path))
