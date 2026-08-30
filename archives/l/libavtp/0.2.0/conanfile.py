#!/usr/bin/env python3
"""Conan recipe for libavtp 0.2.0.

libavtp is a small C library for building and parsing AVTP (IEEE 1722)
packet formats.  The upstream project uses Meson; the recipe obtains the
versioned Meson runner from the OpenHarmony Conan tool repository.
"""

import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibavtpConan(ConanFile):
    name = "libavtp"
    version = "0.2.0"
    description = "C library for AVTP packetization and parsing"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Avnu/libavtp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tests": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "tests": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libavtp requires a POSIX-like target (Linux or OHOS), not {self.settings.os}"
            )

    def build_requirements(self):
        # Meson is a published Conan build tool in ohpcd; use the tool package
        # instead of relying on a worker-global executable or vendored runner.
        self.tool_requires("meson/1.11.0")
        if bool(self.options.tests):
            # cmocka is used only by the upstream unit-test executables and is
            # deliberately kept out of the consumer's link requirements.
            self.test_requires("cmocka/2.0.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Upstream's meson.build uses dependency('cmocka') for its tests.
        # PkgConfigDeps gives Meson a generated cmocka.pc; repair the generated
        # view below because the remote package's pc file can retain a stale
        # build-cache prefix.
        PkgConfigDeps(self).generate()

        toolchain = MesonToolchain(self)
        toolchain.project_options["default_library"] = (
            "shared" if bool(self.options.shared) else "static"
        )
        toolchain.project_options["tests"] = (
            "enabled" if bool(self.options.tests) else "disabled"
        )
        toolchain.generate()
        self._inject_archive_tools()
        self._repair_cmocka_pkgconfig()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        with self._meson_environment().vars(self).apply():
            meson.configure()
            self.run(f'meson compile -C "{self.build_folder}" -j1')

            if bool(self.options.tests):
                test_targets = (
                    "test-avtp test-stream test-aaf test-crf "
                    "test-cvf test-rvf test-ieciidc"
                )
                self.run(
                    f'meson compile -C "{self.build_folder}" -j1 {test_targets}'
                )
                if cross_building(self):
                    self.output.warning(
                        "Skipping executable upstream tests during a cross build; "
                        "the seven test targets were compiled by Meson."
                    )
                else:
                    # Targets are compiled explicitly so --no-rebuild verifies
                    # the exact binaries produced by the preceding command.
                    self.run(
                        f'meson test -C "{self.build_folder}" --no-rebuild '
                        "--print-errorlogs --timeout-multiplier=16"
                    )

    def package(self):
        with self._meson_environment().vars(self).apply():
            Meson(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if bool(self.options.shared):
            self._materialize_shared_aliases()
            self._sign_shared_libraries()

    def package_info(self):
        self.cpp_info.libs = ["avtp"]
        self.cpp_info.set_property("cmake_file_name", "libavtp")
        self.cpp_info.set_property("cmake_target_name", "libavtp::avtp")
        self.cpp_info.set_property("pkg_config_name", "avtp")

    def _meson_environment(self):
        """Return a Conan-scoped environment for Meson and pkg-config."""
        environment = Environment()
        environment.prepend_path("PKG_CONFIG_PATH", self.generators_folder)

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        if bindir and os.path.isdir(bindir):
            environment.prepend_path("PATH", bindir)
        return environment

    def _inject_archive_tools(self):
        """Add llvm-ar/llvm-ranlib when the profile omits Meson's names."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        ar = executables.get("ar") or (os.path.join(bindir, "llvm-ar") if bindir else "")
        ranlib = executables.get("ranlib") or (
            os.path.join(bindir, "llvm-ranlib") if bindir else ""
        )

        for filename in ("conan_meson_cross.ini", "conan_meson_native.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not ar or not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content or "\nar =" in content:
                continue
            insertion = "[binaries]\nar = %r\n" % ar
            if ranlib:
                insertion += "ranlib = %r\n" % ranlib
            content = content.replace("[binaries]\n", insertion, 1)
            with open(machine_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _dependency_package_folder(self, name):
        for context in ("test", "build", "host"):
            dependencies = getattr(self.dependencies, context, None)
            if dependencies is None:
                continue
            try:
                dependency = dependencies[name]
            except (KeyError, TypeError):
                continue
            package_folder = getattr(dependency, "package_folder", "")
            if package_folder:
                return package_folder
        return ""

    def _repair_cmocka_pkgconfig(self):
        if not bool(self.options.tests):
            return
        package_folder = self._dependency_package_folder("cmocka")
        if not package_folder:
            raise ConanException("cmocka test dependency has no package folder")

        pc_file = os.path.join(self.generators_folder, "cmocka.pc")
        lines = [
            f"prefix={package_folder}",
            "libdir=${prefix}/lib",
            "includedir=${prefix}/include",
            "",
            "Name: cmocka",
            "Description: The cmocka unit testing library",
            "Version: 2.0.2",
            "Libs: -L${libdir} -lcmocka",
            "Cflags: -I${includedir}",
            "",
        ]
        # Always write the small canonical file.  This avoids inheriting an
        # absolute path from either the remote package's own pc file or a
        # previous local build directory.
        with open(pc_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))

    def _materialize_shared_aliases(self):
        library_dir = os.path.join(self.package_folder, "lib")
        source = os.path.join(library_dir, "libavtp.so.0.2.0")
        aliases = (
            os.path.join(library_dir, "libavtp.so.0"),
            os.path.join(library_dir, "libavtp.so"),
        )
        if not os.path.isfile(source) or os.path.islink(source):
            raise ConanException(f"installed libavtp shared object is missing: {source}")
        for alias in aliases:
            if os.path.lexists(alias):
                os.unlink(alias)
            shutil.copy2(source, alias)

    def _resolve_ohos_tool(self, name):
        """Resolve an OHOS post-processing tool from Conan/profile paths."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = executables.get(name) or executables.get(name.replace("-", "_"))
        compiler = executables.get("c") or executables.get("cpp") or ""
        compiler_dir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        candidates = [configured, shutil.which(name)]
        if compiler_dir:
            candidates.append(os.path.join(compiler_dir, name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def _sign_shared_libraries(self):
        if str(self.settings.os) != "OHOS":
            return
        objcopy = self._resolve_ohos_tool("llvm-objcopy")
        signer = self._resolve_ohos_tool("binary-sign-tool")
        missing = [name for name, path in (
            ("llvm-objcopy", objcopy), ("binary-sign-tool", signer)
        ) if not path]
        if missing:
            raise ConanException(
                "OHOS shared-library packaging requires " + ", ".join(missing)
            )

        for path in sorted(glob.glob(os.path.join(self.package_folder, "lib", "libavtp.so*"))):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            signed_path = path + ".signed"
            if os.path.exists(signed_path):
                os.remove(signed_path)
            mode = os.stat(path).st_mode
            # llvm-objcopy returns success when .codesign is absent; no error is
            # ignored, so a failed removal or signing operation stops packaging.
            self.run(shlex.join([objcopy, "--remove-section", ".codesign", path]))
            self.run(shlex.join([
                signer, "sign", "-inFile", path, "-outFile", signed_path,
                "-selfSign", "1",
            ]))
            os.replace(signed_path, path)
            os.chmod(path, mode)
