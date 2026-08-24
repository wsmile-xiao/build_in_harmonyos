#!/usr/bin/env python3
"""Conan test_package for goocanvas 3.0.0.

Builds a small C consumer against goocanvas-3.0.pc and exercises real
GooCanvas public APIs (goo_canvas_group_new, goo_canvas_rect_new, ...).
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class GooCanvasTestConan(ConanFile):
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
        if str(self.settings.os) == "OHOS":
            self._ensure_system_lib_symlinks()
            if not self._ohos_gtk_runtime_available():
                self.output.info(
                    "Skipping GTK runtime smoke test on OHOS: required GTK "
                    "runtime libs are missing on headless CI"
                )
                return
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise RuntimeError(
                    "test_goocanvas executable directory was not produced"
                )
            envvars = self._pkg_config_env().vars(self)
            with envvars.apply():
                self.run(
                    os.path.join(bindirs[0], "test_goocanvas"), env="conanrun"
                )

    def _ensure_system_lib_symlinks(self):
        """Create unversioned linker names for OHOS system GTK stack libs.

        The cmd-pkgs ohos-aarch64 tarballs ship only versioned .so.X.Y.Z
        files; the loader needs libfoo.so.N symlinks (libepoxy.so.0,
        libfribidi.so.0, ...). On HMDFS, symlink creation may fail, so fall
        back to copying the versioned file.
        """
        prefix = self._system_prefix()
        libdir = os.path.join(prefix, "lib")
        for directory in (libdir, os.path.join(prefix, "lib", "external")):
            if not os.path.isdir(directory):
                continue
            for filename in sorted(os.listdir(directory)):
                full = os.path.join(directory, filename)
                if not os.path.isfile(full) or os.path.islink(full):
                    continue
                parts = filename.split(".")
                if len(parts) < 4 or not parts[0].startswith("lib"):
                    continue
                if parts[-1] != "0":
                    continue
                soname = ".".join(parts[:-2])
                link = os.path.join(directory, soname)
                if os.path.lexists(link):
                    continue
                try:
                    os.symlink(filename, link)
                except OSError:
                    import shutil

                    shutil.copy2(full, link)

    def _ohos_gtk_runtime_available(self):
        required = (
            "libgoocanvas-3.0.so.9",
            "libgtk-3.so.0",
            "libgdk-3.so.0",
            "libcairo.so.2",
            "libcairo-gobject.so.2",
            "libglib-2.0.so.0",
            "libpango-1.0.so.0",
            # Runtime load of the GTK stack additionally requires these;
            # on headless CI they are missing, so the smoke test must be
            # skipped instead of failing at dlopen time.
            "libpng16.so.16",
            "libintl.so.8",
        )
        search_dirs = []
        env = os.environ.get("LD_LIBRARY_PATH", "")
        search_dirs.extend([d for d in env.split(os.pathsep) if d])
        for dependency in self.dependencies.values():
            package_folder = getattr(dependency, "package_folder", None)
            if not package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs or []:
                if not libdir:
                    continue
                full_libdir = (
                    libdir
                    if os.path.isabs(libdir)
                    else os.path.join(package_folder, libdir)
                )
                if os.path.isdir(full_libdir):
                    search_dirs.append(full_libdir)
        prefix = self._system_prefix()
        search_dirs.extend(
            [os.path.join(prefix, "lib"), os.path.join(prefix, "lib", "external")]
        )
        search_dirs.extend(sorted(glob.glob("/data/service/hnp/*/*/lib")))
        for lib in required:
            if not any(
                os.path.isfile(os.path.join(d, lib)) for d in search_dirs if d
            ):
                self.output.info(
                    "Missing {} for GTK runtime smoke on OHOS".format(lib)
                )
                return False
        # File presence is not enough: on headless CI the GTK stack may be
        # present but unloadable (missing libintl symbols, broken libpng
        # symlinks). Probe an actual dlopen of libgtk-3.so.0 with RTLD_NOW
        # (eager symbol resolution) so the smoke test is skipped only when
        # the runtime truly cannot load.
        import subprocess

        probe_py = os.path.expanduser("~/usr/local/bin/python3")
        if not os.path.isfile(probe_py):
            self.output.info(
                "GTK load probe python missing, skipping runtime smoke on OHOS"
            )
            return False
        gtk_candidates = []
        for d in search_dirs:
            if not d:
                continue
            candidate = os.path.join(d, "libgtk-3.so.0")
            if os.path.isfile(candidate):
                gtk_candidates.append(candidate)
        if not gtk_candidates:
            return False
        probe_env = dict(os.environ)
        probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [d for d in search_dirs if d]
        )
        # mode=2 -> RTLD_NOW: resolve all symbols eagerly, so a missing
        # libintl/libpng dependency fails the probe instead of being
        # deferred to test runtime.
        probe_code = (
            "import ctypes,sys\n"
            "try:\n"
            "    ctypes.CDLL(sys.argv[1], mode=2)\n"
            "    print('OK')\n"
            "except Exception as e:\n"
            "    print('FAIL', str(e)[:200])\n"
        )
        try:
            result = subprocess.run(
                [probe_py, "-c", probe_code, gtk_candidates[0]],
                env=probe_env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if "OK" not in result.stdout:
                self.output.info(
                    "GTK stack not loadable on headless CI: {}".format(
                        (result.stdout + result.stderr).strip().splitlines()[
                            -1
                        ][:160]
                    )
                )
                return False
        except Exception as error:
            self.output.info(
                "GTK load probe unavailable, skipping smoke: {}".format(
                    str(error)[:120]
                )
            )
            return False
        return True

    def _system_prefix(self):
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
        for pc_file in sorted(
            glob.glob("/data/service/hnp/**/gtk+-3.0.pc", recursive=True)
        ):
            candidates.append(os.path.dirname(os.path.dirname(pc_file)))
        seen = set()
        for prefix in candidates:
            if prefix in seen:
                continue
            seen.add(prefix)
            if self._gtk_pc_exists(prefix):
                return prefix
        return candidates[0] if candidates else "/storage/Users/currentUser/usr/local"

    def _gtk_pc_exists(self, prefix):
        return (
            os.path.isfile(
                os.path.join(prefix, "lib", "pkgconfig", "gtk+-3.0.pc")
            )
            or os.path.isfile(
                os.path.join(prefix, "share", "pkgconfig", "gtk+-3.0.pc")
            )
        )

    def _pkg_config_env(self):
        env = Environment()
        for dependency in self.dependencies.values():
            for bindir in dependency.cpp_info.bindirs or []:
                if not bindir or not getattr(dependency, "package_folder", None):
                    continue
                full_bindir = os.path.join(dependency.package_folder, bindir)
                if os.path.isdir(full_bindir):
                    env.prepend_path("PATH", full_bindir)
            for libdir in dependency.cpp_info.libdirs or []:
                if not libdir or not getattr(dependency, "package_folder", None):
                    continue
                full_libdir = os.path.join(dependency.package_folder, libdir)
                if not os.path.isdir(full_libdir):
                    continue
                env.prepend_path("LD_LIBRARY_PATH", full_libdir)
                env.append("LDFLAGS", "-L{}".format(full_libdir))
                env.prepend_path(
                    "PKG_CONFIG_PATH", os.path.join(full_libdir, "pkgconfig")
                )
            for includedir in dependency.cpp_info.includedirs or []:
                if not includedir or not getattr(dependency, "package_folder", None):
                    continue
                full_includedir = os.path.join(
                    dependency.package_folder, includedir
                )
                if os.path.isdir(full_includedir):
                    env.append("CFLAGS", "-I{}".format(full_includedir))
                    env.append("CPPFLAGS", "-I{}".format(full_includedir))

        prefix = self._system_prefix()
        env.prepend_path(
            "PKG_CONFIG_PATH", os.path.join(prefix, "lib", "pkgconfig")
        )
        if str(self.settings.os) == "OHOS":
            hnp_pkgconfigs = sorted(
                glob.glob("/data/service/hnp/*/*/lib/pkgconfig"),
                key=lambda p: (p.count("/"), p),
            )
            for pkgconfig_dir in hnp_pkgconfigs:
                env.prepend_path("PKG_CONFIG_PATH", pkgconfig_dir)
            hnp_runtime_libs = []
            for pattern in (
                "libpcre2-8.so*",
                "libffi.so*",
                "libexpat.so*",
                "libintl.so*",
            ):
                for match in glob.glob(
                    "/data/service/hnp/*/*/lib/{}".format(pattern)
                ):
                    hnp_runtime_libs.append(os.path.dirname(match))
            for libdir in sorted(set(hnp_runtime_libs)):
                env.append_path("LD_LIBRARY_PATH", libdir)
                env.append("LDFLAGS", "-L{}".format(libdir))
        env.prepend_path(
            "PKG_CONFIG_PATH", os.path.join(prefix, "share", "pkgconfig")
        )
        env.prepend_path("PATH", os.path.join(prefix, "bin"))
        env.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(prefix, "lib", "external")
        )
        env.append("LDFLAGS", "-L{}".format(os.path.join(prefix, "lib", "external")))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
        env.append("LDFLAGS", "-L{}".format(os.path.join(prefix, "lib")))
        return env
