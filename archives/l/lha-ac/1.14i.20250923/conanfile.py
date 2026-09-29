#!/usr/bin/env python3
"""Conan recipe for lha-ac 1.14i.20250923.

lha-ac is the Autotools fork of LHa for UNIX. The pinned upstream archive is a
plain Git checkout: it ships ``configure.ac`` / ``Makefile.am`` but no generated
Autotools files. The OHOS build workers do not ship ``automake``/``aclocal``, so
the pinned, reproducible ``autoreconf -i -f`` output is carried in
``prebuilt-autotools.tar.gz.b64`` and unpacked into the source tree instead of
regenerating it on the target. Upstream's own functional suite
(``tests/lha-test``) is executed as the official test entry point.

The payload is base64 text rather than a committed ``.tar.gz`` because the CI
workers re-apply every pull request as a unified diff, and GitCode's ``.diff``
endpoint omits binary patch data, which makes any added binary file
unapplicable (``git apply``: missing binary patch data).
"""
import os
import stat
import base64
import hashlib

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LhaAcConan(ConanFile):
    name = "lha-ac"
    version = "1.14i.20250923"
    description = "LHa for UNIX, the Autotools fork of the LHA archiver"
    license = "LHa-license"
    homepage = "https://github.com/jca02266/lha"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("lha", "archiver", "compression", "autotools", "harmonyos")
    package_type = "application"
    languages = "C"

    settings = "os", "compiler", "build_type", "arch"

    # Base64 text payload carrying the deterministic tar.gz of the pinned
    # `autoreconf -i -f` output. Keep this digest in sync with the file.
    _PREBUILT_PAYLOAD = "prebuilt-autotools.tar.gz.b64"
    _PREBUILT_PAYLOAD_SHA256 = (
        "95e1ec431aee64698de0181ef6d539f0052ee1552fbd2dcb7605b5027cce3058"
    )

    # Files produced by `autoreconf -i -f`. Their timestamps
    # are refreshed after unpacking so make never tries to re-run the missing
    # automake/aclocal tooling on the workers.
    _GENERATED_FILES = (
        "aclocal.m4",
        "compile",
        "config.guess",
        "config.h.in",
        "config.sub",
        "configure",
        "depcomp",
        "install-sh",
        "Makefile.in",
        "missing",
        "man/Makefile.in",
        "olddoc/Makefile.in",
        "src/Makefile.in",
        "tests/Makefile.in",
    )

    def export_sources(self):
        export_conandata_patches(self)
        # OHOS workers have autoconf but no automake/aclocal, so the pinned
        # autoreconf output is shipped inside the recipe.
        copy(
            self,
            self._PREBUILT_PAYLOAD,
            src=self.recipe_folder,
            dst=self.export_sources_folder,
        )

    def validate(self):
        os_name = str(self.settings.os)
        if os_name not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lha-ac adaptation currently supports Linux and OHOS"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            filename="lha-ac-1.14i.20250923.tar.gz",
            strip_root=True,
            **self.conan_data["sources"],
        )

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-ohos",
                    "--host=aarch64-unknown-linux-ohos",
                    "--with-tmp-file=./lhXXXXXX",
                ]
            )
        toolchain.generate()

        if str(self.settings.os) == "OHOS":
            # HarmonyOS mktemp -d can create a directory with broken
            # permissions, which makes config.status fail before configure
            # starts. Force autoconf's AS_TMPDIR fallback to the mkdir path.
            wrapper_dir = os.path.join(self.build_folder, ".hmos_fix")
            os.makedirs(wrapper_dir, exist_ok=True)
            wrapper = os.path.join(wrapper_dir, "mktemp")
            with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("#!/bin/sh\nexit 1\n")
            os.chmod(wrapper, os.stat(wrapper).st_mode | stat.S_IEXEC)

            env = Environment()
            env.prepend_path("PATH", wrapper_dir)
            env.vars(self).save_script("hmos_mktemp")

    def _unpack_prebuilt_autotools(self):
        payload = os.path.join(self.source_folder, self._PREBUILT_PAYLOAD)
        with open(payload, "rb") as handle:
            encoded = handle.read()

        digest = hashlib.sha256(encoded).hexdigest()
        if digest != self._PREBUILT_PAYLOAD_SHA256:
            raise ConanInvalidConfiguration(
                "prebuilt autotools payload digest mismatch: " + digest
            )

        archive = os.path.join(self.build_folder, "prebuilt-autotools.tar.gz")
        with open(archive, "wb") as handle:
            handle.write(base64.b64decode(encoded))
        self.run(f'tar xzf "{archive}" -C "{self.source_folder}"')
        for relative in self._GENERATED_FILES:
            generated = os.path.join(self.source_folder, relative)
            if os.path.exists(generated):
                os.utime(generated, None)

    def _patch_ohos_config_sub(self):
        config_sub_path = os.path.join(self.source_folder, "config.sub")
        with open(config_sub_path, encoding="utf-8") as config_sub_file:
            config_sub = config_sub_file.read()

        if "ohos" in config_sub:
            return

        os_needle = "| android* | bsd*"
        os_replacement = "| android* | ohos* | bsd*"
        os_new_needle = "\t| android* \\"
        os_new_replacement = "\t| android* \\\n\t| ohos* \\"
        if os_needle in config_sub:
            config_sub = config_sub.replace(os_needle, os_replacement, 1)
        elif os_new_needle in config_sub:
            config_sub = config_sub.replace(os_new_needle, os_new_replacement, 1)
        else:
            raise ConanInvalidConfiguration(
                "unexpected config.sub OS validation list; cannot add OHOS"
            )

        kernel_needle = "linux-android* | linux-newlib*"
        kernel_replacement = "linux-android* | linux-ohos* | linux-newlib*"
        kernel_new_needle = "linux-android*- | linux-dietlibc*-"
        kernel_new_replacement = "linux-android*- | linux-ohos*- | linux-dietlibc*-"
        if kernel_needle in config_sub:
            config_sub = config_sub.replace(kernel_needle, kernel_replacement, 1)
        elif kernel_new_needle in config_sub:
            config_sub = config_sub.replace(
                kernel_new_needle, kernel_new_replacement, 1
            )
        else:
            raise ConanInvalidConfiguration(
                "unexpected config.sub kernel-OS validation list; cannot add OHOS"
            )

        with open(config_sub_path, "w", encoding="utf-8") as config_sub_file:
            config_sub_file.write(config_sub)

    def _clean_upstream_test_artifacts(self):
        # lha-test18 intentionally leaves read-only scratch directories behind.
        # A reused Conan build directory then carries their modes into the next
        # test run, so reset the generated scratch tree before each suite.
        tests_dir = os.path.join(self.build_folder, "tests")
        if not os.path.isdir(tests_dir):
            return
        self.run(
            "find . -maxdepth 1 -name 'test-tmp*' -exec chmod -R u+rwx {} +;"
            " rm -rf test-tmp*",
            cwd=tests_dir,
        )

    def build(self):
        autotools = Autotools(self)
        self._unpack_prebuilt_autotools()
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._patch_ohos_config_sub()

        old_umask = os.umask(0o022)
        old_home = os.environ.get("HOME")
        sandbox_home = os.path.join(self.build_folder, "upstream-test-home")
        os.makedirs(sandbox_home, exist_ok=True)
        os.environ["HOME"] = sandbox_home
        try:
            autotools.configure()
            # HarmonyOS does not support the make jobserver FIFO.
            autotools.make(args=["-j1"])
            # Upstream official entry point: runs the default lha-test set
            # (lha-test1..20 minus the two cases commented out upstream).
            # HarmonyOS HMDFS reports a fixed 2771 mode for every directory and
            # ignores chmod(), so the archive records 2771 for the scratch
            # directories. lha restores that mode through mkdir(2), which the
            # process umask still masks: with umask 022 the restored mode becomes
            # 2751 and upstream's mode-restoration assertions fail. Run the
            # upstream suite with an empty umask so the restored mode matches the
            # mode that was actually stored.
            os.umask(0)
            self._clean_upstream_test_artifacts()
            autotools.make(target="check")
            # Extended upstream run adds the 2G/4G archive integrity cases
            # (lha-test51/lha-test52) that upstream gates behind `all`.
            self._clean_upstream_test_artifacts()
            config_shell = os.environ.get(
                "CONFIG_SHELL", "/data/service/hnp/bin/bash"
            )
            self.run(
                f'"{config_shell}" ./lha-test all',
                cwd=os.path.join(self.build_folder, "tests"),
            )
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home
            os.umask(old_umask)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "lha-ac")
        self.cpp_info.set_property("cmake_target_name", "lha-ac::lha-ac")
