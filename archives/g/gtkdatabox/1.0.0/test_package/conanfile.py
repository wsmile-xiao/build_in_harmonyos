#!/usr/bin/env python3
"""Conan test_package for gtkdatabox 1.0.0."""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class GtkDataboxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        envvars = self._pkg_config_env().vars(self)
        with envvars.apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if str(self.settings.os) == "OHOS" and not self._ohos_gtk_runtime_available():
            self.output.info("Skipping GTK runtime smoke test on OHOS: required GTK runtime libs are missing on headless CI")
            return
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise RuntimeError("test_gtkdatabox executable directory was not produced")
            envvars = self._pkg_config_env().vars(self)
            with envvars.apply():
                self.run(os.path.join(bindirs[0], "test_gtkdatabox"), env="conanrun")

    def _ohos_gtk_runtime_available(self):
        required = (
            "libgtk-3.so.0",
            "libgdk-3.so.0",
            "libcairo.so.2",
            "libcairo-gobject.so.2",
            "libepoxy.so.0",
            "libfribidi.so.0",
            "libpango-1.0.so.0",
            "libgdk_pixbuf-2.0.so.0",
        )
        search_dirs = []
        env = os.environ.get("LD_LIBRARY_PATH", "")
        search_dirs.extend([d for d in env.split(os.pathsep) if d])
        prefix = self._system_prefix()
        search_dirs.extend([
            os.path.join(prefix, "lib"),
            os.path.join(prefix, "lib", "external"),
        ])
        search_dirs.extend(sorted(glob.glob("/data/service/hnp/*/*/lib")))
        for lib in required:
            if not any(os.path.isfile(os.path.join(d, lib)) for d in search_dirs if d):
                self.output.info("Missing {} for GTK runtime smoke on OHOS".format(lib))
                return False
        return True

    def _system_prefix(self):
        return self._find_gtk_prefix()

    def _find_gtk_prefix(self):
        candidates = []
        for env_name in ("GTK_PREFIX", "DEFAULT_PREFIX"):
            value = os.environ.get(env_name)
            if value:
                candidates.append(os.path.normpath(value))
        candidates.append("/storage/Users/currentUser/usr/local")
        for pattern in (
            "/data/service/hnp/*/*/lib/pkgconfig",
            "/data/service/hnp/*/*/share/pkgconfig",
        ):
            for pc_dir in sorted(glob.glob(pattern)):
                candidates.append(os.path.dirname(os.path.dirname(pc_dir)))
        for pc_file in sorted(glob.glob("/data/service/hnp/**/gtk+-3.0.pc", recursive=True)):
            candidates.append(os.path.dirname(os.path.dirname(pc_file)))

        seen = set()
        for prefix in candidates:
            if prefix in seen:
                continue
            seen.add(prefix)
            if self._gtk_pc_exists(prefix):
                self.output.info("Using GTK+ prefix {}".format(prefix))
                return prefix
        return candidates[0] if candidates else "/storage/Users/currentUser/usr/local"

    def _gtk_pc_exists(self, prefix):
        return (
            os.path.isfile(os.path.join(prefix, "lib", "pkgconfig", "gtk+-3.0.pc"))
            or os.path.isfile(os.path.join(prefix, "share", "pkgconfig", "gtk+-3.0.pc"))
        )

    def _dependency_path(self, dependency, path):
        if not path:
            return None
        if os.path.isabs(path):
            return path
        if not getattr(dependency, "package_folder", None):
            return None
        return os.path.join(dependency.package_folder, path)

    def _pkg_config_env(self):
        env = Environment()
        for dependency in self.dependencies.values():
            for bindir in dependency.cpp_info.bindirs or []:
                if not bindir or not getattr(dependency, "package_folder", None):
                    continue
                full_bindir = self._dependency_path(dependency, bindir)
                if not full_bindir:
                    continue
                env.prepend_path("PATH", full_bindir)
            for libdir in dependency.cpp_info.libdirs or []:
                if not libdir or not getattr(dependency, "package_folder", None):
                    continue
                full_libdir = self._dependency_path(dependency, libdir)
                if not full_libdir:
                    continue
                env.prepend_path("LD_LIBRARY_PATH", full_libdir)
                env.append("LDFLAGS", "-L{}".format(full_libdir))
                env.prepend_path("PKG_CONFIG_PATH", os.path.join(full_libdir, "pkgconfig"))
            for includedir in dependency.cpp_info.includedirs or []:
                if not includedir or not getattr(dependency, "package_folder", None):
                    continue
                full_includedir = self._dependency_path(dependency, includedir)
                if not full_includedir:
                    continue
                env.append("CFLAGS", "-I{}".format(full_includedir))
                env.append("CXXFLAGS", "-I{}".format(full_includedir))
                env.append("CPPFLAGS", "-I{}".format(full_includedir))

        prefix = self._system_prefix()
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(prefix, "lib", "pkgconfig"))
        if str(self.settings.os) == "OHOS":
            hnp_pkgconfigs = sorted(
                glob.glob("/data/service/hnp/*/*/lib/pkgconfig"),
                key=lambda p: (p.count("/"), p),
            )
            for pkgconfig_dir in hnp_pkgconfigs:
                env.prepend_path("PKG_CONFIG_PATH", pkgconfig_dir)
            hnp_runtime_libs = []
            for pattern in ("libpcre2-8.so*", "libffi.so*", "libexpat.so*", "libintl.so*"):
                for match in glob.glob("/data/service/hnp/*/*/lib/{}".format(pattern)):
                    hnp_runtime_libs.append(os.path.dirname(match))
            for libdir in sorted(set(hnp_runtime_libs)):
                env.append_path("LD_LIBRARY_PATH", libdir)
                env.append("LDFLAGS", "-L{}".format(libdir))
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(prefix, "share", "pkgconfig"))
        env.prepend_path("PATH", os.path.join(prefix, "bin"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib", "external"))
        env.append("LDFLAGS", "-L{}".format(os.path.join(prefix, "lib", "external")))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
        env.append("LDFLAGS", "-L{}".format(os.path.join(prefix, "lib")))
        return env
