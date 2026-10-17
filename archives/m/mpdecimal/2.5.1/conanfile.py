#!/usr/bin/env python3
"""Conan recipe for mpdecimal 2.5.1 (C/C++ decimal floating point library).

mpdecimal implements the General Decimal Arithmetic Specification and is
the reference implementation behind Python's `decimal` module.

Upstream: https://www.bytereef.org/mpdecimal/
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MpdecimalConan(ConanFile):
    name = "mpdecimal"
    version = "2.5.1"
    description = "General Decimal Arithmetic Library (libmpdec/libmpdec++)"
    license = "BSD-2-Clause"
    homepage = "https://www.bytereef.org/mpdecimal/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    topics = ("decimal", "arbitrary-precision", "floating-point")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {"shared": False, "fPIC": True}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mpdecimal/2.5.1 is validated only for Linux and OHOS"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder="src")

    def _ohos_tool(self, name):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        c_compiler = compiler_executables.get("c")
        if c_compiler and os.path.isabs(c_compiler):
            return os.path.join(os.path.dirname(c_compiler), name)
        return name

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        # mpdecimal's configure only knows --enable-shared (default: yes);
        # static builds are always produced alongside when shared is on.
        if self.options.shared:
            toolchain.configure_args.append("--enable-shared")
        else:
            toolchain.configure_args.append("--disable-shared")
        if self.settings.os == "OHOS":
            toolchain.configure_args.extend(
                [
                    f"AR={self._ohos_tool('llvm-ar')}",
                    f"LD={self._ohos_tool('ld.lld')}",
                    f"RANLIB={self._ohos_tool('llvm-ranlib')}",
                    f"NM={self._ohos_tool('llvm-nm')}",
                    f"OBJDUMP={self._ohos_tool('llvm-objdump')}",
                    f"STRIP={self._ohos_tool('llvm-strip')}",
                ]
            )
        toolchain.generate()

    def build(self):
        # mpdecimal's hand-written Makefiles have no VPATH support:
        # configure and make must run inside the source tree.
        autotools = Autotools(self)

        # configure: run in the source folder (in-tree build)
        self.run(
            '"{}/configure" {}'.format(self.source_folder, autotools._configure_args),
            cwd=self.source_folder,
        )

        make_cmd = 'make -C "{}" -j1'.format(self.source_folder)
        self.run(make_cmd, cwd=self.source_folder)

        if can_run(self):
            # Upstream test suite (L1c): make check.
            # gettests.sh uses `wget -nv`, but the HarmonyOS wget does not
            # support -nv (4.0.1 notes, issue #5). Fetch the official decTest
            # data with curl instead and pre-populate tests/testdata, so the
            # scripts skip the download step.
            # gettests.sh skips downloading when testdata/add.decTest exists;
            # tests++/gettests.sh reuses tests/testdata via cp -Rp.
            testdata = os.path.join(self.source_folder, "tests", "testdata")
            if not os.path.exists(os.path.join(testdata, "add.decTest")):
                try:
                    # Use the system curl by absolute path: the conan buildenv
                    # prepends ~/usr/local/bin to PATH, whose curl (a GNU
                    # cross-build) cannot find the OHOS CA bundle and fails
                    # with "unable to get local issuer certificate".
                    self.run(
                        '/usr/bin/curl -fsSL --connect-timeout 20 --max-time 120 '
                        '-o "{}/dectest.zip" '
                        'https://speleotrove.com/decimal/dectest.zip'.format(
                            os.path.join(self.source_folder, "tests")
                        ),
                        cwd=self.source_folder,
                    )
                    self.run(
                        'unzip -qq -o "{}/dectest.zip" -d "{}"'.format(
                            os.path.join(self.source_folder, "tests"),
                            testdata,
                        ),
                        cwd=self.source_folder,
                    )
                except Exception as exc:  # network unavailable
                    self.output.warning(
                        "Cannot fetch official decTest data ({}); "
                        "falling back to bundled testdata".format(exc)
                    )
            # OHOS's hardened musl loader ignores LD_LIBRARY_PATH entries
            # for non-whitelisted paths and the inherited value (with a
            # whitespace-corrupted entry) breaks library resolution entirely.
            # Emptying it makes the loader use its default search path
            # (/etc/ld-musl-aarch64.path), which contains /system/lib64 where
            # libc++_shared.so lives. Upstream runshort.sh then runs the
            # static-library test sections (shared sections are skipped
            # automatically in a --disable-shared build).
            self.run(
                'LD_LIBRARY_PATH= make -C "{}" check -j1'.format(self.source_folder),
                cwd=self.source_folder,
            )

    def package(self):
        # DESTDIR-based install into the conan package folder (prefix is
        # already "/" from the toolchain, so DESTDIR lands files directly
        # under package_folder/{include,lib}).
        self.run(
            'make -C "{}" install DESTDIR="{}"'.format(
                self.source_folder, self.package_folder
            ),
            cwd=self.source_folder,
        )

        licenses_dir = os.path.join(self.package_folder, "licenses")
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=licenses_dir,
            keep_path=False,
        )

    def package_info(self):
        # libmpdec (C) + libmpdec++ (C++); both are installed by the same
        # recipe regardless of the shared/static option.
        self.cpp_info.libs = ["mpdec", "mpdec++"]
        self.cpp_info.set_property("cmake_file_name", "mpdecimal")
        self.cpp_info.set_property("cmake_target_name", "mpdecimal::mpdecimal")
        self.cpp_info.set_property("pkg_config_name", "mpdec")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
