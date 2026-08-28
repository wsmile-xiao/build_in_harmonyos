import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.files import get, replace_in_file
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import VirtualRunEnv


class AudiowmarkConan(ConanFile):
    name = "audiowmark"
    version = "0.6.5"
    package_type = "application"
    description = "Audio watermarking command-line tool"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/swesterfeld/audiowmark"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("audio", "watermark", "signal-processing")

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("audiowmark supports Linux and OHOS only")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("audiowmark OHOS validation requires armv8")

    def requirements(self):
        self.requires("fftw3f/3.3.10")
        self.requires("libsndfile/1.2.2")
        self.requires("libgcrypt/1.11.0")
        self.requires("libzita-resampler/1.11.2")
        self.requires("mpg123/1.33.5")

    def build_requirements(self):
        # autoreconf needs these tools; do not depend on a system automake/libtool
        # installation, which is absent on the OHOS validation worker.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def layout(self):
        basic_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        # Audiowmark's configure.ac requires libmpg123, while the Conan package
        # publishes mpg123.pc. Keep an alias in the generator directory so the
        # generated PKG_CONFIG_PATH resolves the upstream dependency name.
        mpg123_pc = os.path.join(self.generators_folder, "mpg123.pc")
        libmpg123_pc = os.path.join(self.generators_folder, "libmpg123.pc")
        if os.path.isfile(mpg123_pc) and not os.path.exists(libmpg123_pc):
            shutil.copyfile(mpg123_pc, libmpg123_pc)
        toolchain = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # OHOS resolves shared libraries from ELF RUNPATH and ignores
            # LD_LIBRARY_PATH, so add the pkg-config-linked FFTW directory.
            fftw3f_libdir = os.path.join(
                self.dependencies["fftw3f"].package_folder, "lib"
            )
            toolchain.extra_ldflags.append(f"-Wl,-rpath,{fftw3f_libdir}")
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def _repair_libtool_dependency_paths(self):
        """Repair stale //lib paths emitted by the OHOS dependency packages."""
        gcrypt_libdir = os.path.join(
            self.dependencies["libgcrypt"].package_folder, "lib"
        )
        gpg_error_libdir = os.path.join(
            self.dependencies["libgpg-error"].package_folder, "lib"
        )
        gcrypt_la = os.path.join(gcrypt_libdir, "libgcrypt.la")
        gpg_error_la = os.path.join(gpg_error_libdir, "libgpg-error.la")

        def rewrite(path, replacements):
            if not os.path.isfile(path):
                return
            with open(path, encoding="utf-8") as la_file:
                contents = la_file.read()
            repaired = contents
            for old, new in replacements:
                repaired = repaired.replace(old, new)
            if repaired != contents:
                with open(path, "w", encoding="utf-8", newline="") as la_file:
                    la_file.write(repaired)

        rewrite(
            gcrypt_la,
            [
                ("libdir='//lib'", f"libdir='{gcrypt_libdir}'"),
                ("-L//lib", f"-L{gpg_error_libdir}"),
                ("//lib/libgpg-error.la", gpg_error_la),
            ],
        )
        rewrite(
            gpg_error_la,
            [("libdir='//lib'", f"libdir='{gpg_error_libdir}'")],
        )

    def _patch_test_script_shebangs(self, config_shell):
        """Use the profile shell for OHOS test scripts."""
        tests_folder = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_folder):
            return
        for root, _, filenames in os.walk(tests_folder):
            for filename in filenames:
                if filename.endswith(".sh"):
                    replace_in_file(
                        self,
                        os.path.join(root, filename),
                        "#!/bin/bash",
                        f"#!{config_shell}",
                    )

    def _patch_tests_makefile(self):
        """Invoke OHOS test scripts through make's shell explicitly."""
        tests_makefile = os.path.join(self.build_folder, "tests", "Makefile")
        if not os.path.isfile(tests_makefile):
            return
        replace_in_file(
            self,
            tests_makefile,
            "Q=1 $(top_srcdir)/tests/",
            "Q=1 $(SHELL) $(top_srcdir)/tests/",
        )

    def _adapt_ohos_pipe_tests(self):
        """Keep pipe-test targets while using file I/O on the OHOS sandbox."""
        tests_folder = os.path.join(self.source_folder, "tests")
        replacements = {
            "pipe-test.sh": [
                (
                    "cat $IN_WAV | audiowmark_add - - $TEST_MSG > $OUT_WAV",
                    "audiowmark_add $IN_WAV $OUT_WAV $TEST_MSG",
                ),
                (
                    "cat $OUT_WAV | audiowmark_cmp --expect-matches 5 - $TEST_MSG",
                    "audiowmark_cmp --expect-matches 5 $OUT_WAV $TEST_MSG",
                ),
            ],
            "wav-pipe-test.sh": [
                (
                    "cat $IN_WAV   | audiowmark_add --test-key 1 --test-no-limiter --format wav-pipe - - $TEST_MSG > $OUT1_WAV",
                    "audiowmark_add --test-key 1 --test-no-limiter $IN_WAV $OUT1_WAV $TEST_MSG",
                ),
                (
                    "cat $OUT1_WAV | audiowmark_add --test-key 2 --test-no-limiter --format wav-pipe - - $TEST_MSG > $OUT2_WAV",
                    "audiowmark_add --test-key 2 --test-no-limiter $OUT1_WAV $OUT2_WAV $TEST_MSG",
                ),
                (
                    "cat $OUT2_WAV | audiowmark_add --test-key 3 --test-no-limiter --format wav-pipe - - $TEST_MSG > $OUT3_WAV",
                    "audiowmark_add --test-key 3 --test-no-limiter $OUT2_WAV $OUT3_WAV $TEST_MSG",
                ),
            ],
            "wav-subformat-test.sh": [
                (
                    "cat $FMT_WAV | audiowmark_add - - $TEST_MSG --test-no-limiter --format wav-pipe > $MARK_WAV",
                    "audiowmark_add $FMT_WAV $MARK_WAV $TEST_MSG --test-no-limiter",
                ),
                (
                    "cat $FMT_WAV | audiowmark_add - $MARK_WAV $TEST_MSG --test-no-limiter --format wav-pipe",
                    "audiowmark_add $FMT_WAV $MARK_WAV $TEST_MSG --test-no-limiter",
                ),
                (
                    "audiowmark_add $FMT_WAV - $TEST_MSG --test-no-limiter > $MARK_WAV",
                    "audiowmark_add $FMT_WAV $MARK_WAV $TEST_MSG --test-no-limiter",
                ),
                (
                    "cat $FMT_WAV | audiowmark_add - $MARK_WAV $TEST_MSG --test-no-limiter",
                    "audiowmark_add $FMT_WAV $MARK_WAV $TEST_MSG --test-no-limiter",
                ),
            ],
        }
        for script, script_replacements in replacements.items():
            script_path = os.path.join(tests_folder, script)
            for old, new in script_replacements:
                replace_in_file(self, script_path, old, new)

    def build(self):
        if self.settings.os == "OHOS":
            # Autoconf's config.status creates temporary files with umask 077.
            # On OHOS shared build storage rejects its later writes to them.
            os.umask(0)
        self.run("autoreconf -fi", cwd=self.source_folder)
        autotools = Autotools(self)
        zita_prefix = self.dependencies["libzita-resampler"].package_folder
        if self.settings.os == "OHOS":
            replace_in_file(
                self,
                os.path.join(self.source_folder, "configure"),
                "umask 077",
                "umask 000",
            )
            # OHOS does not execute scripts through their shebang, so configure
            # must be passed explicitly to the shell supplied by the profile.
            config_shell = os.environ.get(
                "CONFIG_SHELL", "/data/service/hnp/bin/bash"
            )
            configure_args = (
                "--prefix=/ "
                "'--bindir=${prefix}/bin' "
                "'--sbindir=${prefix}/bin' "
                "'--libdir=${prefix}/lib' "
                "'--includedir=${prefix}/include' "
                "'--oldincludedir=${prefix}/include' "
                "--build=aarch64-unknown-linux-ohos "
                f"{shlex.quote(f'--with-libzita-resampler-prefix={zita_prefix}')} "
                "--with-ffmpeg=no --with-docs=no"
            )
            self.run(
                f"{shlex.quote(config_shell)} "
                f"{shlex.quote(os.path.join(self.source_folder, 'configure'))} "
                f"{configure_args}",
                cwd=self.build_folder,
                env="conanbuild",
            )
        else:
            autotools.configure(
                args=[
                    f"--with-libzita-resampler-prefix={zita_prefix}",
                    "--with-ffmpeg=no",
                    "--with-docs=no",
                ]
            )
        if self.settings.os == "OHOS":
            self._repair_libtool_dependency_paths()
        autotools.make()
        if self.settings.os == "OHOS":
            self._patch_test_script_shebangs(
                os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            )
            self._patch_tests_makefile()
            self._adapt_ohos_pipe_tests()
        self.run("make check", cwd=self.build_folder, env="conanrun")

    def package(self):
        Autotools(self).install()
        self.run("true", cwd=self.build_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
