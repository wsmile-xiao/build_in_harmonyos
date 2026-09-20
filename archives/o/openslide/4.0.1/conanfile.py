#!/usr/bin/env python3
"""Conan recipe for openslide 4.0.1 on HarmonyOS PC (arm64).

Build system: meson
All meson dependencies are hard requirements (no format-level options in
openslide 4.0.1). Dependencies are injected through generated pkg-config
files (PkgConfigDeps + pkg_config_path).
- openjpeg/2.5.4 recipe does not declare pkg_config_name; meson looks up
  'libopenjp2' -> alias pc generated via PkgConfigDeps.set_property.
- wrap_mode=nodownload prevents meson from fetching subprojects
  (libdicom/uthash/xdelta3 wraps) at build time.
- llvm-ar/llvm-ranlib are injected into meson native file because the
  OHOS toolchain binaries are not on PATH by bare name.

Upstream tests: the six upstream developer test programs from test/
(extended, mosaic, parallel, profile, query, try_open) are built and executed
in build() against a generated tiled generic-TIFF slide, see
_run_upstream_tests().
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    get,
    apply_conandata_patches,
    copy,
    export_conandata_patches,
)
from conan.tools.meson import MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class OpenslideConan(ConanFile):
    name = "openslide"
    version = "4.0.1"
    description = "C library for reading whole slide images (virtual slides)"
    license = "LGPL-2.1-only"
    homepage = "https://openslide.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # 依赖生态（cairo/libtiff/zstd 等）为 shared，openslide 对齐 shared，
    # 避免静态库把所有 glib 系传递依赖的符号链接风暴引入消费者。
    default_options = {"shared": True}

    # openslide-4.0.1/test/ 中的上游开发者测试程序（驱动脚本 driver.py 之外的
    # 全部测试可执行文件），在 build() 中于本机/CI 真实执行。
    UPSTREAM_TEST_PROGRAMS = (
        "extended",
        "mosaic",
        "parallel",
        "profile",
        "query",
        "try_open",
    )

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "make_synthetic_slide.py",
             src=self.recipe_folder, dst=self.export_sources_folder)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def requirements(self):
        # zlib/zstd/libjpeg-turbo 版本与 libtiff/4.7.2 的精确约束对齐，
        # 避免依赖图版本冲突；libjpeg-turbo 同时满足 openslide 的
        # jpeg_mem_src >= 1.3 检查。
        self.requires("zlib/1.3.1.1")
        self.requires("zstd/1.5.7")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libpng/1.6.58")
        self.requires("openjpeg/2.5.4")
        self.requires("libtiff/4.7.2")
        self.requires("glib/2.84.0.2")
        self.requires("cairo/1.18.4")
        self.requires("libxml2/2.15.3.1")
        self.requires("sqlite3/3.53.4")
        self.requires("libdicom/1.3.0")

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        # openjpeg recipe ships openjpeg.pc only; meson needs libopenjp2.pc
        pkg_config.set_property("openjpeg", "pkg_config_name", "libopenjp2")
        pkg_config.generate()

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "static"
        # Do not let meson fetch subprojects (libdicom/uthash/xdelta3 wraps).
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["test"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.pkg_config_path = self.generators_folder
        tc.generate()
        self._inject_meson_archive_tools()

    def _inject_meson_archive_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or os.path.join(bindir, "llvm-ar")
        ranlib = executables.get("ranlib") or os.path.join(bindir, "llvm-ranlib")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not bindir or not os.path.isfile(native_file) or not os.path.isfile(ar):
            return
        with open(native_file, encoding="utf-8") as native:
            content = native.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        tools = f"[binaries]\nar = '{ar}'\n"
        if os.path.isfile(ranlib):
            tools += f"ranlib = '{ranlib}'\n"
        with open(native_file, "w", encoding="utf-8") as native:
            native.write(content.replace("[binaries]\n", tools, 1))

    def build(self):
        apply_conandata_patches(self)
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        self._run_meson(
            f'meson setup --native-file "{native_file}" '
            f'"{self.build_folder}" "{self.source_folder}" --prefix=/'
        )
        self._run_meson(f'meson compile -C "{self.build_folder}"')
        self._run_upstream_tests()

    def _run_meson(self, command, extra_path=None):
        import shutil

        ninja = os.environ.get("NINJA")
        if not ninja or not os.path.isfile(ninja):
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = executables.get("c", "")
            candidate = os.path.join(os.path.dirname(compiler), "ninja")
            ninja = candidate if compiler and os.path.isfile(candidate) else None
        if not ninja:
            ninja = shutil.which("ninja")
        if not ninja:
            raise ConanInvalidConfiguration(
                "A Ninja executable is required to build openslide"
            )
        ninja_dir = os.path.dirname(ninja)
        path_entries = [entry for entry in (extra_path, ninja_dir) if entry]
        path = ":".join(path_entries)
        self.run(f'PATH="{path}:$PATH" NINJA="{ninja}" {command}')

    # ── upstream developer test programs ──────────────────────────────────
    def _run_upstream_tests(self):
        """Build and run openslide's six upstream developer test programs.

        The upstream suite (test/extended, test/mosaic, test/parallel,
        test/profile, test/query, test/try_open) is configured in a dedicated
        meson build directory so that the main build/install flow keeps
        -Dtest=disabled: upstream's test environment target runs `pip install`
        (driver.py dependencies) at build time, which cannot work in the
        offline CI environment.  The six programs themselves are independent of
        driver.py, so harmless stub tools for cjpeg/djpeg/xdelta3 are provided
        at meson setup time to satisfy upstream's developer-suite probe.

        Each program is executed against a generated tiled generic-TIFF slide
        (openslide's generic-tiff vendor requires a tiled TIFF - see
        src/openslide-vendor-generic-tiff.c) and the build fails unless all of
        them exit with status 0.
        """
        import stat

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        tools_dir = os.path.join(self.build_folder, "upstream-test-tools")
        os.makedirs(tools_dir, exist_ok=True)
        for tool in ("cjpeg", "djpeg", "xdelta3"):
            stub = os.path.join(tools_dir, tool)
            with open(stub, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\nexit 0\n")
            os.chmod(stub, os.stat(stub).st_mode | stat.S_IXUSR)

        test_build = os.path.join(self.build_folder, "upstream-test-build")
        if os.path.isdir(test_build):
            shutil.rmtree(test_build)
        self._run_meson(
            f'meson setup --native-file "{native_file}" "{test_build}" '
            f'"{self.source_folder}" -Dtest=enabled',
            extra_path=tools_dir,
        )
        self._run_meson(
            f'meson compile -C "{test_build}" '
            + " ".join(self.UPSTREAM_TEST_PROGRAMS)
        )

        data_dir = os.path.join(self.build_folder, "upstream-test-data")
        os.makedirs(data_dir, exist_ok=True)
        slide = os.path.join(data_dir, "synthetic-generic-tiff.tif")
        self.run(
            f'"{sys.executable}" "{self._slide_generator()}" "{slide}"'
        )
        index = os.path.join(data_dir, "mosaic-index.ini")
        with open(index, "w", encoding="utf-8") as handle:
            handle.write(
                "[slide]\nbase=.\nslide=synthetic-generic-tiff.tif\n"
                "level=0\nx=0\ny=0\n"
            )

        ld_library_path = self._test_ld_library_path(test_build)
        invocations = {
            "extended": [f'"{slide}"'],
            "mosaic": [
                f'"{data_dir}"',
                f'"{index}"',
                f'"{os.path.join(data_dir, "mosaic.png")}"',
            ],
            "parallel": [f'"{slide}"', "4"],
            "profile": [f'"{slide}"', "0"],
            "query": ["-n", f'"{slide}"'],
            "try_open": ["-n", "generic-tiff", f'"{slide}"'],
        }
        passed = []
        for name in self.UPSTREAM_TEST_PROGRAMS:
            executable = os.path.join(test_build, "test", name)
            self.run(
                f'LD_LIBRARY_PATH="{ld_library_path}" "{executable}" '
                + " ".join(invocations[name])
            )
            passed.append(name)
            self.output.info(f"upstream test program passed: {name}")
        self.output.info(
            "openslide upstream developer test programs: "
            f"{len(passed)}/{len(self.UPSTREAM_TEST_PROGRAMS)} passed"
        )
        if len(passed) != len(self.UPSTREAM_TEST_PROGRAMS):
            raise ConanException(
                "openslide upstream test programs failed: "
                f"{len(passed)}/{len(self.UPSTREAM_TEST_PROGRAMS)} passed"
            )

    def _slide_generator(self):
        for candidate in (
            os.path.join(self.source_folder, "make_synthetic_slide.py"),
            os.path.join(self.export_sources_folder, "make_synthetic_slide.py"),
            os.path.join(self.recipe_folder, "make_synthetic_slide.py"),
        ):
            if os.path.isfile(candidate):
                return candidate
        raise ConanException("make_synthetic_slide.py is missing from the recipe")

    def _test_ld_library_path(self, test_build):
        paths = [os.path.join(test_build, "src")]
        for _ref, dependency in self.dependencies.items():
            package_folder = dependency.package_folder
            for relative in dependency.cpp_info.libdirs:
                if not relative:
                    continue
                path = relative if os.path.isabs(relative) else os.path.join(
                    package_folder or "", relative
                )
                if path and path not in paths:
                    paths.append(path)
        ambient = os.environ.get("LD_LIBRARY_PATH", "")
        if ambient:
            paths.append(ambient)
        return ":".join(paths)

    # ── packaging ─────────────────────────────────────────────────────────
    def package(self):
        self._run_meson(
            f'meson install -C "{self.build_folder}" --destdir "{self.package_folder}"'
        )
        self._restore_linker_shared_object()
        self._materialize_shared_aliases()

    def _restore_linker_shared_object(self):
        """Install the linker output as-is for the shared library.

        meson rewrites the rpath of installed shared libraries in place (it
        strips the build rpath unless install_rpath is set).  The HarmonyOS
        clang driver signs every ELF it produces with a `.codesign` section
        that covers the file contents, so meson's in-place edit invalidates the
        signature and the dynamic loader then refuses to load the library
        ("Error loading shared library libopenslide.so.1: Permission denied"),
        which breaks every consumer of the package.  Ship meson's build-tree
        object instead; musl ignores DT_RUNPATH, so the recorded build rpath is
        harmless at runtime.
        """
        import shutil

        source = os.path.join(self.build_folder, "src", "libopenslide.so.1.0.1")
        installed = os.path.join(self.package_folder, "lib", "libopenslide.so.1.0.1")
        if not os.path.isfile(source):
            raise ConanException(
                f"built shared object is missing from the build tree: {source}"
            )
        shutil.copy2(source, installed)

    def _materialize_shared_aliases(self):
        """HMDFS has no reliable symlinks: replace meson's
        libopenslide.so -> libopenslide.so.1 -> libopenslide.so.1.0.1 alias
        chain with real copies (verified pattern from libdicom/1.3.0).  The
        OHOS dynamic loader fails to resolve the symlink chain and reports
        "Error loading shared library libopenslide.so.1" with every symbol
        failing relocation otherwise."""
        import shutil

        library_dir = os.path.join(self.package_folder, "lib")
        source = os.path.join(library_dir, "libopenslide.so.1.0.1")
        aliases = (
            os.path.join(library_dir, "libopenslide.so.1"),
            os.path.join(library_dir, "libopenslide.so"),
        )
        if not os.path.isfile(source) or os.path.islink(source):
            raise ConanException(
                f"installed openslide shared object is missing: {source}"
            )
        for alias in aliases:
            if os.path.lexists(alias):
                os.unlink(alias)
            shutil.copy2(source, alias)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "openslide")
        self.cpp_info.libs = ["openslide"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
