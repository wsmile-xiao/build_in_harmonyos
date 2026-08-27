import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class QtUnixodbcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["qt-unixodbc"]
        pkg = dep.package_folder

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp") or compilers.get("cxx")
        if not cxx:
            raise ConanInvalidConfiguration("C++ compiler required for test")

        qt5 = self.dependencies["qt5-qtbase"]
        qt5_pkg = qt5.package_folder

        # Create qtinc directory for QtSql config headers
        # (qt5-qtbase doesn't include them in standard include path)
        qtinc_dir = os.path.join(self.build_folder, "qtinc", "QtSql")
        os.makedirs(qtinc_dir, exist_ok=True)
        qtsql_config = os.path.join(qt5_pkg, "src", "sql", "qtsql-config.h")
        if os.path.isfile(qtsql_config):
            shutil.copy2(qtsql_config, qtinc_dir)

        include_dirs = [
            os.path.join(self.build_folder, "qtinc"),
            os.path.join(pkg, "include"),
            os.path.join(qt5_pkg, "include"),
            os.path.join(qt5_pkg, "include", "QtCore"),
            os.path.join(qt5_pkg, "include", "QtSql"),
        ]
        lib_dirs = [
            os.path.join(pkg, "lib"),
            os.path.join(qt5_pkg, "lib"),
        ]

        cflags = "-pipe -O2 -std=c++14 -fPIC -DQT_NO_DEBUG -DQT_SQL_LIB -DQT_CORE_LIB"
        includes = " ".join(f"-I{d}" for d in include_dirs)
        libdirs_flags = " ".join(f"-L{d}" for d in lib_dirs)

        src = os.path.join(self.source_folder, "test_qt_unixodbc.cpp")
        obj = os.path.join(self.build_folder, "test_qt_unixodbc.o")
        bin_ = os.path.join(self.build_folder, "test_qt_unixodbc")

        self.run(f'"{cxx}" -c {cflags} {includes} "{src}" -o "{obj}"')
        self.run(
            f'"{cxx}" -o "{bin_}" "{obj}" '
            f'{libdirs_flags} -lQt5Sql -lQt5Core '
            f'-Wl,-rpath,{":".join(lib_dirs)}'
        )

    def test(self):
        dep = self.dependencies["qt-unixodbc"]
        pkg = dep.package_folder
        qt5 = self.dependencies["qt5-qtbase"]
        qt5_pkg = qt5.package_folder

        # R34: verify plugin exists and is valid
        plugin_path = os.path.join(pkg, "plugins", "sqldrivers", "libqsqlodbc.so")
        assert os.path.isfile(plugin_path), \
            f"ODBC driver plugin not found: {plugin_path}"

        # Verify ELF dependencies
        readelf = shutil.which("readelf") or "/data/service/hnp/bin/readelf"
        output = subprocess.check_output(
            [readelf, "-d", plugin_path],
            stderr=subprocess.STDOUT, text=True,
        )
        assert "libQt5Sql" in output, "Plugin must depend on libQt5Sql"
        assert "libodbc" in output, "Plugin must depend on libodbc"

        # Run the test binary (R34: substantively uses the package API)
        lib_dirs = [
            os.path.join(pkg, "lib"),
            os.path.join(qt5_pkg, "lib"),
            os.environ.get("LD_LIBRARY_PATH", ""),
        ]
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            d for d in lib_dirs if d
        )
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        test_bin = os.path.join(self.build_folder, "test_qt_unixodbc")
        self.run(test_bin)
