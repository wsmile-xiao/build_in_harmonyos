#!/usr/bin/env python3
"""Conan test_package - libnm 1.52.1 L1 test.

Compiles and runs a C program that uses the real libnm public API
(nm_utils_version / nm_utils_uuid_generate / nm_simple_connection_new /
nm_setting_connection_new / nm_setting_wired_new / nm_setting_ip4_config_new /
nm_ip_address_new / nm_connection_add_setting / nm_connection_normalize /
nm_connection_verify / nm_connection_to_dbus /
nm_simple_connection_new_from_dbus / nm_client_get_type), verifying headers,
linking and runtime behaviour without requiring a running NetworkManager
daemon or a system D-Bus.

The connection round trip is the interesting part for this port: it runs the
same setting validators and the same GVariant (de)serialisation that nmcli
and the daemon use, so it exercises the code the OHOS adaptation touched.

The header is spelled <NetworkManager.h> because upstream installs the headers
into <prefix>/include/libnm and points the include path at that directory
itself ("Cflags: -I${includedir}/libnm" in libnm.pc); the recipe declares the
same directory through cpp_info.includedirs.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibnmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    exports_sources = "CMakeLists.txt", "test_libnm.c"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # the test source also uses glib directly (g_printerr/g_object_set)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ── OHOS runtime helpers ──────────────────────────────────────────────
    #
    # The OHOS (musl-based) dynamic loader of this SDK refuses to resolve a
    # DT_NEEDED entry whose file is a symbolic link. It reports
    # "Error loading shared library libgnutls.so.30: (needed by ...)" with an
    # EMPTY strerror() - the file is right there, the loader just will not
    # follow the link - and the process dies with exit status 127.
    #
    # Several runtime dependencies of libnm are packaged with symlinked
    # sonames (gnutls, libtasn1, libgcrypt, libgpg-error, libidn2, libpsl),
    # so a plain `LD_LIBRARY_PATH=<dep libdirs>` run fails even though the
    # build itself succeeded. Materialising the targets of those links into a
    # private directory removes the symlinks from the resolution path.
    #
    # This touches nothing outside this package's own build folder.

    def _ohos_dependency_libdirs(self):
        """Absolute libdir of every dependency in the graph, no duplicates."""
        libdirs = []
        for dependency in self.dependencies.values():
            try:
                declared = list(dependency.cpp_info.libdirs or [])
            except Exception:
                continue
            for libdir in declared:
                if not libdir:
                    continue
                if not os.path.isabs(libdir):
                    libdir = os.path.join(str(dependency.package_folder), libdir)
                if os.path.isdir(libdir) and libdir not in libdirs:
                    libdirs.append(libdir)
        return libdirs

    def _ohos_symlinked_libs(self):
        """Return {name: real_path} for every symlinked .so* in the deps."""
        found = {}
        for libdir in self._ohos_dependency_libdirs():
            try:
                names = os.listdir(libdir)
            except OSError:
                continue
            for name in names:
                if ".so" not in name:
                    continue
                path = os.path.join(libdir, name)
                if not os.path.islink(path):
                    continue
                real = os.path.realpath(path)
                if os.path.isfile(real):
                    found[name] = real
        return found

    def _materialize_ohos_runtime_libs(self):
        runtime_dir = os.path.join(self.build_folder, "ohos-runtime-lib")
        os.makedirs(runtime_dir, exist_ok=True)
        materialized = []
        for name, real in sorted(self._ohos_symlinked_libs().items()):
            destination = os.path.join(runtime_dir, name)
            if os.path.exists(destination):
                continue
            shutil.copy2(real, destination)
            materialized.append(name)
        if materialized:
            self.output.info(
                "OHOS consumer runtime: materialised %d symlinked .so file(s) "
                "into %s: %s" % (len(materialized), runtime_dir, ", ".join(materialized))
            )
        return runtime_dir

    def _apply_ohos_runtime_environment(self):
        """Put the de-symlinked directory FIRST on LD_LIBRARY_PATH.

        The order matters: the dependency libdirs are prepended by the
        conanrun environment and still contain the symlinks, so they must not
        win the lookup. LD_LIBRARY_PATH is set here explicitly (proven to be
        honoured by this loader) instead of relying on env="conanrun".
        """
        runtime_dir = self._materialize_ohos_runtime_libs()
        paths = [runtime_dir] + self._ohos_dependency_libdirs()
        current = os.environ.get("LD_LIBRARY_PATH", "")
        if current:
            paths.extend(part for part in current.split(":") if part)
        merged = ":".join(paths)
        os.environ["LD_LIBRARY_PATH"] = merged
        os.environ.pop("LD_PRELOAD", None)
        self.output.info("OHOS consumer LD_LIBRARY_PATH=%s" % merged)
        return merged

    def test(self):
        executable = os.path.join(self.cpp.build.bindirs[0], "test_libnm")
        if str(self.settings.os) == "OHOS":
            self._apply_ohos_runtime_environment()
        if not can_run(self):
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT="
                + json.dumps({"executed": False, "passed": False, "discovered": 1,
                              "passedCount": 0,
                              "command": os.path.basename(executable)}, ensure_ascii=False)
            )
            raise Exception("libnm test consumer is not runnable on this configuration")
        try:
            # no env="conanrun" on OHOS: LD_LIBRARY_PATH is composed above so
            # that the de-symlinked directory is searched first.
            self.run(
                f'"{executable}"',
                cwd=self.build_folder,
                env=None if str(self.settings.os) == "OHOS" else "conanrun",
            )
        except Exception:
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT="
                + json.dumps({"executed": True, "passed": False, "discovered": 1,
                              "passedCount": 0,
                              "command": os.path.basename(executable)}, ensure_ascii=False)
            )
            raise
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT="
            + json.dumps({"executed": True, "passed": True, "discovered": 1,
                          "passedCount": 1,
                          "command": os.path.basename(executable)}, ensure_ascii=False)
        )
