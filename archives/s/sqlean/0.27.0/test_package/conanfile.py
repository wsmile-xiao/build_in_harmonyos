import os

from conan import ConanFile


class SqleanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # direct require: transitive deps get no usable package_folder in
        # this context, and the consumer needs sqlite3 headers/library
        self.requires("sqlite3/3.53.4")

    def _cc(self):
        # R33: compiler from the toolchain conf, never a bare shell default
        exe = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return exe.get("c") or exe.get("cpp") or "clang"

    def build(self):
        # compiled directly: sqlite3 is a transitive dep, so its CMakeDeps
        # config is not generated for this consumer
        cc = self._cc()
        sq3 = self.dependencies["sqlite3"]
        inc = str(sq3.cpp_info.includedirs[0])
        if not os.path.isabs(inc):
            inc = os.path.join(str(sq3.package_folder or ""), inc)
        libdir = str(sq3.cpp_info.libdirs[0])
        if not os.path.isabs(libdir):
            libdir = os.path.join(str(sq3.package_folder or ""), libdir)
        lib = os.path.join(libdir, "libsqlite3.a")
        src = os.path.join(os.path.dirname(__file__), "test_sqlean.c")
        out = os.path.join(self.build_folder, "test_sqlean")
        cmd = '{} "{}" -I"{}" -o "{}" "{}" -lm'.format(cc, src, inc, out, lib)
        self.run(cmd)

    def test(self):
        dep = self.dependencies["sqlean"]
        extdir = os.path.join(str(dep.package_folder), str(dep.cpp_info.libdirs[0]))
        cmd = os.path.join(self.build_folder, "test_sqlean")
        self.run('"{}" "{}"'.format(cmd, extdir))
