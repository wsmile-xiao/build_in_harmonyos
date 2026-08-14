import os
import stat

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class MesonConan(ConanFile):
    name = "meson"
    version = "1.11.0"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # zlib is used only by Meson's complete upstream test suite (dependency
        # discovery tests). It is not a runtime dependency of the packaged tool.
        self.tool_requires("zlib/1.3.1.1")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def build(self):
        # Generate local pkg-config / CMake metadata for zlib so that the
        # upstream suite's dependency-discovery tests exercise the real
        # zlib/1.3.1.1 package. The metadata reports the zlib API version
        # (1.3.1), not the recipe revision (1.3.1.1).
        #
        # test_deps is built as a complete zlib install prefix: pkg-config
        # metadata (zlib.pc), a CMake package config (ZLIBConfig.cmake) and
        # the actual headers/static archive. CMake's find_package(ZLIB) uses
        # MODULE mode (FindZLIB.cmake) by default, which needs zlib.h and
        # libz.a under the prefix; the config file additionally covers
        # CONFIG-mode discovery used by other upstream tests.
        test_deps = os.path.join(self.build_folder, "upstream-test-deps")
        pkgconfig_dir = os.path.join(test_deps, "pkgconfig")
        cmake_dir = os.path.join(test_deps, "lib", "cmake", "ZLIB")
        os.makedirs(pkgconfig_dir, exist_ok=True)
        os.makedirs(cmake_dir, exist_ok=True)

        zlib = self.dependencies.build["zlib"]
        zlib_prefix = zlib.package_folder.replace("\\", "/")
        save(
            self,
            os.path.join(pkgconfig_dir, "zlib.pc"),
            "prefix={0}\n"
            "libdir=${{prefix}}/lib\n"
            "includedir=${{prefix}}/include\n\n"
            "Name: zlib\n"
            "Description: zlib supplied for Meson upstream tests\n"
            "Version: 1.3.1\n"
            "Libs: -L${{libdir}} -lz\n"
            "Cflags: -I${{includedir}}\n".format(zlib_prefix),
        )
        save(
            self,
            os.path.join(cmake_dir, "ZLIBConfig.cmake"),
            "add_library(ZLIB::ZLIB STATIC IMPORTED)\n"
            "set_target_properties(ZLIB::ZLIB PROPERTIES\n"
            "  IMPORTED_LOCATION \"{0}/lib/libz.a\"\n"
            "  INTERFACE_INCLUDE_DIRECTORIES \"{0}/include\")\n"
            "set(ZLIB_FOUND TRUE)\n"
            "set(ZLIB_VERSION_STRING \"1.3.1\")\n"
            "set(ZLIB_LIBRARIES ZLIB::ZLIB)\n"
            "set(ZLIB_INCLUDE_DIRS \"{0}/include\")\n".format(zlib_prefix),
        )
        copy(
            self,
            "*.h",
            src=os.path.join(zlib_prefix, "include"),
            dst=os.path.join(test_deps, "include"),
        )
        copy(
            self,
            "*.a",
            src=os.path.join(zlib_prefix, "lib"),
            dst=os.path.join(test_deps, "lib"),
        )

        test_env = Environment()
        # 显式注入 OHOS 工具链目录到 PATH，并直接指定 NINJA/CC/CXX：
        # - run_tests.py 顶部优先读 os.environ['NINJA']（detect_ninja 先查 NINJA 变量）
        # - meson 经 PATH/CC 探测 C/C++ 编译器（clang --version）
        # CI worker 的 conan 进程 PATH 不含 /data/service/hnp/bin，仅靠
        # env="conanbuild" 注入 profile [buildenv] 不可靠（实测仍报
        # "No such file or directory: 'clang'/'ninja'"），故在此显式设置。
        test_env.prepend_path("PATH", "/data/service/hnp/bin")
        test_env.prepend_path("PATH", "/storage/Users/currentUser/usr/local/bin")
        test_env.define("NINJA", "/data/service/hnp/bin/ninja")
        test_env.define("CC", "/data/service/hnp/bin/clang")
        test_env.define("CXX", "/data/service/hnp/bin/clang++")
        # meson 探测静态链接器走 PATH 找 llvm-ar/ar（"Unknown linker(s):
        # [['llvm-ar']]"），CI worker PATH 无工具链目录时报 No such file；
        # AR/RANLIB/NM 显式注入绝对路径，与 CC/CXX 同机制。
        test_env.define("AR", "/data/service/hnp/bin/llvm-ar")
        test_env.define("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
        test_env.define("NM", "/data/service/hnp/bin/llvm-nm")
        # unittests 中 PKG_CONFIG = os.environ.get('PKG_CONFIG', 'pkg-config')，
        # 默认裸名走 PATH；CI worker PATH 无工具链目录时报
        # FileNotFoundError: 'pkg-config'（b18903：8 个 pkg-config 相关用例失败）。
        # 显式注入绝对路径，与 NINJA/CC/AR 同机制。
        test_env.define("PKG_CONFIG", "/data/service/hnp/bin/pkg-config")
        # OHOS SDK 的 lld 动态依赖 libxml2.so.16（llvm/lib 下）；CI worker 上
        # lld 报 "Error relocating lld: xmlFreeDoc: symbol not found"（加载到
        # 了版本不匹配的 libxml2）。显式注入 SDK llvm/lib 到 LD_LIBRARY_PATH，
        # 保证 lld 运行时加载正确的 libxml2，与 PATH 注入同机制。
        test_env.prepend_path(
            "LD_LIBRARY_PATH",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
        )
        test_env.prepend_path("PKG_CONFIG_PATH", pkgconfig_dir)
        test_env.prepend_path("CMAKE_PREFIX_PATH", test_deps)
        test_env.define_path("ZLIB_ROOT", zlib_prefix)
        # pytest-xdist 的默认 basetemp 位于 $HOME/tmp/pytest-of-<user>，CI worker
        # 上该目录属主与 conan 进程 UID 不匹配 → INTERNALERROR（OSError: The
        # temporary directory ... is not owned by the current user），unittests
        # 直接崩溃。把 basetemp/TMPDIR 指到 build_folder 下（本进程可写）。
        _pytest_basetemp = os.path.join(self.build_folder, "pytest-basetemp")
        _tmpdir = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(_pytest_basetemp, exist_ok=True)
        os.makedirs(_tmpdir, exist_ok=True)
        test_env.define("PYTEST_ADDOPTS", "--basetemp={}".format(_pytest_basetemp))
        test_env.define_path("TMPDIR", _tmpdir)
        with test_env.vars(self).apply():
            # CI worker 的 python3 未装 pytest-xdist：run_unittests.py 只能单线程
            # 运行 647 项用例（约 3600s），超过 CI 的 3600s 超时上限导致
            # conan create TIMED OUT。安装 xdist 后恢复 20 workers 并行（约 540s）。
            # 参照 buku/5.0 先例（build() 内 pip install 测试依赖）。
            import importlib.util
            if importlib.util.find_spec("xdist") is None:
                self.run(
                    "python3 -m pip install pytest-xdist --quiet --disable-pip-version-check",
                    cwd=self.source_folder,
                )
            self.run("python3 run_tests.py", cwd=self.source_folder, env="conanbuild")

    def package(self):
        site_packages = os.path.join(
            self.package_folder, "lib", "python3.12", "site-packages"
        )
        copy(self, "meson.py", src=self.source_folder, dst=site_packages)
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "mesonbuild"),
            dst=os.path.join(site_packages, "mesonbuild"),
        )

        launcher = os.path.join(self.package_folder, "bin", "meson")
        save(
            self,
            launcher,
            "#!/bin/sh\n"
            'here=$(CDPATH= cd "$(dirname "$0")" && pwd)\n'
            'exec python3 "$here/../lib/python3.12/site-packages/meson.py" "$@"\n',
        )
        os.chmod(launcher, os.stat(launcher).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
